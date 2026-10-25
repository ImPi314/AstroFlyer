"""
Integration across force-model boundaries.

The SRP acceleration has a kink wherever the satellite enters or leaves the
penumbra or umbra, and NRLMSISE-00 density jumps at fixed altitudes and at
UTC midnight (its day of year is an integer). An adaptive integrator that
steps across a kink or jump loses several orders of accuracy there (metres per
day on Molniya and GTO). Like Orekit's eclipse detectors, we stop the
integration at each boundary and restart from the exact crossing, so no step
ever straddles one.
"""

import math

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import OptimizeResult

from . import forces
from .ephemeris import get_ephemeris

# A boundary that just fired is ignored this close to the restart point (s),
# so the integrator does not find the same zero again
_GUARD_S = 1e-6
_MAX_SEGMENTS = 100000


def shadow_boundary_events(epoch_tt_j2000_s, ephemeris=None, rotation_at=None):
    """
    Penumbra and umbra boundary functions g(t, y), with t in seconds after the epoch.
    rotation_at(t) is the GCRF -> ITRF matrix, which gives the spin axis of the
    occulting ellipsoid (the GCRF z axis when omitted), as in the force model.
    """
    eph = ephemeris or get_ephemeris()

    def make(index):
        def boundary(t, y):
            r_sun = eph.sun_gcrf(epoch_tt_j2000_s + t)
            pole = rotation_at(t)[2, :] if rotation_at is not None else forces._Z_AXIS
            return forces.shadow_boundaries(np.asarray(y[:3]), r_sun, pole=pole)[index]
        return boundary

    return [make(0), make(1)]


def drag_boundary_events(epoch_tt_j2000_s, rotation_at):
    """
    Altitude switches of NRLMSISE-00 and the drag cutoff (geodetic altitude minus
    each threshold), plus UTC midnight. rotation_at(t) is the GCRF -> ITRF matrix.
    """
    from .nrlmsise00 import DISCONTINUITY_ALTITUDES_KM
    last = {"key": None, "h": 0.0}

    def altitude(t, y):
        key = (t, y[0], y[1], y[2])
        if key != last["key"]:
            last["key"] = key
            last["h"] = forces.itrf_to_geodetic(rotation_at(t) @ np.asarray(y[:3]))[2]
        return last["h"]

    def make(h_m):
        return lambda t, y: altitude(t, y) - h_m

    events = [make(h_km * 1e3) for h_km in DISCONTINUITY_ALTITUDES_KM]
    events.append(make(forces.DRAG_CUTOFF_ALT_M))

    def utc_midnight(t, y):
        utc_s = epoch_tt_j2000_s + t - forces._UTC_MIDNIGHT_2000_IN_TT_J2000
        return math.sin(math.pi * utc_s / 86400.0)

    events.append(utc_midnight)
    return events


def _boundary_event(g, start, sign_after):
    def event(t, y):
        if sign_after is not None and abs(t - start) < _GUARD_S:
            return sign_after
        return g(t, y)
    event.terminal = True
    return event


class _Joined:
    """Dense output that switches from `early` to `late` after time `split`."""

    def __init__(self, early, late, split, sense):
        self.early, self.late, self.split, self.sense = early, late, split, sense

    def __call__(self, t):
        t = np.atleast_1d(t)
        out = self.early(t)
        late = self.sense * (t - self.split) > 0.0
        if late.any():
            out[:, late] = self.late(t[late])
        return out


def solve_ivp_segmented(fun, t_span, y0, boundaries, t_eval=None, events=None, **options):
    """
    scipy.integrate.solve_ivp that restarts at every zero of the `boundaries`
    functions g(t, y). Takes and returns what solve_ivp does, plus
    `boundary_times` (the restart times). User `events` are passed through.
    """
    t0, t_end = float(t_span[0]), float(t_span[1])
    sense = 1.0 if t_end >= t0 else -1.0
    user = list(events) if events is not None else []
    n_b = len(boundaries)
    t_eval = None if t_eval is None else np.asarray(t_eval, dtype=float)

    ts, ys = [], []
    t_events = [[] for _ in user]
    y_events = [[] for _ in user]
    boundary_times = []
    counts = {"nfev": 0, "njev": 0, "nlu": 0}
    i_eval = 0
    start, y = t0, np.asarray(y0, dtype=float)
    forced = {}
    status, message = 0, "The solver successfully reached the end of the integration interval."

    for _ in range(_MAX_SEGMENTS):
        wrapped = [_boundary_event(g, start, forced.get(k)) for k, g in enumerate(boundaries)]
        sol = solve_ivp(fun, (start, t_end), y, events=(wrapped + user) or None, dense_output=True,
                        **options)
        for key in counts:
            counts[key] += int(getattr(sol, key, 0) or 0)
        seg_end = float(sol.t[-1])
        fired = [k for k in range(n_b) if sol.status == 1 and len(sol.t_events[k])]
        dense = sol.sol
        if fired and len(sol.t) > 1:
            # The step that found the crossing straddled the kink, so redo it up to the
            # crossing: every stage then sees the same side of the boundary
            t_prev = float(sol.t[-2])
            redo = solve_ivp(fun, (t_prev, seg_end), sol.y[:, -2], dense_output=True, **options)
            for key in counts:
                counts[key] += int(getattr(redo, key, 0) or 0)
            sol.y[:, -1] = redo.y[:, -1]
            dense = _Joined(sol.sol, redo.sol, t_prev, sense)

        if t_eval is None:
            first = 0 if not ts else 1
            ts.append(sol.t[first:])
            ys.append(sol.y[:, first:])
        else:
            stop = i_eval
            while stop < len(t_eval) and sense * (t_eval[stop] - seg_end) <= 0.0:
                stop += 1
            if stop > i_eval:
                seg_t = t_eval[i_eval:stop]
                ts.append(seg_t)
                ys.append(dense(seg_t))
                i_eval = stop

        for j in range(len(user)):
            if sol.t_events is not None and len(sol.t_events[n_b + j]):
                t_events[j].extend(sol.t_events[n_b + j])
                y_events[j].extend(sol.y_events[n_b + j])

        if sol.status != 1:
            status, message = sol.status, sol.message
            break
        if not fired:                      # a terminal user event
            status, message = 1, sol.message
            break

        k = fired[0]
        boundary_times.append(float(sol.t_events[k][0]))
        before = np.sign(wrapped[k](sol.t[-2], sol.y[:, -2])) if len(sol.t) > 1 else 0.0
        forced = {k: -before if before != 0.0 else 1.0}
        start, y = seg_end, sol.y[:, -1]
    else:
        status, message = -1, "Too many shadow-boundary restarts."

    return _result(ts, ys, len(y), events, t_events, y_events, boundary_times, status, message, counts)


def integrate_segmented(fun, t_span, y0, boundaries, t_eval=None, events=None, steering=None, **options):
    """
    integrators.integrate (RKF78, BS, RK4) restarted at every zero of the `boundaries`, like
    solve_ivp_segmented. These integrators locate an event by re-stepping from the start of the
    step, so the state at a crossing never comes from a step across the kink and nothing is redone.
    A steering controller is started once, for the whole run.
    """
    from .integrators import integrate

    t0, t_end = float(t_span[0]), float(t_span[1])
    sense = 1.0 if t_end >= t0 else -1.0
    user = list(events) if events is not None else []
    n_b = len(boundaries)
    t_eval = None if t_eval is None else np.asarray(t_eval, dtype=float)
    steer = None if steering is None else _StartedOnce(steering)

    ts, ys = [], []
    t_events = [[] for _ in user]
    y_events = [[] for _ in user]
    boundary_times = []
    counts = {"nfev": 0}
    start, y = t0, np.asarray(y0, dtype=float)
    forced = {}
    status, message = 0, "The solver successfully reached the end of the integration interval."

    for _ in range(_MAX_SEGMENTS):
        wrapped = [_boundary_event(g, start, forced.get(k)) for k, g in enumerate(boundaries)]
        ahead = None if t_eval is None else t_eval[sense * (t_eval - start) >= 0.0]
        if t_eval is not None and ts and len(ahead) and ahead[0] == start:
            ahead = ahead[1:]          # emitted by the previous segment, which ended here
        sol = integrate(fun, (start, t_end), y, t_eval=ahead, events=wrapped + user, steering=steer, **options)
        counts["nfev"] += int(sol.nfev)
        stopped = sol.message == "terminal event"
        fired = [k for k in range(n_b) if stopped and len(sol.t_events[k])
                 and sol.t_events[k][-1] == sol.t[-1]]
        seg_end = float(sol.t[-1])

        # Without t_eval keep the segment ends; with it, keep the requested times (the last
        # output of a stopped segment is the stop state, not a requested time)
        keep = slice(None)
        if t_eval is None:
            keep = slice(0 if not ts else 1, None)
        elif stopped and not (len(ahead) and np.isclose(ahead, seg_end, rtol=0.0, atol=1e-9).any()):
            keep = slice(0, -1)
        ts.append(sol.t[keep])
        ys.append(sol.y[:, keep])

        for j in range(len(user)):
            t_events[j].extend(sol.t_events[n_b + j])
            y_events[j].extend(sol.y_events[n_b + j])
        if not stopped:
            break
        if not fired:                      # a terminal user event
            status, message = 1, "A termination event occurred."
            break

        k = fired[0]
        boundary_times.append(seg_end)
        forced = {k: -np.sign(wrapped[k](start, y)) or 1.0}
        start, y = seg_end, sol.y[:, -1]
    else:
        status, message = -1, "Too many shadow-boundary restarts."

    return _result(ts, ys, len(y), events, t_events, y_events, boundary_times, status, message, counts)


class _StartedOnce:
    """A steering controller whose start() takes effect only at the first segment."""

    def __init__(self, steering):
        self.steering, self.started = steering, False

    def start(self, t, y):
        if not self.started:
            self.steering.start(t, y)
            self.started = True

    def __getattr__(self, name):
        return getattr(self.steering, name)


def _result(ts, ys, n_y, events, t_events, y_events, boundary_times, status, message, counts):
    t_out = np.concatenate(ts) if ts else np.array([])
    y_out = np.concatenate(ys, axis=1) if ys else np.zeros((n_y, 0))
    return OptimizeResult(
        t=t_out, y=y_out, sol=None,
        t_events=None if events is None else [np.asarray(v) for v in t_events],
        y_events=None if events is None else [np.asarray(v).reshape(-1, n_y) for v in y_events],
        boundary_times=np.asarray(boundary_times), status=status, message=message,
        success=status >= 0, **counts,
    )

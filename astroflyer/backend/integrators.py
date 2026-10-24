"""
AstroFlyer HEO - Numerical integrators
=============================================================================
One-step integrators that land exactly on every requested output time and
locate events by re-stepping from the start of the step, so outputs and
event times carry the integrator's own accuracy (no dense-output interpolation).

  RKF78   Runge-Kutta-Fehlberg 7(8), 13 stages, adaptive (NASA TR R-287, 1968)
  BS      Bulirsch-Stoer: Gragg modified midpoint + polynomial extrapolation
  RK4     classic fixed-step Runge-Kutta 4

integrate() returns an object with the solve_ivp fields propagate() uses:
t, y (n x m), t_events, y_events, success, message, nfev.
=============================================================================
"""

import numpy as np
from scipy.optimize import brentq

METHODS = ("RKF78", "BS", "RK4")

# ==============================================================================
# RUNGE-KUTTA-FEHLBERG 7(8) TABLEAU
# ==============================================================================
_C78 = np.array([0.0, 2/27, 1/9, 1/6, 5/12, 1/2, 5/6, 1/6, 2/3, 1/3, 1.0, 0.0, 1.0])
_A78 = [
    [],
    [2/27],
    [1/36, 1/12],
    [1/24, 0, 1/8],
    [5/12, 0, -25/16, 25/16],
    [1/20, 0, 0, 1/4, 1/5],
    [-25/108, 0, 0, 125/108, -65/27, 125/54],
    [31/300, 0, 0, 0, 61/225, -2/9, 13/900],
    [2, 0, 0, -53/6, 704/45, -107/9, 67/90, 3],
    [-91/108, 0, 0, 23/108, -976/135, 311/54, -19/60, 17/6, -1/12],
    [2383/4100, 0, 0, -341/164, 4496/1025, -301/82, 2133/4100, 45/82, 45/164, 18/41],
    [3/205, 0, 0, 0, 0, -6/41, -3/205, -3/41, 3/41, 6/41, 0],
    [-1777/4100, 0, 0, -341/164, 4496/1025, -289/82, 2193/4100, 51/82, 33/164, 12/41, 0, 1],
]
# 8th-order weights (propagated solution); the 7th-order solution differs by _E78
_B78 = np.array([0, 0, 0, 0, 0, 34/105, 9/35, 9/35, 9/280, 9/280, 0, 41/840, 41/840])
_E78 = np.array([41/840, 0, 0, 0, 0, 0, 0, 0, 0, 0, 41/840, -41/840, -41/840])


def _rkf78_step(fun, t, y, h):
    k = np.empty((13, y.size))
    for i in range(13):
        yi = y + h * (np.dot(_A78[i], k[:i]) if i else 0.0)
        k[i] = fun(t + _C78[i] * h, yi)
    return y + h * (_B78 @ k), h * (_E78 @ k), 13


# ==============================================================================
# BULIRSCH-STOER
# ==============================================================================
_BS_SEQUENCE = (2, 4, 6, 8, 10, 12, 14, 16)


def _modified_midpoint(fun, t, y, h, n, f0):
    sub = h / n
    z0, z1 = y, y + sub * f0
    for m in range(1, n):
        z0, z1 = z1, z0 + 2.0 * sub * fun(t + m * sub, z1)
    return 0.5 * (z0 + z1 + sub * fun(t + h, z1))


def _bs_step(fun, t, y, h, rtol, atol):
    """One extrapolated step; returns (y_new, err_norm, nfev, columns used)."""
    f0 = fun(t, y)
    nfev = 1
    table = []
    err = np.inf
    for j, n in enumerate(_BS_SEQUENCE):
        row = [_modified_midpoint(fun, t, y, h, n, f0)]
        nfev += n
        for k in range(1, j + 1):
            ratio = (n / _BS_SEQUENCE[j - k]) ** 2
            row.append(row[k - 1] + (row[k - 1] - table[j - 1][k - 1]) / (ratio - 1.0))
        table.append(row)
        if j >= 2:
            scale = atol + rtol * np.maximum(np.abs(y), np.abs(row[-1]))
            err = np.sqrt(np.mean(((row[-1] - row[-2]) / scale) ** 2))
            if err <= 1.0:
                return row[-1], err, nfev, j
    return table[-1][-1], err, nfev, len(_BS_SEQUENCE) - 1


# ==============================================================================
# FIXED-STEP RK4
# ==============================================================================
def _rk4_step(fun, t, y, h):
    k1 = fun(t, y)
    k2 = fun(t + 0.5 * h, y + 0.5 * h * k1)
    k3 = fun(t + 0.5 * h, y + 0.5 * h * k2)
    k4 = fun(t + h, y + h * k3)
    return y + h / 6.0 * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


# ==============================================================================
# DRIVER
# ==============================================================================
class IntegrationResult:
    def __init__(self, t, y, t_events, y_events, nfev, message="ok"):
        self.t = np.asarray(t)
        self.y = np.asarray(y).T            # solve_ivp layout: (n_states, n_times)
        self.t_events = [np.asarray(te) for te in t_events]
        self.y_events = [np.asarray(ye) for ye in y_events]
        self.nfev = nfev
        self.success = True
        self.message = message


class _Stepper:
    """Takes one accepted step of a requested size (the controller lives in integrate)."""

    def __init__(self, fun, method, rtol, atol):
        self.fun, self.method, self.rtol, self.atol = fun, method, rtol, atol
        self.nfev = 0

    def error_norm(self, y, y_new, err_vec):
        scale = self.atol + self.rtol * np.maximum(np.abs(y), np.abs(y_new))
        return np.sqrt(np.mean((err_vec / scale) ** 2))

    def attempt(self, t, y, h):
        """Returns (y_new, err_norm, suggested next |h|)."""
        if self.method == "RK4":
            self.nfev += 4
            return _rk4_step(self.fun, t, y, h), 0.0, abs(h)
        if self.method == "RKF78":
            y_new, err_vec, n = _rkf78_step(self.fun, t, y, h)
            self.nfev += n
            err = self.error_norm(y, y_new, err_vec)
            factor = 0.9 * (1.0 / err) ** (1.0 / 8.0) if err > 0 else 4.0
            return y_new, err, abs(h) * min(4.0, max(0.2, factor))
        y_new, err, n, j = _bs_step(self.fun, t, y, h, self.rtol, self.atol)
        self.nfev += n
        factor = 0.94 * (0.65 / err) ** (1.0 / (2 * j + 1)) if err > 0 else 4.0
        if err <= 1.0 and j < 4:
            factor = max(factor, 1.5)      # converged early: grow the step
        return y_new, err, abs(h) * min(4.0, max(0.2, factor))

    def exact(self, t, y, h):
        """Step of exactly h, split into accepted sub-steps if needed (used for outputs and events)."""
        if h == 0.0:
            return y.copy()
        t_end, cur_t, cur_y = t + h, t, y
        sub = h
        while (t_end - cur_t) * np.sign(h) > 0:
            sub = np.sign(h) * min(abs(sub), abs(t_end - cur_t))
            y_new, err, h_next = self.attempt(cur_t, cur_y, sub)
            if err <= 1.0:
                cur_t, cur_y = cur_t + sub, y_new
                sub = np.sign(h) * h_next
            else:
                sub = np.sign(h) * min(h_next, 0.5 * abs(sub))
        return cur_y


def integrate(fun, t_span, y0, method="RKF78", t_eval=None, events=None,
              rtol=1e-11, atol=1e-11, first_step=None, fixed_step=None, max_step=np.inf):
    """Integrates dy/dt = fun(t, y) from t_span[0] to t_span[1].

    Events follow solve_ivp conventions: callables g(t, y) with an optional
    `direction` attribute (+1 rising, -1 falling, 0 both). RK4 needs fixed_step (s).
    """
    method = method.upper()
    if method not in METHODS:
        raise ValueError(f"Unknown integrator {method!r}; choose one of {METHODS}")
    if method == "RK4" and not fixed_step:
        raise ValueError("RK4 needs fixed_step in seconds")

    rhs = fun
    fun = lambda t, y: np.asarray(rhs(t, y), dtype=float)
    t0, tf = float(t_span[0]), float(t_span[1])
    direction = 1.0 if tf >= t0 else -1.0
    y = np.asarray(y0, dtype=float).copy()
    outputs = np.asarray(t_eval if t_eval is not None else [t0, tf], dtype=float)
    stepper = _Stepper(fun, method, rtol, atol)
    events = list(events or [])
    ev_dir = [float(getattr(ev, "direction", 0.0)) for ev in events]
    t_events = [[] for _ in events]
    y_events = [[] for _ in events]

    if fixed_step:
        h = direction * abs(float(fixed_step))
    elif first_step:
        h = direction * abs(float(first_step))
    else:
        # Rough first guess from the state scale and rate, refined by the controller
        f0 = fun(t0, y)
        stepper.nfev += 1
        h = direction * min(abs(tf - t0), 0.01 * np.linalg.norm(y) / max(np.linalg.norm(f0), 1e-30), max_step)

    out_t, out_y = [], []
    k_out = 0
    while k_out < len(outputs) and (outputs[k_out] - t0) * direction <= 0:
        out_t.append(outputs[k_out])
        out_y.append(stepper.exact(t0, y, outputs[k_out] - t0))
        k_out += 1
    g_prev = [ev(t0, y) for ev in events]

    t = t0
    while (tf - t) * direction > 0:
        h = direction * min(abs(h), abs(tf - t), max_step)
        if fixed_step:
            y_new, err, h_next = stepper.attempt(t, y, h)
        else:
            y_new, err, h_next = stepper.attempt(t, y, h)
            if err > 1.0:
                h = direction * h_next
                if abs(h) < 1e-12 * max(1.0, abs(t)):
                    raise RuntimeError(f"Step size underflow at t = {t}")
                continue
        t_new = t + h

        # Events: sign change across the step, refined by re-stepping from (t, y)
        for i, ev in enumerate(events):
            g_new = ev(t_new, y_new)
            g0 = g_prev[i]
            crossed = (g0 < 0 <= g_new) or (g0 > 0 >= g_new)
            if crossed and g0 != 0.0:
                rising = g_new > g0
                if ev_dir[i] == 0 or (ev_dir[i] > 0) == rising:
                    g_of = lambda dt: ev(t + dt, stepper.exact(t, y, dt))
                    dt_root = brentq(g_of, 0.0, h, xtol=1e-9, rtol=1e-14) if h > 0 else -brentq(
                        lambda s: g_of(-s), 0.0, -h, xtol=1e-9, rtol=1e-14)
                    t_events[i].append(t + dt_root)
                    y_events[i].append(stepper.exact(t, y, dt_root))
            g_prev[i] = g_new

        # Outputs inside (t, t_new]: re-step from the step start to land on them exactly
        while k_out < len(outputs) and (outputs[k_out] - t_new) * direction <= 0:
            dt = outputs[k_out] - t
            out_t.append(outputs[k_out])
            out_y.append(y_new.copy() if dt == h else stepper.exact(t, y, dt))
            k_out += 1

        t, y = t_new, y_new
        h = direction * (abs(fixed_step) if fixed_step else h_next)

    return IntegrationResult(out_t, out_y, t_events, y_events, stepper.nfev)

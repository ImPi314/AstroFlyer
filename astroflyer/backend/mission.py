"""
AstroFlyer HEO - Mission objects, maneuvers and targeting
=============================================================================
  Spacecraft          epoch, GCRF state, dry and fuel mass, drag and SRP properties;
                      Keplerian, equinoctial and modified equinoctial element sets
  Propagator          force model + integrator; step() by duration or to an event
  ImpulsiveBurn       delta-v in VNC, RTN or GCRF, fuel from the rocket equation
  FiniteBurn          constant thrust along a VNC/RTN/GCRF direction, mass flow
  DifferentialCorrector
                      vary/achieve targeting: Newton or least squares on a
                      finite-difference Jacobian, with step limits and backtracking

Example (GTO apogee circularization):

    sc = Spacecraft.from_keplerian(epoch, a, e, inc, raan, argp, ta)
    prop = Propagator("j2")
    dc = DifferentialCorrector()
    dc.vary("dv_v", 1500.0, perturbation=1.0, max_step=200.0)
    dc.achieve("ecc", 0.0, tolerance=1e-5)

    def run(values):
        s = prop.step(sc.copy(), until="apogee")
        ImpulsiveBurn([values["dv_v"], 0, 0], frame="VNC").apply(s)
        return {"ecc": s.keplerian()["e"]}

    result = dc.solve(run)
=============================================================================
"""

import copy
import dataclasses
import math
from dataclasses import dataclass, field

import numpy as np

from . import forces
from .epoch import Epoch
from .forces import MU_EARTH, R_EARTH_EQ, ForceModelConfig
from .frames import FastEarthRotation, rtn_matrix, vnc_matrix
from .integrators import integrate

G0 = 9.80665                     # standard gravity (m/s^2), defines Isp
TWO_PI = 2.0 * math.pi


# ==============================================================================
# ELEMENT SETS
# ==============================================================================
def keplerian_from_state(r, v, mu=MU_EARTH):
    """Osculating Keplerian elements (SI, angles in rad); handles circular and equatorial orbits."""
    r = np.asarray(r, dtype=float)
    v = np.asarray(v, dtype=float)
    rm = np.linalg.norm(r)
    h = np.cross(r, v)
    hm = np.linalg.norm(h)
    e_vec = np.cross(v, h) / mu - r / rm
    e = float(np.linalg.norm(e_vec))
    a = 1.0 / (2.0 / rm - v @ v / mu)
    inc = math.acos(np.clip(h[2] / hm, -1.0, 1.0))
    n = np.array([-h[1], h[0], 0.0])
    nm = np.linalg.norm(n)
    equatorial = nm < 1e-11 * hm
    node = np.array([1.0, 0.0, 0.0]) if equatorial else n / nm
    raan = 0.0 if equatorial else math.atan2(n[1], n[0]) % TWO_PI
    w_hat = h / hm
    q = np.cross(w_hat, node)
    circular = e < 1e-11
    argp = 0.0 if circular else math.atan2(e_vec @ q, e_vec @ node) % TWO_PI
    p_hat = node if circular else e_vec / e
    nu = math.atan2(np.cross(p_hat, r) @ w_hat, p_hat @ r) % TWO_PI
    return {"a": a, "e": e, "inc": inc, "raan": raan, "argp": argp, "ta": nu,
            "rp": a * (1.0 - e), "ra": a * (1.0 + e), "period": TWO_PI * math.sqrt(a ** 3 / mu) if a > 0 else math.inf}


def state_from_keplerian(a, e, inc, raan, argp, ta, mu=MU_EARTH):
    p = a * (1.0 - e * e)
    rm = p / (1.0 + e * math.cos(ta))
    r_pf = np.array([rm * math.cos(ta), rm * math.sin(ta), 0.0])
    v_pf = math.sqrt(mu / p) * np.array([-math.sin(ta), e + math.cos(ta), 0.0])
    co, so, ci, si, cw, sw = math.cos(raan), math.sin(raan), math.cos(inc), math.sin(inc), math.cos(argp), math.sin(argp)
    rot = np.array([
        [co * cw - so * sw * ci, -co * sw - so * cw * ci, so * si],
        [so * cw + co * sw * ci, -so * sw + co * cw * ci, -co * si],
        [sw * si, cw * si, ci],
    ])
    return rot @ r_pf, rot @ v_pf


def _mean_from_true(ta, e):
    ecc = 2.0 * math.atan2(math.sqrt(1.0 - e) * math.sin(ta / 2.0), math.sqrt(1.0 + e) * math.cos(ta / 2.0))
    return (ecc - e * math.sin(ecc)) % TWO_PI


def _true_from_mean(m, e):
    ecc = m if e < 0.8 else math.pi
    for _ in range(50):
        d = (ecc - e * math.sin(ecc) - m) / (1.0 - e * math.cos(ecc))
        ecc -= d
        if abs(d) < 1e-15:
            break
    return (2.0 * math.atan2(math.sqrt(1.0 + e) * math.sin(ecc / 2.0), math.sqrt(1.0 - e) * math.cos(ecc / 2.0))) % TWO_PI


def equinoctial_from_keplerian(k):
    """Broucke-Cefola equinoctial elements a, h, k, p, q, mean longitude (prograde set)."""
    lon_peri = k["argp"] + k["raan"]
    t = math.tan(k["inc"] / 2.0)
    return {"a": k["a"], "h": k["e"] * math.sin(lon_peri), "k": k["e"] * math.cos(lon_peri),
            "p": t * math.sin(k["raan"]), "q": t * math.cos(k["raan"]),
            "mean_longitude": (_mean_from_true(k["ta"], k["e"]) + lon_peri) % TWO_PI}


def keplerian_from_equinoctial(a, h, k, p, q, mean_longitude):
    e = math.hypot(h, k)
    inc = 2.0 * math.atan(math.hypot(p, q))
    raan = math.atan2(p, q) % TWO_PI
    lon_peri = math.atan2(h, k)
    argp = (lon_peri - raan) % TWO_PI
    ta = _true_from_mean((mean_longitude - lon_peri) % TWO_PI, e)
    return a, e, inc, raan, argp, ta


def modified_equinoctial_from_keplerian(k):
    """Walker-Ireland-Owens modified equinoctial elements p, f, g, h, k, true longitude L."""
    lon_peri = k["argp"] + k["raan"]
    t = math.tan(k["inc"] / 2.0)
    return {"p": k["a"] * (1.0 - k["e"] ** 2), "f": k["e"] * math.cos(lon_peri), "g": k["e"] * math.sin(lon_peri),
            "h": t * math.cos(k["raan"]), "k": t * math.sin(k["raan"]), "L": (lon_peri + k["ta"]) % TWO_PI}


def keplerian_from_modified_equinoctial(p, f, g, h, k, L):
    e = math.hypot(f, g)
    a = p / (1.0 - e * e)
    inc = 2.0 * math.atan(math.hypot(h, k))
    raan = math.atan2(k, h) % TWO_PI
    lon_peri = math.atan2(g, f)
    return a, e, inc, raan, (lon_peri - raan) % TWO_PI, (L - lon_peri) % TWO_PI


# ==============================================================================
# SPACECRAFT
# ==============================================================================
@dataclass
class Spacecraft:
    epoch: Epoch
    r: np.ndarray                  # GCRF position (m)
    v: np.ndarray                  # GCRF velocity (m/s)
    dry_mass_kg: float = 1000.0
    fuel_mass_kg: float = 500.0
    cd: float = 2.2
    drag_area_m2: float = 10.0
    cr: float = 1.3
    srp_area_m2: float = 10.0
    history: list = field(default_factory=list, repr=False)   # (label, epoch, r, v, mass) after each segment
    ephemeris: list = field(default_factory=list, repr=False)  # (epoch, r, v) samples from step(record_step=...)

    def __post_init__(self):
        self.epoch = Epoch.coerce(self.epoch)
        self.r = np.asarray(self.r, dtype=float).copy()
        self.v = np.asarray(self.v, dtype=float).copy()

    @classmethod
    def from_keplerian(cls, epoch, a, e, inc, raan, argp, ta, degrees=True, **properties):
        """a in metres; angles in degrees unless degrees=False."""
        conv = math.radians if degrees else float
        r, v = state_from_keplerian(a, e, conv(inc), conv(raan), conv(argp), conv(ta))
        return cls(epoch, r, v, **properties)

    @classmethod
    def from_equinoctial(cls, epoch, a, h, k, p, q, mean_longitude, **properties):
        r, v = state_from_keplerian(*keplerian_from_equinoctial(a, h, k, p, q, mean_longitude))
        return cls(epoch, r, v, **properties)

    @classmethod
    def from_modified_equinoctial(cls, epoch, p, f, g, h, k, L, **properties):
        r, v = state_from_keplerian(*keplerian_from_modified_equinoctial(p, f, g, h, k, L))
        return cls(epoch, r, v, **properties)

    @property
    def mass_kg(self):
        return self.dry_mass_kg + self.fuel_mass_kg

    @property
    def state(self):
        return np.concatenate([self.r, self.v])

    def keplerian(self):
        return keplerian_from_state(self.r, self.v)

    def equinoctial(self):
        return equinoctial_from_keplerian(self.keplerian())

    def modified_equinoctial(self):
        return modified_equinoctial_from_keplerian(self.keplerian())

    def altitude_km(self):
        return (np.linalg.norm(self.r) - R_EARTH_EQ) / 1000.0

    def copy(self):
        return copy.deepcopy(self)

    def _record(self, label):
        self.history.append((label, self.epoch, self.r.copy(), self.v.copy(), self.mass_kg))


def _local_frame(frame, r, v):
    """Rows are the local axes in GCRF; a direction d in the frame is rot.T @ d in GCRF."""
    frame = frame.upper()
    if frame == "VNC":
        return vnc_matrix(r, v)
    if frame in ("RTN", "RSW", "RIC"):
        return rtn_matrix(r, v)
    if frame in ("GCRF", "INERTIAL", "ECI"):
        return np.eye(3)
    raise ValueError(f"Unknown burn frame {frame!r}; use VNC, RTN or GCRF")


# ==============================================================================
# MANEUVERS
# ==============================================================================
@dataclass
class ImpulsiveBurn:
    delta_v: tuple                 # m/s, components in `frame`
    frame: str = "VNC"
    isp_s: float = 300.0

    def apply(self, sc):
        dv_local = np.asarray(self.delta_v, dtype=float)
        dv = _local_frame(self.frame, sc.r, sc.v).T @ dv_local
        fuel_used = sc.mass_kg * (1.0 - math.exp(-np.linalg.norm(dv) / (self.isp_s * G0)))
        if fuel_used > sc.fuel_mass_kg + 1e-9:
            raise ValueError(f"Burn needs {fuel_used:.1f} kg of fuel, {sc.fuel_mass_kg:.1f} kg left")
        sc.v = sc.v + dv
        sc.fuel_mass_kg -= fuel_used
        sc._record("impulsive burn")
        return {"delta_v_ms": float(np.linalg.norm(dv)), "fuel_used_kg": float(fuel_used)}


@dataclass
class FiniteBurn:
    thrust_n: float
    isp_s: float
    direction: tuple = (1.0, 0.0, 0.0)   # unit direction in `frame`, re-evaluated along the arc
    frame: str = "VNC"

    @property
    def mass_flow_kg_s(self):
        return self.thrust_n / (self.isp_s * G0)

    def acceleration(self, r, v, mass):
        d = np.asarray(self.direction, dtype=float)
        d = d / np.linalg.norm(d)
        return (self.thrust_n / mass) * (_local_frame(self.frame, r, v).T @ d)


# ==============================================================================
# PROPAGATOR
# ==============================================================================
_EVENT_GUARDS = {
    "perigee": (lambda t, y: y[0] * y[3] + y[1] * y[4] + y[2] * y[5], 1.0),
    "apogee": (lambda t, y: y[0] * y[3] + y[1] * y[4] + y[2] * y[5], -1.0),
    "ascending_node": (lambda t, y: y[2], 1.0),
    "descending_node": (lambda t, y: y[2], -1.0),
}


class Propagator:
    """Force model + integrator for Spacecraft objects.

    model is a forces.ForceModelConfig preset name ("two_body", "j2", "j2_j3_j4",
    anything else = full model) or a ForceModelConfig. Drag and SRP use the
    spacecraft's own Cd*A/m and Cr*A/m, updated at the start of every segment.
    """

    def __init__(self, model="j2", method="RKF78", rtol=1e-11, atol=1e-11, **force_overrides):
        self.base_config = model if isinstance(model, ForceModelConfig) else ForceModelConfig.for_model(model, **force_overrides)
        self.method = method
        self.rtol, self.atol = rtol, atol

    def _config_for(self, sc):
        return dataclasses.replace(
            self.base_config,
            cd_area_over_m=sc.cd * sc.drag_area_m2 / sc.mass_kg,
            cr_area_over_m=sc.cr * sc.srp_area_m2 / sc.mass_kg,
        )

    def step(self, sc, duration=None, until=None, burn=None, max_duration=None, label=None, record_step=None):
        """Advances `sc` in place and returns it.

        duration: seconds (may be negative). until: "perigee", "apogee", "ascending_node"
        or "descending_node" (the next one, searched for up to max_duration, default
        three orbits). burn: a FiniteBurn applied for the whole segment. record_step:
        if given (s), states along the segment are appended to sc.ephemeris.
        """
        if duration is None and until is None:
            raise ValueError("step() needs a duration or an event to stop at")
        if until is not None:
            if until not in _EVENT_GUARDS:
                raise ValueError(f"Unknown stop event {until!r}; choose from {sorted(_EVENT_GUARDS)}")
            span = max_duration or 3.0 * max(sc.keplerian()["period"], 3600.0)
        else:
            span = float(duration)
        if span == 0.0:
            return sc

        cfg = self._config_for(sc)
        epoch_tt = float(sc.epoch - Epoch.j2000())
        rotation = FastEarthRotation(sc.epoch, min(0.0, span), max(0.0, span))
        mdot = burn.mass_flow_kg_s if burn is not None else 0.0

        def rhs(t, y):
            rot = rotation.matrix(t)
            acc = forces.total_acceleration(epoch_tt + t, y[:3], y[3:6], cfg, rot, rotation.omega(t))
            if burn is not None:
                acc = acc + burn.acceleration(y[:3], y[3:6], y[6])
            return np.concatenate([y[3:6], acc, [-mdot]])

        events = []
        if until is not None:
            g, direction = _EVENT_GUARDS[until]
            stop = lambda t, y: g(t, y)
            stop.direction = direction
            stop.terminal = True
            events.append(stop)

        y0 = np.concatenate([sc.r, sc.v, [sc.mass_kg]])
        t_eval = None
        if record_step:
            t_eval = np.append(np.arange(0.0, abs(span), abs(float(record_step))), abs(span)) * np.sign(span)
        res = integrate(rhs, (0.0, span), y0, method=self.method, t_eval=t_eval, events=events,
                        rtol=self.rtol, atol=self.atol)
        if until is not None and res.message != "terminal event":
            raise RuntimeError(f"No {until} within {span:.0f} s")

        y_end = res.y[:, -1]
        elapsed = float(res.t[-1])
        if record_step:
            if sc.ephemeris and abs(sc.ephemeris[-1][0] - sc.epoch) < 1e-6:
                sc.ephemeris.pop()      # same instant (e.g. after an impulsive burn): keep the new state
            for t_k, y_k in zip(res.t, res.y.T):
                if sc.ephemeris and abs((sc.epoch + float(t_k)) - sc.ephemeris[-1][0]) < 1e-3:
                    sc.ephemeris.pop()  # a grid point within 1 ms of the stop event: keep the event state
                sc.ephemeris.append((sc.epoch + float(t_k), y_k[:3].copy(), y_k[3:6].copy()))
        fuel_used = sc.mass_kg - y_end[6]
        if fuel_used > sc.fuel_mass_kg + 1e-9:
            raise ValueError(f"Finite burn needs {fuel_used:.1f} kg of fuel, {sc.fuel_mass_kg:.1f} kg left")
        sc.epoch = sc.epoch + elapsed
        sc.r, sc.v = y_end[:3].copy(), y_end[3:6].copy()
        sc.fuel_mass_kg -= fuel_used
        sc._record(label or (f"to {until}" if until else f"{elapsed:.0f} s"))
        return sc


# ==============================================================================
# DIFFERENTIAL CORRECTOR
# ==============================================================================
@dataclass
class _Variable:
    name: str
    value: float
    perturbation: float
    max_step: float
    lower: float
    upper: float


@dataclass
class _Goal:
    name: str
    target: float
    tolerance: float


@dataclass
class TargetResult:
    converged: bool
    values: dict
    achieved: dict
    iterations: int
    history: list
    message: str


class DifferentialCorrector:
    """Vary/achieve targeter.

    Each iteration evaluates the mission at the current values, builds a forward-
    difference Jacobian of the goals, and takes a Newton step (least squares when
    goals and variables differ in number), clipped to each variable's max_step and
    bounds, halving it until the scaled miss shrinks.
    """

    def __init__(self, max_iterations=25):
        self.max_iterations = max_iterations
        self.variables = []
        self.goals = []

    def vary(self, name, initial, perturbation=1e-3, max_step=math.inf, lower=-math.inf, upper=math.inf):
        self.variables.append(_Variable(name, float(initial), float(perturbation), float(max_step), lower, upper))
        return self

    def achieve(self, name, target, tolerance):
        self.goals.append(_Goal(name, float(target), float(tolerance)))
        return self

    def _misses(self, mission, values):
        achieved = mission(dict(zip([v.name for v in self.variables], values)))
        miss = np.array([(achieved[g.name] - g.target) / g.tolerance for g in self.goals])
        return miss, achieved

    def solve(self, mission):
        """mission(values: dict) -> dict with an entry for every goal name."""
        if not self.variables or not self.goals:
            raise ValueError("Add at least one vary() and one achieve() before solve()")
        x = np.array([v.value for v in self.variables])
        lower = np.array([v.lower for v in self.variables])
        upper = np.array([v.upper for v in self.variables])
        max_step = np.array([v.max_step for v in self.variables])
        names = [v.name for v in self.variables]
        miss, achieved = self._misses(mission, x)
        history = [(dict(zip(names, x)), dict(achieved))]

        for it in range(1, self.max_iterations + 1):
            if np.all(np.abs(miss) <= 1.0):
                return TargetResult(True, dict(zip(names, x)), achieved, it - 1, history, "converged")
            jac = np.empty((len(self.goals), len(x)))
            for j, var in enumerate(self.variables):
                xp = x.copy()
                xp[j] += var.perturbation
                jac[:, j] = (self._misses(mission, xp)[0] - miss) / var.perturbation
            dx = np.linalg.lstsq(jac, -miss, rcond=None)[0]
            # Scale the whole step down so no variable exceeds its max_step
            ratio = np.max(np.abs(dx) / max_step)
            if ratio > 1.0:
                dx /= ratio
            norm0 = np.linalg.norm(miss)
            for _ in range(8):
                x_try = np.clip(x + dx, lower, upper)
                try:
                    miss_try, achieved_try = self._misses(mission, x_try)
                except (RuntimeError, ValueError):
                    dx *= 0.5
                    continue
                if np.linalg.norm(miss_try) < norm0:
                    break
                dx *= 0.5
            else:
                return TargetResult(False, dict(zip(names, x)), achieved, it, history,
                                    "line search failed: the miss does not decrease along the Newton step")
            x, miss, achieved = x_try, miss_try, achieved_try
            history.append((dict(zip(names, x)), dict(achieved)))

        converged = bool(np.all(np.abs(miss) <= 1.0))
        return TargetResult(converged, dict(zip(names, x)), achieved, self.max_iterations, history,
                            "converged" if converged else "iteration limit reached")


# ==============================================================================
# READY-MADE TARGETING SCENARIOS (used by the API)
# ==============================================================================
def _result_payload(result, extra):
    payload = {
        "converged": result.converged,
        "message": result.message,
        "iterations": result.iterations,
        "values": {k: float(v) for k, v in result.values.items()},
        "achieved": {k: float(v) for k, v in result.achieved.items()},
        "history": [{"values": {k: float(v) for k, v in vals.items()},
                     "achieved": {k: float(v) for k, v in ach.items()}} for vals, ach in result.history],
    }
    payload.update(extra)
    return payload


def target_gto_to_geo(epoch, perigee_alt_km=250.0, apogee_alt_km=35786.0, inc_deg=28.5, raan_deg=0.0,
                      dry_mass_kg=1500.0, fuel_mass_kg=2000.0, isp_s=320.0, model="j2"):
    """One impulsive burn that makes a GTO circular and equatorial.

    The burn is placed at the equator crossing at apogee (argument of perigee
    180 deg puts apogee on the ascending node), so an equatorial orbit is reachable.
    Goals are the modified equinoctial f, g, h, k, which are smooth at e = i = 0.
    """
    rp = R_EARTH_EQ + perigee_alt_km * 1e3
    ra = R_EARTH_EQ + apogee_alt_km * 1e3
    gto = Spacecraft.from_keplerian(epoch, (rp + ra) / 2.0, (ra - rp) / (ra + rp), inc_deg, raan_deg, 180.0, 0.0,
                                    dry_mass_kg=dry_mass_kg, fuel_mass_kg=fuel_mass_kg)
    prop = Propagator(model)
    dc = DifferentialCorrector()
    for name in ("dv_v", "dv_n", "dv_c"):
        dc.vary(name, 0.0, perturbation=1.0, max_step=500.0)
    for goal in "fghk":
        dc.achieve(goal, 0.0, 1e-5)

    def mission(values):
        sc = prop.step(gto.copy(), until="ascending_node")
        ImpulsiveBurn([values["dv_v"], values["dv_n"], values["dv_c"]], "VNC", isp_s).apply(sc)
        return sc.modified_equinoctial()

    result = dc.solve(mission)
    sc = prop.step(gto.copy(), until="ascending_node")
    burn = ImpulsiveBurn([result.values[n] for n in ("dv_v", "dv_n", "dv_c")], "VNC", isp_s).apply(sc)
    k = sc.keplerian()
    return _result_payload(result, {
        "scenario": "gto_to_geo",
        "burn_epoch_utc": sc.epoch.iso("UTC"),
        "delta_v_ms": burn["delta_v_ms"],
        "fuel_used_kg": burn["fuel_used_kg"],
        "final_orbit": {"sma_km": k["a"] / 1e3, "ecc": k["e"], "inc_deg": math.degrees(k["inc"])},
    })


def target_perigee_raise(epoch, sma_km=26560.0, perigee_alt_km=450.0, inc_deg=63.4, raan_deg=30.0,
                         argp_deg=270.0, target_perigee_alt_km=600.0, dry_mass_kg=1000.0,
                         fuel_mass_kg=200.0, isp_s=300.0, model="j2_j3_j4"):
    """Perigee maintenance: one along-track burn at apogee sets the next perigee altitude."""
    a = sma_km * 1e3
    e = 1.0 - (R_EARTH_EQ + perigee_alt_km * 1e3) / a
    sat = Spacecraft.from_keplerian(epoch, a, e, inc_deg, raan_deg, argp_deg, 0.0,
                                    dry_mass_kg=dry_mass_kg, fuel_mass_kg=fuel_mass_kg)
    prop = Propagator(model)
    dc = DifferentialCorrector().vary("dv_v", 1.0, perturbation=0.1, max_step=50.0)
    dc.achieve("perigee_alt_km", target_perigee_alt_km, 0.01)

    def mission(values):
        sc = prop.step(sat.copy(), until="apogee")
        ImpulsiveBurn([values["dv_v"], 0.0, 0.0], "VNC", isp_s).apply(sc)
        prop.step(sc, until="perigee")
        return {"perigee_alt_km": sc.altitude_km()}

    result = dc.solve(mission)
    sc = prop.step(sat.copy(), until="apogee")
    burn = ImpulsiveBurn([result.values["dv_v"], 0.0, 0.0], "VNC", isp_s).apply(sc)
    return _result_payload(result, {
        "scenario": "perigee_raise",
        "burn_epoch_utc": sc.epoch.iso("UTC"),
        "delta_v_ms": burn["delta_v_ms"],
        "fuel_used_kg": burn["fuel_used_kg"],
    })

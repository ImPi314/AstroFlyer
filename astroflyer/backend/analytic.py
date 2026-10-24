"""
AstroFlyer HEO - Analytic propagators
=============================================================================
  kepler     exact two-body motion (elliptic orbits), no integration error
  j2_mean    two-body plus the secular J2 drift of node, perigee and mean
             anomaly; the initial osculating elements are taken as mean elements
  sgp4       NORAD SGP4/SDP4 from a two-line element set (TEME, converted to GCRF)

Each returns GCRF position (m) and velocity (m/s) arrays at the requested
times (s after the epoch); analytic_events() finds apsis and node crossings
on any of them by root finding on the closed-form state.
=============================================================================
"""

import math

import numpy as np
from scipy.optimize import brentq

from .epoch import Epoch
from .forces import J2_EARTH, MU_EARTH, R_GRAVITY_REF
from .frames import transform_state

TWO_PI = 2.0 * math.pi


# ==============================================================================
# ELEMENTS
# ==============================================================================
def state_to_elements(r, v, mu=MU_EARTH):
    """Returns a, e, inc, raan, argp, mean anomaly (rad) for an elliptic orbit."""
    r = np.asarray(r, dtype=float)
    v = np.asarray(v, dtype=float)
    rm = np.linalg.norm(r)
    h = np.cross(r, v)
    hm = np.linalg.norm(h)
    e_vec = np.cross(v, h) / mu - r / rm
    e = np.linalg.norm(e_vec)
    a = 1.0 / (2.0 / rm - v @ v / mu)
    if e >= 1.0 or a <= 0.0:
        raise ValueError("Analytic propagators need an elliptic orbit (e < 1)")
    inc = math.acos(np.clip(h[2] / hm, -1.0, 1.0))
    n = np.array([-h[1], h[0], 0.0])
    nm = np.linalg.norm(n)
    # Equatorial or circular orbits: measure from the x axis or the node so the elements stay defined
    raan = math.atan2(n[1], n[0]) if nm > 1e-12 * hm else 0.0
    node_dir = n / nm if nm > 1e-12 * hm else np.array([1.0, 0.0, 0.0])
    q_dir = np.cross(h / hm, node_dir)
    if e > 1e-12:
        argp = math.atan2(e_vec @ q_dir, e_vec @ node_dir)
        p_dir = e_vec / e
    else:
        argp, p_dir = 0.0, node_dir
    nu = math.atan2(np.cross(p_dir, r) @ (h / hm), p_dir @ r)
    ecc_anom = 2.0 * math.atan2(math.sqrt(1.0 - e) * math.sin(nu / 2.0), math.sqrt(1.0 + e) * math.cos(nu / 2.0))
    mean_anom = ecc_anom - e * math.sin(ecc_anom)
    return a, e, inc, raan % TWO_PI, argp % TWO_PI, mean_anom % TWO_PI


def solve_kepler(mean_anom, e):
    """Eccentric anomaly from mean anomaly (vectorized Newton iteration)."""
    m = np.mod(np.asarray(mean_anom, dtype=float), TWO_PI)
    ecc = np.where(e < 0.8, m, np.pi * np.ones_like(m))
    for _ in range(50):
        delta = (ecc - e * np.sin(ecc) - m) / (1.0 - e * np.cos(ecc))
        ecc = ecc - delta
        if np.all(np.abs(delta) < 1e-15):
            break
    return ecc


def elements_to_states(a, e, inc, raan, argp, mean_anom, mu=MU_EARTH):
    """Vectorized: raan, argp and mean_anom may be arrays of equal length."""
    raan, argp, mean_anom = np.broadcast_arrays(*(np.atleast_1d(np.asarray(x, dtype=float))
                                                  for x in (raan, argp, mean_anom)))
    ecc = solve_kepler(mean_anom, e)
    cos_e, sin_e = np.cos(ecc), np.sin(ecc)
    b = a * math.sqrt(1.0 - e * e)
    x_pf = a * (cos_e - e)
    y_pf = b * sin_e
    rate = math.sqrt(mu / a ** 3) / (1.0 - e * cos_e)
    vx_pf = -a * sin_e * rate
    vy_pf = b * cos_e * rate

    co, so = np.cos(raan), np.sin(raan)
    cw, sw = np.cos(argp), np.sin(argp)
    ci, si = math.cos(inc), math.sin(inc)
    p_hat = np.stack([co * cw - so * sw * ci, so * cw + co * sw * ci, sw * si], axis=-1)
    q_hat = np.stack([-co * sw - so * cw * ci, -so * sw + co * cw * ci, cw * si], axis=-1)
    r = x_pf[:, None] * p_hat + y_pf[:, None] * q_hat
    v = vx_pf[:, None] * p_hat + vy_pf[:, None] * q_hat
    return r, v


# ==============================================================================
# PROPAGATORS
# ==============================================================================
def kepler_states(y0, times, mu=MU_EARTH):
    a, e, inc, raan, argp, m0 = state_to_elements(y0[:3], y0[3:], mu)
    n = math.sqrt(mu / a ** 3)
    return elements_to_states(a, e, inc, raan, argp, m0 + n * np.asarray(times, dtype=float), mu)


def j2_secular_rates(a, e, inc, mu=MU_EARTH, r_ref=R_GRAVITY_REF, j2=J2_EARTH):
    """First-order secular rates (rad/s) of node, argument of perigee and mean anomaly."""
    n = math.sqrt(mu / a ** 3)
    p = a * (1.0 - e * e)
    k = 1.5 * j2 * (r_ref / p) ** 2 * n
    ci, si2 = math.cos(inc), math.sin(inc) ** 2
    raan_dot = -k * ci
    argp_dot = k * (2.0 - 2.5 * si2)
    m_dot = n + k * math.sqrt(1.0 - e * e) * (1.0 - 1.5 * si2)
    return raan_dot, argp_dot, m_dot


def j2_mean_states(y0, times, mu=MU_EARTH, r_ref=R_GRAVITY_REF, j2=J2_EARTH):
    a, e, inc, raan, argp, m0 = state_to_elements(y0[:3], y0[3:], mu)
    raan_dot, argp_dot, m_dot = j2_secular_rates(a, e, inc, mu, r_ref, j2)
    t = np.asarray(times, dtype=float)
    return elements_to_states(a, e, inc, raan + raan_dot * t, argp + argp_dot * t, m0 + m_dot * t, mu)


class TLEPropagator:
    """SGP4 from a two-line element set; states come out in GCRF."""

    def __init__(self, line1, line2):
        from sgp4.api import Satrec, WGS72

        self.sat = Satrec.twoline2rv(line1.strip(), line2.strip(), WGS72)
        if self.sat.error:
            raise ValueError(f"Bad TLE (SGP4 error {self.sat.error})")
        # TLE epochs are UTC
        self.epoch = Epoch.from_jd(self.sat.jdsatepoch, self.sat.jdsatepochF, scale="UTC")

    def states(self, epoch, times):
        """GCRF states at `times` seconds after `epoch` (defaults to the TLE epoch)."""
        epoch = self.epoch if epoch is None else Epoch.coerce(epoch)
        t = np.asarray(times, dtype=float)
        jd1, jd2 = epoch.jd("UTC")
        offset_days = (jd1 - self.sat.jdsatepoch) + (jd2 - self.sat.jdsatepochF) + t / 86400.0
        # Pass the whole-day part and the fraction separately to keep sub-millisecond precision
        whole = np.full(t.shape, self.sat.jdsatepoch)
        frac = self.sat.jdsatepochF + offset_days
        err, r_km, v_kms = self.sat.sgp4_array(whole, frac)
        if np.any(err):
            bad = int(np.flatnonzero(err)[0])
            raise ValueError(f"SGP4 failed at t = {t[bad]:.1f} s (error {int(err[bad])})")
        return transform_state(r_km * 1e3, v_kms * 1e3, epoch, "TEME", "GCRF", offsets_s=t)


# ==============================================================================
# EVENTS
# ==============================================================================
_EVENT_FUNCTIONS = (
    ("perigee", lambda r, v: r @ v, 1.0),
    ("apogee", lambda r, v: r @ v, -1.0),
    ("ascending_node", lambda r, v: r[2], 1.0),
    ("descending_node", lambda r, v: r[2], -1.0),
)


def analytic_events(state_fn, times, epoch, apsides=True):
    """Apsis and node crossings of a closed-form trajectory.

    state_fn(t_array) -> (r, v) arrays. Sign changes on the `times` grid are refined
    with Brent's method on the exact state, so the grid only needs to resolve each
    half orbit. Same output as astro_engine.orbit_events.
    """
    times = np.asarray(times, dtype=float)
    r, v = state_fn(times)
    events = []
    for kind, g, direction in _EVENT_FUNCTIONS:
        if kind in ("perigee", "apogee") and not apsides:
            continue
        values = np.array([g(r[i], v[i]) for i in range(len(times))])
        scale = np.max(np.abs(values)) or 1.0
        for i in range(len(times) - 1):
            g0, g1 = values[i], values[i + 1]
            if i == 0 and abs(g0) < 1e-12 * scale and np.sign(g1) == direction:
                events.append(_event(kind, times[0], epoch))
            if g0 * g1 < 0 and np.sign(g1 - g0) == direction:
                f = lambda t: g(*(x[0] for x in state_fn(np.array([t]))))
                events.append(_event(kind, brentq(f, times[i], times[i + 1], xtol=1e-9, rtol=1e-14), epoch))
    events.sort(key=lambda ev: ev["t_s"])
    return events


def _event(kind, t, epoch):
    return {"type": kind, "t_s": float(t), "utc": (epoch + float(t)).iso("UTC")}

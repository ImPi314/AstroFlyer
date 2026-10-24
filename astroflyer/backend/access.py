"""
AstroFlyer HEO - ground-station access, eclipses, beta angle and reports.

Works on any tabulated GCRF trajectory (times in seconds after an epoch). Crossing
times are refined with brentq on an order-8 Lagrange interpolant of the samples,
so they are not tied to the output step; the Sun and Moon come from DE440.
"""

import csv
import io
import math

import numpy as np
from scipy.optimize import brentq, minimize_scalar

from . import frames as F
from .ephemeris import get_ephemeris
from .ephemeris_io import EphemerisTable
from .epoch import Epoch
from .forces import MU_EARTH, R_EARTH_EQ, R_SUN
from .mission import keplerian_from_state

R_MOON = 1737400.0
_XTOL_S = 1e-6


class GroundStation:
    """A site on the WGS-84 ellipsoid with a flat minimum elevation and an optional azimuth mask.

    mask is a list of (azimuth_deg, min_elevation_deg) points, interpolated linearly and
    wrapping at 360; the higher of the mask and min_elevation_deg applies.
    """

    def __init__(self, name, lat_deg, lon_deg, height_m=0.0, min_elevation_deg=0.0, mask=None):
        self.name = str(name)
        self.lat_deg, self.lon_deg, self.height_m = float(lat_deg), float(lon_deg), float(height_m)
        self.min_elevation_deg = float(min_elevation_deg)
        self.mask = None
        if mask:
            pts = sorted((float(az) % 360.0, float(el)) for az, el in mask)
            self.mask = (np.array([p[0] for p in pts]), np.array([p[1] for p in pts]))
        self.site_itrf = np.asarray(F.geodetic_to_itrf(self.lat_deg, self.lon_deg, self.height_m), dtype=float)
        lat, lon = math.radians(self.lat_deg), math.radians(self.lon_deg)
        self._enu = np.array([[-math.sin(lon), math.cos(lon), 0.0],
                              [-math.sin(lat) * math.cos(lon), -math.sin(lat) * math.sin(lon), math.cos(lat)],
                              [math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat)]])

    @classmethod
    def from_dict(cls, d):
        return cls(d["name"], d["lat_deg"], d["lon_deg"], d.get("height_m", 0.0),
                   d.get("min_elevation_deg", 0.0), d.get("mask"))

    def min_elevation_at(self, azimuth_deg):
        az = np.asarray(azimuth_deg, dtype=float) % 360.0
        if self.mask is None:
            out = np.full(az.shape, self.min_elevation_deg)
        else:
            out = np.maximum(np.interp(az, self.mask[0], self.mask[1], period=360.0), self.min_elevation_deg)
        return float(out) if out.ndim == 0 else out

    def look_angles(self, epoch, times, r_gcrf, v_gcrf=None):
        """Azimuth/elevation (deg), range (m) and, with velocities, range rate (m/s)."""
        epoch = Epoch.coerce(epoch)
        times = np.atleast_1d(np.asarray(times, dtype=float))
        r_gcrf = np.atleast_2d(np.asarray(r_gcrf, dtype=float))
        if v_gcrf is None:
            r_itrf = F.transform_position(r_gcrf, epoch, "GCRF", "ITRF", offsets_s=times)
            v_itrf = None
        else:
            r_itrf, v_itrf = F.transform_state(r_gcrf, np.atleast_2d(np.asarray(v_gcrf, dtype=float)), epoch,
                                               "GCRF", "ITRF", offsets_s=times)
        rho = np.atleast_2d(r_itrf) - self.site_itrf
        enu = rho @ self._enu.T
        rng = np.linalg.norm(rho, axis=1)
        out = {"azimuth_deg": np.degrees(np.arctan2(enu[:, 0], enu[:, 1])) % 360.0,
               "elevation_deg": np.degrees(np.arcsin(np.clip(enu[:, 2] / rng, -1.0, 1.0))),
               "range_m": rng}
        if v_itrf is not None:
            out["range_rate_ms"] = np.sum(rho * np.atleast_2d(v_itrf), axis=1) / rng
        return out


def _table(epoch, times, r, v):
    return EphemerisTable([epoch + float(x) for x in times], r, v)


def _crossings(times, g, fn):
    """Refined zeros of fn (sampled as g on times), as (t, rising) pairs."""
    out = []
    for i in np.nonzero(np.signbit(g[:-1]) != np.signbit(g[1:]))[0]:
        t = brentq(fn, times[i], times[i + 1], xtol=_XTOL_S)
        out.append((t, bool(g[i + 1] >= 0.0)))
    return out


def station_passes(station, epoch, times, r, v):
    """Visibility passes of one station: AOS, TCA, LOS (Epochs), max elevation and duration.

    A pass already in progress at the first sample, or still open at the last, is
    clipped to the span and marked partial.
    """
    epoch = Epoch.coerce(epoch)
    times = np.asarray(times, dtype=float)
    table = _table(epoch, times, r, v)

    def look(t):
        rr, vv = table.state_at([float(t) - times[0]])
        return station.look_angles(epoch, [t], rr, vv)

    def margin(t):
        la = look(t)
        return float(la["elevation_deg"][0] - station.min_elevation_at(la["azimuth_deg"][0]))

    la = station.look_angles(epoch, times, r, v)
    g = la["elevation_deg"] - station.min_elevation_at(la["azimuth_deg"])
    edges = _crossings(times, g, margin)
    if g[0] >= 0.0:
        edges.insert(0, (float(times[0]), True))
    if g[-1] >= 0.0:
        edges.append((float(times[-1]), False))

    passes = []
    for (t_aos, _), (t_los, _) in zip(edges[0::2], edges[1::2]):
        if t_los <= t_aos:
            continue
        res = minimize_scalar(lambda t: -float(look(t)["elevation_deg"][0]), bounds=(t_aos, t_los),
                              method="bounded", options={"xatol": 1e-3})
        t_tca = float(res.x)
        aos, los = epoch + t_aos, epoch + t_los
        passes.append({"station": station.name, "aos": aos, "los": los, "tca": epoch + t_tca,
                       "duration_s": los - aos, "max_elevation_deg": -float(res.fun),
                       "aos_azimuth_deg": float(look(t_aos)["azimuth_deg"][0]),
                       "los_azimuth_deg": float(look(t_los)["azimuth_deg"][0]),
                       "partial": bool(t_aos == times[0] or t_los == times[-1])})
    return passes


# ==============================================================================
# SHADOWS
# ==============================================================================
def _sun_moon(epoch, times):
    eph = get_ephemeris()
    tt0 = float(Epoch.coerce(epoch) - Epoch.j2000())
    pairs = [eph.sun_moon_gcrf(tt0 + float(t)) for t in np.atleast_1d(times)]
    return np.array([p[0] for p in pairs]), np.array([p[1] for p in pairs])


def _cone_angles(r, r_sun, r_body, radius):
    """Angular radii of the Sun (a) and the occulting body (b), and their separation (c), seen from r."""
    d_sun = r_sun - r
    d_body = r_body - r
    ds = np.linalg.norm(d_sun, axis=-1)
    db = np.linalg.norm(d_body, axis=-1)
    a = np.arcsin(np.minimum(1.0, R_SUN / ds))
    b = np.arcsin(np.minimum(1.0, radius / db))
    c = np.arccos(np.clip(np.sum(d_sun * d_body, axis=-1) / (ds * db), -1.0, 1.0))
    return a, b, c


def _visible_fraction(a, b, c):
    """Visible fraction of the solar disc (conical model, Montenbruck & Gill 3.4.2), vectorized."""
    a, b, c = np.broadcast_arrays(np.asarray(a, float), np.asarray(b, float), np.asarray(c, float))
    nu = np.ones(a.shape)
    full = c < b - a
    annular = (c < a - b) & ~full
    partial = (c < a + b) & ~full & ~annular
    nu[full] = 0.0
    nu[annular] = 1.0 - (b[annular] / a[annular]) ** 2
    if np.any(partial):
        aa, bb, cc = a[partial], b[partial], c[partial]
        x = (cc * cc + aa * aa - bb * bb) / (2.0 * cc)
        y = np.sqrt(np.maximum(0.0, aa * aa - x * x))
        area = aa * aa * np.arccos(np.clip(x / aa, -1.0, 1.0)) \
            + bb * bb * np.arccos(np.clip((cc - x) / bb, -1.0, 1.0)) - cc * y
        nu[partial] = 1.0 - area / (np.pi * aa * aa)
    return nu


_BODIES = {"EARTH": R_EARTH_EQ, "MOON": R_MOON}


def _occulter_positions(name, r_moon):
    return np.zeros_like(r_moon) if name == "EARTH" else r_moon


def shadow_fraction(epoch, times, r, occulters=("EARTH", "MOON")):
    """Fraction of the solar disc visible at each sample (1 sunlit, 0 umbra)."""
    r = np.atleast_2d(np.asarray(r, dtype=float))
    r_sun, r_moon = _sun_moon(epoch, times)
    nu = np.ones(len(r))
    for name in occulters:
        nu *= _visible_fraction(*_cone_angles(r, r_sun, _occulter_positions(name.upper(), r_moon),
                                              _BODIES[name.upper()]))
    return nu


def eclipse_intervals(epoch, times, r, occulters=("EARTH", "MOON")):
    """Penumbra and umbra intervals per occulting body, with refined start and end Epochs.

    Penumbra means part of the Sun is hidden (an annular phase counts as penumbra);
    umbra means all of it is. Entry and exit share their boundary Epoch with the umbra.
    """
    epoch = Epoch.coerce(epoch)
    times = np.asarray(times, dtype=float)
    r = np.atleast_2d(np.asarray(r, dtype=float))
    v = np.gradient(r, times, axis=0) if len(times) > 1 else np.zeros_like(r)
    table = _table(epoch, times, r, v)
    r_sun, r_moon = _sun_moon(epoch, times)
    out = []
    for name in (o.upper() for o in occulters):
        radius = _BODIES[name]
        a, b, c = _cone_angles(r, r_sun, _occulter_positions(name, r_moon), radius)

        def geometry(t, name=name, radius=radius):
            rr, _ = table.state_at([float(t) - times[0]])
            s, m = _sun_moon(epoch, [t])
            return _cone_angles(rr, s, _occulter_positions(name, m), radius)

        cuts = []
        for g, fn in ((c - (a + b), lambda t: float(np.subtract(*_sum_ab(geometry(t))))),
                      (c - (b - a), lambda t: float(np.subtract(*_diff_ba(geometry(t)))))):
            cuts += [t for t, _ in _crossings(times, g, fn)]
        bounds = [float(times[0])] + sorted(cuts) + [float(times[-1])]
        stamps = [epoch + t for t in bounds]

        current = None
        for k in range(len(bounds) - 1):
            if bounds[k + 1] <= bounds[k]:
                continue
            aa, bb, cc = geometry(0.5 * (bounds[k] + bounds[k + 1]))
            kind = "umbra" if cc[0] < bb[0] - aa[0] else "penumbra" if cc[0] < aa[0] + bb[0] else None
            if current is not None and current["kind"] == kind:
                current["end"] = stamps[k + 1]
                continue
            if current is not None:
                out.append(current)
            current = None if kind is None else {"body": name, "kind": kind, "start": stamps[k], "end": stamps[k + 1]}
        if current is not None:
            out.append(current)
    for ev in out:
        ev["duration_s"] = ev["end"] - ev["start"]
        ev["partial"] = bool(ev["start"] == epoch + float(times[0]) or ev["end"] == epoch + float(times[-1]))
    out.sort(key=lambda ev: (ev["start"] - epoch, ev["body"]))
    return out


def _sum_ab(abc):
    a, b, c = abc
    return c[0], a[0] + b[0]


def _diff_ba(abc):
    a, b, c = abc
    return c[0], b[0] - a[0]


def beta_angle(epoch, times, r, v):
    """Angle (deg) between the Sun direction and the orbit plane, positive on the angular-momentum side."""
    r = np.atleast_2d(np.asarray(r, dtype=float))
    h = np.cross(r, np.atleast_2d(np.asarray(v, dtype=float)))
    h /= np.linalg.norm(h, axis=1)[:, None]
    r_sun, _ = _sun_moon(epoch, times)
    s = r_sun / np.linalg.norm(r_sun, axis=1)[:, None]
    # atan2 keeps full precision near +-90 deg, where arcsin of the dot product does not
    return np.degrees(np.arctan2(np.sum(h * s, axis=1), np.linalg.norm(np.cross(h, s), axis=1)))


# ==============================================================================
# REPORTS
# ==============================================================================
_ELEMENTS = {"SMA": ("a", 1e-3), "ECC": ("e", 1.0), "INC": ("inc", None), "RAAN": ("raan", None),
             "AOP": ("argp", None), "TA": ("ta", None)}
_STATION_FIELDS = {"Elevation": ("elevation_deg", 1.0), "Azimuth": ("azimuth_deg", 1.0),
                   "Range": ("range_m", 1e-3), "RangeRate": ("range_rate_ms", 1e-3)}
REPORT_PARAMETERS = (["Epoch", "ElapsedSecs", "ElapsedDays", "Altitude", "Latitude", "Longitude", "RMAG", "VMAG",
                      "X", "Y", "Z", "VX", "VY", "VZ", "BetaAngle", "ShadowFraction"] + list(_ELEMENTS)
                     + [f"{k}.<station>" for k in _STATION_FIELDS])


def report(epoch, times, r, v, parameters, stations=None):
    """Columns for any list of parameter names (km, km/s, deg; Epoch as UTC ISO strings), in order."""
    epoch = Epoch.coerce(epoch)
    times = np.asarray(times, dtype=float)
    r = np.atleast_2d(np.asarray(r, dtype=float))
    v = np.atleast_2d(np.asarray(v, dtype=float))
    by_name = {s.name: s for s in (stations or [])}
    cache = {}

    def geodetic():
        if "geo" not in cache:
            cache["geo"] = F.gcrf_to_geodetic(r, epoch, offsets_s=times)
        return cache["geo"]

    def elements():
        if "kep" not in cache:
            cache["kep"] = [keplerian_from_state(ri, vi, MU_EARTH) for ri, vi in zip(r, v)]
        return cache["kep"]

    table = {}
    for name in parameters:
        if name == "Epoch":
            col = [(epoch + float(t)).iso("UTC") for t in times]
        elif name == "ElapsedSecs":
            col = times.copy()
        elif name == "ElapsedDays":
            col = times / 86400.0
        elif name in ("Latitude", "Longitude", "Altitude"):
            lat, lon, h = geodetic()
            col = {"Latitude": lat, "Longitude": lon, "Altitude": np.asarray(h) / 1e3}[name]
        elif name == "RMAG":
            col = np.linalg.norm(r, axis=1) / 1e3
        elif name == "VMAG":
            col = np.linalg.norm(v, axis=1) / 1e3
        elif name in ("X", "Y", "Z"):
            col = r[:, "XYZ".index(name)] / 1e3
        elif name in ("VX", "VY", "VZ"):
            col = v[:, ["VX", "VY", "VZ"].index(name)] / 1e3
        elif name == "BetaAngle":
            col = beta_angle(epoch, times, r, v)
        elif name == "ShadowFraction":
            col = shadow_fraction(epoch, times, r)
        elif name in _ELEMENTS:
            key, scale = _ELEMENTS[name]
            vals = np.array([k[key] for k in elements()])
            col = np.degrees(vals) if scale is None else vals * scale
        elif "." in name and name.split(".", 1)[0] in _STATION_FIELDS:
            field, st_name = name.split(".", 1)
            if st_name not in by_name:
                raise ValueError(f"Report parameter {name!r}: no ground station named {st_name!r}")
            key = ("look", st_name)
            if key not in cache:
                cache[key] = by_name[st_name].look_angles(epoch, times, r, v)
            src, scale = _STATION_FIELDS[field]
            col = cache[key][src] * scale
        else:
            raise ValueError(f"Unknown report parameter {name!r}; choose from {', '.join(REPORT_PARAMETERS)}")
        table[name] = col
    return table


def write_report_csv(path, table):
    """Writes the report as CSV (to path, if given) and returns the text."""
    names = list(table)
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(names)
    for row in zip(*(table[n] for n in names)):
        writer.writerow([x if isinstance(x, str) else repr(float(x)) for x in row])
    text = buf.getvalue()
    if path:
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
    return text


def analyze(epoch, times, r, v, stations=(), parameters=("Epoch",), occulters=("EARTH", "MOON")):
    """Passes, eclipses, beta angle and a report for one trajectory, JSON-ready."""
    epoch = Epoch.coerce(epoch)

    def iso(ep):
        return ep.iso("UTC", 6)

    passes = {}
    for st in stations:
        passes[st.name] = [{"aos_utc": iso(p["aos"]), "tca_utc": iso(p["tca"]), "los_utc": iso(p["los"]),
                            "duration_s": p["duration_s"], "max_elevation_deg": p["max_elevation_deg"],
                            "aos_azimuth_deg": p["aos_azimuth_deg"], "los_azimuth_deg": p["los_azimuth_deg"],
                            "partial": p["partial"]}
                           for p in station_passes(st, epoch, times, r, v)]
    eclipses = [{"body": ev["body"], "kind": ev["kind"], "start_utc": iso(ev["start"]), "end_utc": iso(ev["end"]),
                 "duration_s": ev["duration_s"], "partial": ev["partial"]}
                for ev in eclipse_intervals(epoch, times, r, occulters)]
    table = report(epoch, times, r, v, list(parameters), stations=list(stations))
    return {"passes": passes, "eclipses": eclipses,
            "beta_angle_deg": beta_angle(epoch, times, r, v).tolist(),
            "report": {k: (col if isinstance(col, list) else np.asarray(col).tolist()) for k, col in table.items()}}

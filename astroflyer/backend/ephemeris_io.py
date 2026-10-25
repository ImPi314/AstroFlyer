"""
AstroFlyer HEO - Ephemeris files and the ephemeris propagator
=============================================================================
  CCSDS OEM 2.0 (KVN)   read / write    Orbit Ephemeris Message
  CCSDS OPM 2.0 (KVN)   read / write    Orbit Parameter Message (single state)
  SP3-c / SP3-d         read            precise orbits (ITRF, km), converted to GCRF
  EphemerisTable        Lagrange interpolation (default 8th order, 9 points) of
                        position and velocity between tabulated states

All states are GCRF metres and m/s at Epoch instants. Files are written with
REF_FRAME = GCRF (or EME2000 when asked) and TIME_SYSTEM = UTC.
=============================================================================
"""

import math
from datetime import datetime, timezone

import numpy as np

from .epoch import Epoch
from .frames import transform_state

CCSDS_FRAMES = {"GCRF": "GCRF", "ICRF": "GCRF", "EME2000": "EME2000", "J2000": "EME2000", "TEME": "TEME",
                "ITRF": "ITRF", "ITRF2014": "ITRF", "ITRF2020": "ITRF", "ITRF-93": "ITRF", "ITRF-97": "ITRF",
                "ITRF2000": "ITRF", "ITRF2008": "ITRF", "TOD": "TOD", "MOD": "MOD"}


# ==============================================================================
# EPHEMERIS TABLE AND PROPAGATOR
# ==============================================================================
class EphemerisTable:
    """Tabulated GCRF states with Lagrange interpolation.

    Interpolates position and velocity independently over the `order + 1` nearest
    points (order 8 by default; 10 is the usual alternative). Requests outside the
    table raise ValueError rather than extrapolate.
    """

    def __init__(self, epochs, positions_m, velocities_ms, order=8, name=None):
        if len(epochs) < 2:
            raise ValueError("An ephemeris needs at least two states")
        self.epoch0 = Epoch.coerce(epochs[0])
        self.t = np.array([Epoch.coerce(ep) - self.epoch0 for ep in epochs], dtype=float)
        if np.any(np.diff(self.t) <= 0):
            raise ValueError("Ephemeris epochs must be strictly increasing")
        self.r = np.asarray(positions_m, dtype=float)
        self.v = np.asarray(velocities_ms, dtype=float)
        self.order = int(min(order, len(self.t) - 1))
        self.name = name

    @property
    def start(self):
        return self.epoch0 + float(self.t[0])

    @property
    def stop(self):
        return self.epoch0 + float(self.t[-1])

    def _window(self, ts):
        n = self.order + 1
        idx = np.searchsorted(self.t, ts) - n // 2
        return np.clip(idx, 0, len(self.t) - n)

    def state_at(self, epochs_or_seconds):
        """GCRF (r, v) at Epochs, ISO strings, or seconds after the table's first epoch."""
        items = np.atleast_1d(np.asarray(epochs_or_seconds, dtype=object))
        ts = np.array([(Epoch.coerce(x) - self.epoch0) if not isinstance(x, (int, float, np.floating, np.integer))
                       else float(x) for x in items], dtype=float)
        if np.any(ts < self.t[0] - 1e-6) or np.any(ts > self.t[-1] + 1e-6):
            raise ValueError("Requested time is outside the ephemeris span")
        n = self.order + 1
        r_out = np.empty((len(ts), 3))
        v_out = np.empty((len(ts), 3))
        for k, (tk, i0) in enumerate(zip(ts, self._window(ts))):
            nodes = self.t[i0:i0 + n]
            weights = np.ones(n)
            for j in range(n):
                others = np.delete(nodes, j)
                weights[j] = np.prod((tk - others) / (nodes[j] - others))
            r_out[k] = weights @ self.r[i0:i0 + n]
            v_out[k] = weights @ self.v[i0:i0 + n]
        return r_out, v_out


# ==============================================================================
# CCSDS KVN HELPERS
# ==============================================================================
def _ccsds_time(epoch):
    return Epoch.coerce(epoch).iso("UTC", 6).rstrip("Z")


def _parse_ccsds_time(text, scale="UTC"):
    text = text.strip()
    if "T" not in text:
        # Day-of-year form YYYY-DDDThh:mm:ss is handled below; plain date gets midnight
        text = text + "T00:00:00"
    date_part, time_part = text.split("T", 1)
    if len(date_part) == 8:      # YYYY-DDD
        day = datetime.strptime(date_part, "%Y-%j").replace(tzinfo=timezone.utc)
        date_part = day.strftime("%Y-%m-%d")
    return Epoch.from_iso(f"{date_part}T{time_part}", scale=scale)


def _to_gcrf(r, v, epoch, frame):
    canonical = CCSDS_FRAMES.get(frame.upper())
    if canonical is None:
        raise ValueError(f"Unsupported REF_FRAME {frame!r}")
    if canonical == "GCRF":
        return np.asarray(r, float), np.asarray(v, float)
    return transform_state(r, v, epoch, canonical, "GCRF")


def _from_gcrf(r, v, epoch, frame):
    canonical = CCSDS_FRAMES.get(frame.upper())
    if canonical is None:
        raise ValueError(f"Unsupported REF_FRAME {frame!r}")
    if canonical == "GCRF":
        return np.asarray(r, float), np.asarray(v, float)
    return transform_state(r, v, epoch, "GCRF", canonical)


def _header(kind, version="2.0", originator="AstroFlyer"):
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    return [f"CCSDS_{kind}_VERS = {version}", f"CREATION_DATE = {created}", f"ORIGINATOR = {originator}", ""]


def _kvn_pairs(lines):
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("COMMENT"):
            continue
        if "=" in stripped:
            key, value = stripped.split("=", 1)
            yield key.strip().upper(), value.split("[")[0].strip()
        else:
            yield None, stripped


# ==============================================================================
# OEM
# ==============================================================================
def write_oem(path, epochs, positions_m, velocities_ms, object_name="SATELLITE", object_id="NONE",
              ref_frame="GCRF", interpolation_degree=7):
    """Writes one OEM segment (km, km/s) in `ref_frame`, UTC."""
    epochs = [Epoch.coerce(ep) for ep in epochs]
    lines = _header("OEM") + [
        "META_START",
        f"OBJECT_NAME = {object_name}",
        f"OBJECT_ID = {object_id}",
        "CENTER_NAME = EARTH",
        f"REF_FRAME = {ref_frame}",
        "TIME_SYSTEM = UTC",
        f"START_TIME = {_ccsds_time(epochs[0])}",
        f"STOP_TIME = {_ccsds_time(epochs[-1])}",
        "INTERPOLATION = LAGRANGE",
        f"INTERPOLATION_DEGREE = {interpolation_degree}",
        "META_STOP",
        "",
    ]
    for ep, r, v in zip(epochs, positions_m, velocities_ms):
        r_out, v_out = _from_gcrf(r, v, ep, ref_frame)
        lines.append(f"{_ccsds_time(ep)} " + " ".join(f"{x / 1e3:.6f}" for x in r_out)
                     + " " + " ".join(f"{x / 1e3:.9f}" for x in v_out))
    text = "\n".join(lines) + "\n"
    if path is not None:
        with open(path, "w") as fh:
            fh.write(text)
    return text


def read_oem(path_or_text):
    """Reads every segment of a KVN OEM; returns a list of EphemerisTable (GCRF)."""
    text = _read_text(path_or_text)
    segments, meta, rows, in_meta, in_cov = [], {}, [], False, False

    def flush():
        if rows:
            scale = meta.get("TIME_SYSTEM", "UTC")
            epochs = [_parse_ccsds_time(row[0], scale) for row in rows]
            r = np.array([[float(x) * 1e3 for x in row[1:4]] for row in rows])
            v = np.array([[float(x) * 1e3 for x in row[4:7]] for row in rows])
            frame = meta.get("REF_FRAME", "GCRF")
            if CCSDS_FRAMES.get(frame.upper()) != "GCRF":
                conv = [_to_gcrf(ri, vi, ep, frame) for ri, vi, ep in zip(r, v, epochs)]
                r = np.array([c[0] for c in conv])
                v = np.array([c[1] for c in conv])
            order = int(meta.get("INTERPOLATION_DEGREE", 8))
            segments.append(EphemerisTable(epochs, r, v, order=max(order, 1), name=meta.get("OBJECT_NAME")))

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("COMMENT"):
            continue
        if line == "META_START":
            flush()
            rows, meta, in_meta = [], {}, True
            continue
        if line == "META_STOP":
            in_meta = False
            continue
        if line in ("COVARIANCE_START", "COVARIANCE_STOP"):
            in_cov = line == "COVARIANCE_START"
            continue
        if in_meta and "=" in line:
            key, value = line.split("=", 1)
            meta[key.strip().upper()] = value.strip()
        elif not in_meta and not in_cov and "=" not in line:
            parts = line.split()
            if len(parts) >= 7:
                rows.append(parts)
    flush()
    if not segments:
        raise ValueError("No ephemeris data lines found in the OEM")
    return segments


# ==============================================================================
# OPM
# ==============================================================================
def write_opm(path, epoch, r_m, v_ms, object_name="SATELLITE", object_id="NONE", ref_frame="GCRF",
              mass_kg=None, drag_area_m2=None, cd=None, srp_area_m2=None, cr=None):
    epoch = Epoch.coerce(epoch)
    r_out, v_out = _from_gcrf(r_m, v_ms, epoch, ref_frame)
    lines = _header("OPM") + [
        f"OBJECT_NAME = {object_name}",
        f"OBJECT_ID = {object_id}",
        "CENTER_NAME = EARTH",
        f"REF_FRAME = {ref_frame}",
        "TIME_SYSTEM = UTC",
        "",
        f"EPOCH = {_ccsds_time(epoch)}",
    ]
    for name, value in zip(("X", "Y", "Z"), r_out):
        lines.append(f"{name} = {value / 1e3:.6f} [km]")
    for name, value in zip(("X_DOT", "Y_DOT", "Z_DOT"), v_out):
        lines.append(f"{name} = {value / 1e3:.9f} [km/s]")
    if mass_kg is not None:
        lines += ["", f"MASS = {mass_kg:.3f} [kg]"]
        if srp_area_m2 is not None:
            lines.append(f"SOLAR_RAD_AREA = {srp_area_m2:.3f} [m**2]")
        if cr is not None:
            lines.append(f"SOLAR_RAD_COEFF = {cr:.3f}")
        if drag_area_m2 is not None:
            lines.append(f"DRAG_AREA = {drag_area_m2:.3f} [m**2]")
        if cd is not None:
            lines.append(f"DRAG_COEFF = {cd:.3f}")
    text = "\n".join(lines) + "\n"
    if path is not None:
        with open(path, "w") as fh:
            fh.write(text)
    return text


def read_opm(path_or_text):
    """Returns a dict with epoch, r_m, v_ms (GCRF), object_name and any spacecraft parameters."""
    values = dict(pair for pair in _kvn_pairs(_read_text(path_or_text).splitlines()) if pair[0])
    scale = values.get("TIME_SYSTEM", "UTC")
    epoch = _parse_ccsds_time(values["EPOCH"], scale)
    r = np.array([float(values[k]) for k in ("X", "Y", "Z")]) * 1e3
    v = np.array([float(values[k]) for k in ("X_DOT", "Y_DOT", "Z_DOT")]) * 1e3
    r, v = _to_gcrf(r, v, epoch, values.get("REF_FRAME", "GCRF"))
    out = {"epoch": epoch, "r_m": r, "v_ms": v, "object_name": values.get("OBJECT_NAME")}
    for key, name in (("MASS", "mass_kg"), ("SOLAR_RAD_AREA", "srp_area_m2"), ("SOLAR_RAD_COEFF", "cr"),
                      ("DRAG_AREA", "drag_area_m2"), ("DRAG_COEFF", "cd")):
        if key in values:
            out[name] = float(values[key])
    return out


# ==============================================================================
# SP3
# ==============================================================================
def read_sp3(path_or_text, satellite=None, order=8):
    """Reads SP3-c/d position (and velocity, when present) records for one satellite.

    SP3 orbits are Earth-fixed (ITRF-family) in km, usually GPS time. When the file has
    no velocity records, velocities come from differentiating the Lagrange polynomial
    through the neighbouring positions. Returns an EphemerisTable in GCRF.
    """
    lines = _read_text(path_or_text).splitlines()
    if not lines or not lines[0].startswith("#"):
        raise ValueError("Not an SP3 file")
    time_system = "GPS"
    for line in lines:
        if line.startswith("%c") and len(line) > 12 and line[9:12].strip():
            time_system = line[9:12].strip()
            break
    epochs, pos, vel = [], {}, {}
    current = None
    for line in lines:
        if line.startswith("*  "):
            parts = line[1:].split()
            year, month, day, hour, minute = (int(x) for x in parts[:5])
            sec = float(parts[5])
            iso = f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{sec:09.6f}"
            current = Epoch.from_iso(iso, scale=time_system if time_system in ("GPS", "UTC", "TAI", "TT") else "GPS")
            epochs.append(current)
        elif line.startswith("P") and current is not None:
            sat = line[1:4].strip()
            if satellite is None:
                satellite = sat
            if sat == satellite:
                xyz = [float(line[4 + 14 * i:18 + 14 * i]) for i in range(3)]
                pos[len(epochs) - 1] = np.array(xyz) * 1e3
        elif line.startswith("V") and current is not None:
            sat = line[1:4].strip()
            if sat == satellite:
                # SP3 velocities are dm/s
                xyz = [float(line[4 + 14 * i:18 + 14 * i]) for i in range(3)]
                vel[len(epochs) - 1] = np.array(xyz) * 0.1
    keys = sorted(pos)
    if len(keys) < 2:
        raise ValueError(f"Fewer than two positions for satellite {satellite!r}")
    ep = [epochs[k] for k in keys]
    r_itrf = np.array([pos[k] for k in keys])
    if all(k in vel for k in keys):
        v_itrf = np.array([vel[k] for k in keys])
    else:
        t = np.array([e - ep[0] for e in ep])
        v_itrf = _lagrange_derivative_at_nodes(t, r_itrf, order)
    conv = [transform_state(r, v, e, "ITRF", "GCRF") for r, v, e in zip(r_itrf, v_itrf, ep)]
    return EphemerisTable(ep, np.array([c[0] for c in conv]), np.array([c[1] for c in conv]), order=order,
                          name=satellite)


def _lagrange_derivative_at_nodes(t, values, order):
    """d/dt of the Lagrange interpolant through the order + 1 nearest nodes, at each node."""
    n = min(order, len(t) - 1) + 1
    out = np.empty_like(values)
    for k, tk in enumerate(t):
        i0 = int(np.clip(k - n // 2, 0, len(t) - n))
        nodes = t[i0:i0 + n]
        me = k - i0
        weights = np.empty(n)
        for j in range(n):
            if j == me:
                weights[j] = sum(1.0 / (tk - nodes[m]) for m in range(n) if m != me)
            else:
                num = np.prod([tk - nodes[m] for m in range(n) if m not in (j, me)])
                den = np.prod([nodes[j] - nodes[m] for m in range(n) if m != j])
                weights[j] = num / den
        out[k] = weights @ values[i0:i0 + n]
    return out


def _read_text(path_or_text):
    if "\n" in path_or_text or path_or_text.lstrip().startswith(("CCSDS", "#")):
        return path_or_text
    with open(path_or_text) as fh:
        return fh.read()

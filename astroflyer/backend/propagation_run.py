"""
AstroFlyer HEO - Propagation run
=============================================================================
run(request) -> report is the run behind /api/propagate: it reads the request,
propagates (ThirdReviewEngine), predicts the events and builds the report the
console shows.

The request uses the console's field names (missing fields take the defaults
in _DEFAULTS); a value that cannot be what its field names is a ValueError,
never silently replaced:

  orbit         a (km), e, inc, raan, aop, ta (deg), or hp, ha (km above the
                WGS-84 equatorial radius), or position_km + velocity_kms (GCRF);
                Keplerian elements must be elliptic, escape trajectories are
                given as a Cartesian state with duration_s
  epoch         ISO 8601, UTC unless tagged TAI/TT/TDB/UT1/GPS (default J2000.0)
  span          duration_s (0 to 30 days), else num_orbits (0.5 to 20)
  output        num_points, else points_per_orbit (kept between 200 and 3,600)
  propagator    model, method, tolerance, step_s, steering, fidelity, gravity_degree (2 to 70,
                degree and order of the full model's EGM2008 field, default 8)
  forces        enable_drag, enable_third_body, enable_srp
  spacecraft    mass, dry_mass, fuel_mass (kg), cd, drag_area, cr, srp_area (m^2)
  preset        the mission's name, echoed in the report
  burns         impulsive burns, applied in list order (at most 20): {timing, t_s, dv_ms, frame,
                isp_s, name}. timing "elapsed" burns at t_s seconds after the start; "perigee" or
                "apogee" at the first such apsis after the previous burn (or the start). dv_ms is
                the velocity change in m/s in frame VNC (default), RTN or GCRF; isp_s (default
                300 s) sets the propellant by the rocket equation, and the mass after a burn sets
                Cd*A/m and Cr*A/m of the rest of the run. Each burn is a restart of the
                integration from the burned state.

Every report has final_state {utc (to the microsecond), t_s, position_km, velocity_kms (GCRF),
mass_kg}: the state a later run can start from with new settings. A run with burns also has
burns, one entry per requested burn with what happened (applied false when the run ended first).

A start below the WGS-84 surface is refused. A run that reaches the surface stops there: the
report has status "impact" and impact {t_s, utc, latitude_deg, longitude_deg}, and leaves out
the reports of a whole orbit.
=============================================================================
"""

import math
import time
from datetime import date as _date

import numpy as np

from . import forces, mission
from .astro_engine import MU_EARTH, R_EARTH_EQ, ThirdReviewEngine, keplerian_to_cartesian
from .ccsds_exporter import CCSDSExporter
from .covariance_engine import CovarianceEngine
from .epoch import Epoch
from .event_predictor import EventPredictor
from .frames import gcrf_to_geodetic
from .radiation_belts import RadiationBeltModel
from .trajectory_engine import MissionScriptWorkbench

MAX_DURATION_S = 30 * 86400.0
_R_EQ_KM = R_EARTH_EQ / 1000.0
_E_MIN = 1e-6       # a numerically circular orbit: keeps the perigee direction defined
_DEFAULTS = {
    "a": 24389.0, "e": 0.728525, "inc": 28.5, "raan": 45.0, "aop": 30.0, "ta": 0.0,
    "num_orbits": 3.0, "points_per_orbit": 400, "model": "coupled", "method": "DOP853",
    "tolerance": 1e-10, "enable_drag": True, "enable_third_body": True, "enable_srp": True,
    "mass": 1500.0, "dry_mass": 1000.0, "fuel_mass": 500.0, "cd": 2.2, "drag_area": 15.0,
    "cr": 1.2, "srp_area": 15.0, "gravity_degree": 8, "fidelity": "full", "preset": "Custom HEO",
}


def run(request):
    """The propagation run for `request` (see the module docstring); returns the report."""
    q = _Request(request)
    epoch = Epoch.coerce(q.text("epoch") or None)
    duration_s = q.number("duration_s", None)
    if duration_s is not None and not 0.0 < duration_s <= MAX_DURATION_S:
        raise ValueError("duration_s must be between 0 and 2592000 s (30 days)")
    num_orbits = q.number("num_orbits")
    if duration_s is None and not 0.5 <= num_orbits <= 20.0:
        raise ValueError("num_orbits must be between 0.5 and 20")

    initial_state, r0, v0, (a_km, e, inc, raan, aop, ta) = initial_conditions(q)
    if initial_state == "cartesian":
        height_km = float(np.ravel(gcrf_to_geodetic(np.atleast_2d(r0), epoch)[2])[0]) / 1000.0
        if height_km < 0.0:
            raise ValueError(f"The initial position is {-height_km:.1f} km below the Earth's surface "
                             "(WGS-84 ellipsoid)")
    closed = a_km > 0.0 and e < 1.0
    if not closed and duration_s is None:
        raise ValueError("The initial state is an escape trajectory (e >= 1), which has no period, "
                         "so give the run length as duration_s")
    period = 2.0 * math.pi * math.sqrt((a_km * 1000.0) ** 3 / MU_EARTH) if closed else math.inf
    run_s = duration_s if duration_s is not None else num_orbits * period

    num_points = int(q.number("num_points", 0))
    if num_points <= 0:
        per_orbit = q.number("points_per_orbit")
        if duration_s is None:
            num_points = int(per_orbit * num_orbits)
        elif initial_state == "cartesian":
            num_points = int(duration_s / 60.0)     # one a minute: the state may not be a closed orbit
        else:
            num_points = int(per_orbit * duration_s / period)
    num_points = max(200, min(3600, num_points))

    mass = q.number("mass")
    if mass < 10.0:
        raise ValueError("mass must be at least 10 kg")
    cd, drag_area, cr, srp_area = (q.number(k) for k in ("cd", "drag_area", "cr", "srp_area"))
    if min(cd, drag_area, cr, srp_area) < 0.0:
        raise ValueError("cd, drag_area, cr and srp_area cannot be negative")
    fidelity = q.text("fidelity")
    if fidelity not in ("full", "ecr_mf"):
        raise ValueError("fidelity must be 'full' or 'ecr_mf'")
    model, method, tol = q.text("model"), q.text("method"), q.number("tolerance")
    degree = q.number("gravity_degree")
    if not (2 <= degree <= 70 and float(degree).is_integer()):
        raise ValueError("gravity_degree must be a whole number from 2 to 70")
    full_model = model.lower() not in _ZONAL_DEGREE
    degree = int(degree) if full_model else _ZONAL_DEGREE[model.lower()]
    forces_on = {k: q.boolean(k) for k in ("enable_drag", "enable_third_body", "enable_srp")}
    burns = _burn_plan(q.values.get("burns"), run_s)

    if q.text("steering") and burns:
        raise ValueError("Covariance steering runs without burns: its uncertainty does not carry across "
                         "a burn. Turn steering off or remove the burns")
    propagate_options = dict(
        model=model, method=method, rtol=tol, atol=tol, **forces_on,
        fixed_step=q.number("step_s", 0.0) or None, steering=q.text("steering") or None, fidelity=fidelity,
        **({"gravity_degree": degree, "gravity_order": degree} if full_model else {}))

    started = time.time()
    sol, burn_reports, burn_notes, final_mass, legs_closed = _propagate_with_burns(
        r0, v0, epoch, run_s, num_points, burns, mass, cd * drag_area, cr * srp_area, propagate_options)
    solve_s = time.time() - started

    config = {
        "preset_name": q.text("preset"),
        "semi_major_axis_km": round(a_km, 3), "eccentricity": round(e, 6),
        "inclination_deg": round(inc, 3), "raan_deg": round(raan, 3),
        "arg_perigee_deg": round(aop, 3), "true_anomaly_deg": round(ta, 3),
        "perigee_alt_km": round(a_km * (1.0 - e) - _R_EQ_KM, 2),
        "apogee_alt_km": round(a_km * (1.0 + e) - _R_EQ_KM, 2) if closed else None,
        "orbital_period_hours": round(period / 3600.0, 3) if closed else None,
        "num_orbits": (num_orbits if duration_s is None else round(run_s / period, 6)) if closed else None,
        "duration_s": float(run_s), "initial_state": initial_state, "model": model, "integrator": method,
        "gravity_degree": degree,
        "num_points": num_points, **forces_on, "spacecraft_mass_kg": mass, "drag_area_m2": drag_area,
        "cd": cd, "srp_area_m2": srp_area, "cr": cr, "solve_time_sec": round(solve_s, 3),
        "space_weather": (_space_weather_used(epoch, run_s)
                          if forces_on["enable_drag"] and model.lower() not in ("two_body", "j2", "j2_j3_j4")
                          else None),
    }
    report = _trajectory_report(sol, run_s, closed, config)
    report["final_state"] = _final_state(sol, epoch, final_mass)
    report["burns"] = burn_reports
    report.update(_reports_after(sol, q, epoch, closed and legs_closed, (a_km, e, inc, raan, aop, ta), num_orbits))
    if any(b["applied"] for b in burn_reports) and report["status"] == "ok" and closed and legs_closed:
        burn_notes.append("The TLE, OPM and generated mission script describe the starting orbit, before the burns.")
    if burn_notes:
        report["notes"] = report.get("notes", []) + burn_notes
    return report


def _reports_after(sol, q, epoch, closed, elements, num_orbits):
    """The impact or escape remark, or the closed-orbit reports."""
    if sol["impact"] is not None:
        impact = sol["impact"]
        return {"status": "impact", "impact": impact,
                "notes": [f"The spacecraft reached the Earth's surface at {impact['utc']} UTC "
                          f"({impact['t_s'] / 60.0:.1f} min into the run), latitude "
                          f"{impact['latitude_deg']:.2f} deg, longitude {impact['longitude_deg']:.2f} deg; "
                          "the run stops there. Reports of a whole orbit (events, radiation, covariance, "
                          "mission script, TLE/OPM export) are not produced."]}
    if not closed:
        return {"notes": ["Escape trajectory (e >= 1): closed-orbit reports (events, radiation, "
                          "covariance, mission script, TLE/OPM export) are not produced."]}
    return _closed_orbit_reports(sol, q, epoch, *elements, num_orbits)


def _final_state(sol, epoch, mass_kg):
    """The run's last state at full precision, for starting a later run from it."""
    t = float(sol["times"][-1])
    return {"utc": (epoch + t).iso("UTC", 6), "t_s": t,
            "position_km": (np.asarray(sol["position_m"][-1], dtype=float) / 1000.0).tolist(),
            "velocity_kms": (np.asarray(sol["velocity_ms"][-1], dtype=float) / 1000.0).tolist(),
            "mass_kg": float(mass_kg)}


# ---------- Impulsive burns ----------

MAX_BURNS = 20
_BURN_FRAMES = ("VNC", "RTN", "GCRF")
_APSIS_SEARCH_POINTS = 50


def _burn_plan(raw, run_s):
    """The request's burns, checked: [{name, timing, t_s, dv, frame, isp_s}]."""
    if raw is None:
        return []
    if not isinstance(raw, (list, tuple)):
        raise ValueError("burns must be a list of burns")
    if len(raw) > MAX_BURNS:
        raise ValueError(f"A run takes at most {MAX_BURNS} burns")
    plan, previous = [], None
    for k, item in enumerate(raw, 1):
        if not isinstance(item, dict):
            raise ValueError(f"Burn {k} must be an object with timing and dv_ms")
        b = _Request(item)
        name = b.text("name").strip() or f"Burn {k}"
        where = f"Burn {k} ({name})"
        timing = b.text("timing").lower()
        if timing not in ("elapsed", "perigee", "apogee"):
            raise ValueError(f"{where}: timing must be 'elapsed', 'perigee' or 'apogee'")
        dv = b.vector("dv_ms")
        if dv is None:
            raise ValueError(f"{where}: give dv_ms, the velocity change in m/s")
        frame = (b.text("frame") or "VNC").upper()
        if frame not in _BURN_FRAMES:
            raise ValueError(f"{where}: frame must be VNC, RTN or GCRF")
        isp = b.number("isp_s", 300.0)
        if not isp > 0.0:
            raise ValueError(f"{where}: isp_s must be above 0 s")
        t_s = None
        if timing == "elapsed":
            t_s = b.number("t_s", None)
            if t_s is None or t_s < 0.0:
                raise ValueError(f"{where}: give t_s, the time of the burn in seconds after the start")
            if t_s >= run_s:
                raise ValueError(f"{where} at {t_s:.1f} s is after the run ends at {run_s:.1f} s")
            if previous is not None and t_s < previous[1]:
                raise ValueError(f"{where} at {t_s:.1f} s comes before {previous[0]} at {previous[1]:.1f} s")
            previous = (where, t_s)
        plan.append({"name": name, "where": where, "timing": timing, "t_s": t_s, "dv": dv,
                     "frame": frame, "isp_s": isp})
    return plan


def _burn_report(burn, applied=False, **values):
    return {"name": burn["name"], "timing": burn["timing"], "frame": burn["frame"],
            "dv_ms": burn["dv"].tolist(), "delta_v_ms": float(np.linalg.norm(burn["dv"])), "isp_s": burn["isp_s"],
            "applied": applied, "t_s": None, "utc": None, "mass_before_kg": None, "mass_after_kg": None,
            "propellant_kg": None, **values}


def _propagate_with_burns(r0, v0, epoch, run_s, num_points, burns, mass, cd_area, cr_area, options):
    """
    Propagates from (r0, v0) for run_s seconds, applying the impulsive burns in order. Each leg
    between burns is its own propagation from the burned state, so the integrator restarts at
    every burn. Returns (sol, burn reports, notes, final mass, every leg closed).
    """
    def leg(t0, y0, m, span, points):
        return ThirdReviewEngine(y0, epoch=epoch + t0).propagate(
            (0.0, span), num_points=points, sampling="anomaly",      # points follow the orbit
            b_star=cd_area / m, cr_area_over_m=cr_area / m, **options)  # Cd*A/m; the EOM applies the 1/2

    def points_for(span):
        return max(20, int(round(num_points * span / run_s)))

    t, y, m = 0.0, np.concatenate([r0, v0]).astype(float), float(mass)
    pieces, reports, notes, closed = [], [], [], True
    impact = False
    for k, burn in enumerate(burns):
        where = burn["where"]
        if burn["timing"] == "elapsed":
            t_burn = burn["t_s"]
            if t_burn < t:
                raise ValueError(f"{where} at {t_burn:.1f} s comes before the burn before it, at {t:.1f} s")
        else:
            t_burn = _next_apsis(leg, t, y, m, run_s, burn["timing"], where)
            if t_burn is None:
                notes.append(f"{where} was not applied: the run ended before the next {burn['timing']}.")
                reports += [_burn_report(b) for b in burns[k:]]
                break
        if t_burn > t:
            piece = leg(t, y, m, t_burn - t, points_for(t_burn - t))
            pieces.append((t, piece))
            if piece["impact"] is not None:
                impact = True
                reports += [_burn_report(b) for b in burns[k:]]
                break
            y = np.concatenate([piece["position_m"][-1], piece["velocity_ms"][-1]]).astype(float)
        r, v = y[:3], y[3:]
        dv = mission._local_frame(burn["frame"], r, v).T @ burn["dv"]
        m_after = m * math.exp(-float(np.linalg.norm(dv)) / (burn["isp_s"] * mission.G0))
        if m_after < 10.0:
            raise ValueError(f"{where} would leave {m_after:.1f} kg; a spacecraft needs at least 10 kg. "
                             "Lower the velocity change or raise the specific impulse")
        y = np.concatenate([r, v + dv])
        closed = closed and mission.keplerian_from_state(y[:3], y[3:], MU_EARTH)["e"] < 1.0
        reports.append(_burn_report(burn, applied=True, t_s=float(t_burn), utc=(epoch + float(t_burn)).iso("UTC"),
                                    mass_before_kg=m, mass_after_kg=m_after, propellant_kg=m - m_after))
        t, m = float(t_burn), m_after
    if not impact and t < run_s:
        pieces.append((t, leg(t, y, m, run_s - t, points_for(run_s - t))))
    sol = _join(pieces, epoch, [r for r in reports if r["applied"]])
    return sol, reports, notes, m, closed


def _next_apsis(leg, t, y, m, run_s, kind, where):
    """Time of the first perigee or apogee after t (not at t itself), or None if the run ends first."""
    kep = mission.keplerian_from_state(y[:3], y[3:], MU_EARTH)
    if not (kep["a"] > 0.0 and kep["e"] < 1.0):
        raise ValueError(f"{where}: a burn at the {kind} needs a closed orbit; this one is an escape trajectory")
    if kep["e"] < 1e-3:
        raise ValueError(f"{where}: the orbit is near circular (e < 0.001), so its {kind} is not defined; "
                         "time the burn instead")
    period = 2.0 * math.pi * math.sqrt(kep["a"] ** 3 / MU_EARTH)
    span = min(1.5 * period, run_s - t)
    probe = leg(t, y, m, span, _APSIS_SEARCH_POINTS)
    found = [ev["t_s"] for ev in probe["events"] if ev["type"] == kind and ev["t_s"] > 1e-3]
    return t + found[0] if found else None


_PER_SAMPLE = ("times", "time_hours", "position_m", "velocity_ms", "altitude_km", "velocity_kms",
               "semi_major_axis_km", "eccentricity", "inclination_deg", "raan_deg", "arg_perigee_deg",
               "true_anomaly_deg", "energy_joules_kg", "energy_fractional_error", "h_fractional_error",
               "latitude_deg", "longitude_deg", "position_itrf_m", "velocity_itrf_ms", "utc_iso")


def _join(pieces, epoch, burns):
    """
    One solution from the legs [(start time, sol)] of a run with burns. Each leg but the last loses
    its final sample, the state just before the burn, so the samples keep time order and the burn
    instant holds the burned state. Energy and momentum errors stay relative to each leg's start,
    since a burn really changes them.
    """
    burn_events = [{"type": "burn", "t_s": b["t_s"], "utc": b["utc"], "name": b["name"]} for b in burns]
    if len(pieces) == 1 and pieces[0][0] == 0.0:
        sol = dict(pieces[0][1])
        sol["events"] = sorted(list(sol["events"]) + burn_events, key=lambda ev: ev["t_s"])
        return sol
    last = len(pieces) - 1
    cut = [slice(None) if i == last else slice(0, -1) for i in range(len(pieces))]
    first = pieces[0][1]
    sol = dict(first)
    for key in _PER_SAMPLE:
        parts = []
        for (t0, piece), keep in zip(pieces, cut):
            values = piece[key]
            if key == "times":
                values = np.asarray(values) + t0
            elif key == "time_hours":
                values = np.asarray(values) + t0 / 3600.0
            parts.append(list(values[keep]) if key == "utc_iso" else np.asarray(values)[keep])
        sol[key] = sum(parts, []) if key == "utc_iso" else np.concatenate(parts)
    suns = [piece.get("sun_direction_eci") for _, piece in pieces]
    sol["sun_direction_eci"] = (None if any(s is None for s in suns)
                                else np.concatenate([np.asarray(s)[keep] for s, keep in zip(suns, cut)]))
    sol["force_diagnostics"] = {k: sum((list(piece["force_diagnostics"][k])[keep] for (_, piece), keep
                                        in zip(pieces, cut)), [])
                                for k in first["force_diagnostics"]}
    sol["eop_in_range"] = all(piece["eop_in_range"] for _, piece in pieces)
    events = []
    for t0, piece in pieces:
        for ev in piece["events"]:
            shifted = {**ev, "t_s": ev["t_s"] + t0}
            if not any(e["type"] == ev["type"] and abs(e["t_s"] - shifted["t_s"]) < 1e-3 for e in events):
                events.append(shifted)
    sol["events"] = sorted(events + burn_events, key=lambda ev: ev["t_s"])
    if first.get("ecr_mf") is not None:
        switches = [{**s, "t_s": s["t_s"] + t0} for t0, piece in pieces for s in piece["ecr_mf"]["switches"]]
        sol["ecr_mf"] = {**first["ecr_mf"], "switches": switches}
    end_t0, end = pieces[-1]
    sol["impact"] = None if end["impact"] is None else {**end["impact"], "t_s": end["impact"]["t_s"] + end_t0}
    sol["stm"], sol["steps"] = None, None
    return sol


def initial_conditions(q):
    """The initial GCRF state of a request: (kind, r0 m, v0 m/s, (a km, e, inc, raan, aop, ta deg)),
    from position_km + velocity_kms when given, else from Keplerian elements."""
    r_cart, v_cart = q.vector("position_km"), q.vector("velocity_kms")
    if (r_cart is None) != (v_cart is None):
        raise ValueError("Give both position_km and velocity_kms for a Cartesian initial state")
    if r_cart is not None:
        r0, v0 = r_cart * 1000.0, v_cart * 1000.0
        kep = mission.keplerian_from_state(r0, v0, MU_EARTH)
        a_km, e = float(kep["a"]) / 1000.0, float(kep["e"])
        inc, raan, aop, ta = (float(np.degrees(kep[k])) for k in ("inc", "raan", "argp", "ta"))
        return "cartesian", r0, v0, (a_km, e, inc, raan, aop, ta)
    a_km, e = _size_and_shape(q)
    inc, raan, aop, ta = (q.number(k) for k in ("inc", "raan", "aop", "ta"))
    r0, v0 = keplerian_to_cartesian(a_km * 1000.0, e, *(math.radians(x) for x in (inc, raan, aop, ta)))
    return "keplerian", r0, v0, (a_km, e, inc, raan, aop, ta)


def _space_weather_used(epoch, run_s):
    """Which space weather drag ran with: the bundled history's values at the start, and the kinds of
    entry the run's UTC days drew on (OBS observed, PRD daily and PRM monthly predictions, or
    'default' 150/150/15 where the file has nothing)."""
    try:
        from ..offline_data import space_weather
    except ImportError:                 # backend/ imported as a top-level package (app_server)
        from offline_data import space_weather
    tt0 = float(epoch - Epoch.j2000())
    first = forces._utc_day_ordinal(tt0)
    days = range(first - 1, forces._utc_day_ordinal(tt0 + run_s) + 1)    # F10.7 is the previous day's
    kinds = {(sw["kind"] or "OBS") if sw["source"] == "file" else "default"
             for sw in (space_weather(_date.fromordinal(d)) for d in days)}
    f107, f107a, ap = forces.bundled_space_weather(first)
    return {"source": "CelesTrak SW-All.csv (bundled)", "kinds": sorted(kinds),
            "start": {"f107": f107, "f107a": f107a, "ap": ap}}


def _size_and_shape(q):
    """Semi-major axis (km) and eccentricity from hp/ha or a/e, refused unless an elliptic orbit."""
    hp, ha = q.number("hp", None), q.number("ha", None)
    if hp is not None or ha is not None:
        if hp is None or ha is None:
            raise ValueError("Give both hp and ha (perigee and apogee altitude, km)")
        if not ha >= hp:
            raise ValueError("The apogee altitude ha must be at or above the perigee altitude hp")
        rp, ra = _R_EQ_KM + hp, _R_EQ_KM + ha
        a_km, e = (rp + ra) / 2.0, (ra - rp) / (ra + rp)
    else:
        a_km, e = q.number("a"), q.number("e")
    if not 0.0 <= e < 1.0:
        raise ValueError(f"Keplerian elements must be elliptic (0 <= e < 1), got e = {e:g}; give an "
                         "escape trajectory as a Cartesian state (position_km, velocity_kms) with duration_s")
    if a_km * (1.0 - e) <= _R_EQ_KM:
        raise ValueError(f"The perigee radius {a_km * (1.0 - e):.1f} km is below the Earth's surface "
                         f"({_R_EQ_KM} km)")
    return a_km, max(e, _E_MIN)


def _trajectory_report(sol, run_s, closed, config):
    """The propagated arc and the fields every run has."""
    arrays = ("position_m", "velocity_ms", "altitude_km", "velocity_kms", "semi_major_axis_km", "eccentricity",
              "inclination_deg", "raan_deg", "arg_perigee_deg", "true_anomaly_deg", "latitude_deg",
              "longitude_deg", "position_itrf_m", "velocity_itrf_ms")
    report = {
        "status": "ok", "closed_orbit": closed, "duration_s": float(run_s),
        "total_points": len(sol["times"]), "times": np.asarray(sol["times"]).tolist(),
        **{k: np.asarray(sol[k]).tolist() for k in arrays},
        "energy_error": np.asarray(sol["energy_fractional_error"]).tolist(),
        "orbital_period_hours": config["orbital_period_hours"],
        "active_orbit_config": config,
        **{k: sol[k] for k in ("epoch_utc", "utc_iso", "frame", "eop_in_range", "epoch", "events")},
    }
    # Unit Sun vector in the frame of position_m; None outside the bundled DE440 years
    sun = sol.get("sun_direction_eci")
    report["sun_direction_eci"] = None if sun is None else np.asarray(sun).tolist()
    return report


def _closed_orbit_reports(sol, q, epoch, a_km, e, inc, raan, aop, ta, num_orbits):
    """Events, analysis and exports that assume a closed orbit."""
    times, pos, vel = (np.asarray(sol[k]) for k in ("times", "position_m", "velocity_ms"))
    predictor = EventPredictor()
    passes = predictor.predict_ground_station_passes(times, pos, epoch, vel)
    cov = CovarianceEngine()
    elements = dict(sma_km=a_km, ecc=e, inc_deg=inc, raan_deg=raan, aop_deg=aop, ta_deg=ta)
    try:
        tle = CCSDSExporter.generate_tle(epoch, pos[0], vel[0])
    except ValueError as err:     # e.g. a perigee inside the Earth, which SGP4 treats as decayed
        tle, tle_note = None, f"No TLE: {err}."
    opm = CCSDSExporter.generate_ccsds_opm(
        epoch, pos[0] / 1000.0, vel[0] / 1000.0, **elements, gm_km3s2=MU_EARTH / 1e9, mass_kg=q.number("mass"),
        cd=q.number("cd"), cr=q.number("cr"), drag_area_m2=q.number("drag_area"), srp_area_m2=q.number("srp_area"))
    script = MissionScriptWorkbench.generate_mission_script(
        epoch=epoch, **elements, dry_mass_kg=q.number("dry_mass"), fuel_mass_kg=q.number("fuel_mass"),
        drag_area_m2=q.number("drag_area"), srp_area_m2=q.number("srp_area"), cd=q.number("cd"),
        cr=q.number("cr"), num_orbits=int(num_orbits))
    return {
        "events_suite": {
            "solar_eclipses": predictor.predict_solar_eclipses(times, pos, sol.get("sun_direction_eci")),
            "ground_stations": {
                name: {k: d[k] for k in ("passes", "total_passes_count", "total_contact_min")}
                | {"metadata": d["station_metadata"]}
                for name, d in passes.items()
            },
            "exact_apsidal_events": predictor.predict_apsidal_events(times, pos, vel),
            "exact_nodal_events": predictor.predict_orbital_nodes(times, pos, vel),
        },
        "radiation_belts": RadiationBeltModel().evaluate_trajectory_radiation(times, np.asarray(sol["position_itrf_m"])),
        # The run's own variational equations when it integrated them, else along the trajectory
        "covariance_dispersion": (cov.dispersion_from_stm(pos, vel, np.asarray(sol["stm"]))
                                  if sol.get("stm") is not None
                                  else cov.propagate_stm_and_covariance(times, pos, vel)),
        "force_diagnostics": sol.get("force_diagnostics", {}),
        "ccsds_interoperability": {"tle_string": tle["tle"] if tle else None, "opm_string": opm,
                                   "tle_fit": ({k: tle[k] for k in ("position_error_m", "velocity_error_ms")}
                                               if tle else None)},
        "innovations_suite": {"ecr_mf": _strict_json_tiers(sol.get("ecr_mf")),
                              "covariance_steered_stepping": steering_summary(sol.get("steps"))},
        "script_workbench": {"script_content": str(script)},
        **({} if tle else {"notes": [tle_note]}),
    }


def _strict_json_tiers(ecr_mf):
    """The ECR-MF report with the open outer tier's radius as None: strict JSON has no Infinity."""
    if ecr_mf is None:
        return None
    tiers = [{**t, "r_outer_m": t["r_outer_m"] if math.isfinite(t["r_outer_m"]) else None} for t in ecr_mf["tiers"]]
    return {**ecr_mf, "tiers": tiers}


def steering_summary(steps):
    """What covariance steering did to the run's steps, or None when the run was not steered."""
    if steps is None:
        return None
    h = np.asarray(steps["h_s"][1:])
    sigma = np.asarray(steps["sigma_pos_m"])
    return {
        "eta": steps["eta"],
        "accepted_steps": int(len(h)),
        "limited_steps": int(sum(steps["limited"][1:])),
        "min_step_s": float(h.min()) if len(h) else None,
        "max_step_s": float(h.max()) if len(h) else None,
        "max_step_sigma_growth": float(np.max(np.abs(np.diff(sigma)) / sigma[:-1])) if len(sigma) > 1 else 0.0,
        "initial_1sigma_pos_m": float(sigma[0]),
        "final_1sigma_pos_m": float(sigma[-1]),
    }


_UNSET = object()
_ZONAL_DEGREE = {"two_body": 0, "j2": 2, "j2_j3_j4": 4}     # the models with a fixed gravity field


class _Request:
    """Typed reads of a request; None or '' means absent, so the default applies (_DEFAULTS
    unless the read names its own)."""

    def __init__(self, request):
        self.values = {k: v for k, v in dict(request).items() if v is not None and v != ""}

    def _raw(self, key, default=_UNSET):
        return self.values.get(key, _DEFAULTS.get(key) if default is _UNSET else default)

    def number(self, key, default=_UNSET):
        raw = self._raw(key, default)
        if raw is None:
            return None
        try:
            value = float(raw)
        except (TypeError, ValueError):
            raise ValueError(f"{key} must be a number, got {raw!r}") from None
        if not math.isfinite(value):
            raise ValueError(f"{key} must be a finite number")
        return value

    def text(self, key):
        raw = self._raw(key)
        return "" if raw is None else str(raw)

    def boolean(self, key):
        raw = self._raw(key)
        if isinstance(raw, bool):
            return raw
        text = str(raw).strip().lower()
        if text in ("true", "1", "yes", "on"):
            return True
        if text in ("false", "0", "no", "off"):
            return False
        raise ValueError(f"{key} must be true or false, got {raw!r}")

    def vector(self, key):
        """A 3-vector from a list or from text such as "x, y, z" or "[x, y, z]"; None when absent."""
        raw = self.values.get(key)
        if raw is None:
            return None
        if isinstance(raw, str):
            raw = [p for p in raw.strip().strip("[]").replace(",", " ").split() if p]
        try:
            vec = np.array([float(x) for x in raw], dtype=float)
        except (TypeError, ValueError):
            raise ValueError(f"{key} must be three numbers") from None
        if vec.shape != (3,) or not np.all(np.isfinite(vec)):
            raise ValueError(f"{key} must be three numbers, got {len(vec)}")
        return vec

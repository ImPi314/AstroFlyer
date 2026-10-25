"""
AstroFlyer HEO - GMAT cross-check

Runs the same HEO cases (Molniya, Tundra, GTO, e = 0.88 stress orbit) through the same force-model
ladder L0-L7 as the Orekit cross-check, with NASA's General Mission Analysis Tool (GMAT, Apache 2.0)
as the reference, and reports position and velocity differences in the reference orbit's radial /
in-track / cross-track frame every 600 s.

GMAT is given AstroFlyer's inputs wherever it can take them, so the comparison is of the propagators,
not their data: the bundled EGM2008 coefficients (written as a GMAT .cof file), the same spacecraft
(Cd*A/m, Cr*A/m), constant space weather (F10.7 = 150, Kp 3 = Ap 15), ICRF axes and a TT epoch.
Sun and Moon come from GMAT's own DE424 SPK file: SPICE refuses AstroFlyer's DE440 subset (one
segment ends a word short; jplephem reads it), and DE424 and DE440 differ by metres at most there,
about 1e-13 m/s^2 at the spacecraft. GMAT keeps its own Earth orientation, leap-second and shadow models.

Requirements (developer machine only, never shipped): a GMAT install. GmatConsole.exe is found from
the GMAT_CONSOLE environment variable, or under ~/GMAT/*/bin or C:/GMAT/*/bin.

Usage:
    python -m astroflyer.validation.gmat_crosscheck --days 1 --out astroflyer/validation/results/gmat_1day
    python -m astroflyer.validation.gmat_crosscheck --days 7 --levels L3 L4 L5 L6 L7 --out astroflyer/validation/results/gmat_7day
"""

import argparse
import glob
import math
import os
import subprocess
import sys
import tempfile
import time

import numpy as np

from astroflyer.backend import forces
from astroflyer.backend.astro_engine import keplerian_to_cartesian
from astroflyer.backend.epoch import Epoch
from astroflyer.validation import cases as C
from astroflyer.validation.orekit_crosscheck import OUTPUT_STEP_S, astroflyer_run, ric, write_report

SPEED_OF_LIGHT = 299792458.0
DEFAULT_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "gmat")
MASS_KG = 1000.0


def find_gmat():
    """Path of GmatConsole.exe, or None."""
    env = os.environ.get("GMAT_CONSOLE")
    if env and os.path.isfile(env):
        return env
    for pattern in (os.path.expanduser("~/GMAT/*/bin/GmatConsole.exe"), "C:/GMAT/*/bin/GmatConsole.exe",
                    "C:/Program Files/GMAT*/bin/GmatConsole.exe"):
        found = sorted(glob.glob(pattern))
        if found:
            return found[-1]
    return None


def write_cof(path):
    """Writes the bundled EGM2008 coefficients (fully normalized) as a GMAT .cof file."""
    data = np.load(forces._resource_path("gravity", "EGM2008_70.npz"))
    c, s = data["C"], data["S"]
    n_max = c.shape[0] - 1
    with open(path, "w") as f:
        f.write("COMMENT   1\n")
        f.write("CCCCC  EGM2008 to degree and order 70, from AstroFlyer resources/gravity/EGM2008_70.npz\n")
        f.write(f"POTFIELD{n_max:3d}{n_max:3d}  1{float(data['gm']):21.14E}{float(data['radius']):21.14E}"
                f"{1.0:21.14E}\n")
        for n in range(2, n_max + 1):
            for m in range(n + 1):
                if m == 0:
                    f.write(f"RECOEF{n:5d}{m:3d}   {c[n, m]:21.14E}\n")
                else:
                    f.write(f"RECOEF{n:5d}{m:3d}   {c[n, m]:21.14E}{s[n, m]:21.14E}\n")
        f.write("END\n")


def _gmat_epoch(iso_tt):
    """'2026-01-01T00:00:00' -> '01 Jan 2026 00:00:00.000' (GMAT Gregorian)."""
    months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    date, clock = iso_tt.split("T")
    year, month, day = date.split("-")
    return f"{day} {months[int(month) - 1]} {year} {clock}.000"


def mission_script(state, level, duration_s, cof_path, spk_path, report_path):
    """GMAT script propagating `state` (GCRF, m and m/s) for `duration_s` with the forces of `level`,
    reporting the state every OUTPUT_STEP_S."""
    r_km = [float(x) / 1000.0 for x in state[:3]]
    v_kms = [float(x) / 1000.0 for x in state[3:]]
    steps = int(round(duration_s / OUTPUT_STEP_S))
    on = lambda flag: "On" if flag else "Off"
    lines = [
        "Create Spacecraft Sat;",
        "Sat.DateFormat = TTGregorian;",
        f"Sat.Epoch = '{_gmat_epoch(C.EPOCH_ISO_TT)}';",
        "Sat.CoordinateSystem = EarthICRF;",      # built in: Earth origin, ICRF axes (GCRF)
        "Sat.DisplayStateType = Cartesian;",
        f"Sat.X = {r_km[0]!r};", f"Sat.Y = {r_km[1]!r};", f"Sat.Z = {r_km[2]!r};",
        f"Sat.VX = {v_kms[0]!r};", f"Sat.VY = {v_kms[1]!r};", f"Sat.VZ = {v_kms[2]!r};",
        f"Sat.DryMass = {MASS_KG};",
        "Sat.Cd = 1.0;", f"Sat.DragArea = {C.CD_AREA_OVER_M * MASS_KG};",
        "Sat.Cr = 1.0;", f"Sat.SRPArea = {C.CR_AREA_OVER_M * MASS_KG};",
        "",
    ]
    if level.third_body or level.srp:
        lines += ["SolarSystem.EphemerisSource = 'SPICE';", f"SolarSystem.SPKFilename = '{spk_path}';", ""]
    lines += [
        "Create ForceModel FM;",
        "FM.CentralBody = Earth;",
        "FM.PrimaryBodies = {Earth};",
        "FM.ErrorControl = RSSStep;",
        f"FM.GravityField.Earth.Degree = {level.gravity_degree};",
        f"FM.GravityField.Earth.Order = {level.gravity_order};",
        f"FM.GravityField.Earth.PotentialFile = '{cof_path}';",
        "FM.GravityField.Earth.TideModel = 'None';",
    ]
    if level.third_body:
        lines.append("FM.PointMasses = {Sun, Luna};")
    lines.append(f"FM.SRP = {on(level.srp)};")
    if level.srp:
        lines += [f"FM.SRP.Flux = {forces.P_SR_1AU * SPEED_OF_LIGHT!r};",
                  f"FM.SRP.Nominal_Sun = {forces.AU_METERS / 1000.0!r};",
                  "FM.SRP.SRPModel = Spherical;"]
    if level.drag:
        lines += ["FM.Drag.AtmosphereModel = NRLMSISE00;",
                  "FM.Drag.HistoricWeatherSource = 'ConstantFluxAndGeoMag';",
                  "FM.Drag.PredictedWeatherSource = 'ConstantFluxAndGeoMag';",
                  f"FM.Drag.F107 = {C.F107:g};", f"FM.Drag.F107A = {C.F107A:g};",
                  "FM.Drag.MagneticIndex = 3;"]
    lines += [
        f"FM.RelativisticCorrection = {on(level.relativity)};",
        "",
        "Create Propagator Prop;",
        "Prop.FM = FM;",
        "Prop.Type = RungeKutta89;",
        "Prop.InitialStepSize = 60;",
        "Prop.Accuracy = 1e-13;",
        "Prop.MinStep = 0;",
        "Prop.MaxStep = 600;",
        "Prop.MaxStepAttempts = 100;",
        "",
        "Create ReportFile RF;",
        f"RF.Filename = '{report_path}';",
        "RF.Precision = 17;",
        "RF.WriteHeaders = false;",
        "RF.ColumnWidth = 26;",
        "",
        "Create Variable I;",
        "BeginMissionSequence;",
        "Report RF Sat.TTModJulian Sat.EarthICRF.X Sat.EarthICRF.Y Sat.EarthICRF.Z "
        "Sat.EarthICRF.VX Sat.EarthICRF.VY Sat.EarthICRF.VZ;",
        f"For I = 1:{steps};",
        f"   Propagate Prop(Sat) {{Sat.ElapsedSecs = {OUTPUT_STEP_S:g}}};",
        "   Report RF Sat.TTModJulian Sat.EarthICRF.X Sat.EarthICRF.Y Sat.EarthICRF.Z "
        "Sat.EarthICRF.VX Sat.EarthICRF.VY Sat.EarthICRF.VZ;",
        "EndFor;",
    ]
    return "\n".join(lines) + "\n"


def read_report(path):
    """Seconds from the first row, positions (m) and velocities (m/s) from a mission_script report."""
    rows = np.atleast_2d(np.loadtxt(path))
    t = (rows[:, 0] - rows[0, 0]) * 86400.0
    return t, rows[:, 1:4] * 1000.0, rows[:, 4:7] * 1000.0


def run_gmat(console, script_text, workdir, timeout_s=3600):
    script_path = os.path.join(workdir, "case.script")
    with open(script_path, "w") as f:
        f.write(script_text)
    proc = subprocess.run([console, script_path], cwd=os.path.dirname(console), capture_output=True,
                          text=True, timeout=timeout_s)
    return proc


def compare_case(console, orbit_name, level, days):
    a, e, i, raan, argp, nu = C.ORBITS[orbit_name]
    r0, v0 = keplerian_to_cartesian(a, e, math.radians(i), math.radians(raan), math.radians(argp),
                                    math.radians(nu), mu=forces.MU_EARTH)
    state = np.concatenate([r0, v0])
    epoch = Epoch.from_iso(C.EPOCH_ISO_TT, scale="TT")
    duration = days * 86400.0
    n_points = int(round(duration / OUTPUT_STEP_S)) + 1

    times, pos, vel, af_runtime = astroflyer_run(state, epoch, level, duration, n_points)

    with tempfile.TemporaryDirectory() as tmp:
        cof = os.path.join(tmp, "EGM2008_70.cof").replace("\\", "/")
        report = os.path.join(tmp, "states.txt").replace("\\", "/")
        write_cof(cof)
        t0 = time.perf_counter()
        spk = os.path.join(os.path.dirname(os.path.dirname(console)), "data", "planetary_ephem", "spk",
                           "DE424AllPlanets.bsp").replace("\\", "/")
        proc = run_gmat(console, mission_script(state, level, duration, cof, spk, report), tmp)
        gmat_runtime = time.perf_counter() - t0
        if not os.path.exists(report):
            tail = (proc.stdout + proc.stderr).strip().splitlines()[-8:]
            raise RuntimeError("GMAT wrote no report: " + " | ".join(tail))
        ref_t, ref_pos, ref_vel = read_report(report)
    if len(ref_t) != len(times) or np.abs(ref_t - np.asarray(times)).max() > 1e-3:
        raise RuntimeError(f"GMAT output times differ from AstroFlyer's ({len(ref_t)} vs {len(times)} points)")

    dr = np.asarray(pos) - ref_pos
    dv = np.asarray(vel) - ref_vel
    d3 = np.linalg.norm(dr, axis=1)
    ric_err = np.array([ric(ref_pos[k], ref_vel[k], dr[k]) for k in range(len(times))])
    limit = C.threshold_for(days)
    return {
        "orbit": orbit_name,
        "level": level.name,
        "forces": level.description,
        "days": days,
        "variant": "dop853",
        "max_pos_err_m": float(d3.max()),
        "final_pos_err_m": float(d3[-1]),
        "max_radial_m": float(np.abs(ric_err[:, 0]).max()),
        "max_intrack_m": float(np.abs(ric_err[:, 1]).max()),
        "max_crosstrack_m": float(np.abs(ric_err[:, 2]).max()),
        "max_vel_err_ms": float(np.linalg.norm(dv, axis=1).max()),
        "threshold_m": limit,
        "passed": bool(d3.max() <= limit),
        "astroflyer_runtime_s": af_runtime,
        "gmat_runtime_s": gmat_runtime,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--cases", nargs="+", default=list(C.ORBITS), choices=list(C.ORBITS))
    parser.add_argument("--levels", nargs="+", default=list(C.LEVELS), choices=list(C.LEVELS))
    parser.add_argument("--days", type=float, default=1.0)
    parser.add_argument("--gmat", default=None, help="path of GmatConsole.exe (default: GMAT_CONSOLE or a search)")
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    console = args.gmat or find_gmat()
    if not console:
        print("GMAT not found: install it and set GMAT_CONSOLE to GmatConsole.exe")
        return 2
    version = os.path.basename(os.path.dirname(os.path.dirname(console)))
    print(f"GMAT: {console}")
    results = []
    for orbit in args.cases:
        for name in args.levels:
            level = C.LEVELS[name]
            try:
                res = compare_case(console, orbit, level, args.days)
            except Exception as exc:  # report and keep going
                res = {"orbit": orbit, "level": name, "forces": level.description, "days": args.days,
                       "error": f"{type(exc).__name__}: {exc}"}
            results.append(res)
            if "error" in res:
                print(f"{orbit:10s} {name}  ERROR {res['error']}")
            else:
                print(f"{orbit:10s} {name}  max {res['max_pos_err_m']:10.3f} m  "
                      f"(R {res['max_radial_m']:.3f}, I {res['max_intrack_m']:.3f}, "
                      f"C {res['max_crosstrack_m']:.3f})  {'PASS' if res['passed'] else 'FAIL'}")
    source = (f"GMAT {version}, RungeKutta89 at accuracy 1e-13; AstroFlyer's EGM2008 coefficients; "
              f"GMAT's DE424 Sun/Moon, Earth orientation and shadow model")
    path = write_report(results, args.out, source, reference="GMAT", stem="gmat_crosscheck")
    print(f"Report: {path}")
    return 0 if results and all(r.get("passed") for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())

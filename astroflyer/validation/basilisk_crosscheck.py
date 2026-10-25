"""
AstroFlyer HEO - Basilisk cross-check

Runs the HEO cases (Molniya, Tundra, GTO, e = 0.88 stress orbit) through the force-model levels
Basilisk models the same way as AstroFlyer, L0-L6, with Basilisk (AVS Lab, University of Colorado,
ISC licence) as the reference, and reports position and velocity differences in the reference
orbit's radial / in-track / cross-track frame every 600 s. L7 is left out: Basilisk has no
relativistic correction.

Basilisk is given AstroFlyer's inputs wherever it can take them: the bundled EGM2008 coefficients
(written in Basilisk's gravity-file format, zonal terms only for L1-L2), AstroFlyer's GM values for
Earth, Sun and Moon, the same spacecraft (Cd*A/m, and Cr*A/m scaled for Basilisk's 1361 W/m^2 solar
flux so the pressure equals AstroFlyer's 4.56e-6 N/m^2), constant space weather (F10.7 = 150, Ap = 15)
and an atmosphere co-rotating with the Earth (zeroWindModel). Sun, Moon and Earth orientation come
from SPICE kernels shipped with GMAT (DE424, leap seconds, high-precision ITRF93 PCK); Basilisk's
own kernels would have to be downloaded. Integration is Basilisk's RKF78 (task step: see TASK_STEP_S). Two
Basilisk details are corrected so it models the same physics: the Earth orientation gravity sees is
held at mid-step (basilisk_runner.HeldOrientation), and the air co-rotates at the IERS rate about +z
(the rate Basilisk derives from SPICE made GTO drag 9% too strong).

Basilisk pins numpy and sgp4 versions, so it lives in its own virtual environment and runs as a
separate process (basilisk_runner.py). Its python.exe is found from BSK_PYTHON or ~/bsk-venv; the
kernels from GMAT_CONSOLE or a GMAT install under ~/GMAT or C:/GMAT.

Usage:
    python -m astroflyer.validation.basilisk_crosscheck --days 1 --out astroflyer/validation/results/basilisk_1day
    python -m astroflyer.validation.basilisk_crosscheck --days 7 --levels L3 L4 L5 L6 --out astroflyer/validation/results/basilisk_7day
"""

import argparse
import json
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
from astroflyer.validation.gmat_crosscheck import find_gmat
from astroflyer.validation.orekit_crosscheck import OUTPUT_STEP_S, astroflyer_run, ric, write_report

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.join(HERE, "results", "basilisk")
LEVELS = {name: level for name, level in C.LEVELS.items() if not level.relativity}
BSK_SOLAR_FLUX = 1361.0             # W/m^2, Basilisk astroConstants SOLAR_FLUX_EARTH
BSK_AU_M = 149597870693.0           # m, Basilisk astroConstants AU
MASS_KG = 1000.0
# Basilisk advances the Earth's orientation linearly within a task step (gravityEffector.cpp:66,
# dcm += dcm_dot * dt) and applies it even to point-mass gravity; the matrix stops being a rotation
# and scales gravity by ~(omega * dt)^2 / 2 (Molniya over 6 h: 60 s -> 204 m, 10 s -> 5.7 m). The
# runner holds the orientation at mid-step instead, so gravity-only levels run with 10 s steps.
# Eclipse and atmosphere update only once per task step, so SRP and drag levels use 1 s.
TASK_STEP_S = 10.0
ENV_TASK_STEP_S = 1.0
_MONTHS = ("JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST", "SEPTEMBER",
           "OCTOBER", "NOVEMBER", "DECEMBER")


def find_bsk_python():
    """python.exe of the environment Basilisk is installed in, or None."""
    for path in (os.environ.get("BSK_PYTHON"), os.path.expanduser("~/bsk-venv/Scripts/python.exe"),
                 os.path.expanduser("~/bsk-venv/bin/python")):
        if path and os.path.isfile(path):
            return path
    return None


def find_kernels():
    """SPICE kernels from the GMAT install: DE424, leap seconds, ITRF93 PCK, planetary constants."""
    console = find_gmat()
    if not console:
        return None
    data = os.path.join(os.path.dirname(os.path.dirname(console)), "data")
    paths = {
        "spk": os.path.join(data, "planetary_ephem", "spk", "DE424AllPlanets.bsp"),
        "lsk": os.path.join(data, "time", "SPICELeapSecondKernel.tls"),
        "pck_earth": os.path.join(data, "planetary_coeff", "earth_latest_high_prec.bpc"),
        "pck": os.path.join(data, "planetary_coeff", "SPICEPlanetaryConstantsKernel.tpc"),
    }
    if not all(os.path.isfile(p) for p in paths.values()):
        return None
    return {k: p.replace("\\", "/") for k, p in paths.items()}


def write_gravity_csv(path, degree, zonal_only=False):
    """The bundled EGM2008 coefficients (fully normalized) to `degree`, in Basilisk's gravity-file
    format: a header row (radius, GM, rotation rate, degree, order, normalized flag, 0, 0) then
    n, m, C, S, sigma C, sigma S. With zonal_only, every m > 0 term is zero."""
    data = np.load(forces._resource_path("gravity", "EGM2008_70.npz"))
    c, s = data["C"], data["S"]
    with open(path, "w") as f:
        f.write(f"{float(data['radius']):.10E}, {float(data['gm']):.15E}, {forces.OMEGA_EARTH:.10E}, "
                f"{degree}, {degree}, 1, 0.0, 0.0\n")
        for n in range(degree + 1):
            for m in range(n + 1):
                cnm, snm = (c[n, m], s[n, m]) if (m == 0 or not zonal_only) else (0.0, 0.0)
                if n == 0:
                    cnm, snm = 1.0, 0.0
                elif n == 1:
                    cnm, snm = 0.0, 0.0
                f.write(f"{n:5d}, {m:4d}, {cnm: .15E}, {snm: .15E}, 0.0, 0.0\n")


def _epoch_utc():
    """The TT epoch of the cases as a Basilisk/SPICE UTC string."""
    iso = Epoch.from_iso(C.EPOCH_ISO_TT, scale="TT").iso("UTC", 3).rstrip("Z")
    date, clock = iso.split("T")
    year, month, day = date.split("-")
    return f"{year} {_MONTHS[int(month) - 1]} {int(day)} {clock} (UTC)"


def job_for(state, level, duration_s, gravity_file, kernels):
    """Everything basilisk_runner.py needs for one case."""
    zonal = level.gravity_order == 0 and level.gravity_degree > 0
    srp_area = (C.CR_AREA_OVER_M * MASS_KG * forces.P_SR_1AU / (BSK_SOLAR_FLUX / 299792458.0)
                * (forces.AU_METERS / BSK_AU_M) ** 2)
    return {
        "r_m": [float(x) for x in state[:3]],
        "v_ms": [float(x) for x in state[3:]],
        "epoch_utc": _epoch_utc(),
        "duration_s": float(duration_s),
        "output_step_s": OUTPUT_STEP_S,
        "task_step_s": ENV_TASK_STEP_S if (level.srp or level.drag) else TASK_STEP_S,
        "rel_tol": 1e-12,
        "abs_tol": 1e-6,
        "mu_earth": float(forces.MU_EARTH),
        "mu_sun": float(forces.MU_SUN),
        "mu_moon": float(forces.MU_MOON),
        "earth_radius_m": float(forces.R_EARTH_EQ),
        "gravity_degree": level.gravity_degree,
        "zonal_only": zonal,
        "gravity_file": gravity_file,
        "third_body": level.third_body,
        "srp": level.srp,
        "drag": level.drag,
        "mass_kg": MASS_KG,
        "cr": 1.0,
        "srp_area_m2": srp_area,
        "cd": 1.0,
        "drag_area_m2": C.CD_AREA_OVER_M * MASS_KG,
        "f107": C.F107,
        "f107a": C.F107A,
        "ap": C.AP,
        "wind_omega_n": [0.0, 0.0, float(forces.OMEGA_EARTH)],
        "kernels": [kernels[k] for k in ("lsk", "pck", "pck_earth", "spk") if k in kernels],
    }


def read_states(path):
    rows = np.atleast_2d(np.loadtxt(path))
    return rows[:, 0], rows[:, 1:4], rows[:, 4:7]


def compare_case(orbit_name, level, days, bsk_python=None, kernels=None):
    bsk_python = bsk_python or find_bsk_python()
    kernels = kernels or find_kernels()
    a, e, i, raan, argp, nu = C.ORBITS[orbit_name]
    r0, v0 = keplerian_to_cartesian(a, e, math.radians(i), math.radians(raan), math.radians(argp),
                                    math.radians(nu), mu=forces.MU_EARTH)
    state = np.concatenate([r0, v0])
    epoch = Epoch.from_iso(C.EPOCH_ISO_TT, scale="TT")
    duration = days * 86400.0
    n_points = int(round(duration / OUTPUT_STEP_S)) + 1
    times, pos, vel, af_runtime = astroflyer_run(state, epoch, level, duration, n_points)

    with tempfile.TemporaryDirectory() as tmp:
        grav = os.path.join(tmp, "egm2008.txt").replace("\\", "/")
        job = job_for(state, level, duration, grav, kernels)
        if level.gravity_degree > 0:
            write_gravity_csv(grav, level.gravity_degree, zonal_only=job["zonal_only"])
        job_path = os.path.join(tmp, "job.json")
        out = os.path.join(tmp, "states.txt")
        with open(job_path, "w") as f:
            json.dump(job, f)
        t0 = time.perf_counter()
        proc = subprocess.run([bsk_python, os.path.join(HERE, "basilisk_runner.py"), job_path, out],
                              capture_output=True, text=True, timeout=7200)
        bsk_runtime = time.perf_counter() - t0
        if proc.returncode != 0 or not os.path.exists(out):
            tail = (proc.stdout + proc.stderr).strip().splitlines()[-8:]
            raise RuntimeError("Basilisk run failed: " + " | ".join(tail))
        ref_t, ref_pos, ref_vel = read_states(out)
    if len(ref_t) != len(times) or np.abs(ref_t - np.asarray(times)).max() > 1e-3:
        raise RuntimeError(f"Basilisk output times differ from AstroFlyer's ({len(ref_t)} vs {len(times)} points)")

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
        "basilisk_runtime_s": bsk_runtime,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--cases", nargs="+", default=list(C.ORBITS), choices=list(C.ORBITS))
    parser.add_argument("--levels", nargs="+", default=list(LEVELS), choices=list(LEVELS))
    parser.add_argument("--days", type=float, default=1.0)
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    bsk_python, kernels = find_bsk_python(), find_kernels()
    if not bsk_python or not kernels:
        print("Basilisk environment (BSK_PYTHON) or GMAT's SPICE kernels not found")
        return 2
    version = subprocess.run([bsk_python, "-c", "import importlib.metadata as m; print(m.version('bsk'))"],
                             capture_output=True, text=True).stdout.strip()
    print(f"Basilisk {version}: {bsk_python}")
    results = []
    for orbit in args.cases:
        for name in args.levels:
            level = LEVELS[name]
            try:
                res = compare_case(orbit, level, args.days, bsk_python, kernels)
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
    source = (f"Basilisk {version}, RKF78 at relTol 1e-12; AstroFlyer's EGM2008 and GM values; "
              f"DE424 Sun/Moon and ITRF93 orientation from GMAT's SPICE kernels; L7 omitted (no relativity)")
    path = write_report(results, args.out, source, reference="Basilisk", stem="basilisk_crosscheck")
    print(f"Report: {path}")
    return 0 if results and all(r.get("passed") for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())

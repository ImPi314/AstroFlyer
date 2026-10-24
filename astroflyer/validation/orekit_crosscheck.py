"""
AstroFlyer HEO - Orekit cross-check

Propagates each HEO case (Molniya, Tundra, GTO, e = 0.88 stress orbit) through
the force-model ladder L0-L7 with both AstroFlyer and Orekit, from the same
GCRF state and with matching force settings, then reports the position and
velocity differences in the reference orbit's radial / in-track / cross-track
(RIC) frame.

Orekit is an independent implementation (CS GROUP, used operationally by CNES
and ESA), so agreement here checks the integrator, the gravity recursion, the
Sun/Moon geometry, the shadow model, MSIS drag and the Earth-orientation chain.
Both sides use the same EGM2008 coefficients (written to an ICGEM file for
Orekit) so that coefficient sets are not what is being compared.

Requirements (developer machine only, never shipped):
    pip install orekit-jpype      # needs a Java 11+ runtime
Orekit data (DE440, EOP, leap seconds) for L4-L7:
    python -m astroflyer.validation.orekit_crosscheck --download-orekit-data
Without it, only L0-L3 run, using AstroFlyer's bundled IERS files.

Usage:
    python -m astroflyer.validation.orekit_crosscheck                 # all cases, L0-L7, 1 day
    python -m astroflyer.validation.orekit_crosscheck --days 7 --cases molniya gto --levels L3 L7
"""

import argparse
import json
import math
import os
import shutil
import sys
import tempfile
import time

import numpy as np

from astroflyer.backend import forces
from astroflyer.backend.astro_engine import ThirdReviewEngine, keplerian_to_cartesian
from astroflyer.backend.epoch import Epoch
from astroflyer.backend.ephemeris import _resource_path
from astroflyer.validation import cases as C

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OREKIT_DATA = os.path.join(HERE, "orekit-data")
DEFAULT_OUT = os.path.join(HERE, "results")
OUTPUT_STEP_S = 600.0


# ==============================================================================
# OREKIT SETUP
# ==============================================================================
def write_icgem(path):
    """Writes the bundled EGM2008 coefficients as an ICGEM .gfc file for Orekit."""
    data = np.load(_resource_path("gravity", "EGM2008_70.npz"))
    c, s = data["C"], data["S"]
    n_max = c.shape[0] - 1
    with open(path, "w") as f:
        f.write("begin_of_head\n")
        f.write("product_type gravity_field\n")
        f.write("modelname EGM2008_70\n")
        f.write(f"earth_gravity_constant {float(data['gm']):.15e}\n")
        f.write(f"radius {float(data['radius']):.4f}\n")
        f.write(f"max_degree {n_max}\n")
        f.write("errors no\n")
        f.write("norm fully_normalized\n")
        f.write(f"tide_system {str(data['tide_system'])}\n")
        f.write("key L M C S\n")
        f.write("end_of_head\n")
        for n in range(n_max + 1):
            for m in range(n + 1):
                f.write(f"gfc {n} {m} {c[n, m]:.15e} {s[n, m]:.15e}\n")


_MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")


def write_tai_utc_dat(leap_second_dat, path):
    """Converts the bundled IERS Leap_Second.dat into the USNO tai-utc.dat format Orekit reads."""
    with open(leap_second_dat) as src, open(path, "w") as out:
        for line in src:
            if line.startswith("#") or not line.strip():
                continue
            mjd, day, month, year, offset = line.split()[:5]
            jd = float(mjd) + 2400000.5
            out.write(f" {int(year):4d} {_MONTHS[int(month) - 1]} {int(day):2d} =JD {jd:9.1f}  "
                      f"TAI-UTC= {float(offset):10.7f} S + (MJD - {float(mjd):6.0f}.) X 0.0      S\n")


def download_orekit_data(target=DEFAULT_OREKIT_DATA):
    """Downloads the official orekit-data bundle (needs internet)."""
    import urllib.request
    import zipfile
    url = "https://gitlab.orekit.org/orekit/orekit-data/-/archive/main/orekit-data-main.zip"
    os.makedirs(os.path.dirname(target), exist_ok=True)
    zip_path = target + ".zip"
    print(f"Downloading {url} ...")
    urllib.request.urlretrieve(url, zip_path)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(os.path.dirname(target))
    extracted = os.path.join(os.path.dirname(target), "orekit-data-main")
    if os.path.exists(target):
        shutil.rmtree(target)
    os.rename(extracted, target)
    os.remove(zip_path)
    print(f"Orekit data in {target}")
    return target


class OrekitContext:
    """Starts the JVM and configures Orekit data; exposes the classes the runner uses."""

    def __init__(self, orekit_data=None):
        import orekit_jpype
        orekit_jpype.initVM()
        from java.io import File
        from org.orekit.data import DataContext, DirectoryCrawler, ZipJarCrawler
        from org.orekit.forces.gravity.potential import GravityFieldFactory, ICGEMFormatReader

        self.tmp = tempfile.mkdtemp(prefix="astroflyer_orekit_")
        manager = DataContext.getDefault().getDataProvidersManager()

        self.has_ephemeris = False
        if orekit_data and os.path.exists(orekit_data):
            crawler = ZipJarCrawler(File(orekit_data)) if orekit_data.endswith(".zip") \
                else DirectoryCrawler(File(orekit_data))
            manager.addProvider(crawler)
            self.has_ephemeris = True
            self.data_source = f"orekit-data at {orekit_data}"
        else:
            iers = os.path.join(self.tmp, "iers")
            os.makedirs(iers)
            shutil.copy(_resource_path("iers", "finals2000A.all"), iers)
            write_tai_utc_dat(_resource_path("iers", "Leap_Second.dat"), os.path.join(iers, "tai-utc.dat"))
            manager.addProvider(DirectoryCrawler(File(iers)))
            self.data_source = "AstroFlyer bundled IERS files (no ephemerides: L0-L3 only)"

        gravity_dir = os.path.join(self.tmp, "gravity")
        os.makedirs(gravity_dir)
        write_icgem(os.path.join(gravity_dir, "EGM2008_70.gfc"))
        manager.addProvider(DirectoryCrawler(File(gravity_dir)))
        GravityFieldFactory.clearPotentialCoefficientsReaders()
        GravityFieldFactory.addPotentialCoefficientsReader(ICGEMFormatReader("EGM2008_70.gfc", False))

        from org.orekit.frames import FramesFactory
        from org.orekit.utils import IERSConventions, Constants
        from org.orekit.bodies import OneAxisEllipsoid
        self.gcrf = FramesFactory.getGCRF()
        self.itrf = FramesFactory.getITRF(IERSConventions.IERS_2010, False)
        self.earth = OneAxisEllipsoid(Constants.WGS84_EARTH_EQUATORIAL_RADIUS,
                                      Constants.WGS84_EARTH_FLATTENING, self.itrf)
        self.mu = GravityFieldFactory.getNormalizedProvider(2, 0).getMu()

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def date(self, epoch):
        from org.orekit.time import AbsoluteDate
        tt_s = float(epoch - Epoch.j2000())
        return AbsoluteDate.J2000_EPOCH.shiftedBy(tt_s)

    def _msis_inputs(self):
        from jpype import JImplements, JOverride, JArray, JDouble
        from org.orekit.time import AbsoluteDate

        @JImplements("org.orekit.models.earth.atmosphere.NRLMSISE00InputParameters")
        class ConstantSpaceWeather:
            @JOverride
            def getMinDate(self):
                return AbsoluteDate.PAST_INFINITY

            @JOverride
            def getMaxDate(self):
                return AbsoluteDate.FUTURE_INFINITY

            @JOverride
            def getDailyFlux(self, date):
                return C.F107

            @JOverride
            def getAverageFlux(self, date):
                return C.F107A

            @JOverride
            def getAp(self, date):
                return JArray(JDouble)([C.AP] * 7)

        return ConstantSpaceWeather()

    def mean_sun(self):
        """
        Sun direction that gives NRLMSISE-00 its standard local solar time,
        UT + longitude / 15. Orekit's NRLMSISE00 otherwise takes local time from
        the true Sun (apparent solar time), which differs from the MSIS
        convention (and pymsis) by the equation of time, up to 16 minutes: about
        0.3% in density, or 30 m per day for a 250 km GTO perigee.
        """
        from jpype import JImplements, JOverride
        from org.hipparchus.geometry.euclidean.threed import Vector3D
        from org.orekit.time import AbsoluteDate, TimeScalesFactory
        utc = TimeScalesFactory.getUTC()
        itrf = self.itrf

        @JImplements("org.orekit.utils.ExtendedPositionProvider")
        class MeanSun:
            @JOverride
            def getPosition(self, date, frame):
                if not isinstance(date, AbsoluteDate):
                    raise NotImplementedError("field dates are not used by the cross-check")
                seconds = date.getComponents(utc).getTime().getSecondsInUTCDay()
                lon = math.pi - 2.0 * math.pi * seconds / 86400.0
                p = Vector3D(math.cos(lon) * forces.AU_METERS, math.sin(lon) * forces.AU_METERS, 0.0)
                return itrf.getStaticTransformTo(frame, date).transformPosition(p)

        return MeanSun()

    def atmosphere(self):
        """Orekit NRLMSISE-00 with AstroFlyer's constant space weather and the mean Sun."""
        from org.orekit.models.earth.atmosphere import NRLMSISE00
        from org.orekit.time import TimeScalesFactory
        return NRLMSISE00(self._msis_inputs(), self.mean_sun(), self.earth, TimeScalesFactory.getUTC())

    def propagator(self, orbit_state, date, level):
        from org.hipparchus.ode.nonstiff import DormandPrince853Integrator
        from org.hipparchus.geometry.euclidean.threed import Vector3D
        from org.orekit.bodies import CelestialBodyFactory
        from org.orekit.forces.gravity import (HolmesFeatherstoneAttractionModel, ThirdBodyAttraction,
                                               Relativity)
        from org.orekit.forces.gravity.potential import GravityFieldFactory
        from org.orekit.orbits import CartesianOrbit, OrbitType
        from org.orekit.propagation import SpacecraftState
        from org.orekit.propagation.numerical import NumericalPropagator
        from org.orekit.utils import PVCoordinates

        r, v = orbit_state
        pv = PVCoordinates(Vector3D(*map(float, r)), Vector3D(*map(float, v)))
        orbit = CartesianOrbit(pv, self.gcrf, date, self.mu)

        try:
            from org.orekit.propagation import ToleranceProvider
            tol = ToleranceProvider.getDefaultToleranceProvider(1e-6).getTolerances(orbit, OrbitType.CARTESIAN)
        except ImportError:
            tol = NumericalPropagator.tolerances(1e-6, orbit, OrbitType.CARTESIAN)
        integrator = DormandPrince853Integrator(1e-3, 600.0, tol[0], tol[1])
        prop = NumericalPropagator(integrator)
        prop.setOrbitType(OrbitType.CARTESIAN)
        prop.setInitialState(SpacecraftState(orbit, 1.0))  # 1 kg: areas below are A/m

        if level.gravity_degree >= 2:
            provider = GravityFieldFactory.getNormalizedProvider(level.gravity_degree, level.gravity_order)
            prop.addForceModel(HolmesFeatherstoneAttractionModel(self.itrf, provider))
        sun = moon = None
        if level.needs_ephemeris:
            sun = CelestialBodyFactory.getSun()
            moon = CelestialBodyFactory.getMoon()
        if level.third_body:
            prop.addForceModel(ThirdBodyAttraction(sun))
            prop.addForceModel(ThirdBodyAttraction(moon))
        if level.srp:
            from org.orekit.forces.radiation import SolarRadiationPressure, IsotropicRadiationSingleCoefficient
            prop.addForceModel(SolarRadiationPressure(
                sun, self.earth, IsotropicRadiationSingleCoefficient(C.CR_AREA_OVER_M, 1.0)))
        if level.drag:
            from org.orekit.forces.drag import DragForce, IsotropicDrag
            prop.addForceModel(DragForce(self.atmosphere(), IsotropicDrag(C.CD_AREA_OVER_M, 1.0)))
        if level.relativity:
            prop.addForceModel(Relativity(self.mu))
        return prop


# ==============================================================================
# ASTROFLYER SIDE
# ==============================================================================
# AstroFlyer propagator settings compared against the same Orekit reference
VARIANTS = {
    "dop853": dict(method="DOP853"),
    "ecr_mf": dict(method="DOP853", fidelity="ecr_mf"),
    "rkf78": dict(method="RKF78"),
    "rkf78_steered": dict(method="RKF78", steering="covariance"),
}


def astroflyer_run(state, epoch, level, duration_s, n_points, variant="dop853"):
    model = {"L0": "two_body", "L1": "j2", "L2": "j2_j3_j4"}.get(level.name, "coupled")
    eng = ThirdReviewEngine(state, epoch=epoch)
    t0 = time.perf_counter()
    sol = eng.propagate(
        (0.0, duration_s), num_points=n_points, model=model, rtol=1e-12, atol=1e-6, **VARIANTS[variant],
        enable_drag=level.drag, enable_third_body=level.third_body, enable_srp=level.srp,
        enable_relativity=level.relativity, enable_albedo=False,
        gravity_degree=level.gravity_degree if model == "coupled" else None,
        gravity_order=level.gravity_order if model == "coupled" else None,
        b_star=C.CD_AREA_OVER_M, cr_area_over_m=C.CR_AREA_OVER_M,
        f107=C.F107, f107a=C.F107A, ap=C.AP,
    )
    return sol["times"], sol["position_m"], sol["velocity_ms"], time.perf_counter() - t0


def ric(r_ref, v_ref, dr):
    r_hat = r_ref / np.linalg.norm(r_ref)
    h = np.cross(r_ref, v_ref)
    c_hat = h / np.linalg.norm(h)
    i_hat = np.cross(c_hat, r_hat)
    return np.array([dr @ r_hat, dr @ i_hat, dr @ c_hat])


def compare_case(ctx, orbit_name, level, days, variant="dop853"):
    a, e, i, raan, argp, nu = C.ORBITS[orbit_name]
    r0, v0 = keplerian_to_cartesian(a, e, math.radians(i), math.radians(raan), math.radians(argp),
                                    math.radians(nu), mu=forces.MU_EARTH)
    state = np.concatenate([r0, v0])
    epoch = Epoch.from_iso(C.EPOCH_ISO_TT, scale="TT")
    duration = days * 86400.0
    n_points = int(round(duration / OUTPUT_STEP_S)) + 1

    times, pos, vel, af_runtime = astroflyer_run(state, epoch, level, duration, n_points, variant)

    t0 = time.perf_counter()
    date0 = ctx.date(epoch)
    prop = ctx.propagator((r0, v0), date0, level)
    ref_pos = np.zeros_like(pos)
    ref_vel = np.zeros_like(vel)
    for k, t in enumerate(times):
        pv = prop.propagate(date0.shiftedBy(float(t))).getPVCoordinates(ctx.gcrf)
        p, w = pv.getPosition(), pv.getVelocity()
        ref_pos[k] = (p.getX(), p.getY(), p.getZ())
        ref_vel[k] = (w.getX(), w.getY(), w.getZ())
    ok_runtime = time.perf_counter() - t0

    dr = pos - ref_pos
    dv = vel - ref_vel
    d3 = np.linalg.norm(dr, axis=1)
    ric_err = np.array([ric(ref_pos[k], ref_vel[k], dr[k]) for k in range(len(times))])
    limit = C.threshold_for(days)
    return {
        "orbit": orbit_name,
        "level": level.name,
        "forces": level.description,
        "days": days,
        "variant": variant,
        "max_pos_err_m": float(d3.max()),
        "final_pos_err_m": float(d3[-1]),
        "max_radial_m": float(np.abs(ric_err[:, 0]).max()),
        "max_intrack_m": float(np.abs(ric_err[:, 1]).max()),
        "max_crosstrack_m": float(np.abs(ric_err[:, 2]).max()),
        "max_vel_err_ms": float(np.linalg.norm(dv, axis=1).max()),
        "threshold_m": limit,
        "passed": bool(d3.max() <= limit),
        "astroflyer_runtime_s": af_runtime,
        "orekit_runtime_s": ok_runtime,
    }


def write_report(results, out_dir, data_source, variant="dop853", reference="Orekit", stem="orekit_crosscheck"):
    """Writes <stem>.json and <stem>.md; each result's reference run time is under
    "<reference lowercased>_runtime_s"."""
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"{stem}.json"), "w") as f:
        json.dump({"data_source": data_source, "variant": variant, "results": results}, f, indent=2)
    runtime_key = f"{reference.lower()}_runtime_s"
    lines = [
        f"# AstroFlyer vs {reference} cross-check",
        "",
        f"Reference data: {data_source}. Epoch {C.EPOCH_ISO_TT} TT, GCRF, output every {OUTPUT_STEP_S:.0f} s.",
        f"AstroFlyer propagator: {variant} ({VARIANTS[variant]}).",
        "",
        f"| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | {reference} (s) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in results:
        if "error" in r:
            lines.append(f"| {r['orbit']} | {r['level']} | {r.get('forces', '')} | {r.get('days', '')} | "
                         f"error: {r['error']} |  |  |  |  |  | ERROR |  |  |")
            continue
        lines.append(
            f"| {r['orbit']} | {r['level']} | {r['forces']} | {r['days']:g} | {r['max_pos_err_m']:.3g} | "
            f"{r['max_radial_m']:.3g} | {r['max_intrack_m']:.3g} | {r['max_crosstrack_m']:.3g} | "
            f"{r['max_vel_err_ms']:.3g} | {r['threshold_m']:g} | {'PASS' if r['passed'] else 'FAIL'} | "
            f"{r['astroflyer_runtime_s']:.1f} | {r[runtime_key]:.1f} |")
    path = os.path.join(out_dir, f"{stem}.md")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--cases", nargs="+", default=list(C.ORBITS), choices=list(C.ORBITS))
    parser.add_argument("--levels", nargs="+", default=list(C.LEVELS), choices=list(C.LEVELS))
    parser.add_argument("--days", type=float, default=1.0)
    parser.add_argument("--orekit-data", default=DEFAULT_OREKIT_DATA,
                        help="orekit-data folder or zip (needed for L4-L7)")
    parser.add_argument("--download-orekit-data", action="store_true")
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--variant", default="dop853", choices=list(VARIANTS),
                        help="AstroFlyer propagator settings to compare")
    args = parser.parse_args(argv)

    if args.download_orekit_data:
        download_orekit_data(args.orekit_data)

    ctx = OrekitContext(args.orekit_data)
    print(f"Orekit data: {ctx.data_source}")
    results = []
    try:
        for orbit in args.cases:
            for name in args.levels:
                level = C.LEVELS[name]
                if level.needs_ephemeris and not ctx.has_ephemeris:
                    print(f"skip {orbit} {name}: needs orekit-data (run with --download-orekit-data)")
                    continue
                try:
                    res = compare_case(ctx, orbit, level, args.days, args.variant)
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
    finally:
        ctx.close()
    path = write_report(results, args.out, ctx.data_source, args.variant)
    print(f"Report: {path}")
    return 0 if results and all(r.get("passed") for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())

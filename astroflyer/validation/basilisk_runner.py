"""
AstroFlyer HEO - Basilisk propagation for the Basilisk cross-check.

Runs inside Basilisk's own Python environment (it needs only NumPy and Basilisk, not AstroFlyer):

    <bsk-venv>/python basilisk_runner.py job.json states.txt

job.json (written by basilisk_crosscheck.job_for) holds the GCRF start state, run length, output
step, forces and constants; states.txt gets one row per output: t (s), x y z (m), vx vy vz (m/s).
"""

import json
import sys

import numpy as np
from Basilisk.architecture import messaging, sysModel
from Basilisk.simulation import (dragDynamicEffector, eclipse, msisAtmosphere, radiationPressure, spacecraft,
                                 spiceInterface, svIntegrators, zeroWindModel)
from Basilisk.utilities import SimulationBaseClass, macros, simIncludeGravBody

# NRLMSISE-00 space-weather inputs, in msisAtmosphere's order: 21 3-hourly/daily ap values, then
# F10.7 81-day average and previous-day F10.7.
N_AP = 21
MONTHS = ("JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST", "SEPTEMBER",
          "OCTOBER", "NOVEMBER", "DECEMBER")


class HeldOrientation(sysModel.SysModel):
    """Copy of a SPICE planet-state message whose orientation is held, within each task step, at the
    step's midpoint. Basilisk's gravity steps a planet's orientation matrix linearly within a task
    step (gravityEffector.cpp:66, dcm += dcm_dot * dt), which stops it being a rotation and scales even
    point-mass gravity by ~(omega dt)^2 / 2. Here the matrix is moved to mid-step, made a rotation
    again (nearest orthonormal matrix) and its rate set to zero, so gravity sees a true rotation whose
    lag averages out over the step. It is still updated from SPICE every step."""

    def __init__(self, source, step_s):
        super().__init__()
        self.ModelTag = "heldOrientation"
        self.step_s = step_s
        self.reader = messaging.SpicePlanetStateMsgReader()
        self.reader.subscribeTo(source)
        self.outMsg = messaging.SpicePlanetStateMsg()

    def UpdateState(self, current_nanos):
        payload = self.reader()
        # A message written at time t serves the step that integrates from t - dt up to t
        mid = np.array(payload.J20002Pfix) - np.array(payload.J20002Pfix_dot) * (0.5 * self.step_s)
        u, _, vt = np.linalg.svd(mid)
        payload.J20002Pfix = (u @ vt).tolist()
        payload.J20002Pfix_dot = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
        self.outMsg.write(payload, current_nanos, self.moduleID)


def epoch_message(utc):
    """Epoch message from '2025 DECEMBER 31 23:58:50.816 (UTC)' (Basilisk's own helper needs pytest)."""
    year, month, day, clock = utc.replace("(UTC)", "").split()
    hours, minutes, seconds = clock.split(":")
    payload = messaging.EpochMsgPayload()
    payload.year, payload.month, payload.day = int(year), MONTHS.index(month) + 1, int(day)
    payload.hours, payload.minutes, payload.seconds = int(hours), int(minutes), float(seconds)
    return messaging.EpochMsg().write(payload)


def propagate(job):
    sim = SimulationBaseClass.SimBaseClass()
    proc = sim.CreateNewProcess("proc")
    task_dt = macros.sec2nano(job["task_step_s"])
    proc.addTask(sim.CreateNewTask("task", task_dt))

    sc = spacecraft.Spacecraft()
    sc.ModelTag = "sat"
    sc.hub.mHub = job["mass_kg"]
    sc.hub.r_CN_NInit = job["r_m"]
    sc.hub.v_CN_NInit = job["v_ms"]
    integrator = svIntegrators.svIntegratorRKF78(sc)
    integrator.relTol = job["rel_tol"]
    integrator.absTol = job["abs_tol"]
    sc.setIntegrator(integrator)

    # Sun, Moon and Earth orientation (ITRF93, high-precision PCK) from SPICE, positions relative to Earth
    spice = spiceInterface.SpiceInterface()
    spice.ModelTag = "spice"
    for path in job["kernels"]:
        folder, name = path.rsplit("/", 1)
        spice.loadSpiceKernel(name, folder + "/")
    spice.addPlanetNames(spiceInterface.StringVector(["earth", "sun", "moon"]))
    spice.planetFrames = spiceInterface.StringVector(["ITRF93", "IAU_SUN", "IAU_MOON"])
    spice.UTCCalInit = job["epoch_utc"]
    spice.zeroBase = "earth"
    epoch_msg = epoch_message(job["epoch_utc"])
    spice.epochInMsg.subscribeTo(epoch_msg)
    earth_msg, sun_msg, moon_msg = (spice.planetStateOutMsgs[k] for k in range(3))

    grav = simIncludeGravBody.gravBodyFactory()
    earth = grav.createEarth()
    earth.isCentralBody = True
    earth.mu = job["mu_earth"]
    if job["gravity_degree"] > 0:
        earth.useSphericalHarmonicsGravityModel(job["gravity_file"], job["gravity_degree"])
    held = HeldOrientation(earth_msg, job["task_step_s"])
    earth.planetBodyInMsg.subscribeTo(held.outMsg)
    if job["third_body"]:
        sun = grav.createSun()
        sun.mu = job["mu_sun"]
        sun.planetBodyInMsg.subscribeTo(sun_msg)
        moon = grav.createMoon()
        moon.mu = job["mu_moon"]
        moon.planetBodyInMsg.subscribeTo(moon_msg)
    grav.addBodiesTo(sc)

    sim.AddModelToTask("task", spice, 100)
    sim.AddModelToTask("task", held, 95)
    keep = [epoch_msg, held]

    if job["srp"]:
        shadow = eclipse.Eclipse()
        shadow.ModelTag = "eclipse"
        shadow.addSpacecraftToModel(sc.scStateOutMsg)
        shadow.addPlanetToModel(earth_msg)
        shadow.sunInMsg.subscribeTo(sun_msg)
        srp = radiationPressure.RadiationPressure()
        srp.ModelTag = "srp"
        srp.area = job["srp_area_m2"]
        srp.coefficientReflection = job["cr"]
        srp.sunEphmInMsg.subscribeTo(sun_msg)
        srp.sunEclipseInMsg.subscribeTo(shadow.eclipseOutMsgs[0])
        sc.addDynamicEffector(srp)
        sim.AddModelToTask("task", shadow, 90)
        sim.AddModelToTask("task", srp, 80)

    if job["drag"]:
        atmo = msisAtmosphere.MsisAtmosphere()
        atmo.ModelTag = "msis"
        atmo.planetRadius = job["earth_radius_m"]
        atmo.addSpacecraftToModel(sc.scStateOutMsg)
        atmo.planetPosInMsg.subscribeTo(earth_msg)
        atmo.epochInMsg.subscribeTo(epoch_msg)
        values = [job["ap"]] * N_AP + [job["f107a"], job["f107"]]
        for k, value in enumerate(values):
            payload = messaging.SwDataMsgPayload()
            payload.dataValue = value
            msg = messaging.SwDataMsg().write(payload)
            atmo.swDataInMsgs[k].subscribeTo(msg)
            keep.append(msg)
        wind = zeroWindModel.ZeroWindModel()   # air co-rotating with the Earth
        wind.ModelTag = "wind"
        wind.addSpacecraftToModel(sc.scStateOutMsg)
        wind.planetPosInMsg.subscribeTo(earth_msg)
        wind.setPlanetOmega_N(job["wind_omega_n"])   # SPICE-derived rate made GTO drag 9% too strong
        drag = dragDynamicEffector.DragDynamicEffector()
        drag.ModelTag = "drag"
        drag.coreParams.projectedArea = job["drag_area_m2"]
        drag.coreParams.dragCoeff = job["cd"]
        drag.atmoDensInMsg.subscribeTo(atmo.envOutMsgs[0])
        drag.windVelInMsg.subscribeTo(wind.envOutMsgs[0])
        sc.addDynamicEffector(drag)
        sim.AddModelToTask("task", atmo, 70)
        sim.AddModelToTask("task", wind, 60)
        sim.AddModelToTask("task", drag, 50)

    sim.AddModelToTask("task", sc, 10)
    recorder = sc.scStateOutMsg.recorder(macros.sec2nano(job["output_step_s"]))
    sim.AddModelToTask("task", recorder)

    sim.InitializeSimulation()
    sim.ConfigureStopTime(macros.sec2nano(job["duration_s"]))
    sim.ExecuteSimulation()
    t = recorder.times() * macros.NANO2SEC
    return np.column_stack([t, recorder.r_BN_N, recorder.v_BN_N]), keep


def main(job_path, out_path):
    with open(job_path) as f:
        job = json.load(f)
    rows, _ = propagate(job)
    np.savetxt(out_path, rows, fmt="%.17g")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))

"""
Restarts at force-model discontinuities, on and off, against Orekit.

Runs the Orekit cross-check cases twice with the same AstroFlyer settings: once as shipped (the
integrator stops and restarts at every shadow edge and NRLMSISE-00 jump, backend/trajectory.py) and
once with those boundary lists emptied for the run, so steps may straddle the discontinuities.
The application code is not changed; the boundary functions are replaced in memory here only.

Run from the project root:
    python astroflyer/validation/results/discontinuity_restarts/restart_ablation.py --days 7
"""

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.getcwd())

from astroflyer.backend import trajectory  # noqa: E402
from astroflyer.validation import cases as C  # noqa: E402
from astroflyer.validation import orekit_crosscheck as OC  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SHADOW, DRAG = trajectory.shadow_boundary_events, trajectory.drag_boundary_events


def set_restarts(on):
    trajectory.shadow_boundary_events = SHADOW if on else (lambda *a, **k: [])
    trajectory.drag_boundary_events = DRAG if on else (lambda *a, **k: [])


def reference(ctx, orbit, level, days):
    """Orekit positions at the cross-check's output times, and the start state."""
    a, e, i, raan, argp, nu = C.ORBITS[orbit]
    r0, v0 = OC.keplerian_to_cartesian(a, e, np.radians(i), np.radians(raan), np.radians(argp),
                                       np.radians(nu), mu=OC.forces.MU_EARTH)
    epoch = OC.Epoch.from_iso(C.EPOCH_ISO_TT, scale="TT")
    duration = days * 86400.0
    times = np.linspace(0.0, duration, int(round(duration / OC.OUTPUT_STEP_S)) + 1)
    date0 = ctx.date(epoch)
    prop = ctx.propagator((r0, v0), date0, level)
    ref = np.array([[c.getX(), c.getY(), c.getZ()] for c in (
        prop.propagate(date0.shiftedBy(float(t))).getPVCoordinates(ctx.gcrf).getPosition() for t in times)])
    return np.concatenate([r0, v0]), epoch, duration, times, ref


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=float, default=7.0)
    p.add_argument("--levels", nargs="+", default=["L5", "L6", "L7"])
    p.add_argument("--variants", nargs="+", default=["dop853", "rkf78"])
    args = p.parse_args()

    ctx = OC.OrekitContext(OC.DEFAULT_OREKIT_DATA)
    rows, series = [], {}
    try:
        for orbit in C.ORBITS:
            for name in args.levels:
                level = C.LEVELS[name]
                state, epoch, duration, times, ref = reference(ctx, orbit, level, args.days)
                for variant in args.variants:
                    for on in (True, False):
                        set_restarts(on)
                        t, pos, _, runtime = OC.astroflyer_run(state, epoch, level, duration, len(times), variant)
                        assert np.allclose(t, times)
                        d3 = np.linalg.norm(pos - ref, axis=1)
                        rows.append({"orbit": orbit, "level": name, "forces": level.description, "days": args.days,
                                     "variant": variant, "restarts": on, "max_pos_err_m": float(d3.max()),
                                     "final_pos_err_m": float(d3[-1]), "astroflyer_runtime_s": runtime})
                        series[f"{orbit}_{name}_{variant}_{'on' if on else 'off'}"] = d3
                        series["t"] = times
                        print(f"{orbit:10s} {name} {variant:7s} restarts {'on ' if on else 'off'} "
                              f"max {d3.max():10.4f} m  AF {runtime:.1f} s", flush=True)
    finally:
        set_restarts(True)
        ctx.close()
    tag = f"{args.days:g}day"
    with open(os.path.join(HERE, f"restart_ablation_{tag}.json"), "w") as f:
        json.dump({"data_source": ctx.data_source, "days": args.days, "results": rows}, f, indent=2)
    np.savez_compressed(os.path.join(HERE, f"restart_ablation_{tag}_series.npz"), **series)


if __name__ == "__main__":
    main()

"""
ECR-MF against the full model at 70x70 gravity: accuracy given up and run time.

Both runs are AstroFlyer's (DOP853, full force model), so no Orekit is needed.

Usage:
    python -m astroflyer.validation.ecr_mf_benchmark            # 1 day
    python -m astroflyer.validation.ecr_mf_benchmark --days 7
"""

import argparse
import time

import numpy as np

from astroflyer.backend import forces
from astroflyer.backend.astro_engine import ThirdReviewEngine, keplerian_to_cartesian
from astroflyer.backend.epoch import Epoch
from astroflyer.validation import cases as C

DEGREE = 70


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--days", type=float, default=1.0)
    args = parser.parse_args(argv)

    epoch = Epoch.from_iso(C.EPOCH_ISO_TT, scale="TT")
    # Warm-up so Numba compilation is not timed
    r0, v0 = keplerian_to_cartesian(26600e3, 0.74, 1.1, 0.0, 0.0, 0.0, mu=forces.MU_EARTH)
    ThirdReviewEngine(np.concatenate([r0, v0]), epoch=epoch).propagate(
        (0.0, 600.0), num_points=3, method="DOP853", gravity_degree=DEGREE, gravity_order=DEGREE)

    for orbit in C.ORBITS:
        a, e, i, raan, argp, nu = C.ORBITS[orbit]
        r0, v0 = keplerian_to_cartesian(a, e, *np.radians([i, raan, argp, nu]), mu=forces.MU_EARTH)
        runs = {}
        for fidelity in ("full", "ecr_mf"):
            t0 = time.perf_counter()
            sol = ThirdReviewEngine(np.concatenate([r0, v0]), epoch=epoch).propagate(
                (0.0, args.days * 86400.0), num_points=int(args.days * 144) + 1, method="DOP853",
                rtol=1e-12, atol=1e-6, gravity_degree=DEGREE, gravity_order=DEGREE,
                b_star=C.CD_AREA_OVER_M, cr_area_over_m=C.CR_AREA_OVER_M, fidelity=fidelity)
            runs[fidelity] = (time.perf_counter() - t0, np.asarray(sol["position_m"]), sol["ecr_mf"])
        diff = np.linalg.norm(runs["full"][1] - runs["ecr_mf"][1], axis=1).max()
        tiers = [t["gravity_degree"] for t in runs["ecr_mf"][2]["tiers"]]
        print(f"{orbit:10s} {args.days:g} d  full {runs['full'][0]:6.1f} s  ecr_mf {runs['ecr_mf'][0]:6.1f} s  "
              f"speed-up {runs['full'][0] / runs['ecr_mf'][0]:4.2f}x  max diff {diff:.4f} m  tiers {tiers}")


if __name__ == "__main__":
    main()

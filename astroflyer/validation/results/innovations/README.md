# Innovations re-measured against Orekit

Generated 2026-10-24 with `python -m astroflyer.validation.orekit_crosscheck --variant <v>` (Orekit 13.1,
same EGM2008 coefficients, epoch 2026-01-01 00:00 TT). Four AstroFlyer settings, all at rtol 1e-12:

| Variant | Propagator |
| --- | --- |
| `dop853` | SciPy DOP853 with shadow/drag restarts (the baseline) |
| `ecr_mf` | `dop853` + `fidelity="ecr_mf"` (gravity degree by radius tier) |
| `rkf78` | AstroFlyer's RKF7(8) |
| `rkf78_steered` | `rkf78` + `steering="covariance"` (eta 0.02) |

## Summary

Rerun after the WGS-84 shadow fix (integration 17a0db8). Every case passes for every variant (10 m at
1 day, 100 m at 7 days). AstroFlyer run time is the sum over the cases.

| Variant | 1 day, L0–L7 (32 cases): worst / time | 7 days, L3–L7 (20 cases): worst / time |
| --- | --- | --- |
| `dop853` | 0.628 m / 16.2 s | 6.12 m / 47.4 s |
| `ecr_mf` | 0.628 m / 16.5 s | 6.12 m / 57.5 s |
| `rkf78` | 0.700 m / 17.8 s | 27.2 m / 55.3 s |
| `rkf78_steered` | 0.607 m / 71.8 s | 25.7 m / 207.0 s |

Selected cases (max position difference from Orekit, AstroFlyer time):

| Case | `dop853` | `rkf78` | `rkf78_steered` |
| --- | --- | --- | --- |
| Molniya L7, 1 day | 0.184 m, 0.5 s | 0.456 m, 0.5 s | 0.242 m, 3.4 s |
| Molniya L5, 7 days | 1.71 m, 2.5 s | 0.695 m, 2.8 s | 3.94 m, 14.2 s |
| Tundra L7, 7 days | 0.0205 m, 1.4 s | 18.2 m, 2.3 s | 8.99 m, 5.5 s |
| GTO L3, 7 days | 1.77 m, 1.0 s | 0.519 m, 1.7 s | 0.165 m, 9.2 s |
| GTO L7, 7 days | 6.12 m, 6.0 s | 9.90 m, 4.1 s | 17.4 m, 17.3 s |
| HEO stress L7, 7 days | 4.51 m, 1.6 s | 26.3 m, 2.4 s | 6.02 m, 8.6 s |

## What this shows

**Covariance steering** shortens steps where the linearised uncertainty grows fastest. Against plain
RKF7(8) it removes much of the error in several cases (HEO stress L7 over 7 days: 26.3 m → 6.0 m; Tundra:
18.2 m → 9.0 m; GTO gravity-only: 0.52 m → 0.17 m), at about 4× the run time. It does not beat the
DOP853 baseline overall, and it made some cases worse (GTO L7 over 7 days: 9.9 m → 17.4 m; Molniya L5:
0.70 m → 3.9 m). The RKF7(8) path does not restart at shadow edges and drag-model jumps the way the
DOP853 path does, so with SRP and drag on its error is dominated by those kinks, which steering does not
address.

**ECR-MF** at this cross-check's 8×8 gravity has nothing to drop (every tier keeps degree 8), so it
matches `dop853` exactly. At 70×70 (`python -m astroflyer.validation.ecr_mf_benchmark [--days 7]`,
full model, DOP853) the tiers become
70 / 58 / 8 and the run stays within 0.0032 m (Molniya) to 0.0008 m (others) of the full model over one
day, and within 0.04–2.8 m over seven days (GTO the largest), as expected from epsilon = 1e-10 m/s².
Run time is unchanged within timing noise (0.9–1.5× across repeated sub-second runs): gravity is not where the time goes (most of it is SciPy's step loop and
the Sun/Moon/drag evaluations), so ECR-MF is a certified-accuracy fidelity schedule, not a speed-up.

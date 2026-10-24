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

Every case passes for every variant (10 m at 1 day, 100 m at 7 days). AstroFlyer run time is the sum over the cases.

| Variant | 1 day, L0–L7 (32 cases): worst / time | 7 days, L3–L7 (20 cases): worst / time |
| --- | --- | --- |
| `dop853` | 1.008 m / 16.3 s | 31.7 m / 44.7 s |
| `ecr_mf` | 1.008 m / 16.6 s | 31.7 m / 47.9 s |
| `rkf78` | 1.878 m / 18.1 s | 38.1 m / 53.1 s |
| `rkf78_steered` | 0.955 m / 69.0 s | 30.3 m / 190.8 s |

Selected cases (max position difference from Orekit, AstroFlyer time):

| Case | `dop853` | `rkf78` | `rkf78_steered` |
| --- | --- | --- | --- |
| Molniya L7, 1 day | 0.896 m, 0.4 s | 1.765 m, 0.5 s | 0.840 m, 3.0 s |
| Tundra L7, 7 days | 2.34 m, 1.3 s | 21.2 m, 2.0 s | 5.71 m, 4.9 s |
| GTO L3, 7 days | 1.77 m, 1.1 s | 0.519 m, 1.9 s | 0.165 m, 9.3 s |
| GTO L7, 7 days | 5.59 m, 5.4 s | 9.08 m, 3.7 s | 18.6 m, 15.1 s |
| HEO stress L7, 7 days | 2.87 m, 1.5 s | 28.4 m, 2.1 s | 4.37 m, 7.6 s |

## What this shows

**Covariance steering** shortens steps where the linearised uncertainty grows fastest. Against plain
RKF7(8) it removes most of the error in many cases (HEO stress L7 over 7 days: 28.4 m → 4.4 m; Tundra:
21.2 m → 5.7 m; GTO gravity-only: 0.52 m → 0.17 m), at about 3.6× the run time. It does not beat the
DOP853 baseline overall, and it made GTO L7 over 7 days worse (9.1 m → 18.6 m). The RKF7(8) path does not
restart at shadow edges and drag-model jumps the way the DOP853 path does, so with SRP and drag on its
error is dominated by those kinks, which steering does not address.

**ECR-MF** at this cross-check's 8×8 gravity has nothing to drop (every tier keeps degree 8), so it
matches `dop853` exactly. At 70×70 (`python -m astroflyer.validation.ecr_mf_benchmark [--days 7]`,
full model, DOP853) the tiers become
70 / 58 / 8 and the run stays within 0.0033 m (Molniya) to 0.0010 m (others) of the full model over one
day, and within 0.04–6.0 m over seven days (GTO the largest), as expected from epsilon = 1e-10 m/s².
Run time is unchanged within timing noise (0.9–1.5× across repeated sub-second runs): gravity is not where the time goes (most of it is SciPy's step loop and
the Sun/Moon/drag evaluations), so ECR-MF is a certified-accuracy fidelity schedule, not a speed-up.

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

`dop853` and `ecr_mf` were run after the WGS-84 shadow fix (integration 17a0db8); `rkf78` and
`rkf78_steered` were rerun on 2026-10-26, after every integrator was made to restart at shadow edges and
drag-model jumps (`backend/trajectory.py`). Every case passes for every variant (10 m at 1 day, 100 m at
7 days). AstroFlyer run time is the sum over the cases.

| Variant | 1 day, L0–L7 (32 cases): worst / time | 7 days, L3–L7 (20 cases): worst / time |
| --- | --- | --- |
| `dop853` | 0.628 m / 16.2 s | 6.12 m / 47.4 s |
| `ecr_mf` | 0.628 m / 16.5 s | 6.12 m / 57.5 s |
| `rkf78` | 0.565 m / 22.2 s | 7.04 m / 72.5 s |
| `rkf78_steered` | 0.568 m / 76.0 s | 7.78 m / 215.3 s |

Selected cases (max position difference from Orekit, AstroFlyer time):

| Case | `dop853` | `rkf78` | `rkf78_steered` |
| --- | --- | --- | --- |
| Molniya L7, 1 day | 0.184 m, 0.5 s | 0.205 m, 0.8 s | 0.195 m, 3.6 s |
| Molniya L5, 7 days | 1.71 m, 2.5 s | 2.60 m, 3.7 s | 2.65 m, 15.1 s |
| Tundra L7, 7 days | 0.0205 m, 1.4 s | 0.0101 m, 2.9 s | 0.0108 m, 6.7 s |
| GTO L3, 7 days | 1.77 m, 1.0 s | 0.519 m, 1.7 s | 0.165 m, 8.0 s |
| GTO L7, 7 days | 6.12 m, 6.0 s | 7.04 m, 7.5 s | 7.78 m, 21.6 s |
| HEO stress L7, 7 days | 4.51 m, 1.6 s | 4.49 m, 3.5 s | 4.41 m, 9.8 s |

## What this shows

**RKF7(8) with restarts.** Before the restarts, plain RKF7(8) was 18.2 m off on Tundra L7 and 26.3 m
on the HEO stress orbit over 7 days; those errors came from stepping across shadow edges and drag-model
jumps. With the restarts it is 0.010 m and 4.49 m, close to DOP853.

**Covariance steering** shortens steps where the linearised uncertainty grows fastest. With the
boundary errors gone there is little left for it to remove: the clear gain is on gravity-only GTO over
7 days (0.519 m → 0.165 m, L3 and L4), with smaller gains on the HEO stress orbit (0.30 m → 0.20 m, L3)
and Molniya over one day (0.024 m → 0.011 m). It makes some cases worse (GTO L7 over 7 days:
7.04 m → 7.78 m; GTO L5: 6.24 m → 6.95 m; Molniya L3 over 7 days: 0.26 m → 0.31 m), and costs about
3–3.5× the run time. It does not beat the DOP853 baseline overall.

**ECR-MF** at this cross-check's 8×8 gravity has nothing to drop (every tier keeps degree 8), so it
matches `dop853` exactly. At 70×70 (`python -m astroflyer.validation.ecr_mf_benchmark [--days 7]`,
full model, DOP853) the tiers become
70 / 58 / 8 and the run stays within 0.0032 m (Molniya) to 0.0008 m (others) of the full model over one
day, and within 0.04–2.8 m over seven days (GTO the largest), as expected from epsilon = 1e-10 m/s².
Run time is unchanged within timing noise (0.9–1.5× across repeated sub-second runs): gravity is not where the time goes (most of it is SciPy's step loop and
the Sun/Moon/drag evaluations), so ECR-MF is a certified-accuracy fidelity schedule, not a speed-up.

## Steering after the gravity-gradient fix (2026-10-26)

The steered runs above used a gravity gradient whose J2 ∂a_z/∂z entry was wrong (15 z²/r² instead of
30 z²/r²; fixed in `backend/covariance_engine.py`). The trajectory does not depend on the gradient, but
steering chooses its steps from it, so `rkf78_steered` was rerun on the cases that need no planetary
ephemeris in Orekit (L0–L3; the run had Orekit 13.1 with the bundled IERS files only, so L4–L7 were not
rerun): [1 day](rkf78_steered_fixed_gradient_1day/orekit_crosscheck.md),
[7 days](rkf78_steered_fixed_gradient_7day/orekit_crosscheck.md). Plain `rkf78` was rerun alongside and
reproduced the stored results to 0.3 mm.

| Case (gravity only, L3) | `rkf78` | `rkf78_steered`, old gradient | `rkf78_steered`, fixed gradient |
| --- | --- | --- | --- |
| GTO, 7 days | 0.519 m | 0.165 m | 0.160 m |
| HEO stress, 7 days | 0.299 m | 0.201 m | 0.209 m |
| Molniya, 7 days | 0.264 m | 0.309 m | 0.307 m |
| Tundra, 7 days | 0.0174 m | 0.0141 m | 0.0141 m |

The one-day L0–L3 results are unchanged to 0.1 mm. The conclusions above stand: the clear gain is on
gravity-only GTO over 7 days (now 0.52 m → 0.16 m).

# AstroFlyer vs Basilisk cross-check

Reference data: Basilisk 2.11.1, RKF78 at relTol 1e-12; AstroFlyer's EGM2008 and GM values; DE424 Sun/Moon and ITRF93 orientation from GMAT's SPICE kernels; L7 omitted (no relativity). Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.
AstroFlyer propagator: dop853 ({'method': 'DOP853'}).

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | Basilisk (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L0 | two-body | 7 | 1.12 | 0.482 | 1.11 | 5.06e-07 | 0.0009 | 100 | PASS | 1.6 | 14.9 |
| molniya | L1 | J2 only | 7 | 3.29 | 1.42 | 3.25 | 0.0266 | 0.00263 | 100 | PASS | 1.3 | 14.3 |
| molniya | L2 | zonal 4x0 | 7 | 3.23 | 1.39 | 3.19 | 0.0266 | 0.00258 | 100 | PASS | 0.8 | 12.2 |
| molniya | L3 | gravity 8x8 | 7 | 3.23 | 1.4 | 3.19 | 0.0268 | 0.00257 | 100 | PASS | 0.8 | 13.3 |
| molniya | L4 | 8x8 + Sun/Moon (DE440) | 7 | 3.29 | 1.42 | 3.24 | 0.0267 | 0.00263 | 100 | PASS | 1.1 | 583.4 |
| molniya | L5 | L4 + SRP, conical shadow | 7 | 30.3 | 13.1 | 29.9 | 0.0276 | 0.0242 | 100 | PASS | 2.8 | 242.4 |
| molniya | L6 | L5 + NRLMSISE-00 drag | 7 | 1.62e+03 | 701 | 1.6e+03 | 0.0495 | 1.3 | 100 | FAIL | 10.7 | 121.9 |
| tundra | L0 | two-body | 7 | 0.00367 | 0.000706 | 0.00366 | 2.4e-07 | 3.05e-07 | 100 | PASS | 0.4 | 15.1 |
| tundra | L1 | J2 only | 7 | 0.0376 | 0.00864 | 0.0376 | 0.00322 | 3.91e-06 | 100 | PASS | 0.4 | 13.8 |
| tundra | L2 | zonal 4x0 | 7 | 0.0376 | 0.00851 | 0.0375 | 0.00322 | 3.91e-06 | 100 | PASS | 0.5 | 13.6 |
| tundra | L3 | gravity 8x8 | 7 | 0.0378 | 0.00851 | 0.0377 | 0.00322 | 3.92e-06 | 100 | PASS | 0.4 | 14.2 |
| tundra | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.0377 | 0.00847 | 0.0376 | 0.00299 | 3.92e-06 | 100 | PASS | 0.5 | 15.8 |
| tundra | L5 | L4 + SRP, conical shadow | 7 | 2.28 | 0.53 | 2.28 | 0.00366 | 0.000234 | 100 | PASS | 1.1 | 165.4 |
| tundra | L6 | L5 + NRLMSISE-00 drag | 7 | 2.29 | 0.532 | 2.29 | 0.00358 | 0.000235 | 100 | PASS | 1.7 | 150.2 |
| gto | L0 | two-body | 7 | 1.7 | 0.806 | 1.7 | 2.38e-07 | 0.00152 | 100 | PASS | 0.9 | 13.1 |
| gto | L1 | J2 only | 7 | 0.853 | 0.372 | 0.845 | 0.0714 | 0.000725 | 100 | PASS | 1.0 | 12.8 |
| gto | L2 | zonal 4x0 | 7 | 0.885 | 0.385 | 0.877 | 0.0715 | 0.000753 | 100 | PASS | 0.9 | 12.7 |
| gto | L3 | gravity 8x8 | 7 | 4.14 | 1.78 | 4.09 | 0.0716 | 0.00354 | 100 | PASS | 0.9 | 13.7 |
| gto | L4 | 8x8 + Sun/Moon (DE440) | 7 | 4.09 | 1.75 | 4.05 | 0.0714 | 0.00351 | 100 | PASS | 1.3 | 14.7 |
| gto | L5 | L4 + SRP, conical shadow | 7 | 0.231 | 0.0929 | 0.23 | 0.0714 | 0.000212 | 100 | PASS | 2.8 | 119.1 |
| gto | L6 | L5 + NRLMSISE-00 drag | 7 | 1.66e+04 | 7.13e+03 | 1.64e+04 | 0.517 | 14 | 100 | FAIL | 5.6 | 125.7 |
| heo_stress | L0 | two-body | 7 | 0.0997 | 0.0464 | 0.0996 | 5.29e-07 | 7.53e-05 | 100 | PASS | 0.5 | 16.7 |
| heo_stress | L1 | J2 only | 7 | 5.89 | 2.76 | 5.88 | 0.0395 | 0.00442 | 100 | PASS | 0.5 | 14.5 |
| heo_stress | L2 | zonal 4x0 | 7 | 5.81 | 2.72 | 5.79 | 0.0395 | 0.00435 | 100 | PASS | 0.5 | 13.8 |
| heo_stress | L3 | gravity 8x8 | 7 | 8.55 | 4 | 8.54 | 0.0396 | 0.00642 | 100 | PASS | 0.4 | 12.7 |
| heo_stress | L4 | 8x8 + Sun/Moon (DE440) | 7 | 8.56 | 4.04 | 8.47 | 0.0395 | 0.00637 | 100 | PASS | 0.6 | 13.2 |
| heo_stress | L5 | L4 + SRP, conical shadow | 7 | 7.61 | 3.59 | 7.53 | 0.0392 | 0.00567 | 100 | PASS | 1.1 | 119.4 |
| heo_stress | L6 | L5 + NRLMSISE-00 drag | 7 | 11.6 | 5.47 | 11.5 | 0.0392 | 0.00862 | 100 | PASS | 1.4 | 119.3 |

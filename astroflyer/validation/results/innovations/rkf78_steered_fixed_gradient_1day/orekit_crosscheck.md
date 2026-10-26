# AstroFlyer vs Orekit cross-check

Reference data: AstroFlyer bundled IERS files (no ephemerides: L0-L3 only). Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.
AstroFlyer propagator: rkf78_steered ({'method': 'RKF78', 'steering': 'covariance'}).

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | Orekit (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L0 | two-body | 1 | 0.00264 | 0.0011 | 0.00264 | 8.38e-08 | 2.27e-06 | 10 | PASS | 3.1 | 0.2 |
| molniya | L1 | J2 only | 1 | 0.0112 | 0.00507 | 0.0106 | 0.000117 | 7.81e-06 | 10 | PASS | 3.0 | 0.5 |
| molniya | L2 | zonal 4x0 | 1 | 0.0112 | 0.00507 | 0.0106 | 0.000118 | 7.8e-06 | 10 | PASS | 2.5 | 0.2 |
| molniya | L3 | gravity 8x8 | 1 | 0.0113 | 0.00511 | 0.0107 | 0.000112 | 7.85e-06 | 10 | PASS | 2.4 | 0.2 |
| tundra | L0 | two-body | 1 | 2.61e-05 | 1.57e-05 | 2.24e-05 | 4.08e-08 | 5.04e-09 | 10 | PASS | 1.7 | 0.0 |
| tundra | L1 | J2 only | 1 | 0.000126 | 3.47e-05 | 0.000125 | 7.5e-06 | 1.68e-08 | 10 | PASS | 1.5 | 0.1 |
| tundra | L2 | zonal 4x0 | 1 | 0.00013 | 3.6e-05 | 0.000129 | 7.47e-06 | 1.73e-08 | 10 | PASS | 1.6 | 0.2 |
| tundra | L3 | gravity 8x8 | 1 | 0.000127 | 3.5e-05 | 0.000125 | 7.53e-06 | 1.69e-08 | 10 | PASS | 1.7 | 0.1 |
| gto | L0 | two-body | 1 | 0.00178 | 0.000742 | 0.00176 | 7.47e-08 | 1.57e-06 | 10 | PASS | 2.6 | 0.0 |
| gto | L1 | J2 only | 1 | 0.0118 | 0.00501 | 0.0117 | 0.000272 | 1.03e-05 | 10 | PASS | 2.6 | 0.1 |
| gto | L2 | zonal 4x0 | 1 | 0.0119 | 0.00505 | 0.0118 | 0.000273 | 1.04e-05 | 10 | PASS | 2.6 | 0.2 |
| gto | L3 | gravity 8x8 | 1 | 0.0121 | 0.00514 | 0.012 | 0.00027 | 1.06e-05 | 10 | PASS | 2.6 | 0.1 |
| heo_stress | L0 | two-body | 1 | 0.000143 | 7.19e-05 | 0.000137 | 1.52e-07 | 8.51e-09 | 10 | PASS | 1.6 | 0.0 |
| heo_stress | L1 | J2 only | 1 | 0.000649 | 0.000441 | 0.000441 | 0.000199 | 1.57e-08 | 10 | PASS | 1.9 | 0.2 |
| heo_stress | L2 | zonal 4x0 | 1 | 0.000652 | 0.000444 | 0.000444 | 0.000198 | 1.57e-08 | 10 | PASS | 1.7 | 0.2 |
| heo_stress | L3 | gravity 8x8 | 1 | 0.000697 | 0.000485 | 0.000468 | 0.000198 | 1.58e-08 | 10 | PASS | 1.9 | 0.1 |

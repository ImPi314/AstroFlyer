# AstroFlyer vs Orekit cross-check

Reference data: AstroFlyer bundled IERS files (no ephemerides: L0-L3 only). Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | Orekit (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L0 | two-body | 1 | 0.00361 | 0.00141 | 0.0036 | 5.64e-08 | 3.27e-06 | 10 | PASS | 1.0 | 0.4 |
| molniya | L1 | J2 only | 1 | 0.00756 | 0.00404 | 0.00745 | 0.000116 | 5.87e-06 | 10 | PASS | 1.9 | 1.6 |
| molniya | L2 | zonal 4x0 | 1 | 0.00751 | 0.00398 | 0.00741 | 0.000116 | 5.8e-06 | 10 | PASS | 0.3 | 0.2 |
| molniya | L3 | gravity 8x8 | 1 | 0.00761 | 0.00406 | 0.0075 | 0.00011 | 5.94e-06 | 10 | PASS | 0.3 | 0.2 |
| tundra | L0 | two-body | 1 | 0.000811 | 0.00038 | 0.00081 | 1.8e-08 | 7.66e-08 | 10 | PASS | 0.2 | 0.0 |
| tundra | L1 | J2 only | 1 | 0.000934 | 0.000489 | 0.000933 | 7.47e-06 | 8.7e-08 | 10 | PASS | 0.2 | 0.2 |
| tundra | L2 | zonal 4x0 | 1 | 0.000949 | 0.000424 | 0.000949 | 7.43e-06 | 8.89e-08 | 10 | PASS | 0.2 | 0.2 |
| tundra | L3 | gravity 8x8 | 1 | 0.00094 | 0.000468 | 0.000939 | 7.52e-06 | 8.73e-08 | 10 | PASS | 0.2 | 0.2 |
| gto | L0 | two-body | 1 | 0.018 | 0.00756 | 0.0177 | 4.51e-08 | 1.55e-05 | 10 | PASS | 0.4 | 0.0 |
| gto | L1 | J2 only | 1 | 0.0285 | 0.0117 | 0.0284 | 0.000274 | 2.53e-05 | 10 | PASS | 0.4 | 0.2 |
| gto | L2 | zonal 4x0 | 1 | 0.0289 | 0.0119 | 0.0289 | 0.000274 | 2.57e-05 | 10 | PASS | 0.5 | 0.2 |
| gto | L3 | gravity 8x8 | 1 | 0.0283 | 0.0116 | 0.0283 | 0.000272 | 2.51e-05 | 10 | PASS | 0.5 | 0.2 |
| heo_stress | L0 | two-body | 1 | 0.00204 | 0.00122 | 0.00163 | 1.38e-07 | 6.99e-08 | 10 | PASS | 0.2 | 0.0 |
| heo_stress | L1 | J2 only | 1 | 0.00116 | 0.000267 | 0.00113 | 0.000199 | 4.41e-08 | 10 | PASS | 0.2 | 0.2 |
| heo_stress | L2 | zonal 4x0 | 1 | 0.000802 | 0.000488 | 0.000671 | 0.000198 | 3.72e-08 | 10 | PASS | 0.2 | 0.2 |
| heo_stress | L3 | gravity 8x8 | 1 | 0.0011 | 0.000161 | 0.00107 | 0.000198 | 6.56e-08 | 10 | PASS | 0.2 | 0.1 |

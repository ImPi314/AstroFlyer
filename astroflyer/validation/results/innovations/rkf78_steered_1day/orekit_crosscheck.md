# AstroFlyer vs Orekit cross-check

Reference data: orekit-data at C:\Users\Harshith\OneDrive\Desktop\major_project_py\astroflyer\validation\orekit-data. Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.
AstroFlyer propagator: rkf78_steered ({'method': 'RKF78', 'steering': 'covariance'}).

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | Orekit (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L0 | two-body | 1 | 0.00259 | 0.00108 | 0.00259 | 5.72e-08 | 2.23e-06 | 10 | PASS | 2.4 | 0.2 |
| molniya | L1 | J2 only | 1 | 0.0112 | 0.00505 | 0.0106 | 0.000117 | 7.77e-06 | 10 | PASS | 2.4 | 0.2 |
| molniya | L2 | zonal 4x0 | 1 | 0.0111 | 0.00504 | 0.0106 | 0.000118 | 7.76e-06 | 10 | PASS | 1.8 | 0.1 |
| molniya | L3 | gravity 8x8 | 1 | 0.0112 | 0.00508 | 0.0106 | 0.000112 | 7.82e-06 | 10 | PASS | 1.8 | 0.2 |
| molniya | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.0113 | 0.00509 | 0.0107 | 0.000112 | 7.85e-06 | 10 | PASS | 2.3 | 0.2 |
| molniya | L5 | L4 + SRP, conical shadow | 1 | 0.126 | 0.0583 | 0.12 | 0.000129 | 8.7e-05 | 10 | PASS | 3.0 | 0.6 |
| molniya | L6 | L5 + NRLMSISE-00 drag | 1 | 0.207 | 0.0952 | 0.195 | 0.000151 | 0.000142 | 10 | PASS | 10.9 | 1.8 |
| molniya | L7 | L6 + relativity (full model) | 1 | 0.242 | 0.112 | 0.229 | 0.00015 | 0.000167 | 10 | PASS | 3.4 | 1.6 |
| tundra | L0 | two-body | 1 | 2.82e-05 | 1.54e-05 | 2.5e-05 | 5.37e-08 | 4.78e-09 | 10 | PASS | 1.0 | 0.0 |
| tundra | L1 | J2 only | 1 | 0.000124 | 3.42e-05 | 0.000123 | 7.47e-06 | 1.66e-08 | 10 | PASS | 1.1 | 0.1 |
| tundra | L2 | zonal 4x0 | 1 | 0.000127 | 3.5e-05 | 0.000126 | 7.42e-06 | 1.69e-08 | 10 | PASS | 1.1 | 0.1 |
| tundra | L3 | gravity 8x8 | 1 | 0.000127 | 3.5e-05 | 0.000125 | 7.49e-06 | 1.69e-08 | 10 | PASS | 1.1 | 0.2 |
| tundra | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.000133 | 3.67e-05 | 0.000132 | 6.95e-06 | 1.73e-08 | 10 | PASS | 1.4 | 0.2 |
| tundra | L5 | L4 + SRP, conical shadow | 1 | 0.0143 | 0.00406 | 0.0142 | 4.11e-05 | 1.37e-06 | 10 | PASS | 1.9 | 0.7 |
| tundra | L6 | L5 + NRLMSISE-00 drag | 1 | 0.00163 | 0.000465 | 0.00163 | 1.42e-05 | 1.69e-07 | 10 | PASS | 2.0 | 1.4 |
| tundra | L7 | L6 + relativity (full model) | 1 | 0.00202 | 0.000573 | 0.00201 | 1.47e-05 | 2.07e-07 | 10 | PASS | 2.1 | 1.5 |
| gto | L0 | two-body | 1 | 0.00179 | 0.000745 | 0.00177 | 3.76e-08 | 1.57e-06 | 10 | PASS | 1.7 | 0.0 |
| gto | L1 | J2 only | 1 | 0.0118 | 0.00501 | 0.0117 | 0.000272 | 1.03e-05 | 10 | PASS | 1.8 | 0.1 |
| gto | L2 | zonal 4x0 | 1 | 0.0118 | 0.00504 | 0.0118 | 0.000273 | 1.03e-05 | 10 | PASS | 1.8 | 0.1 |
| gto | L3 | gravity 8x8 | 1 | 0.0121 | 0.00514 | 0.012 | 0.00027 | 1.06e-05 | 10 | PASS | 1.8 | 0.2 |
| gto | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.0121 | 0.00514 | 0.012 | 0.00027 | 1.06e-05 | 10 | PASS | 2.3 | 0.2 |
| gto | L5 | L4 + SRP, conical shadow | 1 | 0.374 | 0.158 | 0.373 | 0.000353 | 0.000333 | 10 | PASS | 3.1 | 0.7 |
| gto | L6 | L5 + NRLMSISE-00 drag | 1 | 0.496 | 0.21 | 0.495 | 0.000317 | 0.000442 | 10 | PASS | 3.3 | 1.6 |
| gto | L7 | L6 + relativity (full model) | 1 | 0.607 | 0.257 | 0.606 | 0.000348 | 0.000535 | 10 | PASS | 3.5 | 1.6 |
| heo_stress | L0 | two-body | 1 | 0.000143 | 6.99e-05 | 0.000137 | 3.43e-08 | 8.51e-09 | 10 | PASS | 1.1 | 0.0 |
| heo_stress | L1 | J2 only | 1 | 0.000647 | 0.00044 | 0.00044 | 0.000199 | 1.57e-08 | 10 | PASS | 1.2 | 0.1 |
| heo_stress | L2 | zonal 4x0 | 1 | 0.000652 | 0.000444 | 0.000444 | 0.000198 | 1.57e-08 | 10 | PASS | 1.2 | 0.1 |
| heo_stress | L3 | gravity 8x8 | 1 | 0.000696 | 0.000484 | 0.000467 | 0.000198 | 1.58e-08 | 10 | PASS | 1.2 | 0.1 |
| heo_stress | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.000686 | 0.000483 | 0.000453 | 0.000198 | 1.58e-08 | 10 | PASS | 1.5 | 0.2 |
| heo_stress | L5 | L4 + SRP, conical shadow | 1 | 0.0495 | 0.0428 | 0.0247 | 0.000455 | 1.18e-06 | 10 | PASS | 2.0 | 0.6 |
| heo_stress | L6 | L5 + NRLMSISE-00 drag | 1 | 0.0363 | 0.0319 | 0.0173 | 7.18e-05 | 8.73e-07 | 10 | PASS | 2.2 | 1.3 |
| heo_stress | L7 | L6 + relativity (full model) | 1 | 0.026 | 0.0231 | 0.0119 | 0.000154 | 6.29e-07 | 10 | PASS | 2.3 | 1.3 |

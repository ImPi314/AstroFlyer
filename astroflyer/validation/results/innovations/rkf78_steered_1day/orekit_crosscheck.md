# AstroFlyer vs Orekit cross-check

Reference data: orekit-data at astroflyer/validation/orekit-data. Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.
AstroFlyer propagator: rkf78_steered ({'method': 'RKF78', 'steering': 'covariance'}).

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | Orekit (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L0 | two-body | 1 | 0.00259 | 0.00108 | 0.00259 | 5.72e-08 | 2.23e-06 | 10 | PASS | 2.3 | 0.2 |
| molniya | L1 | J2 only | 1 | 0.0112 | 0.00505 | 0.0106 | 0.000117 | 7.77e-06 | 10 | PASS | 2.3 | 0.3 |
| molniya | L2 | zonal 4x0 | 1 | 0.0111 | 0.00504 | 0.0106 | 0.000118 | 7.76e-06 | 10 | PASS | 1.9 | 0.2 |
| molniya | L3 | gravity 8x8 | 1 | 0.0112 | 0.00508 | 0.0106 | 0.000112 | 7.82e-06 | 10 | PASS | 2.2 | 0.2 |
| molniya | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.0113 | 0.00509 | 0.0107 | 0.000112 | 7.85e-06 | 10 | PASS | 2.4 | 0.3 |
| molniya | L5 | L4 + SRP, conical shadow | 1 | 0.0818 | 0.0375 | 0.0775 | 0.000134 | 5.63e-05 | 10 | PASS | 3.0 | 0.7 |
| molniya | L6 | L5 + NRLMSISE-00 drag | 1 | 0.16 | 0.0733 | 0.151 | 0.000156 | 0.00011 | 10 | PASS | 11.6 | 2.3 |
| molniya | L7 | L6 + relativity (full model) | 1 | 0.195 | 0.0896 | 0.184 | 0.000155 | 0.000134 | 10 | PASS | 3.6 | 1.9 |
| tundra | L0 | two-body | 1 | 2.82e-05 | 1.54e-05 | 2.5e-05 | 5.37e-08 | 4.78e-09 | 10 | PASS | 1.0 | 0.0 |
| tundra | L1 | J2 only | 1 | 0.000124 | 3.42e-05 | 0.000123 | 7.47e-06 | 1.66e-08 | 10 | PASS | 1.0 | 0.2 |
| tundra | L2 | zonal 4x0 | 1 | 0.000127 | 3.5e-05 | 0.000126 | 7.42e-06 | 1.69e-08 | 10 | PASS | 1.0 | 0.2 |
| tundra | L3 | gravity 8x8 | 1 | 0.000127 | 3.5e-05 | 0.000125 | 7.49e-06 | 1.69e-08 | 10 | PASS | 1.1 | 0.2 |
| tundra | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.000133 | 3.67e-05 | 0.000132 | 6.95e-06 | 1.73e-08 | 10 | PASS | 1.6 | 0.3 |
| tundra | L5 | L4 + SRP, conical shadow | 1 | 0.0125 | 0.00356 | 0.0125 | 3.83e-05 | 1.19e-06 | 10 | PASS | 2.1 | 0.8 |
| tundra | L6 | L5 + NRLMSISE-00 drag | 1 | 0.000164 | 4.17e-05 | 0.000163 | 1.14e-05 | 1.11e-08 | 10 | PASS | 2.0 | 1.7 |
| tundra | L7 | L6 + relativity (full model) | 1 | 0.000225 | 6.55e-05 | 0.000222 | 1.19e-05 | 2.89e-08 | 10 | PASS | 2.2 | 1.9 |
| gto | L0 | two-body | 1 | 0.00179 | 0.000745 | 0.00177 | 3.76e-08 | 1.57e-06 | 10 | PASS | 1.6 | 0.0 |
| gto | L1 | J2 only | 1 | 0.0118 | 0.00501 | 0.0117 | 0.000272 | 1.03e-05 | 10 | PASS | 1.9 | 0.2 |
| gto | L2 | zonal 4x0 | 1 | 0.0118 | 0.00504 | 0.0118 | 0.000273 | 1.03e-05 | 10 | PASS | 1.7 | 0.2 |
| gto | L3 | gravity 8x8 | 1 | 0.0121 | 0.00514 | 0.012 | 0.00027 | 1.06e-05 | 10 | PASS | 1.7 | 0.2 |
| gto | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.0121 | 0.00514 | 0.012 | 0.00027 | 1.06e-05 | 10 | PASS | 2.1 | 0.2 |
| gto | L5 | L4 + SRP, conical shadow | 1 | 0.0337 | 0.0142 | 0.0337 | 0.000263 | 3.01e-05 | 10 | PASS | 4.5 | 0.9 |
| gto | L6 | L5 + NRLMSISE-00 drag | 1 | 0.568 | 0.239 | 0.567 | 0.00023 | 0.000503 | 10 | PASS | 4.2 | 2.0 |
| gto | L7 | L6 + relativity (full model) | 1 | 0.535 | 0.226 | 0.534 | 0.000267 | 0.000473 | 10 | PASS | 4.1 | 1.8 |
| heo_stress | L0 | two-body | 1 | 0.000143 | 6.99e-05 | 0.000137 | 3.43e-08 | 8.51e-09 | 10 | PASS | 1.0 | 0.0 |
| heo_stress | L1 | J2 only | 1 | 0.000647 | 0.00044 | 0.00044 | 0.000199 | 1.57e-08 | 10 | PASS | 1.1 | 0.2 |
| heo_stress | L2 | zonal 4x0 | 1 | 0.000652 | 0.000444 | 0.000444 | 0.000198 | 1.57e-08 | 10 | PASS | 1.1 | 0.2 |
| heo_stress | L3 | gravity 8x8 | 1 | 0.000696 | 0.000484 | 0.000467 | 0.000198 | 1.58e-08 | 10 | PASS | 1.1 | 0.2 |
| heo_stress | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.000686 | 0.000483 | 0.000453 | 0.000198 | 1.58e-08 | 10 | PASS | 1.5 | 0.2 |
| heo_stress | L5 | L4 + SRP, conical shadow | 1 | 0.0494 | 0.0428 | 0.0247 | 0.000462 | 1.18e-06 | 10 | PASS | 2.0 | 0.9 |
| heo_stress | L6 | L5 + NRLMSISE-00 drag | 1 | 0.0361 | 0.0318 | 0.0172 | 7.76e-05 | 8.69e-07 | 10 | PASS | 2.6 | 1.8 |
| heo_stress | L7 | L6 + relativity (full model) | 1 | 0.0258 | 0.0229 | 0.0118 | 0.000149 | 6.24e-07 | 10 | PASS | 2.5 | 1.9 |

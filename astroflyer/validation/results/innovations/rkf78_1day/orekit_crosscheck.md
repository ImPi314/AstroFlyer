# AstroFlyer vs Orekit cross-check

Reference data: orekit-data at C:\Users\Harshith\OneDrive\Desktop\major_project_py\astroflyer\validation\orekit-data. Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.
AstroFlyer propagator: rkf78 ({'method': 'RKF78'}).

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | Orekit (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L0 | two-body | 1 | 0.0164 | 0.00695 | 0.0164 | 5.01e-08 | 1.38e-05 | 10 | PASS | 1.0 | 0.3 |
| molniya | L1 | J2 only | 1 | 0.0243 | 0.0111 | 0.023 | 0.000118 | 1.69e-05 | 10 | PASS | 0.8 | 0.3 |
| molniya | L2 | zonal 4x0 | 1 | 0.0243 | 0.0111 | 0.023 | 0.000118 | 1.69e-05 | 10 | PASS | 0.2 | 0.1 |
| molniya | L3 | gravity 8x8 | 1 | 0.0244 | 0.0111 | 0.0231 | 0.000112 | 1.69e-05 | 10 | PASS | 0.2 | 0.2 |
| molniya | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.0244 | 0.0111 | 0.0231 | 0.000112 | 1.7e-05 | 10 | PASS | 0.3 | 0.3 |
| molniya | L5 | L4 + SRP, conical shadow | 1 | 0.501 | 0.216 | 0.494 | 0.000548 | 0.000394 | 10 | PASS | 0.4 | 0.6 |
| molniya | L6 | L5 + NRLMSISE-00 drag | 1 | 0.464 | 0.2 | 0.458 | 0.000532 | 0.000365 | 10 | PASS | 7.9 | 1.8 |
| molniya | L7 | L6 + relativity (full model) | 1 | 0.456 | 0.197 | 0.449 | 0.000532 | 0.000358 | 10 | PASS | 0.5 | 1.7 |
| tundra | L0 | two-body | 1 | 0.00148 | 0.000375 | 0.00147 | 3.45e-08 | 1.77e-07 | 10 | PASS | 0.1 | 0.0 |
| tundra | L1 | J2 only | 1 | 0.00161 | 0.000408 | 0.0016 | 7.47e-06 | 1.89e-07 | 10 | PASS | 0.1 | 0.1 |
| tundra | L2 | zonal 4x0 | 1 | 0.00161 | 0.000409 | 0.00161 | 7.45e-06 | 1.89e-07 | 10 | PASS | 0.1 | 0.1 |
| tundra | L3 | gravity 8x8 | 1 | 0.00161 | 0.000408 | 0.0016 | 7.52e-06 | 1.89e-07 | 10 | PASS | 0.1 | 0.2 |
| tundra | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.00161 | 0.000411 | 0.00161 | 7.06e-06 | 1.9e-07 | 10 | PASS | 0.2 | 0.2 |
| tundra | L5 | L4 + SRP, conical shadow | 1 | 0.408 | 0.12 | 0.406 | 0.00205 | 2.99e-05 | 10 | PASS | 0.3 | 0.7 |
| tundra | L6 | L5 + NRLMSISE-00 drag | 1 | 0.419 | 0.121 | 0.418 | 0.00207 | 3.1e-05 | 10 | PASS | 0.3 | 1.7 |
| tundra | L7 | L6 + relativity (full model) | 1 | 0.419 | 0.121 | 0.417 | 0.00207 | 3.1e-05 | 10 | PASS | 0.3 | 1.7 |
| gto | L0 | two-body | 1 | 0.00568 | 0.00238 | 0.0056 | 3.57e-08 | 4.98e-06 | 10 | PASS | 0.2 | 0.0 |
| gto | L1 | J2 only | 1 | 0.00777 | 0.00339 | 0.00774 | 0.000272 | 6.69e-06 | 10 | PASS | 0.3 | 0.1 |
| gto | L2 | zonal 4x0 | 1 | 0.00783 | 0.00342 | 0.00781 | 0.000272 | 6.75e-06 | 10 | PASS | 0.3 | 0.2 |
| gto | L3 | gravity 8x8 | 1 | 0.00806 | 0.00352 | 0.00804 | 0.00027 | 6.95e-06 | 10 | PASS | 0.3 | 0.2 |
| gto | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.00807 | 0.00352 | 0.00805 | 0.00027 | 6.96e-06 | 10 | PASS | 0.3 | 0.2 |
| gto | L5 | L4 + SRP, conical shadow | 1 | 0.281 | 0.12 | 0.281 | 0.000479 | 0.000246 | 10 | PASS | 0.5 | 0.8 |
| gto | L6 | L5 + NRLMSISE-00 drag | 1 | 0.4 | 0.17 | 0.399 | 0.000437 | 0.000352 | 10 | PASS | 0.6 | 1.8 |
| gto | L7 | L6 + relativity (full model) | 1 | 0.7 | 0.294 | 0.698 | 0.000472 | 0.000621 | 10 | PASS | 0.6 | 1.9 |
| heo_stress | L0 | two-body | 1 | 0.0051 | 0.00429 | 0.00274 | 4.52e-08 | 1.19e-07 | 10 | PASS | 0.1 | 0.0 |
| heo_stress | L1 | J2 only | 1 | 0.00454 | 0.00397 | 0.0022 | 0.000199 | 1.09e-07 | 10 | PASS | 0.1 | 0.2 |
| heo_stress | L2 | zonal 4x0 | 1 | 0.00453 | 0.00396 | 0.00219 | 0.000198 | 1.09e-07 | 10 | PASS | 0.2 | 0.2 |
| heo_stress | L3 | gravity 8x8 | 1 | 0.00448 | 0.00392 | 0.00217 | 0.000198 | 1.08e-07 | 10 | PASS | 0.2 | 0.2 |
| heo_stress | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.00449 | 0.00392 | 0.00218 | 0.000198 | 1.08e-07 | 10 | PASS | 0.2 | 0.2 |
| heo_stress | L5 | L4 + SRP, conical shadow | 1 | 0.214 | 0.182 | 0.112 | 0.00433 | 5.03e-06 | 10 | PASS | 0.3 | 0.7 |
| heo_stress | L6 | L5 + NRLMSISE-00 drag | 1 | 0.238 | 0.202 | 0.125 | 0.0048 | 5.6e-06 | 10 | PASS | 0.3 | 1.5 |
| heo_stress | L7 | L6 + relativity (full model) | 1 | 0.246 | 0.209 | 0.129 | 0.00496 | 5.78e-06 | 10 | PASS | 0.3 | 1.4 |

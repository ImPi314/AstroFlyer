# AstroFlyer vs Orekit cross-check

Reference data: orekit-data at C:\Users\Harshith\OneDrive\Desktop\major_project_py\astroflyer\validation\orekit-data. Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.
AstroFlyer propagator: rkf78 ({'method': 'RKF78'}).

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | Orekit (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L0 | two-body | 1 | 0.0164 | 0.00695 | 0.0164 | 5.01e-08 | 1.38e-05 | 10 | PASS | 1.0 | 0.2 |
| molniya | L1 | J2 only | 1 | 0.0243 | 0.0111 | 0.023 | 0.000118 | 1.69e-05 | 10 | PASS | 0.8 | 0.3 |
| molniya | L2 | zonal 4x0 | 1 | 0.0243 | 0.0111 | 0.023 | 0.000118 | 1.69e-05 | 10 | PASS | 0.3 | 0.1 |
| molniya | L3 | gravity 8x8 | 1 | 0.0244 | 0.0111 | 0.0231 | 0.000112 | 1.69e-05 | 10 | PASS | 0.2 | 0.2 |
| molniya | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.0244 | 0.0111 | 0.0231 | 0.000112 | 1.7e-05 | 10 | PASS | 0.3 | 0.2 |
| molniya | L5 | L4 + SRP, conical shadow | 1 | 1.88 | 0.865 | 1.78 | 0.000736 | 0.00129 | 10 | PASS | 0.4 | 0.5 |
| molniya | L6 | L5 + NRLMSISE-00 drag | 1 | 1.8 | 0.829 | 1.7 | 0.000719 | 0.00124 | 10 | PASS | 8.6 | 1.9 |
| molniya | L7 | L6 + relativity (full model) | 1 | 1.77 | 0.813 | 1.67 | 0.000719 | 0.00121 | 10 | PASS | 0.5 | 1.7 |
| tundra | L0 | two-body | 1 | 0.00148 | 0.000375 | 0.00147 | 3.45e-08 | 1.77e-07 | 10 | PASS | 0.1 | 0.0 |
| tundra | L1 | J2 only | 1 | 0.00161 | 0.000408 | 0.0016 | 7.47e-06 | 1.89e-07 | 10 | PASS | 0.2 | 0.1 |
| tundra | L2 | zonal 4x0 | 1 | 0.00161 | 0.000409 | 0.00161 | 7.45e-06 | 1.89e-07 | 10 | PASS | 0.2 | 0.1 |
| tundra | L3 | gravity 8x8 | 1 | 0.00161 | 0.000408 | 0.0016 | 7.52e-06 | 1.89e-07 | 10 | PASS | 0.2 | 0.2 |
| tundra | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.00161 | 0.000411 | 0.00161 | 7.06e-06 | 1.9e-07 | 10 | PASS | 0.2 | 0.2 |
| tundra | L5 | L4 + SRP, conical shadow | 1 | 0.436 | 0.124 | 0.434 | 0.0021 | 3.28e-05 | 10 | PASS | 0.3 | 0.7 |
| tundra | L6 | L5 + NRLMSISE-00 drag | 1 | 0.447 | 0.128 | 0.445 | 0.00213 | 3.39e-05 | 10 | PASS | 0.3 | 1.7 |
| tundra | L7 | L6 + relativity (full model) | 1 | 0.447 | 0.127 | 0.445 | 0.00213 | 3.39e-05 | 10 | PASS | 0.3 | 1.7 |
| gto | L0 | two-body | 1 | 0.00568 | 0.00238 | 0.0056 | 3.57e-08 | 4.98e-06 | 10 | PASS | 0.3 | 0.0 |
| gto | L1 | J2 only | 1 | 0.00777 | 0.00339 | 0.00774 | 0.000272 | 6.69e-06 | 10 | PASS | 0.3 | 0.2 |
| gto | L2 | zonal 4x0 | 1 | 0.00783 | 0.00342 | 0.00781 | 0.000272 | 6.75e-06 | 10 | PASS | 0.3 | 0.1 |
| gto | L3 | gravity 8x8 | 1 | 0.00806 | 0.00352 | 0.00804 | 0.00027 | 6.95e-06 | 10 | PASS | 0.3 | 0.2 |
| gto | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.00807 | 0.00352 | 0.00805 | 0.00027 | 6.96e-06 | 10 | PASS | 0.4 | 0.3 |
| gto | L5 | L4 + SRP, conical shadow | 1 | 0.287 | 0.123 | 0.287 | 0.00048 | 0.000251 | 10 | PASS | 0.4 | 0.7 |
| gto | L6 | L5 + NRLMSISE-00 drag | 1 | 0.406 | 0.173 | 0.405 | 0.000438 | 0.000357 | 10 | PASS | 0.5 | 1.8 |
| gto | L7 | L6 + relativity (full model) | 1 | 0.693 | 0.291 | 0.692 | 0.000473 | 0.000616 | 10 | PASS | 0.5 | 1.8 |
| heo_stress | L0 | two-body | 1 | 0.0051 | 0.00429 | 0.00274 | 4.52e-08 | 1.19e-07 | 10 | PASS | 0.1 | 0.0 |
| heo_stress | L1 | J2 only | 1 | 0.00454 | 0.00397 | 0.0022 | 0.000199 | 1.09e-07 | 10 | PASS | 0.1 | 0.1 |
| heo_stress | L2 | zonal 4x0 | 1 | 0.00453 | 0.00396 | 0.00219 | 0.000198 | 1.09e-07 | 10 | PASS | 0.1 | 0.2 |
| heo_stress | L3 | gravity 8x8 | 1 | 0.00448 | 0.00392 | 0.00217 | 0.000198 | 1.08e-07 | 10 | PASS | 0.1 | 0.2 |
| heo_stress | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.00449 | 0.00392 | 0.00218 | 0.000198 | 1.08e-07 | 10 | PASS | 0.2 | 0.2 |
| heo_stress | L5 | L4 + SRP, conical shadow | 1 | 0.232 | 0.198 | 0.121 | 0.00436 | 5.48e-06 | 10 | PASS | 0.2 | 0.7 |
| heo_stress | L6 | L5 + NRLMSISE-00 drag | 1 | 0.258 | 0.22 | 0.134 | 0.00485 | 6.07e-06 | 10 | PASS | 0.2 | 1.7 |
| heo_stress | L7 | L6 + relativity (full model) | 1 | 0.265 | 0.226 | 0.138 | 0.00501 | 6.25e-06 | 10 | PASS | 0.3 | 1.7 |

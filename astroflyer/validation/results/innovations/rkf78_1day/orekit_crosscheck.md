# AstroFlyer vs Orekit cross-check

Reference data: orekit-data at C:\Users\Harshith\OneDrive\Desktop\major_project_py\astroflyer\validation\orekit-data. Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.
AstroFlyer propagator: rkf78 ({'method': 'RKF78'}).

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | Orekit (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L0 | two-body | 1 | 0.0164 | 0.00695 | 0.0164 | 5.01e-08 | 1.38e-05 | 10 | PASS | 2.1 | 0.3 |
| molniya | L1 | J2 only | 1 | 0.0243 | 0.0111 | 0.023 | 0.000118 | 1.69e-05 | 10 | PASS | 0.8 | 0.3 |
| molniya | L2 | zonal 4x0 | 1 | 0.0243 | 0.0111 | 0.023 | 0.000118 | 1.69e-05 | 10 | PASS | 0.2 | 0.2 |
| molniya | L3 | gravity 8x8 | 1 | 0.0244 | 0.0111 | 0.0231 | 0.000112 | 1.69e-05 | 10 | PASS | 0.2 | 0.2 |
| molniya | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.0244 | 0.0111 | 0.0231 | 0.000112 | 1.7e-05 | 10 | PASS | 0.3 | 0.3 |
| molniya | L5 | L4 + SRP, conical shadow | 1 | 0.0941 | 0.0432 | 0.0891 | 0.000134 | 6.48e-05 | 10 | PASS | 0.6 | 0.7 |
| molniya | L6 | L5 + NRLMSISE-00 drag | 1 | 0.172 | 0.0788 | 0.162 | 0.000156 | 0.000118 | 10 | PASS | 8.8 | 2.0 |
| molniya | L7 | L6 + relativity (full model) | 1 | 0.205 | 0.0945 | 0.194 | 0.000156 | 0.000141 | 10 | PASS | 0.8 | 1.9 |
| tundra | L0 | two-body | 1 | 0.00148 | 0.000375 | 0.00147 | 3.45e-08 | 1.77e-07 | 10 | PASS | 0.2 | 0.0 |
| tundra | L1 | J2 only | 1 | 0.00161 | 0.000408 | 0.0016 | 7.47e-06 | 1.89e-07 | 10 | PASS | 0.1 | 0.2 |
| tundra | L2 | zonal 4x0 | 1 | 0.00161 | 0.000409 | 0.00161 | 7.45e-06 | 1.89e-07 | 10 | PASS | 0.2 | 0.1 |
| tundra | L3 | gravity 8x8 | 1 | 0.00161 | 0.000408 | 0.0016 | 7.52e-06 | 1.89e-07 | 10 | PASS | 0.1 | 0.1 |
| tundra | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.00161 | 0.000411 | 0.00161 | 7.06e-06 | 1.9e-07 | 10 | PASS | 0.2 | 0.3 |
| tundra | L5 | L4 + SRP, conical shadow | 1 | 0.0138 | 0.0039 | 0.0137 | 3.84e-05 | 1.35e-06 | 10 | PASS | 0.3 | 0.8 |
| tundra | L6 | L5 + NRLMSISE-00 drag | 1 | 0.00124 | 0.000301 | 0.00123 | 1.14e-05 | 1.52e-07 | 10 | PASS | 0.4 | 1.8 |
| tundra | L7 | L6 + relativity (full model) | 1 | 0.00161 | 0.000406 | 0.00161 | 1.2e-05 | 1.9e-07 | 10 | PASS | 0.4 | 1.7 |
| gto | L0 | two-body | 1 | 0.00568 | 0.00238 | 0.0056 | 3.57e-08 | 4.98e-06 | 10 | PASS | 0.2 | 0.0 |
| gto | L1 | J2 only | 1 | 0.00777 | 0.00339 | 0.00774 | 0.000272 | 6.69e-06 | 10 | PASS | 0.2 | 0.1 |
| gto | L2 | zonal 4x0 | 1 | 0.00783 | 0.00342 | 0.00781 | 0.000272 | 6.75e-06 | 10 | PASS | 0.2 | 0.2 |
| gto | L3 | gravity 8x8 | 1 | 0.00806 | 0.00352 | 0.00804 | 0.00027 | 6.95e-06 | 10 | PASS | 0.4 | 0.3 |
| gto | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.00807 | 0.00352 | 0.00805 | 0.00027 | 6.96e-06 | 10 | PASS | 0.4 | 0.3 |
| gto | L5 | L4 + SRP, conical shadow | 1 | 0.0296 | 0.0125 | 0.0295 | 0.000262 | 2.63e-05 | 10 | PASS | 0.7 | 0.9 |
| gto | L6 | L5 + NRLMSISE-00 drag | 1 | 0.565 | 0.238 | 0.564 | 0.000229 | 0.000501 | 10 | PASS | 1.1 | 1.8 |
| gto | L7 | L6 + relativity (full model) | 1 | 0.539 | 0.228 | 0.538 | 0.000266 | 0.000476 | 10 | PASS | 1.1 | 2.0 |
| heo_stress | L0 | two-body | 1 | 0.0051 | 0.00429 | 0.00274 | 4.52e-08 | 1.19e-07 | 10 | PASS | 0.1 | 0.0 |
| heo_stress | L1 | J2 only | 1 | 0.00454 | 0.00397 | 0.0022 | 0.000199 | 1.09e-07 | 10 | PASS | 0.1 | 0.2 |
| heo_stress | L2 | zonal 4x0 | 1 | 0.00453 | 0.00396 | 0.00219 | 0.000198 | 1.09e-07 | 10 | PASS | 0.2 | 0.2 |
| heo_stress | L3 | gravity 8x8 | 1 | 0.00448 | 0.00392 | 0.00217 | 0.000198 | 1.08e-07 | 10 | PASS | 0.2 | 0.2 |
| heo_stress | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.00449 | 0.00392 | 0.00218 | 0.000198 | 1.08e-07 | 10 | PASS | 0.2 | 0.3 |
| heo_stress | L5 | L4 + SRP, conical shadow | 1 | 0.0543 | 0.047 | 0.0273 | 0.000461 | 1.29e-06 | 10 | PASS | 0.3 | 0.7 |
| heo_stress | L6 | L5 + NRLMSISE-00 drag | 1 | 0.0408 | 0.0358 | 0.0195 | 7.76e-05 | 9.8e-07 | 10 | PASS | 0.4 | 1.8 |
| heo_stress | L7 | L6 + relativity (full model) | 1 | 0.0304 | 0.0269 | 0.0142 | 0.000149 | 7.35e-07 | 10 | PASS | 0.4 | 1.7 |

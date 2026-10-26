# AstroFlyer vs Orekit cross-check

Reference data: orekit-data at C:\Users\Harshith\OneDrive\Desktop\major_project_py\astroflyer\validation\orekit-data. Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.
AstroFlyer propagator: rkf78 ({'method': 'RKF78'}).

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | Orekit (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L3 | gravity 8x8 | 7 | 0.264 | 0.113 | 0.26 | 0.000698 | 0.00021 | 100 | PASS | 3.0 | 1.5 |
| molniya | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.263 | 0.113 | 0.259 | 0.0007 | 0.000211 | 100 | PASS | 2.2 | 1.4 |
| molniya | L5 | L4 + SRP, conical shadow | 7 | 2.6 | 1.12 | 2.57 | 0.00201 | 0.00208 | 100 | PASS | 3.7 | 3.0 |
| molniya | L6 | L5 + NRLMSISE-00 drag | 7 | 6.62 | 2.86 | 6.54 | 0.0022 | 0.0053 | 100 | PASS | 12.8 | 11.8 |
| molniya | L7 | L6 + relativity (full model) | 7 | 6.03 | 2.61 | 5.95 | 0.00194 | 0.00482 | 100 | PASS | 5.3 | 11.2 |
| tundra | L3 | gravity 8x8 | 7 | 0.0174 | 0.00275 | 0.0174 | 2.64e-05 | 1.95e-06 | 100 | PASS | 0.9 | 1.0 |
| tundra | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.0175 | 0.00276 | 0.0175 | 2.98e-05 | 1.96e-06 | 100 | PASS | 1.3 | 1.5 |
| tundra | L5 | L4 + SRP, conical shadow | 7 | 0.0391 | 0.00769 | 0.0391 | 4.94e-05 | 4.19e-06 | 100 | PASS | 2.8 | 4.9 |
| tundra | L6 | L5 + NRLMSISE-00 drag | 7 | 0.0162 | 0.00239 | 0.0162 | 6.5e-05 | 1.84e-06 | 100 | PASS | 2.8 | 10.0 |
| tundra | L7 | L6 + relativity (full model) | 7 | 0.0101 | 0.00395 | 0.0101 | 0.000122 | 8.19e-07 | 100 | PASS | 2.9 | 9.9 |
| gto | L3 | gravity 8x8 | 7 | 0.519 | 0.223 | 0.514 | 0.000339 | 0.000445 | 100 | PASS | 1.7 | 0.8 |
| gto | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.519 | 0.222 | 0.514 | 0.000338 | 0.000446 | 100 | PASS | 2.3 | 1.5 |
| gto | L5 | L4 + SRP, conical shadow | 7 | 6.24 | 2.66 | 6.19 | 0.000883 | 0.00537 | 100 | PASS | 4.9 | 4.1 |
| gto | L6 | L5 + NRLMSISE-00 drag | 7 | 2.33 | 0.972 | 2.33 | 0.00103 | 0.00207 | 100 | PASS | 7.8 | 9.3 |
| gto | L7 | L6 + relativity (full model) | 7 | 7.04 | 3.02 | 6.94 | 0.00107 | 0.00595 | 100 | PASS | 7.5 | 8.7 |
| heo_stress | L3 | gravity 8x8 | 7 | 0.299 | 0.14 | 0.299 | 0.000392 | 0.000225 | 100 | PASS | 1.0 | 0.8 |
| heo_stress | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.302 | 0.142 | 0.299 | 0.000393 | 0.000225 | 100 | PASS | 1.3 | 1.2 |
| heo_stress | L5 | L4 + SRP, conical shadow | 7 | 2.96 | 1.4 | 2.93 | 0.000932 | 0.0022 | 100 | PASS | 2.1 | 4.3 |
| heo_stress | L6 | L5 + NRLMSISE-00 drag | 7 | 5.26 | 2.48 | 5.21 | 0.00104 | 0.00392 | 100 | PASS | 2.7 | 11.6 |
| heo_stress | L7 | L6 + relativity (full model) | 7 | 4.49 | 2.12 | 4.44 | 0.000753 | 0.00334 | 100 | PASS | 3.5 | 12.3 |

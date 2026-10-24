# AstroFlyer vs Orekit cross-check

Reference data: orekit-data at C:\Users\Harshith\OneDrive\Desktop\major_project_py\astroflyer\validation\orekit-data. Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.
AstroFlyer propagator: rkf78 ({'method': 'RKF78'}).

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | Orekit (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L3 | gravity 8x8 | 7 | 0.264 | 0.113 | 0.26 | 0.000698 | 0.00021 | 100 | PASS | 3.0 | 1.4 |
| molniya | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.263 | 0.113 | 0.259 | 0.0007 | 0.000211 | 100 | PASS | 2.3 | 1.0 |
| molniya | L5 | L4 + SRP, conical shadow | 7 | 38.1 | 16.5 | 37.6 | 0.00462 | 0.0304 | 100 | PASS | 2.6 | 2.5 |
| molniya | L6 | L5 + NRLMSISE-00 drag | 7 | 34 | 14.7 | 33.6 | 0.00439 | 0.0272 | 100 | PASS | 10.9 | 11.7 |
| molniya | L7 | L6 + relativity (full model) | 7 | 34.6 | 15 | 34.2 | 0.00465 | 0.0277 | 100 | PASS | 3.2 | 11.8 |
| tundra | L3 | gravity 8x8 | 7 | 0.0174 | 0.00275 | 0.0174 | 2.64e-05 | 1.95e-06 | 100 | PASS | 1.1 | 1.1 |
| tundra | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.0175 | 0.00276 | 0.0175 | 2.98e-05 | 1.96e-06 | 100 | PASS | 1.5 | 1.5 |
| tundra | L5 | L4 + SRP, conical shadow | 7 | 21.2 | 5.08 | 21.2 | 0.0638 | 0.00215 | 100 | PASS | 1.7 | 4.1 |
| tundra | L6 | L5 + NRLMSISE-00 drag | 7 | 21.2 | 5.09 | 21.2 | 0.0639 | 0.00215 | 100 | PASS | 1.8 | 9.9 |
| tundra | L7 | L6 + relativity (full model) | 7 | 21.2 | 5.09 | 21.2 | 0.0639 | 0.00215 | 100 | PASS | 2.0 | 9.9 |
| gto | L3 | gravity 8x8 | 7 | 0.519 | 0.223 | 0.514 | 0.000339 | 0.000445 | 100 | PASS | 1.9 | 0.9 |
| gto | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.519 | 0.222 | 0.514 | 0.000338 | 0.000446 | 100 | PASS | 2.5 | 1.4 |
| gto | L5 | L4 + SRP, conical shadow | 7 | 8.3 | 3.54 | 8.22 | 0.000552 | 0.00715 | 100 | PASS | 2.9 | 4.2 |
| gto | L6 | L5 + NRLMSISE-00 drag | 7 | 1.21 | 0.507 | 1.21 | 0.000618 | 0.00107 | 100 | PASS | 3.5 | 10.6 |
| gto | L7 | L6 + relativity (full model) | 7 | 9.08 | 3.9 | 8.95 | 0.00056 | 0.00768 | 100 | PASS | 3.7 | 10.6 |
| heo_stress | L3 | gravity 8x8 | 7 | 0.299 | 0.14 | 0.299 | 0.000392 | 0.000225 | 100 | PASS | 1.1 | 0.9 |
| heo_stress | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.302 | 0.142 | 0.299 | 0.000393 | 0.000225 | 100 | PASS | 1.6 | 1.3 |
| heo_stress | L5 | L4 + SRP, conical shadow | 7 | 29.2 | 13.8 | 28.9 | 0.0177 | 0.0217 | 100 | PASS | 1.7 | 4.0 |
| heo_stress | L6 | L5 + NRLMSISE-00 drag | 7 | 27.8 | 13.1 | 27.5 | 0.0179 | 0.0207 | 100 | PASS | 2.0 | 9.8 |
| heo_stress | L7 | L6 + relativity (full model) | 7 | 28.4 | 13.4 | 28.1 | 0.0181 | 0.0211 | 100 | PASS | 2.1 | 9.7 |

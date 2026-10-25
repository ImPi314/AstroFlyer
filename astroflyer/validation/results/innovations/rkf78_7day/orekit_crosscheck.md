# AstroFlyer vs Orekit cross-check

Reference data: orekit-data at C:\Users\Harshith\OneDrive\Desktop\major_project_py\astroflyer\validation\orekit-data. Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.
AstroFlyer propagator: rkf78 ({'method': 'RKF78'}).

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | Orekit (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L3 | gravity 8x8 | 7 | 0.264 | 0.113 | 0.26 | 0.000698 | 0.00021 | 100 | PASS | 2.9 | 1.4 |
| molniya | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.263 | 0.113 | 0.259 | 0.0007 | 0.000211 | 100 | PASS | 1.9 | 1.3 |
| molniya | L5 | L4 + SRP, conical shadow | 7 | 0.695 | 0.304 | 0.685 | 0.00491 | 0.000559 | 100 | PASS | 2.8 | 3.2 |
| molniya | L6 | L5 + NRLMSISE-00 drag | 7 | 4.17 | 1.8 | 4.12 | 0.0051 | 0.00334 | 100 | PASS | 10.5 | 12.2 |
| molniya | L7 | L6 + relativity (full model) | 7 | 3.59 | 1.55 | 3.54 | 0.00477 | 0.00287 | 100 | PASS | 3.4 | 12.0 |
| tundra | L3 | gravity 8x8 | 7 | 0.0174 | 0.00275 | 0.0174 | 2.64e-05 | 1.95e-06 | 100 | PASS | 1.0 | 1.1 |
| tundra | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.0175 | 0.00276 | 0.0175 | 2.98e-05 | 1.96e-06 | 100 | PASS | 1.4 | 1.6 |
| tundra | L5 | L4 + SRP, conical shadow | 7 | 18.1 | 4.35 | 18.1 | 0.0516 | 0.00184 | 100 | PASS | 1.9 | 4.9 |
| tundra | L6 | L5 + NRLMSISE-00 drag | 7 | 18.2 | 4.35 | 18.1 | 0.0517 | 0.00184 | 100 | PASS | 2.2 | 11.4 |
| tundra | L7 | L6 + relativity (full model) | 7 | 18.2 | 4.36 | 18.2 | 0.0518 | 0.00184 | 100 | PASS | 2.3 | 11.2 |
| gto | L3 | gravity 8x8 | 7 | 0.519 | 0.223 | 0.514 | 0.000339 | 0.000445 | 100 | PASS | 1.7 | 1.1 |
| gto | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.519 | 0.222 | 0.514 | 0.000338 | 0.000446 | 100 | PASS | 2.4 | 1.6 |
| gto | L5 | L4 + SRP, conical shadow | 7 | 9.12 | 3.89 | 9.04 | 0.000544 | 0.00786 | 100 | PASS | 3.4 | 4.9 |
| gto | L6 | L5 + NRLMSISE-00 drag | 7 | 1.83 | 0.766 | 1.82 | 0.000605 | 0.00161 | 100 | PASS | 4.1 | 12.1 |
| gto | L7 | L6 + relativity (full model) | 7 | 9.9 | 4.25 | 9.76 | 0.000546 | 0.00838 | 100 | PASS | 4.1 | 12.3 |
| heo_stress | L3 | gravity 8x8 | 7 | 0.299 | 0.14 | 0.299 | 0.000392 | 0.000225 | 100 | PASS | 1.1 | 1.3 |
| heo_stress | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.302 | 0.142 | 0.299 | 0.000393 | 0.000225 | 100 | PASS | 1.5 | 1.8 |
| heo_stress | L5 | L4 + SRP, conical shadow | 7 | 27.2 | 12.8 | 26.9 | 0.0175 | 0.0202 | 100 | PASS | 2.1 | 4.9 |
| heo_stress | L6 | L5 + NRLMSISE-00 drag | 7 | 25.7 | 12.1 | 25.4 | 0.0176 | 0.0191 | 100 | PASS | 2.3 | 11.2 |
| heo_stress | L7 | L6 + relativity (full model) | 7 | 26.3 | 12.4 | 26 | 0.0179 | 0.0196 | 100 | PASS | 2.4 | 11.1 |

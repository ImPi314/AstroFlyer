# AstroFlyer vs Orekit cross-check

Reference data: orekit-data at C:\Users\Harshith\OneDrive\Desktop\major_project_py\astroflyer\validation\orekit-data. Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.
AstroFlyer propagator: rkf78_steered ({'method': 'RKF78', 'steering': 'covariance'}).

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | Orekit (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L3 | gravity 8x8 | 7 | 0.309 | 0.133 | 0.304 | 0.00069 | 0.000246 | 100 | PASS | 10.6 | 1.4 |
| molniya | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.31 | 0.133 | 0.306 | 0.000692 | 0.000248 | 100 | PASS | 12.0 | 1.4 |
| molniya | L5 | L4 + SRP, conical shadow | 7 | 30.3 | 13.1 | 29.9 | 0.00376 | 0.0242 | 100 | PASS | 12.8 | 4.1 |
| molniya | L6 | L5 + NRLMSISE-00 drag | 7 | 26.2 | 11.3 | 25.9 | 0.00351 | 0.021 | 100 | PASS | 22.2 | 12.3 |
| molniya | L7 | L6 + relativity (full model) | 7 | 26.8 | 11.6 | 26.5 | 0.00378 | 0.0214 | 100 | PASS | 15.1 | 11.9 |
| tundra | L3 | gravity 8x8 | 7 | 0.0141 | 0.00276 | 0.0141 | 2.64e-05 | 1.52e-06 | 100 | PASS | 3.1 | 1.0 |
| tundra | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.0141 | 0.00278 | 0.0141 | 2.96e-05 | 1.53e-06 | 100 | PASS | 4.2 | 1.6 |
| tundra | L5 | L4 + SRP, conical shadow | 7 | 5.76 | 1.34 | 5.76 | 0.0137 | 0.000582 | 100 | PASS | 4.4 | 4.9 |
| tundra | L6 | L5 + NRLMSISE-00 drag | 7 | 5.74 | 1.33 | 5.73 | 0.0136 | 0.00058 | 100 | PASS | 4.6 | 11.2 |
| tundra | L7 | L6 + relativity (full model) | 7 | 5.71 | 1.32 | 5.71 | 0.0135 | 0.000577 | 100 | PASS | 4.9 | 11.1 |
| gto | L3 | gravity 8x8 | 7 | 0.165 | 0.0704 | 0.164 | 0.000335 | 0.000142 | 100 | PASS | 9.3 | 1.1 |
| gto | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.162 | 0.0689 | 0.161 | 0.000335 | 0.00014 | 100 | PASS | 11.9 | 1.5 |
| gto | L5 | L4 + SRP, conical shadow | 7 | 24.1 | 10.3 | 23.9 | 0.000813 | 0.0207 | 100 | PASS | 13.2 | 4.5 |
| gto | L6 | L5 + NRLMSISE-00 drag | 7 | 26.8 | 11.5 | 26.5 | 0.00102 | 0.0227 | 100 | PASS | 14.7 | 11.3 |
| gto | L7 | L6 + relativity (full model) | 7 | 18.6 | 7.96 | 18.3 | 0.000977 | 0.0157 | 100 | PASS | 15.1 | 10.5 |
| heo_stress | L3 | gravity 8x8 | 7 | 0.201 | 0.0939 | 0.2 | 0.000389 | 0.000151 | 100 | PASS | 4.8 | 0.9 |
| heo_stress | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.228 | 0.108 | 0.226 | 0.00039 | 0.00017 | 100 | PASS | 6.3 | 1.4 |
| heo_stress | L5 | L4 + SRP, conical shadow | 7 | 2.87 | 1.36 | 2.85 | 0.00186 | 0.00214 | 100 | PASS | 6.8 | 4.1 |
| heo_stress | L6 | L5 + NRLMSISE-00 drag | 7 | 5.14 | 2.43 | 5.09 | 0.00193 | 0.00383 | 100 | PASS | 7.1 | 8.5 |
| heo_stress | L7 | L6 + relativity (full model) | 7 | 4.37 | 2.06 | 4.33 | 0.00162 | 0.00325 | 100 | PASS | 7.6 | 8.5 |

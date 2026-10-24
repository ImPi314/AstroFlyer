# AstroFlyer vs Orekit cross-check

Reference data: orekit-data at C:\Users\Harshith\OneDrive\Desktop\major_project_py\astroflyer\validation\orekit-data. Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.
AstroFlyer propagator: rkf78_steered ({'method': 'RKF78', 'steering': 'covariance'}).

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | Orekit (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L3 | gravity 8x8 | 7 | 0.309 | 0.133 | 0.304 | 0.00069 | 0.000246 | 100 | PASS | 9.7 | 1.2 |
| molniya | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.31 | 0.133 | 0.306 | 0.000692 | 0.000248 | 100 | PASS | 10.9 | 1.2 |
| molniya | L5 | L4 + SRP, conical shadow | 7 | 3.94 | 1.7 | 3.89 | 0.00274 | 0.00315 | 100 | PASS | 14.2 | 3.1 |
| molniya | L6 | L5 + NRLMSISE-00 drag | 7 | 7.99 | 3.45 | 7.89 | 0.00296 | 0.00639 | 100 | PASS | 23.2 | 10.9 |
| molniya | L7 | L6 + relativity (full model) | 7 | 7.41 | 3.2 | 7.31 | 0.00269 | 0.00592 | 100 | PASS | 16.1 | 11.1 |
| tundra | L3 | gravity 8x8 | 7 | 0.0141 | 0.00276 | 0.0141 | 2.64e-05 | 1.52e-06 | 100 | PASS | 3.0 | 1.0 |
| tundra | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.0141 | 0.00278 | 0.0141 | 2.96e-05 | 1.53e-06 | 100 | PASS | 3.8 | 1.4 |
| tundra | L5 | L4 + SRP, conical shadow | 7 | 9.03 | 2.08 | 9.03 | 0.0163 | 0.00092 | 100 | PASS | 5.0 | 3.9 |
| tundra | L6 | L5 + NRLMSISE-00 drag | 7 | 9.01 | 2.08 | 9.01 | 0.0162 | 0.000918 | 100 | PASS | 5.2 | 9.4 |
| tundra | L7 | L6 + relativity (full model) | 7 | 8.99 | 2.07 | 8.98 | 0.0162 | 0.000915 | 100 | PASS | 5.5 | 9.6 |
| gto | L3 | gravity 8x8 | 7 | 0.165 | 0.0704 | 0.164 | 0.000335 | 0.000142 | 100 | PASS | 9.2 | 0.9 |
| gto | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.162 | 0.0689 | 0.161 | 0.000335 | 0.00014 | 100 | PASS | 11.6 | 1.4 |
| gto | L5 | L4 + SRP, conical shadow | 7 | 22.8 | 9.72 | 22.6 | 0.000814 | 0.0196 | 100 | PASS | 15.0 | 4.0 |
| gto | L6 | L5 + NRLMSISE-00 drag | 7 | 25.7 | 11 | 25.3 | 0.00102 | 0.0217 | 100 | PASS | 21.9 | 10.5 |
| gto | L7 | L6 + relativity (full model) | 7 | 17.4 | 7.48 | 17.2 | 0.000975 | 0.0147 | 100 | PASS | 17.3 | 10.1 |
| heo_stress | L3 | gravity 8x8 | 7 | 0.201 | 0.0939 | 0.2 | 0.000389 | 0.000151 | 100 | PASS | 4.7 | 0.9 |
| heo_stress | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.228 | 0.108 | 0.226 | 0.00039 | 0.00017 | 100 | PASS | 6.1 | 1.5 |
| heo_stress | L5 | L4 + SRP, conical shadow | 7 | 4.54 | 2.14 | 4.49 | 0.0021 | 0.00338 | 100 | PASS | 7.8 | 4.2 |
| heo_stress | L6 | L5 + NRLMSISE-00 drag | 7 | 6.79 | 3.21 | 6.72 | 0.00216 | 0.00506 | 100 | PASS | 8.3 | 10.4 |
| heo_stress | L7 | L6 + relativity (full model) | 7 | 6.02 | 2.85 | 5.96 | 0.00185 | 0.00449 | 100 | PASS | 8.6 | 10.1 |

# AstroFlyer vs Orekit cross-check

Reference data: orekit-data at C:\Users\Harshith\OneDrive\Desktop\major_project_py\astroflyer\validation\orekit-data. Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.
AstroFlyer propagator: rkf78_steered ({'method': 'RKF78', 'steering': 'covariance'}).

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | Orekit (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L3 | gravity 8x8 | 7 | 0.309 | 0.133 | 0.304 | 0.00069 | 0.000246 | 100 | PASS | 9.3 | 1.5 |
| molniya | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.31 | 0.133 | 0.306 | 0.000692 | 0.000248 | 100 | PASS | 10.3 | 1.1 |
| molniya | L5 | L4 + SRP, conical shadow | 7 | 2.65 | 1.15 | 2.62 | 0.00201 | 0.00212 | 100 | PASS | 15.1 | 4.6 |
| molniya | L6 | L5 + NRLMSISE-00 drag | 7 | 6.68 | 2.89 | 6.59 | 0.0022 | 0.00534 | 100 | PASS | 24.6 | 11.0 |
| molniya | L7 | L6 + relativity (full model) | 7 | 6.09 | 2.63 | 6.01 | 0.00194 | 0.00487 | 100 | PASS | 17.6 | 12.8 |
| tundra | L3 | gravity 8x8 | 7 | 0.0141 | 0.00276 | 0.0141 | 2.64e-05 | 1.52e-06 | 100 | PASS | 2.8 | 1.3 |
| tundra | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.0141 | 0.00278 | 0.0141 | 2.96e-05 | 1.53e-06 | 100 | PASS | 3.5 | 1.6 |
| tundra | L5 | L4 + SRP, conical shadow | 7 | 0.0387 | 0.00839 | 0.0387 | 4.93e-05 | 4.01e-06 | 100 | PASS | 5.8 | 4.7 |
| tundra | L6 | L5 + NRLMSISE-00 drag | 7 | 0.015 | 0.00287 | 0.015 | 6.5e-05 | 1.63e-06 | 100 | PASS | 5.9 | 11.8 |
| tundra | L7 | L6 + relativity (full model) | 7 | 0.0108 | 0.00326 | 0.0108 | 0.000122 | 1.01e-06 | 100 | PASS | 6.7 | 10.7 |
| gto | L3 | gravity 8x8 | 7 | 0.165 | 0.0704 | 0.164 | 0.000335 | 0.000142 | 100 | PASS | 8.0 | 0.9 |
| gto | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.162 | 0.0689 | 0.161 | 0.000335 | 0.00014 | 100 | PASS | 10.5 | 1.5 |
| gto | L5 | L4 + SRP, conical shadow | 7 | 6.95 | 2.97 | 6.89 | 0.000865 | 0.00598 | 100 | PASS | 15.2 | 4.0 |
| gto | L6 | L5 + NRLMSISE-00 drag | 7 | 1.99 | 0.833 | 1.99 | 0.000995 | 0.00177 | 100 | PASS | 19.5 | 11.3 |
| gto | L7 | L6 + relativity (full model) | 7 | 7.78 | 3.34 | 7.67 | 0.00104 | 0.00658 | 100 | PASS | 21.6 | 12.2 |
| heo_stress | L3 | gravity 8x8 | 7 | 0.201 | 0.0939 | 0.2 | 0.000389 | 0.000151 | 100 | PASS | 4.3 | 1.1 |
| heo_stress | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.228 | 0.108 | 0.226 | 0.00039 | 0.00017 | 100 | PASS | 5.8 | 1.6 |
| heo_stress | L5 | L4 + SRP, conical shadow | 7 | 2.92 | 1.38 | 2.89 | 0.000935 | 0.00217 | 100 | PASS | 7.7 | 5.8 |
| heo_stress | L6 | L5 + NRLMSISE-00 drag | 7 | 5.18 | 2.45 | 5.13 | 0.00104 | 0.00386 | 100 | PASS | 11.2 | 11.9 |
| heo_stress | L7 | L6 + relativity (full model) | 7 | 4.41 | 2.08 | 4.36 | 0.000755 | 0.00328 | 100 | PASS | 9.8 | 11.4 |

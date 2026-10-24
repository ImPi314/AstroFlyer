# AstroFlyer vs Orekit cross-check

Reference data: orekit-data at C:\Users\Harshith\OneDrive\Desktop\major_project_py\astroflyer\validation\orekit-data. Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.
AstroFlyer propagator: ecr_mf ({'method': 'DOP853', 'fidelity': 'ecr_mf'}).

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | Orekit (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L3 | gravity 8x8 | 7 | 0.74 | 0.319 | 0.729 | 0.000615 | 0.000588 | 100 | PASS | 2.5 | 1.5 |
| molniya | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.79 | 0.341 | 0.779 | 0.00062 | 0.000632 | 100 | PASS | 1.4 | 1.5 |
| molniya | L5 | L4 + SRP, conical shadow | 7 | 31.7 | 13.7 | 31.3 | 0.00442 | 0.0254 | 100 | PASS | 2.3 | 4.1 |
| molniya | L6 | L5 + NRLMSISE-00 drag | 7 | 27.7 | 12 | 27.4 | 0.00418 | 0.0222 | 100 | PASS | 11.5 | 12.9 |
| molniya | L7 | L6 + relativity (full model) | 7 | 28.3 | 12.3 | 28 | 0.00445 | 0.0226 | 100 | PASS | 3.4 | 12.9 |
| tundra | L3 | gravity 8x8 | 7 | 0.00253 | 0.000789 | 0.00253 | 2.64e-05 | 1.23e-07 | 100 | PASS | 0.5 | 1.2 |
| tundra | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.00267 | 0.000796 | 0.00267 | 2.9e-05 | 1.34e-07 | 100 | PASS | 0.7 | 1.8 |
| tundra | L5 | L4 + SRP, conical shadow | 7 | 2.29 | 0.531 | 2.29 | 0.00431 | 0.000235 | 100 | PASS | 1.1 | 4.5 |
| tundra | L6 | L5 + NRLMSISE-00 drag | 7 | 2.32 | 0.537 | 2.32 | 0.0044 | 0.000237 | 100 | PASS | 1.3 | 9.7 |
| tundra | L7 | L6 + relativity (full model) | 7 | 2.34 | 0.542 | 2.34 | 0.00445 | 0.00024 | 100 | PASS | 1.4 | 9.7 |
| gto | L3 | gravity 8x8 | 7 | 1.77 | 0.755 | 1.75 | 0.000348 | 0.00152 | 100 | PASS | 1.3 | 1.0 |
| gto | L4 | 8x8 + Sun/Moon (DE440) | 7 | 1.72 | 0.73 | 1.7 | 0.000351 | 0.00148 | 100 | PASS | 1.6 | 1.4 |
| gto | L5 | L4 + SRP, conical shadow | 7 | 4.94 | 2.11 | 4.89 | 0.000733 | 0.00424 | 100 | PASS | 2.4 | 4.2 |
| gto | L6 | L5 + NRLMSISE-00 drag | 7 | 3.11 | 1.3 | 3.11 | 0.000756 | 0.00277 | 100 | PASS | 5.4 | 10.2 |
| gto | L7 | L6 + relativity (full model) | 7 | 5.59 | 2.41 | 5.51 | 0.000832 | 0.00473 | 100 | PASS | 5.7 | 10.1 |
| heo_stress | L3 | gravity 8x8 | 7 | 0.0526 | 0.0247 | 0.0518 | 0.000376 | 3.79e-05 | 100 | PASS | 0.6 | 0.8 |
| heo_stress | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.0562 | 0.027 | 0.0555 | 0.000379 | 4.15e-05 | 100 | PASS | 0.7 | 1.3 |
| heo_stress | L5 | L4 + SRP, conical shadow | 7 | 1.21 | 0.573 | 1.2 | 0.000711 | 0.000891 | 100 | PASS | 1.0 | 3.8 |
| heo_stress | L6 | L5 + NRLMSISE-00 drag | 7 | 3.64 | 1.72 | 3.61 | 0.000826 | 0.00271 | 100 | PASS | 1.4 | 9.5 |
| heo_stress | L7 | L6 + relativity (full model) | 7 | 2.87 | 1.36 | 2.84 | 0.000561 | 0.00214 | 100 | PASS | 1.5 | 9.7 |

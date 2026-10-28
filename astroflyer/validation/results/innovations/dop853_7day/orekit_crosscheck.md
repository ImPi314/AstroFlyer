# AstroFlyer vs Orekit cross-check

Reference data: orekit-data at astroflyer/validation/orekit-data. Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.
AstroFlyer propagator: dop853 ({'method': 'DOP853'}).

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | Orekit (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L3 | gravity 8x8 | 7 | 0.74 | 0.319 | 0.729 | 0.000615 | 0.000588 | 100 | PASS | 2.2 | 1.4 |
| molniya | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.79 | 0.341 | 0.779 | 0.00062 | 0.000632 | 100 | PASS | 1.2 | 1.3 |
| molniya | L5 | L4 + SRP, conical shadow | 7 | 1.71 | 0.758 | 1.69 | 0.00199 | 0.00136 | 100 | PASS | 2.5 | 2.3 |
| molniya | L6 | L5 + NRLMSISE-00 drag | 7 | 5.74 | 2.48 | 5.67 | 0.00219 | 0.00459 | 100 | PASS | 10.8 | 10.1 |
| molniya | L7 | L6 + relativity (full model) | 7 | 5.15 | 2.23 | 5.09 | 0.00193 | 0.00412 | 100 | PASS | 3.5 | 9.7 |
| tundra | L3 | gravity 8x8 | 7 | 0.00253 | 0.000789 | 0.00253 | 2.64e-05 | 1.23e-07 | 100 | PASS | 0.4 | 0.9 |
| tundra | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.00267 | 0.000796 | 0.00267 | 2.9e-05 | 1.34e-07 | 100 | PASS | 0.5 | 1.3 |
| tundra | L5 | L4 + SRP, conical shadow | 7 | 0.0285 | 0.00728 | 0.0285 | 4.91e-05 | 2.84e-06 | 100 | PASS | 1.1 | 3.7 |
| tundra | L6 | L5 + NRLMSISE-00 drag | 7 | 0.00525 | 0.00176 | 0.00525 | 6.62e-05 | 4.88e-07 | 100 | PASS | 1.4 | 8.4 |
| tundra | L7 | L6 + relativity (full model) | 7 | 0.0205 | 0.00508 | 0.0205 | 0.000124 | 2.14e-06 | 100 | PASS | 1.4 | 8.6 |
| gto | L3 | gravity 8x8 | 7 | 1.77 | 0.755 | 1.75 | 0.000348 | 0.00152 | 100 | PASS | 1.0 | 0.9 |
| gto | L4 | 8x8 + Sun/Moon (DE440) | 7 | 1.72 | 0.73 | 1.7 | 0.000351 | 0.00148 | 100 | PASS | 1.4 | 1.2 |
| gto | L5 | L4 + SRP, conical shadow | 7 | 5.47 | 2.33 | 5.42 | 0.000702 | 0.00471 | 100 | PASS | 2.7 | 3.5 |
| gto | L6 | L5 + NRLMSISE-00 drag | 7 | 2.85 | 1.19 | 2.85 | 0.000696 | 0.00254 | 100 | PASS | 5.7 | 9.0 |
| gto | L7 | L6 + relativity (full model) | 7 | 6.12 | 2.63 | 6.03 | 0.00078 | 0.00517 | 100 | PASS | 6.0 | 9.0 |
| heo_stress | L3 | gravity 8x8 | 7 | 0.0526 | 0.0247 | 0.0518 | 0.000376 | 3.79e-05 | 100 | PASS | 0.5 | 0.7 |
| heo_stress | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.0562 | 0.027 | 0.0555 | 0.000379 | 4.15e-05 | 100 | PASS | 0.6 | 1.2 |
| heo_stress | L5 | L4 + SRP, conical shadow | 7 | 2.8 | 1.32 | 2.77 | 0.000948 | 0.00209 | 100 | PASS | 1.2 | 3.3 |
| heo_stress | L6 | L5 + NRLMSISE-00 drag | 7 | 5.3 | 2.5 | 5.24 | 0.00106 | 0.00394 | 100 | PASS | 1.6 | 7.7 |
| heo_stress | L7 | L6 + relativity (full model) | 7 | 4.51 | 2.13 | 4.46 | 0.000766 | 0.00336 | 100 | PASS | 1.6 | 7.7 |

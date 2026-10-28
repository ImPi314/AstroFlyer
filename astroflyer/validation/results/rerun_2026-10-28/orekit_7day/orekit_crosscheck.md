# AstroFlyer vs Orekit cross-check

Reference data: orekit-data at astroflyer/validation/orekit-data. Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.
AstroFlyer propagator: dop853 ({'method': 'DOP853'}).

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | Orekit (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L0 | two-body | 7 | 1.1 | 0.474 | 1.09 | 1.11e-07 | 0.000884 | 100 | PASS | 1.7 | 0.5 |
| molniya | L1 | J2 only | 7 | 0.746 | 0.321 | 0.736 | 0.00062 | 0.000596 | 100 | PASS | 1.4 | 1.1 |
| molniya | L2 | zonal 4x0 | 7 | 0.684 | 0.295 | 0.676 | 0.000621 | 0.000546 | 100 | PASS | 1.3 | 1.8 |
| molniya | L3 | gravity 8x8 | 7 | 0.74 | 0.319 | 0.729 | 0.000615 | 0.000588 | 100 | PASS | 69.9 | 1.4 |
| molniya | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.79 | 0.341 | 0.779 | 0.00062 | 0.000632 | 100 | PASS | 1.5 | 1.1 |
| molniya | L5 | L4 + SRP, conical shadow | 7 | 1.71 | 0.758 | 1.69 | 0.00199 | 0.00136 | 100 | PASS | 2.7 | 4.1 |
| molniya | L6 | L5 + NRLMSISE-00 drag | 7 | 5.74 | 2.48 | 5.67 | 0.00219 | 0.00459 | 100 | PASS | 11.5 | 14.0 |
| molniya | L7 | L6 + relativity (full model) | 7 | 5.15 | 2.23 | 5.09 | 0.00193 | 0.00412 | 100 | PASS | 5.2 | 13.3 |
| tundra | L0 | two-body | 7 | 0.00364 | 0.000709 | 0.00363 | 8.39e-08 | 3e-07 | 100 | PASS | 0.4 | 0.2 |
| tundra | L1 | J2 only | 7 | 0.00274 | 0.000793 | 0.00274 | 2.64e-05 | 1.51e-07 | 100 | PASS | 0.4 | 1.1 |
| tundra | L2 | zonal 4x0 | 7 | 0.00275 | 0.000777 | 0.00275 | 2.64e-05 | 1.39e-07 | 100 | PASS | 0.4 | 1.3 |
| tundra | L3 | gravity 8x8 | 7 | 0.00253 | 0.000789 | 0.00253 | 2.64e-05 | 1.23e-07 | 100 | PASS | 0.5 | 1.3 |
| tundra | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.00267 | 0.000796 | 0.00267 | 2.9e-05 | 1.34e-07 | 100 | PASS | 0.6 | 1.7 |
| tundra | L5 | L4 + SRP, conical shadow | 7 | 0.0285 | 0.00728 | 0.0285 | 4.91e-05 | 2.84e-06 | 100 | PASS | 1.5 | 4.8 |
| tundra | L6 | L5 + NRLMSISE-00 drag | 7 | 0.00525 | 0.00176 | 0.00525 | 6.62e-05 | 4.88e-07 | 100 | PASS | 1.7 | 11.1 |
| tundra | L7 | L6 + relativity (full model) | 7 | 0.0205 | 0.00508 | 0.0205 | 0.000124 | 2.14e-06 | 100 | PASS | 1.6 | 11.5 |
| gto | L0 | two-body | 7 | 1.67 | 0.789 | 1.67 | 1.21e-07 | 0.00149 | 100 | PASS | 1.1 | 0.1 |
| gto | L1 | J2 only | 7 | 1.75 | 0.747 | 1.74 | 0.000357 | 0.00151 | 100 | PASS | 1.1 | 1.0 |
| gto | L2 | zonal 4x0 | 7 | 1.77 | 0.754 | 1.76 | 0.000356 | 0.00153 | 100 | PASS | 1.3 | 1.1 |
| gto | L3 | gravity 8x8 | 7 | 1.77 | 0.755 | 1.75 | 0.000348 | 0.00152 | 100 | PASS | 1.3 | 1.2 |
| gto | L4 | 8x8 + Sun/Moon (DE440) | 7 | 1.72 | 0.73 | 1.7 | 0.000351 | 0.00148 | 100 | PASS | 1.6 | 1.4 |
| gto | L5 | L4 + SRP, conical shadow | 7 | 5.47 | 2.33 | 5.42 | 0.000702 | 0.00471 | 100 | PASS | 3.5 | 4.5 |
| gto | L6 | L5 + NRLMSISE-00 drag | 7 | 2.85 | 1.19 | 2.85 | 0.000696 | 0.00254 | 100 | PASS | 6.8 | 10.1 |
| gto | L7 | L6 + relativity (full model) | 7 | 6.12 | 2.63 | 6.03 | 0.00078 | 0.00517 | 100 | PASS | 6.2 | 9.2 |
| heo_stress | L0 | two-body | 7 | 0.0982 | 0.0457 | 0.0981 | 1.18e-07 | 7.42e-05 | 100 | PASS | 0.5 | 0.1 |
| heo_stress | L1 | J2 only | 7 | 0.0649 | 0.0307 | 0.0647 | 0.000376 | 4.83e-05 | 100 | PASS | 0.5 | 0.7 |
| heo_stress | L2 | zonal 4x0 | 7 | 0.0713 | 0.0335 | 0.0703 | 0.000376 | 5.17e-05 | 100 | PASS | 0.5 | 0.8 |
| heo_stress | L3 | gravity 8x8 | 7 | 0.0526 | 0.0247 | 0.0518 | 0.000376 | 3.79e-05 | 100 | PASS | 0.5 | 0.8 |
| heo_stress | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.0562 | 0.027 | 0.0555 | 0.000379 | 4.15e-05 | 100 | PASS | 0.7 | 1.2 |
| heo_stress | L5 | L4 + SRP, conical shadow | 7 | 2.8 | 1.32 | 2.77 | 0.000948 | 0.00209 | 100 | PASS | 1.3 | 4.3 |
| heo_stress | L6 | L5 + NRLMSISE-00 drag | 7 | 5.3 | 2.5 | 5.24 | 0.00106 | 0.00394 | 100 | PASS | 1.8 | 9.4 |
| heo_stress | L7 | L6 + relativity (full model) | 7 | 4.51 | 2.13 | 4.46 | 0.000766 | 0.00336 | 100 | PASS | 2.1 | 9.7 |

# AstroFlyer vs Basilisk cross-check

Reference data: Basilisk 2.11.1, RKF78 at relTol 1e-12; AstroFlyer's EGM2008 and GM values; DE424 Sun/Moon and ITRF93 orientation from GMAT's SPICE kernels; L7 omitted (no relativity). Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.
AstroFlyer propagator: dop853 ({'method': 'DOP853'}).

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | Basilisk (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L3 | gravity 8x8 | 7 | 3.23 | 1.4 | 3.19 | 0.0268 | 0.00257 | 100 | PASS | 2.2 | 13.0 |
| molniya | L4 | 8x8 + Sun/Moon (DE440) | 7 | 3.29 | 1.42 | 3.24 | 0.0267 | 0.00263 | 100 | PASS | 1.3 | 13.1 |
| molniya | L5 | L4 + SRP, conical shadow | 7 | 28.5 | 12.3 | 28.1 | 0.0275 | 0.0227 | 100 | PASS | 2.8 | 119.9 |
| molniya | L6 | L5 + NRLMSISE-00 drag | 7 | 1.62e+03 | 702 | 1.6e+03 | 0.0495 | 1.3 | 100 | FAIL | 11.4 | 131.3 |
| tundra | L3 | gravity 8x8 | 7 | 0.0378 | 0.00851 | 0.0377 | 0.00322 | 3.92e-06 | 100 | PASS | 0.5 | 14.0 |
| tundra | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.0377 | 0.00847 | 0.0376 | 0.00299 | 3.92e-06 | 100 | PASS | 0.6 | 13.6 |
| tundra | L5 | L4 + SRP, conical shadow | 7 | 2.16 | 0.501 | 2.16 | 0.00363 | 0.000221 | 100 | PASS | 1.3 | 125.3 |
| tundra | L6 | L5 + NRLMSISE-00 drag | 7 | 2.17 | 0.504 | 2.17 | 0.00356 | 0.000222 | 100 | PASS | 1.6 | 127.9 |
| gto | L3 | gravity 8x8 | 7 | 4.14 | 1.78 | 4.09 | 0.0716 | 0.00354 | 100 | PASS | 1.1 | 14.6 |
| gto | L4 | 8x8 + Sun/Moon (DE440) | 7 | 4.09 | 1.75 | 4.05 | 0.0714 | 0.00351 | 100 | PASS | 1.5 | 13.6 |
| gto | L5 | L4 + SRP, conical shadow | 7 | 3.58 | 1.54 | 3.55 | 0.071 | 0.00307 | 100 | PASS | 3.1 | 119.3 |
| gto | L6 | L5 + NRLMSISE-00 drag | 7 | 1.68e+04 | 7.21e+03 | 1.66e+04 | 0.526 | 14.2 | 100 | FAIL | 6.2 | 121.7 |
| heo_stress | L3 | gravity 8x8 | 7 | 8.55 | 4 | 8.54 | 0.0396 | 0.00642 | 100 | PASS | 0.6 | 13.8 |
| heo_stress | L4 | 8x8 + Sun/Moon (DE440) | 7 | 8.56 | 4.04 | 8.47 | 0.0395 | 0.00637 | 100 | PASS | 0.7 | 13.6 |
| heo_stress | L5 | L4 + SRP, conical shadow | 7 | 6.01 | 2.84 | 5.95 | 0.0389 | 0.00448 | 100 | PASS | 1.3 | 133.2 |
| heo_stress | L6 | L5 + NRLMSISE-00 drag | 7 | 10.1 | 4.79 | 10 | 0.0388 | 0.00755 | 100 | PASS | 1.7 | 124.4 |

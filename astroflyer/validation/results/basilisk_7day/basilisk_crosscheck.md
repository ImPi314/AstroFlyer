# AstroFlyer vs Basilisk cross-check

Reference data: Basilisk 2.11.1, RKF78 at relTol 1e-12; AstroFlyer's EGM2008 and GM values; DE424 Sun/Moon and ITRF93 orientation from GMAT's SPICE kernels; L7 omitted (no relativity). Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.
AstroFlyer propagator: dop853 ({'method': 'DOP853'}).

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | Basilisk (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L3 | gravity 8x8 | 7 | 3.23 | 1.4 | 3.19 | 0.0268 | 0.00257 | 100 | PASS | 2.1 | 13.1 |
| molniya | L4 | 8x8 + Sun/Moon (DE440) | 7 | 3.29 | 1.42 | 3.24 | 0.0267 | 0.00263 | 100 | PASS | 1.2 | 13.0 |
| molniya | L5 | L4 + SRP, conical shadow | 7 | 30.3 | 13.1 | 29.9 | 0.0276 | 0.0242 | 100 | PASS | 2.4 | 113.8 |
| molniya | L6 | L5 + NRLMSISE-00 drag | 7 | 1.62e+03 | 701 | 1.6e+03 | 0.0495 | 1.3 | 100 | FAIL | 10.4 | 128.0 |
| tundra | L3 | gravity 8x8 | 7 | 0.0378 | 0.00851 | 0.0377 | 0.00322 | 3.92e-06 | 100 | PASS | 0.5 | 13.1 |
| tundra | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.0377 | 0.00847 | 0.0376 | 0.00299 | 3.92e-06 | 100 | PASS | 0.5 | 12.8 |
| tundra | L5 | L4 + SRP, conical shadow | 7 | 2.28 | 0.53 | 2.28 | 0.00366 | 0.000234 | 100 | PASS | 1.2 | 119.0 |
| tundra | L6 | L5 + NRLMSISE-00 drag | 7 | 2.29 | 0.532 | 2.29 | 0.00358 | 0.000235 | 100 | PASS | 1.3 | 117.2 |
| gto | L3 | gravity 8x8 | 7 | 4.14 | 1.78 | 4.09 | 0.0716 | 0.00354 | 100 | PASS | 1.0 | 13.2 |
| gto | L4 | 8x8 + Sun/Moon (DE440) | 7 | 4.09 | 1.75 | 4.05 | 0.0714 | 0.00351 | 100 | PASS | 1.3 | 12.9 |
| gto | L5 | L4 + SRP, conical shadow | 7 | 0.231 | 0.0929 | 0.23 | 0.0714 | 0.000212 | 100 | PASS | 2.7 | 114.5 |
| gto | L6 | L5 + NRLMSISE-00 drag | 7 | 1.66e+04 | 7.13e+03 | 1.64e+04 | 0.517 | 14 | 100 | FAIL | 5.9 | 122.0 |
| heo_stress | L3 | gravity 8x8 | 7 | 8.55 | 4 | 8.54 | 0.0396 | 0.00642 | 100 | PASS | 0.5 | 13.0 |
| heo_stress | L4 | 8x8 + Sun/Moon (DE440) | 7 | 8.56 | 4.04 | 8.47 | 0.0395 | 0.00637 | 100 | PASS | 0.6 | 12.8 |
| heo_stress | L5 | L4 + SRP, conical shadow | 7 | 7.61 | 3.59 | 7.53 | 0.0392 | 0.00567 | 100 | PASS | 1.1 | 115.6 |
| heo_stress | L6 | L5 + NRLMSISE-00 drag | 7 | 11.6 | 5.47 | 11.5 | 0.0392 | 0.00862 | 100 | PASS | 1.5 | 118.2 |

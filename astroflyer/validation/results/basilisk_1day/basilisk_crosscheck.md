# AstroFlyer vs Basilisk cross-check

Reference data: Basilisk 2.11.1, RKF78 at relTol 1e-12; AstroFlyer's EGM2008 and GM values; DE424 Sun/Moon and ITRF93 orientation from GMAT's SPICE kernels; L7 omitted (no relativity). Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.
AstroFlyer propagator: dop853 ({'method': 'DOP853'}).

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | Basilisk (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L0 | two-body | 1 | 0.0189 | 0.00794 | 0.0189 | 8.31e-08 | 1.6e-05 | 10 | PASS | 0.9 | 3.3 |
| molniya | L1 | J2 only | 1 | 0.372 | 0.171 | 0.352 | 0.00332 | 0.000256 | 10 | PASS | 0.6 | 3.4 |
| molniya | L2 | zonal 4x0 | 1 | 0.361 | 0.166 | 0.341 | 0.00333 | 0.000249 | 10 | PASS | 0.1 | 3.4 |
| molniya | L3 | gravity 8x8 | 1 | 0.363 | 0.167 | 0.343 | 0.00336 | 0.00025 | 10 | PASS | 0.1 | 3.5 |
| molniya | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.363 | 0.167 | 0.344 | 0.00337 | 0.000251 | 10 | PASS | 0.2 | 3.6 |
| molniya | L5 | L4 + SRP, conical shadow | 1 | 0.661 | 0.305 | 0.626 | 0.00327 | 0.000454 | 10 | PASS | 0.4 | 18.5 |
| molniya | L6 | L5 + NRLMSISE-00 drag | 1 | 33.2 | 15.3 | 31.4 | 0.00327 | 0.0228 | 10 | FAIL | 7.9 | 17.8 |
| tundra | L0 | two-body | 1 | 0.000817 | 0.000406 | 0.000817 | 9.03e-08 | 7.69e-08 | 10 | PASS | 0.1 | 3.3 |
| tundra | L1 | J2 only | 1 | 0.00247 | 0.00102 | 0.00238 | 0.000261 | 2.39e-07 | 10 | PASS | 0.1 | 3.3 |
| tundra | L2 | zonal 4x0 | 1 | 0.00256 | 0.00107 | 0.00237 | 0.000261 | 2.4e-07 | 10 | PASS | 0.1 | 3.5 |
| tundra | L3 | gravity 8x8 | 1 | 0.00243 | 0.00092 | 0.00234 | 0.00026 | 2.34e-07 | 10 | PASS | 0.1 | 3.4 |
| tundra | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.0021 | 0.000905 | 0.002 | 0.000267 | 2.06e-07 | 10 | PASS | 0.1 | 3.4 |
| tundra | L5 | L4 + SRP, conical shadow | 1 | 0.112 | 0.0319 | 0.111 | 0.000388 | 1.09e-05 | 10 | PASS | 0.2 | 18.4 |
| tundra | L6 | L5 + NRLMSISE-00 drag | 1 | 0.112 | 0.0319 | 0.112 | 0.000391 | 1.09e-05 | 10 | PASS | 0.2 | 18.6 |
| gto | L0 | two-body | 1 | 0.0177 | 0.00743 | 0.0174 | 2.29e-07 | 1.53e-05 | 10 | PASS | 0.1 | 3.3 |
| gto | L1 | J2 only | 1 | 0.0932 | 0.0391 | 0.093 | 0.0114 | 8.39e-05 | 10 | PASS | 0.2 | 3.3 |
| gto | L2 | zonal 4x0 | 1 | 0.0916 | 0.0384 | 0.0914 | 0.0114 | 8.25e-05 | 10 | PASS | 0.2 | 3.3 |
| gto | L3 | gravity 8x8 | 1 | 0.32 | 0.135 | 0.319 | 0.0115 | 0.000282 | 10 | PASS | 0.2 | 3.5 |
| gto | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.32 | 0.135 | 0.319 | 0.0115 | 0.000282 | 10 | PASS | 0.2 | 3.4 |
| gto | L5 | L4 + SRP, conical shadow | 1 | 0.0549 | 0.0228 | 0.0548 | 0.0114 | 5.01e-05 | 10 | PASS | 0.5 | 17.8 |
| gto | L6 | L5 + NRLMSISE-00 drag | 1 | 336 | 142 | 335 | 0.0428 | 0.297 | 10 | FAIL | 0.9 | 18.4 |
| heo_stress | L0 | two-body | 1 | 0.00268 | 0.00168 | 0.00208 | 8.38e-08 | 7.57e-08 | 10 | PASS | 0.1 | 3.3 |
| heo_stress | L1 | J2 only | 1 | 0.127 | 0.111 | 0.0616 | 0.00853 | 3.05e-06 | 10 | PASS | 0.1 | 3.3 |
| heo_stress | L2 | zonal 4x0 | 1 | 0.124 | 0.109 | 0.0597 | 0.00853 | 2.99e-06 | 10 | PASS | 0.1 | 3.5 |
| heo_stress | L3 | gravity 8x8 | 1 | 0.182 | 0.161 | 0.0846 | 0.00851 | 4.39e-06 | 10 | PASS | 0.1 | 3.4 |
| heo_stress | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.182 | 0.16 | 0.085 | 0.00851 | 4.37e-06 | 10 | PASS | 0.1 | 3.5 |
| heo_stress | L5 | L4 + SRP, conical shadow | 1 | 0.126 | 0.11 | 0.0623 | 0.0084 | 3.02e-06 | 10 | PASS | 0.2 | 18.6 |
| heo_stress | L6 | L5 + NRLMSISE-00 drag | 1 | 0.149 | 0.129 | 0.0728 | 0.0084 | 3.55e-06 | 10 | PASS | 0.2 | 18.5 |

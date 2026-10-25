# AstroFlyer vs Basilisk cross-check

Reference data: Basilisk 2.11.1, RKF78 at relTol 1e-12; AstroFlyer's EGM2008 and GM values; DE424 Sun/Moon and ITRF93 orientation from GMAT's SPICE kernels; L7 omitted (no relativity). Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.
AstroFlyer propagator: dop853 ({'method': 'DOP853'}).

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | Basilisk (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L0 | two-body | 1 | 0.0189 | 0.00794 | 0.0189 | 8.31e-08 | 1.6e-05 | 10 | PASS | 0.9 | 3.8 |
| molniya | L1 | J2 only | 1 | 0.372 | 0.171 | 0.352 | 0.00332 | 0.000256 | 10 | PASS | 0.7 | 3.6 |
| molniya | L2 | zonal 4x0 | 1 | 0.361 | 0.166 | 0.341 | 0.00333 | 0.000249 | 10 | PASS | 0.1 | 3.6 |
| molniya | L3 | gravity 8x8 | 1 | 0.363 | 0.167 | 0.343 | 0.00336 | 0.00025 | 10 | PASS | 0.1 | 3.4 |
| molniya | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.363 | 0.167 | 0.344 | 0.00337 | 0.000251 | 10 | PASS | 0.2 | 3.4 |
| molniya | L5 | L4 + SRP, conical shadow | 1 | 0.719 | 0.332 | 0.68 | 0.00327 | 0.000493 | 10 | PASS | 0.3 | 18.0 |
| molniya | L6 | L5 + NRLMSISE-00 drag | 1 | 33 | 15.2 | 31.2 | 0.00326 | 0.0227 | 10 | FAIL | 7.7 | 18.3 |
| tundra | L0 | two-body | 1 | 0.000817 | 0.000406 | 0.000817 | 9.03e-08 | 7.69e-08 | 10 | PASS | 0.1 | 3.2 |
| tundra | L1 | J2 only | 1 | 0.00247 | 0.00102 | 0.00238 | 0.000261 | 2.39e-07 | 10 | PASS | 0.1 | 3.1 |
| tundra | L2 | zonal 4x0 | 1 | 0.00256 | 0.00107 | 0.00237 | 0.000261 | 2.4e-07 | 10 | PASS | 0.1 | 3.2 |
| tundra | L3 | gravity 8x8 | 1 | 0.00243 | 0.00092 | 0.00234 | 0.00026 | 2.34e-07 | 10 | PASS | 0.1 | 3.6 |
| tundra | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.0021 | 0.000905 | 0.002 | 0.000267 | 2.06e-07 | 10 | PASS | 0.1 | 3.5 |
| tundra | L5 | L4 + SRP, conical shadow | 1 | 0.115 | 0.033 | 0.115 | 0.000386 | 1.13e-05 | 10 | PASS | 0.2 | 18.6 |
| tundra | L6 | L5 + NRLMSISE-00 drag | 1 | 0.116 | 0.033 | 0.115 | 0.000389 | 1.13e-05 | 10 | PASS | 0.2 | 18.4 |
| gto | L0 | two-body | 1 | 0.0177 | 0.00743 | 0.0174 | 2.29e-07 | 1.53e-05 | 10 | PASS | 0.1 | 3.2 |
| gto | L1 | J2 only | 1 | 0.0932 | 0.0391 | 0.093 | 0.0114 | 8.39e-05 | 10 | PASS | 0.2 | 3.2 |
| gto | L2 | zonal 4x0 | 1 | 0.0916 | 0.0384 | 0.0914 | 0.0114 | 8.25e-05 | 10 | PASS | 0.1 | 3.3 |
| gto | L3 | gravity 8x8 | 1 | 0.32 | 0.135 | 0.319 | 0.0115 | 0.000282 | 10 | PASS | 0.1 | 3.3 |
| gto | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.32 | 0.135 | 0.319 | 0.0115 | 0.000282 | 10 | PASS | 0.2 | 3.3 |
| gto | L5 | L4 + SRP, conical shadow | 1 | 0.0992 | 0.0415 | 0.0989 | 0.0114 | 8.92e-05 | 10 | PASS | 0.4 | 17.9 |
| gto | L6 | L5 + NRLMSISE-00 drag | 1 | 313 | 132 | 312 | 0.0408 | 0.276 | 10 | FAIL | 0.8 | 18.4 |
| heo_stress | L0 | two-body | 1 | 0.00268 | 0.00168 | 0.00208 | 8.38e-08 | 7.57e-08 | 10 | PASS | 0.1 | 3.2 |
| heo_stress | L1 | J2 only | 1 | 0.127 | 0.111 | 0.0616 | 0.00853 | 3.05e-06 | 10 | PASS | 0.1 | 3.2 |
| heo_stress | L2 | zonal 4x0 | 1 | 0.124 | 0.109 | 0.0597 | 0.00853 | 2.99e-06 | 10 | PASS | 0.1 | 3.3 |
| heo_stress | L3 | gravity 8x8 | 1 | 0.182 | 0.161 | 0.0846 | 0.00851 | 4.39e-06 | 10 | PASS | 0.1 | 3.2 |
| heo_stress | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.182 | 0.16 | 0.085 | 0.00851 | 4.37e-06 | 10 | PASS | 0.1 | 3.4 |
| heo_stress | L5 | L4 + SRP, conical shadow | 1 | 0.14 | 0.122 | 0.0683 | 0.00847 | 3.35e-06 | 10 | PASS | 0.2 | 18.5 |
| heo_stress | L6 | L5 + NRLMSISE-00 drag | 1 | 0.159 | 0.139 | 0.0772 | 0.00847 | 3.81e-06 | 10 | PASS | 0.2 | 19.0 |

# AstroFlyer vs Orekit cross-check

Reference data: AstroFlyer bundled IERS files (no ephemerides: L0-L3 only). Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.
AstroFlyer propagator: rkf78_steered ({'method': 'RKF78', 'steering': 'covariance'}).

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | Orekit (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L3 | gravity 8x8 | 7 | 0.307 | 0.132 | 0.303 | 0.00069 | 0.000244 | 100 | PASS | 13.4 | 2.5 |
| tundra | L3 | gravity 8x8 | 7 | 0.0141 | 0.00276 | 0.0141 | 2.64e-05 | 1.53e-06 | 100 | PASS | 4.5 | 1.0 |
| gto | L3 | gravity 8x8 | 7 | 0.16 | 0.068 | 0.158 | 0.000335 | 0.000138 | 100 | PASS | 13.3 | 1.1 |
| heo_stress | L3 | gravity 8x8 | 7 | 0.209 | 0.0977 | 0.208 | 0.000389 | 0.000157 | 100 | PASS | 7.0 | 0.9 |

# AstroFlyer vs Orekit cross-check

Reference data: AstroFlyer bundled IERS files (no ephemerides: L0-L3 only). Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | Orekit (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L0 | two-body | 7 | 0.89 | 0.382 | 0.88 | 1.66e-07 | 0.000714 | 100 | PASS | 2.6 | 1.0 |
| molniya | L3 | gravity 8x8 | 7 | 0.675 | 0.292 | 0.666 | 0.000615 | 0.000537 | 100 | PASS | 3.8 | 2.5 |
| tundra | L0 | two-body | 7 | 0.00362 | 0.0007 | 0.00361 | 8.27e-08 | 2.99e-07 | 100 | PASS | 1.0 | 0.3 |
| tundra | L3 | gravity 8x8 | 7 | 0.0026 | 0.000781 | 0.0026 | 2.63e-05 | 1.28e-07 | 100 | PASS | 1.1 | 1.4 |
| gto | L0 | two-body | 7 | 1.67 | 0.789 | 1.67 | 1.39e-07 | 0.00149 | 100 | PASS | 2.4 | 0.2 |
| gto | L3 | gravity 8x8 | 7 | 1.68 | 0.717 | 1.66 | 0.000352 | 0.00144 | 100 | PASS | 2.8 | 1.5 |
| heo_stress | L0 | two-body | 7 | 0.0512 | 0.0237 | 0.0511 | 2.34e-07 | 3.88e-05 | 100 | PASS | 1.3 | 0.3 |
| heo_stress | L3 | gravity 8x8 | 7 | 0.11 | 0.0519 | 0.11 | 0.000376 | 8.24e-05 | 100 | PASS | 1.4 | 2.1 |

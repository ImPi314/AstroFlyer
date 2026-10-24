# AstroFlyer vs Orekit cross-check

Reference data: orekit-data at C:\Users\Harshith\OneDrive\Desktop\major_project_py\astroflyer\validation\orekit-data. Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.
AstroFlyer propagator: dop853 ({'method': 'DOP853'}).

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | Orekit (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L0 | two-body | 1 | 0.0197 | 0.00828 | 0.0197 | 3.68e-08 | 1.67e-05 | 10 | PASS | 0.9 | 0.2 |
| molniya | L1 | J2 only | 1 | 0.00785 | 0.00365 | 0.00737 | 0.000116 | 5.62e-06 | 10 | PASS | 0.7 | 0.3 |
| molniya | L2 | zonal 4x0 | 1 | 0.0076 | 0.00405 | 0.00749 | 0.000116 | 5.94e-06 | 10 | PASS | 0.1 | 0.1 |
| molniya | L3 | gravity 8x8 | 1 | 0.00683 | 0.0032 | 0.0064 | 0.00011 | 4.91e-06 | 10 | PASS | 0.2 | 0.2 |
| molniya | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.00686 | 0.00326 | 0.00643 | 0.00011 | 4.94e-06 | 10 | PASS | 0.3 | 0.4 |
| molniya | L5 | L4 + SRP, conical shadow | 1 | 1.01 | 0.465 | 0.954 | 0.000147 | 0.000693 | 10 | PASS | 0.3 | 0.8 |
| molniya | L6 | L5 + NRLMSISE-00 drag | 1 | 0.931 | 0.429 | 0.881 | 0.000126 | 0.00064 | 10 | PASS | 8.6 | 1.9 |
| molniya | L7 | L6 + relativity (full model) | 1 | 0.896 | 0.413 | 0.848 | 0.000126 | 0.000616 | 10 | PASS | 0.4 | 1.7 |
| tundra | L0 | two-body | 1 | 0.000819 | 0.000407 | 0.000819 | 4.13e-08 | 7.72e-08 | 10 | PASS | 0.1 | 0.0 |
| tundra | L1 | J2 only | 1 | 0.000941 | 0.000436 | 0.00094 | 7.47e-06 | 8.82e-08 | 10 | PASS | 0.1 | 0.1 |
| tundra | L2 | zonal 4x0 | 1 | 0.000953 | 0.00044 | 0.000953 | 7.44e-06 | 9.01e-08 | 10 | PASS | 0.1 | 0.1 |
| tundra | L3 | gravity 8x8 | 1 | 0.000935 | 0.00049 | 0.000934 | 7.52e-06 | 8.72e-08 | 10 | PASS | 0.1 | 0.1 |
| tundra | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.000948 | 0.00045 | 0.000947 | 7.07e-06 | 8.86e-08 | 10 | PASS | 0.1 | 0.2 |
| tundra | L5 | L4 + SRP, conical shadow | 1 | 0.104 | 0.0299 | 0.104 | 0.000184 | 1.02e-05 | 10 | PASS | 0.1 | 0.6 |
| tundra | L6 | L5 + NRLMSISE-00 drag | 1 | 0.117 | 0.0335 | 0.116 | 0.000212 | 1.14e-05 | 10 | PASS | 0.2 | 1.4 |
| tundra | L7 | L6 + relativity (full model) | 1 | 0.116 | 0.0334 | 0.116 | 0.000211 | 1.14e-05 | 10 | PASS | 0.2 | 1.4 |
| gto | L0 | two-body | 1 | 0.018 | 0.00756 | 0.0177 | 4.94e-08 | 1.55e-05 | 10 | PASS | 0.2 | 0.0 |
| gto | L1 | J2 only | 1 | 0.0288 | 0.0118 | 0.0288 | 0.000274 | 2.56e-05 | 10 | PASS | 0.2 | 0.1 |
| gto | L2 | zonal 4x0 | 1 | 0.0286 | 0.0117 | 0.0286 | 0.000274 | 2.54e-05 | 10 | PASS | 0.2 | 0.2 |
| gto | L3 | gravity 8x8 | 1 | 0.0286 | 0.0117 | 0.0285 | 0.000272 | 2.53e-05 | 10 | PASS | 0.2 | 0.2 |
| gto | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.0283 | 0.0116 | 0.0282 | 0.000272 | 2.51e-05 | 10 | PASS | 0.2 | 0.2 |
| gto | L5 | L4 + SRP, conical shadow | 1 | 0.051 | 0.0209 | 0.0509 | 0.000262 | 4.57e-05 | 10 | PASS | 0.3 | 0.6 |
| gto | L6 | L5 + NRLMSISE-00 drag | 1 | 0.63 | 0.265 | 0.628 | 0.000229 | 0.000558 | 10 | PASS | 0.8 | 1.6 |
| gto | L7 | L6 + relativity (full model) | 1 | 0.471 | 0.199 | 0.47 | 0.000267 | 0.000415 | 10 | PASS | 0.8 | 1.6 |
| heo_stress | L0 | two-body | 1 | 0.00292 | 0.00192 | 0.0022 | 6.29e-08 | 7.55e-08 | 10 | PASS | 0.1 | 0.0 |
| heo_stress | L1 | J2 only | 1 | 0.00115 | 0.000254 | 0.00112 | 0.000199 | 4.4e-08 | 10 | PASS | 0.1 | 0.1 |
| heo_stress | L2 | zonal 4x0 | 1 | 0.00395 | 0.00258 | 0.00299 | 0.000198 | 8.52e-08 | 10 | PASS | 0.1 | 0.1 |
| heo_stress | L3 | gravity 8x8 | 1 | 0.00307 | 0.00186 | 0.00244 | 0.000199 | 8.07e-08 | 10 | PASS | 0.1 | 0.1 |
| heo_stress | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.003 | 0.00181 | 0.00239 | 0.000199 | 8.04e-08 | 10 | PASS | 0.1 | 0.2 |
| heo_stress | L5 | L4 + SRP, conical shadow | 1 | 0.0377 | 0.0327 | 0.0187 | 0.000401 | 8.98e-07 | 10 | PASS | 0.1 | 0.6 |
| heo_stress | L6 | L5 + NRLMSISE-00 drag | 1 | 0.0249 | 0.022 | 0.0116 | 7.37e-05 | 6e-07 | 10 | PASS | 0.2 | 1.5 |
| heo_stress | L7 | L6 + relativity (full model) | 1 | 0.0146 | 0.0132 | 0.00631 | 0.000205 | 3.57e-07 | 10 | PASS | 0.2 | 1.5 |

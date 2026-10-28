# AstroFlyer vs GMAT cross-check

Reference data: GMAT R2026a, RungeKutta89 at accuracy 1e-13; AstroFlyer's EGM2008 coefficients; GMAT's DE424 Sun/Moon, Earth orientation and shadow model. Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.
AstroFlyer propagator: dop853 ({'method': 'DOP853'}).

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | GMAT (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L0 | two-body | 1 | 0.0426 | 0.0238 | 0.0425 | 0.0138 | 3.13e-05 | 10 | PASS | 2.3 | 1.0 |
| molniya | L1 | J2 only | 1 | 0.0656 | 0.0345 | 0.0607 | 0.014 | 4.12e-05 | 10 | PASS | 0.9 | 0.6 |
| molniya | L2 | zonal 4x0 | 1 | 0.0528 | 0.0191 | 0.0506 | 0.014 | 4.03e-05 | 10 | PASS | 0.2 | 0.7 |
| molniya | L3 | gravity 8x8 | 1 | 0.0444 | 0.0154 | 0.0428 | 0.014 | 1.49e-05 | 10 | PASS | 0.2 | 0.9 |
| molniya | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.0408 | 0.0126 | 0.0389 | 0.014 | 1.71e-05 | 10 | PASS | 0.3 | 0.8 |
| molniya | L5 | L4 + SRP, conical shadow | 1 | 1.06 | 0.488 | 1 | 0.0139 | 0.000733 | 10 | PASS | 0.4 | 0.6 |
| molniya | L6 | L5 + NRLMSISE-00 drag | 1 | 0.0775 | 0.0333 | 0.0765 | 0.0139 | 6.33e-05 | 10 | PASS | 8.7 | 1.2 |
| molniya | L7 | L6 + relativity (full model) | 1 | 0.0752 | 0.0323 | 0.074 | 0.0091 | 6.07e-05 | 10 | PASS | 0.6 | 1.0 |
| tundra | L0 | two-body | 1 | 0.0441 | 0.00118 | 0.0417 | 0.0234 | 4.79e-06 | 10 | PASS | 0.1 | 0.5 |
| tundra | L1 | J2 only | 1 | 0.0462 | 0.0035 | 0.0451 | 0.0234 | 5.31e-06 | 10 | PASS | 0.1 | 0.5 |
| tundra | L2 | zonal 4x0 | 1 | 0.0466 | 0.002 | 0.0441 | 0.0234 | 5.44e-06 | 10 | PASS | 0.1 | 0.5 |
| tundra | L3 | gravity 8x8 | 1 | 0.0444 | 0.00162 | 0.042 | 0.0234 | 4.79e-06 | 10 | PASS | 0.1 | 0.5 |
| tundra | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.0378 | 0.00377 | 0.035 | 0.0234 | 4.55e-06 | 10 | PASS | 0.1 | 0.5 |
| tundra | L5 | L4 + SRP, conical shadow | 1 | 0.146 | 0.0318 | 0.144 | 0.0234 | 1.5e-05 | 10 | PASS | 0.2 | 0.6 |
| tundra | L6 | L5 + NRLMSISE-00 drag | 1 | 0.155 | 0.0337 | 0.154 | 0.0234 | 1.62e-05 | 10 | PASS | 0.2 | 0.8 |
| tundra | L7 | L6 + relativity (full model) | 1 | 0.161 | 0.0348 | 0.16 | 0.0154 | 1.69e-05 | 10 | PASS | 0.2 | 0.8 |
| gto | L0 | two-body | 1 | 0.0395 | 0.0187 | 0.0365 | 0.0389 | 3e-05 | 10 | PASS | 0.1 | 0.5 |
| gto | L1 | J2 only | 1 | 0.0393 | 0.0171 | 0.0369 | 0.0388 | 3.23e-05 | 10 | PASS | 0.1 | 0.5 |
| gto | L2 | zonal 4x0 | 1 | 0.0702 | 0.0326 | 0.0697 | 0.0388 | 6.12e-05 | 10 | PASS | 0.1 | 0.5 |
| gto | L3 | gravity 8x8 | 1 | 0.0394 | 0.0142 | 0.0262 | 0.0388 | 2.31e-05 | 10 | PASS | 0.2 | 0.5 |
| gto | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.0412 | 0.00734 | 0.0136 | 0.0389 | 1.37e-05 | 10 | PASS | 0.2 | 0.6 |
| gto | L5 | L4 + SRP, conical shadow | 1 | 0.0395 | 0.0126 | 0.0278 | 0.0389 | 2.44e-05 | 10 | PASS | 0.4 | 0.7 |
| gto | L6 | L5 + NRLMSISE-00 drag | 1 | 0.0741 | 0.0342 | 0.0736 | 0.0389 | 6.45e-05 | 10 | PASS | 0.9 | 0.9 |
| gto | L7 | L6 + relativity (full model) | 1 | 0.0362 | 0.0109 | 0.0259 | 0.0348 | 2.32e-05 | 10 | PASS | 0.9 | 1.0 |
| heo_stress | L0 | two-body | 1 | 0.0421 | 0.00221 | 0.0279 | 0.0328 | 1.82e-06 | 10 | PASS | 0.1 | 0.5 |
| heo_stress | L1 | J2 only | 1 | 0.0401 | 0.00664 | 0.0263 | 0.0319 | 1.17e-06 | 10 | PASS | 0.1 | 0.6 |
| heo_stress | L2 | zonal 4x0 | 1 | 0.0417 | 0.00462 | 0.0286 | 0.0319 | 3.6e-06 | 10 | PASS | 0.1 | 0.5 |
| heo_stress | L3 | gravity 8x8 | 1 | 0.0404 | 0.00356 | 0.0267 | 0.0319 | 1.74e-06 | 10 | PASS | 0.1 | 0.5 |
| heo_stress | L4 | 8x8 + Sun/Moon (DE440) | 1 | 0.0388 | 0.00533 | 0.0242 | 0.0318 | 1.48e-06 | 10 | PASS | 0.1 | 0.5 |
| heo_stress | L5 | L4 + SRP, conical shadow | 1 | 0.0378 | 0.0144 | 0.0176 | 0.0319 | 1.76e-06 | 10 | PASS | 0.2 | 0.6 |
| heo_stress | L6 | L5 + NRLMSISE-00 drag | 1 | 0.0401 | 0.022 | 0.0143 | 0.0319 | 3.44e-06 | 10 | PASS | 0.2 | 0.8 |
| heo_stress | L7 | L6 + relativity (full model) | 1 | 0.0508 | 0.0339 | 0.0156 | 0.0359 | 1.47e-06 | 10 | PASS | 0.2 | 0.8 |

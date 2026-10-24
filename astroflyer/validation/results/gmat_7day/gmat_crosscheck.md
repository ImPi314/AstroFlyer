# AstroFlyer vs GMAT cross-check

Reference data: GMAT R2026a, RungeKutta89 at accuracy 1e-13; AstroFlyer's EGM2008 coefficients; GMAT's DE424 Sun/Moon, Earth orientation and shadow model. Epoch 2026-01-01T00:00:00 TT, GCRF, output every 600 s.
AstroFlyer propagator: dop853 ({'method': 'DOP853'}).

| Orbit | Level | Forces | Days | Max 3D (m) | Radial (m) | In-track (m) | Cross-track (m) | Max |dv| (m/s) | Limit (m) | Result | AstroFlyer (s) | GMAT (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| molniya | L3 | gravity 8x8 | 7 | 0.865 | 0.373 | 0.851 | 0.156 | 0.000688 | 100 | PASS | 2.3 | 0.8 |
| molniya | L4 | 8x8 + Sun/Moon (DE440) | 7 | 1.04 | 0.447 | 1.03 | 0.156 | 0.000835 | 100 | PASS | 1.2 | 1.4 |
| molniya | L5 | L4 + SRP, conical shadow | 7 | 32.6 | 14.1 | 32.2 | 0.16 | 0.026 | 100 | PASS | 2.6 | 2.0 |
| molniya | L6 | L5 + NRLMSISE-00 drag | 7 | 16.2 | 7 | 16 | 0.159 | 0.013 | 100 | PASS | 11.3 | 3.6 |
| molniya | L7 | L6 + relativity (full model) | 7 | 16.2 | 6.98 | 15.9 | 0.14 | 0.0129 | 100 | PASS | 3.8 | 4.1 |
| tundra | L3 | gravity 8x8 | 7 | 0.179 | 0.0046 | 0.0641 | 0.177 | 1.08e-05 | 100 | PASS | 0.4 | 0.7 |
| tundra | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.18 | 0.00507 | 0.0674 | 0.178 | 1.09e-05 | 100 | PASS | 0.5 | 1.1 |
| tundra | L5 | L4 + SRP, conical shadow | 7 | 2.27 | 0.528 | 2.27 | 0.18 | 0.000232 | 100 | PASS | 1.2 | 1.5 |
| tundra | L6 | L5 + NRLMSISE-00 drag | 7 | 2.29 | 0.535 | 2.29 | 0.18 | 0.000234 | 100 | PASS | 1.6 | 3.0 |
| tundra | L7 | L6 + relativity (full model) | 7 | 2.5 | 0.576 | 2.5 | 0.162 | 0.000256 | 100 | PASS | 1.5 | 3.2 |
| gto | L3 | gravity 8x8 | 7 | 1.88 | 0.8 | 1.86 | 0.0642 | 0.00162 | 100 | PASS | 1.1 | 0.8 |
| gto | L4 | 8x8 + Sun/Moon (DE440) | 7 | 1.57 | 0.669 | 1.56 | 0.0643 | 0.00136 | 100 | PASS | 1.4 | 1.7 |
| gto | L5 | L4 + SRP, conical shadow | 7 | 0.766 | 0.322 | 0.759 | 0.0643 | 0.000666 | 100 | PASS | 2.9 | 2.0 |
| gto | L6 | L5 + NRLMSISE-00 drag | 7 | 7.41 | 3.17 | 7.3 | 0.0645 | 0.00627 | 100 | PASS | 6.1 | 4.3 |
| gto | L7 | L6 + relativity (full model) | 7 | 7.39 | 3.16 | 7.28 | 0.0938 | 0.00626 | 100 | PASS | 6.3 | 4.8 |
| heo_stress | L3 | gravity 8x8 | 7 | 0.378 | 0.0275 | 0.188 | 0.327 | 4.05e-05 | 100 | PASS | 0.5 | 0.7 |
| heo_stress | L4 | 8x8 + Sun/Moon (DE440) | 7 | 0.381 | 0.0584 | 0.196 | 0.327 | 7.38e-05 | 100 | PASS | 0.6 | 1.1 |
| heo_stress | L5 | L4 + SRP, conical shadow | 7 | 1.74 | 0.829 | 1.72 | 0.327 | 0.00129 | 100 | PASS | 1.2 | 1.4 |
| heo_stress | L6 | L5 + NRLMSISE-00 drag | 7 | 3.73 | 1.77 | 3.69 | 0.327 | 0.00277 | 100 | PASS | 1.8 | 2.8 |
| heo_stress | L7 | L6 + relativity (full model) | 7 | 4.33 | 2.05 | 4.29 | 0.355 | 0.00322 | 100 | PASS | 1.7 | 3.1 |

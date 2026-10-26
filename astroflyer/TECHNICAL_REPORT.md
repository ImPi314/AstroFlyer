# AstroFlyer HEO — Technical Report

**Precise Trajectory Propagation and Events Prediction for Highly Eccentric Orbits (HEOs)**

Department of Aerospace Engineering, ACS College of Engineering (affiliated to VTU, Belagavi)

Candidates: Girish Gowda S (1AH23AS019), Gowtham N (1AH23AS020), Harshith S Purohith (1AH23AS021).
Guides: Mr. Vijay M (Assistant Professor), Dr. Suresh C (Professor & Head of Department).

Status as of October 2026 (branch `integration`). Every number below was produced by the code in this
repository and can be regenerated with the commands given; nothing is quoted from elsewhere.

---

## 1. Summary

AstroFlyer HEO is an offline Windows desktop application for propagating spacecraft in highly eccentric
orbits (Molniya, Tundra, GTO, high-apogee science orbits, lunar transfers) and predicting their events
(apsides, nodes, eclipses, ground-station contacts).

* **Engine:** Python, NumPy and SciPy (Numba optional, for gravity), Cowell formulation in GCRF.
* **Force model:** EGM2008 gravity to 70×70, JPL DE440 Sun and Moon, solar radiation pressure with a
  WGS-84 conical shadow, NRLMSISE-00 drag (double-precision port) driven by the bundled CelesTrak
  daily F10.7/Ap history, and post-Newtonian relativity.
* **Default integrator:** SciPy DOP853, restarted exactly at shadow edges and drag-model jumps.
* **Validation:** the same 52 cases cross-checked against three independent propagators (§4).
  All pass against Orekit and NASA GMAT. Against Basilisk, 40 of 44 pass; the four that fail are drag
  cases, from a documented difference in how Basilisk's atmosphere computes altitude.
* **Application:** a local Python server (127.0.0.1) and a browser console (Three.js 3D view, ground
  track, uPlot plots) in a native window through pywebview / Edge WebView2. All data ships with the
  installer; nothing is downloaded at runtime.

---

## 2. Architecture

| Layer | What it is | Main files |
| --- | --- | --- |
| Engine | Force model, trajectory integration, propagation, events | `backend/forces.py`, `trajectory.py`, `astro_engine.py`, `integrators.py`, `event_predictor.py`, `eclipse.py`, `access.py` |
| Time and frames | UTC/TAI/TT/TDB/UT1/GPS; IAU 2006/2000A GCRF↔ITRF with IERS EOP | `backend/epoch.py`, `frames.py`, `eop.py` |
| Server | Local HTTP adapters (`/api/propagate`, access, targeting, mission script) | `backend/app_server.py`, `propagation_run.py` |
| Console | Mission / Analysis / Data workspaces; 3D view, ground track, plots, watch panel | `frontend/` |
| Packaging | PyInstaller app + Inno Setup installer with bundled data and the WebView2 offline installer | `AstroFlyer.spec`, `build_release.py`, `installer/AstroFlyer_Installer.iss` |

There is no C++ kernel and no PyQt or OpenGL desktop code; earlier review documents that describe them
were wrong (see §7).

---

## 3. Methods

**Propagators.** DOP853 (default) and Radau from SciPy; in-house RKF7(8), Bulirsch–Stoer and fixed-step
RK4; analytic Kepler, J2 mean-element and SGP4. Every integrator runs through one trajectory
integration module (`backend/trajectory.py`), used by the propagate endpoint and by mission scripts,
targeting and finite burns alike. It stops and restarts at every umbra/penumbra edge and at the
altitudes and times where NRLMSISE-00 itself is discontinuous, so step control never straddles a kink;
RKF7(8) and DOP853 then agree to 1 cm over 7 days on Tundra with SRP (24.8 m apart before RKF7(8) got
the restarts). DOP853 is 5–6× faster than Radau on the validation cases and agrees with
it to 0.85 m over 32 days.

**Output sampling.** For display the API samples the integrated trajectory evenly in eccentric anomaly,
so perigee passes are drawn with as many points as apogee dwells. Validation uses uniform time.

**Events.** Apsides and nodes are located by root-finding on the dense output during integration;
eclipses from the conical umbra/penumbra model; ground-station AOS/LOS with elevation masks.

**Two propagation experiments**, measured against Orekit
([validation/results/innovations](validation/results/innovations/README.md)):

* *Covariance-steered stepping* (`steering="covariance"`): the state transition matrix is integrated
  with the orbit and each step is capped so the 1-σ position uncertainty grows by at most η. Against
  plain RKF7(8) (both restarting at shadow and drag boundaries) it improves a few 7-day cases
  (gravity-only GTO: 0.52 m → 0.17 m) at about 3× the run time; it makes some worse (GTO, full model:
  7.04 m → 7.78 m) and does not beat DOP853 overall.
* *ECR-MF fidelity tiers* (`fidelity="ecr_mf"`): above 2,000 km and 20,000 km altitude, gravity is cut
  to the lowest degree whose omitted acceleration is below 10⁻¹⁰ m/s². At 70×70 it stays within
  0.0032 m of the full model over a day, but gives no speed-up: gravity is not the costly force.

---

## 4. Validation

Four orbits (Molniya, Tundra, GTO, and an e = 0.88 stress orbit), epoch 2026-01-01 00:00 TT, the
same Cartesian start state, the force model built up one level at a time: L0 two-body, L1 J2,
L2 J2–J4, L3 8×8, L4 + Sun/Moon, L5 + SRP, L6 + drag, L7 + relativity. Every tool is given AstroFlyer's
own EGM2008 coefficients, spacecraft (Cr·A/m 0.02, Cd·A/m 0.01 m²/kg) and constant space weather
(F10.7 150, Ap 15). Limits: 10 m after 1 day, 100 m after 7 days.

| Reference | Run | Largest position difference | Result |
| --- | --- | --- | --- |
| Orekit 13.1 | 1 day, L0–L7 | 0.63 m (GTO, drag on) | 32/32 pass |
| Orekit 13.1 | 7 days, L3–L7 | 6.1 m (GTO, full model) | 20/20 pass |
| NASA GMAT R2026a | 1 day, L0–L7 | 1.06 m (Molniya, SRP on) | 32/32 pass |
| NASA GMAT R2026a | 7 days, L3–L7 | 32.6 m (Molniya, SRP on) | 20/20 pass |
| Basilisk 2.11.1 | 1 day, L0–L6 | 0.72 m through L5; drag 313 m (GTO) | 26/28 pass |
| Basilisk 2.11.1 | 7 days, L3–L6 | 30.3 m through L5; drag 16.6 km (GTO) | 14/16 pass |

Through L4 (gravity, Sun and Moon) AstroFlyer agrees with all three to centimetres over a day. Each
larger difference was traced by an experiment that changed one side to match the other and watched the
difference vanish:

* **Shadow shape.** GMAT and Basilisk cast the Earth's shadow from a sphere; AstroFlyer and Orekit use
  the WGS-84 ellipsoid. This is GMAT's and Basilisk's Molniya SRP difference (32.6 m and 30.3 m over
  7 days).
* **Anomalous oxygen.** GMAT's NRLMSISE-00 uses `gtd7`; AstroFlyer uses `gtd7d`, the model authors'
  recommendation for drag, which Orekit agrees with. It matters above ~500 km (Molniya, 1.1 m a day).
* **Spherical altitude.** Basilisk's atmosphere takes altitude above a sphere, not the ellipsoid. That
  alone is its Molniya and GTO drag failure; with AstroFlyer switched to a sphere, drag agrees to
  0.5 m a day (GTO) and 0.1 m (Molniya).
* **Basilisk numerical artefacts**, corrected in the cross-check runner: its gravity steps the Earth's
  orientation linearly within a task step (204 m on Molniya in 6 h at a 60 s step), its environment
  modules are evaluated from the step-start state (24 m a day on GTO drag at a 1 s step), and its
  SPICE-derived air co-rotation rate made GTO drag 9% too strong.
* **Not yet explained:** a 0.37 m a day difference from Basilisk on Molniya with J2 or 8×8 gravity.

Also fixed in AstroFlyer by these comparisons: restarts at shadow edges (Molniya, 7.5 m a day), the
WGS-84 shadow (Molniya L5 over 7 days, 31.7 m → 1.7 m against Orekit) and a double-precision
NRLMSISE-00 (single precision made GTO drag differ by metres between computers).

Tables, method and rerun commands: [validation/results](validation/results/README.md).

**Run time.** Over the 32 one-day cases AstroFlyer takes 16 s in total, against Orekit's 19 s and GMAT's
21 s. These are wall-clock times that include process and JVM start-up, so they show the tools are
comparable, not that one is faster.

---

## 5. Application

* Mission workspace: mission tree, inspector, tiled panes; linked 3D orbit view, ground track with
  station contacts and shadow, parameter plots and a watch panel on one playback timeline.
* Analysis workspace: events, access, targeting (differential corrector, impulsive and finite burns),
  Van Allen belt crossings, covariance.
* Data workspace: mission script (Create / Propagate / Maneuver / Target / If / While / For / Report),
  CCSDS OEM/OPM and SP3 exchange, TLE generation.
* Twelve sample orbits, each checked against its cited source.
* Runs report only what the engine computed; there are no canned or demo figures.

---

## 6. Testing

184 Python tests (`python -m pytest astroflyer/tests`; the Orekit tests need `JAVA_HOME` set, the GMAT
and Basilisk tests skip when those tools are not installed) and 44 frontend `node:test` tests. New
behaviour was written test-first.

---

## 7. Corrections to earlier review documents

The Third Review report (September 2026), the review handbooks and the first abstract stated things this
project did not build or measure. They are corrected here:

| Earlier claim | What is true |
| --- | --- |
| Compiled C++17 SIMD/AVX-2 kernel; PyQt6/OpenGL desktop | Python/NumPy/SciPy engine; browser console in pywebview/WebView2 |
| Verified against FreeFlyer 8.0.1; "26.35× faster than FreeFlyer"; 15–28× speed-up | No FreeFlyer comparison has been run. Run times are comparable to Orekit and GMAT (§4) |
| Sundman time regularisation and Kustaanheimo–Stiefel coordinates | Not implemented; Cowell formulation with adaptive step control |
| Radau-IIA as the main integrator | DOP853 is the default; Radau remains a choice |
| Energy drift 1.12 × 10⁻¹¹; RSS error budget of 8.98 m | Not measured. Measured accuracy is the §4 cross-checks |
| Bidirectional `.MissionPlan` exporter verified with FreeFlyer | Removed (clean-room rule); export is CCSDS OEM/OPM |
| 18.9% fuel saving; 25-year debris lifetime predictor | Not measured; the lifetime model was removed |

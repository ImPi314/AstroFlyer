# AstroFlyer HEO — Flight Dynamics & Trajectory Analysis Studio

[![License](https://img.shields.io/badge/license-Proprietary%20%2F%20Academic-blue.svg)]()
[![Platform](https://img.shields.io/badge/platform-Windows%20x64-lightgrey.svg)]()
[![Python](https://img.shields.io/badge/python-3.12%2B-00e5ff.svg)]()

**AstroFlyer HEO** is an offline desktop application for precise trajectory propagation and
event prediction in **Highly Eccentric Orbits** — Molniya, Tundra, QZS, geostationary transfer
orbits (GTO), high-apogee science orbits and lunar transfers.

It is a Python astrodynamics backend served on `127.0.0.1` and a browser-based operations
console, shown in a native window through pywebview (Edge WebView2). Everything it needs —
ephemerides, gravity field, Earth-orientation and space-weather data — ships with it; nothing
is downloaded at runtime.

*Major Project, Department of Aerospace Engineering, ACS College of Engineering (VTU).*

---

## Capabilities

### Force model (`astroflyer/backend/forces.py`)
* **Gravity:** EGM2008 spherical harmonics up to degree/order 70 (default 8×8), plus `two_body`,
  `j2` and `j2_j3_j4` presets.
* **Third bodies:** Sun and Moon from JPL **DE440** (bundled subset, 1990–2060).
* **Solar radiation pressure** with conical umbra/penumbra shadow from the Earth and the Moon;
  optional Earth albedo and infrared.
* **Atmospheric drag:** double-precision **NRLMSISE-00**, driven by the bundled CelesTrak space-weather
  history (`SW-All.csv`): each UTC day's observed or predicted F10.7, 81-day mean and Ap, with
  moderate defaults (150/150/15) outside the file's coverage. Fixed values can be given instead;
  the cross-checks below use fixed F10.7 150, Ap 15.
* **Relativity:** post-Newtonian Schwarzschild term.

### Time and reference frames
* `Epoch` with UTC, TAI, TT, TDB, UT1 and GPS scales; IERS leap seconds and `finals2000A` EOP.
* IAU 2006/2000A GCRF ↔ ITRF transformation with polar motion; RTN, VNC and LVLH local frames.

### Propagators (`astro_engine.py`, `trajectory.py`, `integrators.py`, `analytic.py`)
* SciPy **DOP853** (default) and **Radau** (implicit, for stiff arcs); in-house **RKF7(8)**,
  **Bulirsch–Stoer** and fixed-step **RK4**. Every one integrates through `trajectory.py` and is
  restarted exactly at shadow edges and drag-model discontinuities, so step control never straddles
  them — the propagate endpoint, mission scripts, targeting and finite burns alike.
* Analytic **Kepler**, **J2 mean-element** and **SGP4** (from TLEs).
* Closed orbits by element set or Cartesian GCRF state; escape trajectories (e ≥ 1) by duration.

### Propagation innovations
* **Covariance-steered stepping** (`steering="covariance"`, RKF7(8)/BS; `covariance_engine.py`): the
  variational equations dΦ/dt = AΦ are integrated with the orbit, and each step is capped so the
  1-σ position uncertainty of P = ΦP₀Φᵀ grows by at most η (predicted from dP/dt, enforced by rejecting
  steps that exceed it). The run returns its STM and step record.
* **ECR-MF fidelity tiers** (`fidelity="ecr_mf"`; `ecr_mf_controller.py`): above 2,000 km and 20,000 km
  altitude the gravity field is cut to the lowest degree whose omitted acceleration is provably below
  ε = 10⁻¹⁰ m/s²; the run reports each tier's degree, its certified bound and every switch time.
* Measured against Orekit in
  [validation/results/innovations](astroflyer/validation/results/innovations/README.md): steering improves
  a few cases (gravity-only GTO over 7 days 0.52 → 0.16 m), makes others worse and costs ~3× the run
  time, so it does not beat DOP853 overall; ECR-MF keeps the full model's accuracy
  but gives no speed-up, because gravity is not the costly force.

### Events and access (`event_predictor.py`, `access.py`, `eclipse.py`)
* Apsides and nodes located by root-finding during integration.
* Ground-station AOS/LOS with elevation masks, look angles and peak elevation, with the real Earth
  orientation at the run's epoch (IAU 2006/2000A) and WGS-84 station positions.
* Earth and Moon eclipses (umbra/penumbra), beta angle, CSV reports.

### Mission design (`mission.py`, `script_runner.py`, `differential_corrector.py`)
* Impulsive and finite burns with mass flow; differential corrector (vary/achieve).
* A mission-script interpreter (Create/Propagate/Maneuver/Target/If/While/For/Report).
* GTO→GEO and perigee-raise targeting; multi-burn perigee pumping.
* Targeting tab: apogee raise and finite burn from the run's first perigee, on the run's force model.
* Impulsive burns in the mission itself: add them under **Burns** in the mission tree (at the next
  perigee, the next apogee or a time after the start; velocity change in the VNC frame; propellant from
  the specific impulse). Run applies them in order and restarts the integration at each one.

### Analysis modules
* Van Allen belt L-shell, magnetic field and belt crossings along the trajectory
  (`radiation_belts.py`).
* Linear covariance propagation and dispersion (`covariance_engine.py`).

### Data exchange
* CCSDS OEM / OPM read and write, SP3 read, NORAD TLE generation (`ephemeris_io.py`,
  `ccsds_exporter.py`). A run's OPM, TLE and mission script are for its own epoch and initial state;
  the TLE holds SGP4 mean elements fitted to reproduce that state (no drag term).

### Operations console (`astroflyer/frontend/`)
* Three workspaces: **Mission** (mission tree, inspector, tiled panes), **Analysis** (Events,
  Access, Targeting, Radiation, Covariance) and **Data** (mission script, export).
* Linked 3D orbit view (Three.js), ground track with station contacts and shadow, parameter plots
  (uPlot) and a watch panel, all driven by one playback timeline.
* Mission files: **Save** (Ctrl+S) writes the mission as JSON; **Open** (Ctrl+O) or the Start
  screen reads it back.
* **Continue from the end of the last run** (the button after Save): the mission starts again from
  the last run's final state (GCRF position and velocity, epoch to the microsecond, mass after burns),
  with whatever integrator, force model, span and burns you choose next. Saving then keeps that point
  as a checkpoint, and the file lists the legs it was continued from. Continuing a 1-orbit Molniya
  run for another orbit (full model, 8 x 8 field) ends 2.9 cm from the same 2-orbit run done in one go.
* Twelve sample orbits, from Molniya and Tundra to XMM-Newton, Chandra and a lunar transfer.
* Fonts, icons, textures and libraries are bundled; the console works with no network. Earth
  imagery: NASA Blue Marble Next Generation (NASA Goddard Space Flight Center / Reto Stöckli, NASA
  Earth Observatory), oceans darkened.

---

## Validation

The propagator is checked against three independent tools, from the same starting state at epoch
2026-01-01 00:00 TT, on four orbits (Molniya, Tundra, GTO, an e = 0.88 stress case), building the
force model up one level at a time (L0 two-body → L7 full model). All are given AstroFlyer's
own EGM2008 coefficients, so the comparison is of the propagators, not their input data.

Latest run 2026-10-28 on the development laptop (Python 3.14.6; per-case tables in
[results/rerun_2026-10-28](astroflyer/validation/results/rerun_2026-10-28)):

| Reference | Run | Largest position difference | Limit | Result |
| --- | --- | --- | --- | --- |
| Orekit 13.1.9 | 1 day, L0–L7 | 0.63 m (GTO, drag on) | 10 m | 32/32 pass |
| Orekit 13.1.9 | 7 days, L0–L7 | 6.12 m (GTO, full model) | 100 m | 32/32 pass |
| NASA GMAT R2026a | 1 day, L0–L7 | 1.06 m (Molniya, SRP on) | 10 m | 32/32 pass |
| NASA GMAT R2026a | 7 days, L0–L7 | 32.6 m (Molniya, SRP on) | 100 m | 32/32 pass |
| Basilisk 2.11.1 | 1 day, L0–L6 | 0.72 m (Molniya, SRP on) through L5; drag 313 m (GTO) | 10 m | 26/28 pass |
| Basilisk 2.11.1 | 7 days, L0–L6 | 30.3 m (Molniya, SRP on) through L5; drag 16.6 km (GTO) | 100 m | 26/28 pass |

![Largest difference from each reference per force level](docs/figures/validation/crosscheck_overview.png)

Gravity and Sun/Moon agree with both to a few centimetres over a day. The larger GMAT differences
come from two documented modelling choices, each confirmed by changing AstroFlyer to match and
watching the difference vanish: GMAT casts the Earth's shadow from a sphere (AstroFlyer and Orekit
use the WGS-84 ellipsoid), and GMAT's NRLMSISE-00 leaves out anomalous oxygen (AstroFlyer uses the
model's recommended drag density, which Orekit's results agree with). Basilisk has no relativity
(L7 is not run) and fails at L6 on the two low-perigee orbits: its atmosphere takes altitude above a
sphere, not the WGS-84 ellipsoid. With AstroFlyer switched to a sphere in an experiment, drag agrees
to 0.5 m a day on GTO and 0.1 m on Molniya. Tables, method and how to rerun them are in
[astroflyer/validation/results](astroflyer/validation/results/README.md).

### Integration across force-model discontinuities

SRP switches off through the penumbra and NRLMSISE-00 density jumps at fixed altitudes and at UTC
midnight. An adaptive integrator that steps across such a point loses its error control there; Woodburn
(2000) measured up to 118 m a week from shadow crossings alone and recommended restarting at them.
AstroFlyer restarts every integrator (DOP853, RKF7(8), Bulirsch–Stoer, Radau, RK4) at the exact
penumbra and umbra edges of the WGS-84 shadow and at every drag-model jump, in every run the
application makes. The same cases were run against Orekit with the restarts removed for the run only
([restart_ablation.py](astroflyer/validation/results/discontinuity_restarts/restart_ablation.py)):

| 7 days, max difference from Orekit | DOP853, stepping across | DOP853, restarted | RKF7(8), stepping across | RKF7(8), restarted |
| --- | --- | --- | --- | --- |
| Molniya, SRP (L5) | 54.1 m | 1.71 m | 0.70 m | 2.60 m |
| Molniya, full model (L7) | 63.9 m | 5.15 m | 3.59 m | 6.03 m |
| Tundra, full model (L7) | 11.5 m | 0.021 m | 18.2 m | 0.010 m |
| GTO, SRP (L5) | 56.8 m | 5.47 m | 9.13 m | 6.24 m |
| GTO, drag (L6) | 2.60 m | 2.85 m | 1.83 m | 2.33 m |
| GTO, full model (L7) | 12.9 m | 6.12 m | 9.90 m | 7.04 m |
| HEO stress, SRP (L5) | 65.0 m | 2.80 m | 27.2 m | 2.96 m |
| HEO stress, full model (L7) | 51.4 m | 4.51 m | 26.3 m | 4.49 m |

The worst case over all 24 orbit/level/integrator combinations (L5–L7) falls from 65.9 m to 7.04 m.
Without restarts the result depends on where the steps happen to land: five combinations (RKF7(8) on
Molniya, both integrators on GTO drag) come out 0.25–2.45 m closer without them. With restarts the two
integrators agree with each other and with Orekit. One day: Molniya with drag goes from
14.4 m to 0.15 m (DOP853).

![Restarts on and off, 7 days](docs/figures/validation/restarts_7day.png)
![Difference from Orekit over 7 days, Molniya and the e = 0.88 orbit](docs/figures/validation/restarts_molniya_stress_series.png)

### Uncertainty-steered steps and radius-tiered gravity

Two engine options (`steering="covariance"` and `fidelity="ecr_mf"` on `/api/propagate` and
`ThirdReviewEngine.propagate`, and on the console's propagator panel as **Step control** for
RKF7(8)/BS and **Gravity fidelity** next to **Gravity field** (degree 2–70) for the full model; the run
log reports what each did) were measured against Orekit and against the full model ([innovations](astroflyer/validation/results/innovations/README.md)).

**Covariance-steered stepping** integrates the state transition matrix with the orbit and caps each
step so the 1-σ position uncertainty grows by at most η = 0.02, so step size follows the uncertainty
the analyst reads rather than the truncation error alone.

| Gravity only (L3), 7 days, vs Orekit | RKF7(8) | RKF7(8), steered |
| --- | --- | --- |
| GTO | 0.519 m | 0.160 m |
| HEO stress | 0.299 m | 0.209 m |
| Tundra | 0.0174 m | 0.0141 m |
| Molniya | 0.264 m | 0.307 m |

With the full force model it gives no consistent gain (GTO L7 over 7 days 7.04 m → 7.78 m) and the run
takes about 3–3.5× as long.

![Covariance-steered steps over one GTO revolution](docs/figures/validation/steering_gto_steps.png)

**ECR-MF** splits the orbit by radius and, in each tier, keeps the lowest gravity degree whose omitted
acceleration is provably below ε = 10⁻¹⁰ m/s² (a bound from the EGM2008 degree amplitudes). At 70×70
the tiers are degree 70 below 2,000 km, 58 to 20,000 km and 8 above. Against the full 70×70 model
([ecr_mf_70x70](astroflyer/validation/results/ecr_mf_70x70)), run 2026-10-28:

| Orbit | 1 day | 7 days |
| --- | --- | --- |
| Molniya | 0.0020 m | 0.243 m |
| Tundra | 0.0010 m | 0.039 m |
| GTO | 0.0075 m | 2.08 m |
| HEO stress | 0.0009 m | 0.046 m |

Run time changes by 0.98–1.14×: gravity is not where the time goes, so ECR-MF gives a certified bound
on what each part of the orbit leaves out, not a speed-up.

![Certified omitted-gravity bound per tier](docs/figures/validation/ecr_mf_bound.png)

### Offline operation

Every run above used only data in the installed application: EGM2008 to 70×70, the DE440 Sun/Moon
subset (1990–2060), IERS leap seconds and Earth orientation, and the CelesTrak space-weather history
([offline_data.md](docs/app_data/offline_data.md)). The server binds to 127.0.0.1 only, the window
resolves no host but localhost and WebView2 background networking is off; `test_offline_packaging.py`
checks each of these. Orekit, GMAT and Basilisk are needed only to rerun the cross-checks.

---

## Installing

Download `AstroFlyer_HEO_v<version>_Setup.exe` from the
[latest release](https://github.com/ImPi314/AstroFlyer/releases/latest) and run it (Windows 10/11,
64-bit). It installs the app with its data and, if missing, the Edge WebView2 runtime. A newer
installer run over an older one upgrades it in place.

## Running locally

**Requirements:** Windows x64, Python 3.12 or newer, and the packages in `requirements.txt`
(NumPy, SciPy, pywebview, pyerfa, jplephem, pymsis, sgp4; Numba is optional and speeds up gravity).

```bash
python -m pip install -r requirements.txt
```

```bash
python main.py
```

opens the desktop window. `python main.py --browser` opens the console in your default browser
instead, and `python astroflyer/backend/app_server.py` runs the server alone at
`http://127.0.0.1:8003`. If port 8003 is busy, the launcher picks a free port.

### Tests

```bash
python -m pytest astroflyer/tests
```

```bash
node --test astroflyer/tests/frontend/*.test.mjs
```

The four Orekit cross-check tests need Orekit (`orekit-jpype`) and its data; without them they
fail at import and the rest of the suite is unaffected.

### Building the Windows installer

```bash
python build_release.py
```

builds `dist/AstroFlyer_HEO/AstroFlyer.exe` with PyInstaller (`AstroFlyer.spec`) and, if Inno
Setup 6 is installed, `dist_installer/AstroFlyer_HEO_v<version>_Setup.exe`.

---

## Project structure

```
major_project_py/
├── main.py                     # Launcher (delegates to astroflyer/main.py)
├── astroflyer/
│   ├── main.py                 # Desktop window / browser entry point
│   ├── backend/                # Astrodynamics engine and the HTTP API (app_server.py)
│   ├── frontend/               # Operations console: index.html, css/, js/, vendor/
│   ├── resources/              # Bundled DE440, EGM2008, IERS and space-weather data
│   ├── validation/             # Orekit, GMAT and Basilisk cross-checks and results
│   ├── tests/                  # pytest suite and frontend/ (node:test)
│   └── figures/, data/, docs/
├── installer/                  # Inno Setup script
├── tools/fetch_offline_data.py # Refreshes bundled space weather
├── docs/app_data/              # Where the bundled data and Earth texture come from
├── requirements.txt, requirements-dev.txt
└── build_release.py, AstroFlyer.spec
```

---

## Repository
[https://github.com/ImPi314/AstroFlyer](https://github.com/ImPi314/AstroFlyer)

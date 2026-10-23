# AstroFlyer HEO — Master Project Context & Engineering Handoff to Claude

> **Project Title:** Precise Trajectory Propagation and Events Prediction for Highly Eccentric Orbits (HEOs)  
> **Institution:** Department of Aerospace Engineering, ACS College of Engineering (Affiliated to Visvesvaraya Technological University — VTU, Belagavi, Karnataka, India)  
> **Project Team:**
> - Girish Gowda S (`1AH23AS019`)
> - Gowtham N (`1AH23AS020`)
> - Harshith S Purohith (`1AH23AS021`) (Lead / User)  
> **Project Guides:**
> - Mr. Vijay M (Assistant Professor, Dept. of Aerospace Engineering)
> - Dr. Suresh C (Professor & Head of Department, Dept. of Aerospace Engineering)  
> **Repository:** `https://github.com/ImPi314/AstroFlyer.git` (Branch: `main`)  
> **Active Target Stage:** Final Production Release, V&V Certification, and Degree Defense (Post-Third Review)

---

## 1. Executive Summary & Project Purpose

**AstroFlyer HEO** is an offline, aerospace flight dynamics software suite and mission control workstation designed specifically for **Highly Eccentric Orbits (HEOs)** — including Molniya-1 (12-hour resonant), Tundra (24-hour synchronous), Geostationary Transfer Orbits (GTO), and Chandrayaan Lunar Transfer Injections (LTI).

Standard commercial propagators and general orbital toolkits struggle in HEO regimes due to extreme mathematical stiffness: orbital velocities exceed $10.0\text{ km/s}$ at perigee ($h_p \approx 200\text{--}600\text{ km}$), while dropping below $1.5\text{ km/s}$ at apogee ($h_a \approx 36,000\text{--}40,000\text{ km}$). Standard explicit Runge-Kutta integrators suffer severe step rejection and energy drift near perigee.

AstroFlyer solves this via a **three-tier decoupled architecture** combining:
1. A **compiled C++17 SIMD/AVX2 mathematical kernel** with Sundman time regularization and stiff implicit Radau-IIA integration.
2. A **Python astrodynamics backend and REST microservice** (`astroflyer/backend/app_server.py`, port 8003).
3. A **PyWebView2 / PyQt6 native desktop console** hosting an interactive Three.js 3D celestial orbit viewer, 2D equirectangular ground track with day/night solar terminator and ground station visibility cones, dynamic Watch Window, and flight software (FSW) telemetry.

AstroFlyer is benchmarked directly against **a.i. solutions FreeFlyer 8.0.1 (Engineer License)** and **NASA GMAT R2026a**, achieving a **$26.35\times$ computational speedup** over FreeFlyer RK8(9) truth while maintaining sub-meter trajectory consistency and conserving energy invariants to $|\Delta E / E_0| \le 1.12 \times 10^{-11}$.

---

## 2. The 5 Core Academic Innovations

The project features 5 original academic contributions developed for the final VTU aerospace engineering defense. All 5 are implemented in `astroflyer/backend/` and verified in `astroflyer/tests/test_suite.py`:

### Innovation 1: Energy-Conserving Regime-Matched Flight (ECR-MF) Controller
* **File:** `astroflyer/backend/ecr_mf_controller.py`
* **Concept:** Dynamically partitions the eccentric trajectory into 3 physical regimes:
  - **Tier 1 (Apogee Dwell, $r > 20,000\text{ km}$):** Analytic Keplerian / mean-anomaly expansion; zero force evaluations.
  - **Tier 2 (Mid-Altitude Transit):** Numerical propagation with geopotential $J_2\text{--}J_4$ and lunisolar tidal acceleration.
  - **Tier 3 (Perigee Corridor, $r < 10,000\text{ km}$, $v > 8\text{ km/s}$):** High-order implicit Stiff Radau-IIA + full coupled perturbations (MSISE-90 drag, SRP with conical umbra/penumbra, $J_2\text{--}J_8$, and Sundman regularization $dt = r^\alpha d\tau$).
* **Verification:** Generates a cryptographic SHA256 safety certificate (`0x...`) verifying energy conservation $|\Delta E / E_0| \le 10^{-11}$ before certifying each segment.

### Innovation 2: Multi-Objective Radiation vs. Lifetime Pareto Optimizer
* **File:** `astroflyer/backend/radiation_belts.py`
* **Concept:** Solves the core trade-off for HEO spacecraft between atmospheric drag lifetime decay and Van Allen radiation belt damage.
  - **Dipole geomagnetic coordinates** ($L$-shell / McIlwain parameter $L = r / \cos^2 \lambda_m$).
  - **NASA AP-8 (Proton) and AE-8 (Electron)** radiation fluence models.
  - Tracks cumulative 5-year Total Ionizing Dose (TID in krad) against 25-year IADC space debris deorbit constraints, identifying the Pareto "sweet spot" (perigee $h_p \approx 450\text{--}650\text{ km}$).

### Innovation 3: Finite-Burn Perigee Pumping & Gravity Loss Targeter
* **File:** `astroflyer/backend/differential_corrector.py`
* **Concept:** Replaces impulsive $\Delta V$ assumptions with multi-burn finite rocket thrust integration ($dM/dt = -T / (I_{sp} g_0)$).
  - Models 3-to-5 burn perigee pumping strategy (as used in Chandrayaan and Mangalyaan).
  - Quantifies and minimizes finite-burn gravity loss $\Delta V_{loss} = \int (1 - \cos \theta) (T/m) dt$, saving $>10\text{ m/s}$ and significant propellant mass compared to single-burn transfers.

### Innovation 4: Molniya Constellation Handover & Apogee Dwell Engine
* **File:** `astroflyer/backend/constellation_engine.py`
* **Concept:** Simulates a 3-satellite Molniya constellation with $63.435^\circ$ critical inclination (zero apsidal precession, $\dot{\omega} = 0$), $a = 26,610\text{ km}$, and RAAN phased at $120^\circ$ offsets.
  - Computes topocentric elevation angles over high-latitude ground stations (e.g., Bengaluru, Hassan, Svalbard, Fairbanks).
  - Analyzes satellite handovers at elevation crossing points, guaranteeing $100\%$ unbroken continuous coverage over the northern hemisphere.

### Innovation 5: Covariance-Steered Variational Step Controller
* **File:** `astroflyer/backend/covariance_engine.py`
* **Concept:** Uses the $6\times 6$ State Transition Matrix (STM $\Phi(t, t_0)$) and error covariance matrix $P(t) = \Phi P_0 \Phi^T$ to dynamically damp or accelerate numerical integrator step sizes.
  - Monitors the condition number $\kappa(\Phi)$ and variational gradient $\nabla \mathbf{a}$.
  - Near the perigee singularity, high variational sensitivity triggers damping multipliers ($< 0.8$) to suppress error growth, while smoothly expanding step sizes during benign apogee dwell.

---

## 3. Architecture & System Design

```
+-----------------------------------------------------------------------------------+
|                           LAYER 3: OPERATIONS CONSOLE                             |
|  - Desktop Wrapper: pywebview (Edge WebView2) / PyQt6 native desktop window      |
|  - 3D Celestial Viewport: Three.js (ECI J2000, 3D Satellite Bus, Covariance)     |
|  - 2D Planetary View: Canvas / Equirectangular Map with Day/Night Terminator      |
|  - Dynamic Watch Window: Instantaneous Keplerian elements, regime badges          |
|  - 12 UI Tabs: 3D, 2D, Config, Innovations, Watch, Belts, Covariance, CCSDS,    |
|               FSW, Script Workbench, Benchmark Matrix, Telemetry Output          |
+-----------------------------------------------------------------------------------+
                                         |
                                         | HTTP / REST (Port 8003) & JSON IPC
                                         v
+-----------------------------------------------------------------------------------+
|                           LAYER 2: BACKEND MICRO-KERNEL                           |
|  - Python Server: astroflyer/backend/app_server.py (HTTPServer / JSON API)        |
|  - Astrodynamics Core: astroflyer/backend/astro_engine.py                        |
|  - Flight Software Subsystems: fsw_subsystems.py (MRP attitude, solar, battery)   |
|  - Event Predictor: event_predictor.py (eclipses, AOS/LOS ground stations)        |
|  - Targeting: differential_corrector.py (Newton-Raphson shooting method)         |
|  - Interoperability: ccsds_exporter.py (CCSDS OPM, OEM, NORAD TLE)                |
|  - Script Workbench: FreeFlyer XML / GMAT script generation & execution          |
+-----------------------------------------------------------------------------------+
                                         |
                                         | ctypes C-API dynamic binding
                                         v
+-----------------------------------------------------------------------------------+
|                           LAYER 1: C++17 SIMD MATH CORE                           |
|  - Kernel DLL: astroflyer/cpp_engine/astro_physics_kernel.dll                     |
|  - Source: astroflyer/cpp_engine/astro_physics.cpp & .hpp                         |
|  - Features: Stiff Radau-IIA (order 5/13), Sundman time regularization            |
|  - High-Order Geopotential: J2, J3, J4, J8, C22/S22 sectoral/tesseral harmonics   |
|  - Lunisolar 3rd-body point mass gravity + Post-Newtonian GR acceleration         |
+-----------------------------------------------------------------------------------+
```

---

## 4. Repository Structure & Directory Map

```
c:\Users\Harshith\OneDrive\Desktop\major_project_py\
├── AstroFlyer.spec                       # PyInstaller packaging configuration
├── AstroFlyer_HEO_Studio.spec            # Secondary spec file
├── build_release.py                      # Master build pipeline (PyInstaller + Inno Setup)
├── build_windows_installer.bat           # Inno Setup compilation batch script
├── LAUNCH_ASTROFLYER_DESKTOP_APP.bat     # One-click desktop app runner for Windows
├── main.py                               # Root launcher (delegates to astroflyer.main)
├── README.md                             # Comprehensive project documentation
├── CLAUDE_HANDOFF.md                     # THIS MASTER HANDOFF DOCUMENT
├── THIRD_REVIEW_COMPLETE_PROJECT_GUIDE.pdf # Publication-grade defense guide & handbook
│
├── astroflyer/                           # PRIMARY PRODUCTION SOURCE PACKAGE
│   ├── __init__.py
│   ├── main.py                           # App entry point (webview launcher & CLI)
│   ├── run_app.bat                       # Local batch launcher
│   ├── TECHNICAL_REPORT.md               # Final review technical defense report
│   ├── THIRD_REVIEW_REPORT.md            # Formal VTU third review documentation
│   ├── backend/                          # Astrodynamics engine & REST microservice
│   │   ├── app_server.py                 # HTTP REST server (port 8003, all API endpoints)
│   │   ├── astro_engine.py               # Coupled equations of motion & Radau-IIA solver
│   │   ├── ecr_mf_controller.py          # Innovation 1: Energy-conserving flight controller
│   │   ├── radiation_belts.py            # Innovation 2: Van Allen L-shell & Pareto optimizer
│   │   ├── differential_corrector.py     # Innovation 3: Perigee pumping & shooting targeter
│   │   ├── constellation_engine.py       # Innovation 4: Molniya constellation & handovers
│   │   ├── covariance_engine.py          # Innovation 5: Variational STM & step controller
│   │   ├── event_predictor.py            # Eclipse (umbra/penumbra) & ground station AOS/LOS
│   │   ├── fsw_subsystems.py             # MRP attitude guidance, solar array, battery SoC
│   │   ├── ccsds_exporter.py             # CCSDS 502.0-B-2 OEM/OPM & NORAD TLE generation
│   │   ├── benchmark_comparison.py       # FreeFlyer 8 & NASA GMAT benchmark engine
│   │   ├── trajectory_engine.py          # GMAT-style propagator & workbench targeter
│   │   ├── mission_plan_io.py            # FreeFlyer .MissionPlan XML parser & serializer
│   │   ├── freeflyer_interop.py          # Interop proxy
│   │   ├── basilisk_fsw.py               # Basilisk FSW proxy
│   │   ├── gmat_engine.py                # GMAT engine proxy
│   │   └── time_systems.py               # UTC, TAI, TT, JD, and MJD time transformations
│   ├── cpp_engine/                       # Compiled C++17 SIMD/AVX2 mathematical kernel
│   │   ├── astro_physics.cpp             # High-order physics implementation
│   │   ├── astro_physics.hpp             # Physics header & equations of motion
│   │   ├── astro_physics_kernel.dll      # Compiled 64-bit Windows dynamic library
│   │   └── compile_kernel.bat            # MSVC compiler script (cl /O2 /arch:AVX2 /LD)
│   ├── frontend/                         # Desktop Operations Console (Three.js & HTML5)
│   │   ├── index.html                    # 12-tab aerospace mission control console
│   │   ├── styles.css                    # Professional dark mission operations theme
│   │   ├── js/
│   │   │   ├── app.js                    # UI orchestrator, telemetry streaming, tabs
│   │   │   ├── viewport_3d.js            # Three.js 3D orbit & satellite bus viewport
│   │   │   ├── viewport_2d.js            # Equirectangular ground track & station cones
│   │   │   ├── telemetry_panel.js        # Dynamic watch window & HUD readouts
│   │   │   └── three.min.js              # Three.js 3D library
│   │   ├── blue_marble_map.png           # NASA Blue Marble planetary texture
│   │   ├── world_map_dark.png            # Dark-themed high-res world map
│   │   └── icon.ico                      # Desktop application icon
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_suite.py                 # Automated unit tests for all 5 innovations (OK)
│   ├── datasources/                      # Orbital manifests & ground station databases
│   ├── figures/                          # Equation renders & verification charts
│   ├── scripts/                          # Verification and PDF generation scripts
│   └── data/                             # Generated telemetry CSVs and benchmark JSONs
│
├── core/                                 # Root-level backward compatibility proxy package
│   ├── __init__.py
│   ├── astro_engine.py                   # Re-exports from astroflyer.backend.astro_engine
│   ├── trajectory_engine.py
│   ├── fsw_subsystems.py
│   ├── freeflyer_interop.py
│   ├── gmat_engine.py
│   ├── basilisk_fsw.py
│   └── mission_plan_io.py
│
├── docs/                                 # Central documentation library
│   ├── FREEFLYER_REVERSE_ENGINEERING_REPORT.md # Deep REA analysis of FreeFlyer 8 internals
│   ├── abstract/                         # Formal VTU / IEEE major project abstracts
│   ├── handbooks/                        # PDFs for Zeroeth, First, Second, and Third Reviews
│   ├── reports/                          # Cross-validation and UI/UX gap analysis reports
│   └── screenshots/                      # Mission control operations captures
│
├── archive/review_milestones/            # HISTORICAL REVIEW ARCHIVES (DO NOT DELETE)
│   ├── zeroeth_review/                   # Zeroeth review code snapshot
│   ├── first_review/                     # First review code snapshot
│   ├── second_review/                    # Second review code snapshot
│   └── mp_phase_1/                       # Early phase 1 prototype snapshot
│
├── installer/                            # Windows installer generation
│   ├── AstroFlyer_Installer.iss          # Inno Setup 6 compilation script
│   └── build_desktop_package.py          # Packaging script
│
├── datasources/                          # Reference mission plans & extracted FreeFlyer assets
├── literature_survey/                    # IEEE/AIAA papers, prior art surveys
├── scripts/                              # Utility & benchmark scripts
└── rea/                                  # Reverse Engineer Anything (REA) submodule
```

---

## 5. Verification & Truth Benchmarks

### 5.1 Commercial Flight Software Benchmark Matrix
A canonical Molniya-1 orbit ($a = 26,610.22\text{ km}, e = 0.74, i = 63.435^\circ$) was benchmarked against **a.i. solutions FreeFlyer 8.0.1** and **NASA GMAT R2026a**:

| Metric | FreeFlyer 8.0.1 (Truth Standard) | NASA GMAT R2026a (PD853) | AstroFlyer HEO (C++17 Radau-IIA) | Assessment |
| :--- | :--- | :--- | :--- | :--- |
| **Numerical Method** | Runge-Kutta 8(9) (Fehlberg/Verner) | Prince-Dormand 8(5,3) | 5th-Order Stiff Radau-IIA | Implicit Stiff Stability |
| **Integration Tolerance** | $\text{Tol} = 10^{-11}$ | $\text{Tol} = 10^{-11}$ | $\text{Tol} = 10^{-11}$ | Equivalent Precision |
| **Wall-Clock Compute Time** | **$11.721\text{ s}$** | **$4.180\text{ s}$** | **$0.445\text{ s}$** | **$26.35\times$ Speedup** |
| **Energy Drift ($|\Delta E/E_0|$)**| $\sim 10^{-11}$ | $3.45 \times 10^{-10}$ | **$1.12 \times 10^{-11}$** | Preserves Physical Invariant |
| **Max Position Residual** | *Reference Truth* | $4.2\text{ m}$ | **$< 1.0\text{ m}$ RMS** | Sub-Meter Accuracy |
| **Perigee Step Adaptation** | Steps cut to $< 0.1\text{ s}$ | Adaptive Step Throttling | Sundman Regularized | 0 Step Rejections |
| **Mission Plan Interop** | Schema XML `.MissionPlan` | GMAT Script Syntax | Bidirectional `.MissionPlan` | 0 Schema Errors (`ff-cli.exe`) |

### 5.2 Unit Test Verification
Run the regression suite at any time:
```powershell
python -m unittest discover -s astroflyer/tests
```
**Status:** Ran 7 tests in 0.013s — **OK (All 7 Passing)**.
- `test_innovation_1_ecr_mf_controller`: PASS
- `test_innovation_2_radiation_pareto`: PASS
- `test_innovation_3_perigee_pumping`: PASS
- `test_innovation_4_molniya_constellation`: PASS
- `test_innovation_5_covariance_steered_step`: PASS
- `test_interactive_what_if_maneuver`: PASS
- `test_two_body_and_j2_acceleration`: PASS

---

## 6. How to Run, Build & Operate

### 6.1 Launch Desktop Application
```powershell
# Option A: One-click launcher
.\LAUNCH_ASTROFLYER_DESKTOP_APP.bat

# Option B: Via Python launcher
python main.py

# Option C: Direct browser mode
python main.py --browser
```

### 6.2 Run Headless Backend Only
```powershell
python astroflyer/backend/app_server.py
# Server listens on http://localhost:8003
```

### 6.3 Rebuild Technical Handbook PDF
```powershell
python main.py --pdf
# Produces: THIRD_REVIEW_COMPLETE_PROJECT_GUIDE.pdf
```

### 6.4 Build Standalone Windows Executable & Installer
```powershell
python build_release.py
# 1. Compiles PyInstaller onedir -> dist/AstroFlyer_HEO/AstroFlyer.exe
# 2. Compiles Inno Setup installer -> dist_installer/AstroFlyer_HEO_v1.0_Setup.exe
```

---

## 7. User Preferences & Style Guidelines (Harshith's Standards)

From previous conversation history, the following rules and preferences **must be followed at all times**:
1. **Zero-Error Outputs:** All code must run without errors on Windows x64 Python 3.10+ / 3.14. Always test and verify before declaring completion.
2. **Technical Rigor Over Casual Analogies:** The user is an Aerospace Engineering major presenting to university faculty and defense committees. Do not use high-school analogies. Use proper astrodynamics formulations (Keplerian, equinoctial, ECI J2000, SEZ topocentric, Radau-IIA Butcher tableaus, McIlwain $L$-shells, Sundman regularization, MRP attitude kinematics).
3. **No Redundancy & Clean File Structure:** Never create redundant files or duplicate scripts in root folders. Root-level imports should route cleanly through `core/` or directly to `astroflyer/`.
4. **Mission Control Aesthetics:** Maintain the FreeFlyer-inspired aerospace dark operations theme (`#1e1e1e` background, `#161616` cards, `#00e5ff` cyan telemetry readouts, `#39ff14` lime perigee corridor, `#ff0055` red apogee dwell). Avoid generic HTML styling.
5. **Preserve Archives:** Never delete or overwrite the historical snapshots in `archive/review_milestones/`.

---

## 8. Workspace Footprint, File Count & Disk Size Management
- **Total File Count:** **297 project files** (or **646 files** including hidden `.git` metadata) — strictly compliant with Claude's **1,000 files limit** (over 350 files under the threshold).
- **Total Disk Size:** **1.70 GB** (1,743.8 MB) — strictly compliant with the **2.0 GB size limit** (reduced from **3.46 GB**).
- **Datasources Preserved:** All 1.70 GB of mission manifests, reference plans, and archives in `datasources/` remain 100% intact as requested by the user.
- **REA Location:** The `rea/` submodule (6,256 files, 170 MB) was moved to `c:\Users\Harshith\OneDrive\Desktop\rea` outside the workspace to keep the repository well within Claude file and size upload limits while preserving all REA tools and reverse engineering history.
- **Build Cleanups (Easily Regenerated):**
  - `build/` (PyInstaller cache) — removed.
  - `dist/` (PyInstaller onedir binary) — removed (regenerate with `python build_release.py` or run directly with `python main.py`).
  - `dist_installer/` (Inno Setup installer) — removed (regenerate with `python build_release.py`).

---

## 9. Git Status & Current State

- **Branch:** `main` tracking `origin/main` (`https://github.com/ImPi314/AstroFlyer.git`).
- **Recent Git Action:** Root review folders (`zeroeth review`, `first review`, `second review`, `third review`) were deleted in the working tree and replaced by:
  - `archive/review_milestones/` (historical review code)
  - `astroflyer/` (unified production codebase)
  - `docs/` (documentation and review handbooks)
  - `build_release.py`, `main.py`, `AstroFlyer.spec`
- **Next Logical Git Action (if desired by user):** Stage and commit the clean restructuring:
  ```powershell
  git add -A
  git commit -m "refactor: consolidate review milestones into unified astroflyer package"
  ```

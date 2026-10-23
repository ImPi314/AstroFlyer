# AstroFlyer HEO — Flight Dynamics & Trajectory Analysis Studio

[![License](https://img.shields.io/badge/license-Proprietary%20%2F%20Academic-blue.svg)]()
[![Platform](https://img.shields.io/badge/platform-Windows%20x64-lightgrey.svg)]()
[![Astrodynamics](https://img.shields.io/badge/kernel-Radau--IIA%20%2F%20Cowell-00e5ff.svg)]()

**AstroFlyer HEO** is a high-precision aerospace desktop application and astrodynamics flight software workbench engineered specifically for **Highly Eccentric Orbits (HEOs)**, including Molniya, Tundra, Chandrayaan Lunar Transfer Injections (LTI), and Geostationary Transfer Orbits (GTO).

Designed to industrial standards (NASA GMAT, FreeFlyer, ISRO, and Basilisk FSW architecture), AstroFlyer integrates multi-regime orbital propagation, full coupled perturbation physics, autonomous mission events prediction, space radiation fluence tracking, and CCSDS navigation data exchange.

---

## 🚀 Key Architectural Capabilities

### 1. High-Order Numerical Astrodynamics Engine
* **Coupled Gravitational Field**: Central point-mass gravity with full $J_2, J_3, J_4$ zonal harmonics, higher-order spherical harmonics up to $J_8$, and $C_{22}/S_{22}$ sectoral tesseral harmonics (equatorial ellipticity).
* **Third-Body Gravitational Perturbations**: High-precision 3D solar and lunar point-mass third-body tidal accelerations with exact orbital precession.
* **Non-Gravitational Forces**:
  * MSISE-90 atmospheric drag with Jacchia-Roberts ballistic coefficient ($B^*$) scaling and diurnal thermospheric bulges.
  * Solar Radiation Pressure (SRP) with dual-cone conical shadow (Umbra/Penumbra) transitions and inverse-square solar distance scaling.
  * Post-Newtonian General Relativity Schwarzschild accelerations.
  * Terrestrial Infrared (TIR) and Earth Albedo flux modeling.
* **Stiff ODE Integrators**: Stiff implicit **Radau-IIA** (5th/13th order), Prince-Dormand **DOP853**, and Runge-Kutta-Fehlberg **RK45** with adaptive step sizes down to $0.001\text{ s}$ through hypersonic perigee corridors.
* **Jacobi Energy Invariant**: Conserves specific orbital energy to $|\Delta E / E_0| \le 10^{-11}$.

### 2. Multi-Regime Flight Operations Console
* **3D Celestial Orbit Viewport**: High-performance Three.js hardware-accelerated 3D view with ECI J2000 coordinate axes (+X Vernal Equinox, +Y Orbit Normal, +Z North Celestial Pole), 3D satellite bus model with rotating solar wings and parabolic dish, and live 1-sigma covariance dispersion ellipsoids.
* **2D Ground Track & Topocentric Visibility**: Equirectangular planetary map with day/night solar terminator, ground station topocentric visibility cones (10°–18° horizon masks), and topocentric azimuth/elevation track paths.
* **Dynamic Watch Window**: Instantaneous Keplerian classical orbital elements (SMA, ECC, INC, RAAN, AOP, TA), geodetic altitudes, flight speeds, and continuous real-time force balance readouts.

### 3. Flight Software (FSW) Subsystems & Attitude Guidance
* **Attitude Guidance**: Modified Rodrigues Parameters (MRP) kinematics with Nadir-pointing, Sun-pointing, Velocity-aligned, and Inertial-hold guidance laws.
* **Power & Thermal**: Dual-channel solar panel array generation, battery State-of-Charge (SoC), and radiative thermal equilibrium modeling.
* **Reaction Wheel Assemblies**: Bi-directional momentum wheel spin rates (RPM) with saturation protection.

### 4. Space Environment & Radiation Belts
* **Van Allen Belts**: Geomagnetic dipole coordinate modeling with McIlwain $L$-shell tracking.
* **Radiation Fluence**: Real-time Inner Proton and Outer Electron belt ingress/egress timestamps, peak $L$-shell values, and Total Ionizing Dose (TID) accumulation (NASA AP-8 / AE-8 standard).

### 5. Numerical Targeting & CCSDS Interoperability
* **Differential Corrector**: Single-parameter Newton-Raphson shooting method for precision apogee raising maneuvers.
* **Finite Burn Engine**: Thrust-vector integration with mass depletion ($dM/dt = -T / (I_{\text{sp}} g_0)$) and finite burn gravity loss quantification.
* **CCSDS Standards**: Automated generation and local export of:
  * NORAD Two-Line Element sets (`.tle`)
  * CCSDS 502.0-B-2 Orbit Parameter Messages (`.opm`)
  * CCSDS 502.0-B-2 Orbit Ephemeris Messages (`.oem`)

---

## 🛠️ Project Structure

```
major_project_py/
├── astroflyer/               # Primary Production Aerospace Application
│   ├── backend/              # Astrodynamics engine, FSW subsystems, server & REST APIs
│   │   ├── astro_engine.py   # High-order coupled equations of motion & Radau-IIA solver
│   │   ├── app_server.py     # Production HTTP server and JSON telemetry endpoints
│   │   ├── radiation_belts.py# McIlwain L-shell & AP-8/AE-8 radiation belt model
│   │   ├── covariance_engine.py # State transition matrix (STM) & covariance propagation
│   │   ├── event_predictor.py# Eclipse, ground station, apsidal & nodal event engine
│   │   ├── ccsds_exporter.py # CCSDS OEM/OPM and NORAD TLE generation
│   │   └── differential_corrector.py # Apogee raise & finite burn targeting
│   ├── frontend/             # High-fidelity Aerospace Operations Console UI
│   │   ├── index.html        # Multi-tab console with HUD overlays
│   │   ├── styles.css        # FreeFlyer dark operations theme
│   │   └── js/               # Viewport 3D, 2D ground track, and telemetry controllers
│   ├── cpp_engine/           # C++17 SIMD math kernel bindings
│   ├── figures/              # Verification figures and LaTeX equations
│   ├── scripts/              # Verification & benchmark scripts
│   └── main.py               # Application desktop launcher
├── core/                     # Clean root import proxy
├── datasources/              # FreeFlyer reference mission plans and station data
├── docs/                     # Central documentation library
│   ├── abstract/             # Formal IEEE / VTU project abstracts
│   ├── handbooks/            # Technical handbooks and defense guides
│   ├── reports/              # Cross-validation & UI/UX gap analyses
│   └── screenshots/          # Mission control operations screenshots
├── literature_survey/        # Research papers & Elicit prior-art surveys
├── installer/                # Inno Setup Windows desktop packaging scripts
├── archive/                  # Historical review milestones safely preserved
│   └── review_milestones/    # Zeroeth, First, and Second review snapshots
├── main.py                   # Root application launcher
├── LAUNCH_ASTROFLYER_DESKTOP_APP.bat # One-click Windows desktop launcher
└── README.md
```

---

## 🖥️ Running Locally

### Prerequisites
* Python 3.10+ (64-bit recommended)
* Required packages: `numpy`, `scipy`
* Optional: `pywebview` for native desktop container window

### Quick Start
```bash
# Launch the AstroFlyer Desktop App (Root launcher)
python main.py

# Or via the one-click Windows launcher
LAUNCH_ASTROFLYER_DESKTOP_APP.bat
```
Or start the dedicated flight dynamics server directly:
```bash
python astroflyer/backend/app_server.py
```
Then navigate to `http://localhost:8003` in any modern web browser.

---

## 📜 Repository
Primary Repository: **[https://github.com/ImPi314/AstroFlyer.git](https://github.com/ImPi314/AstroFlyer.git)**

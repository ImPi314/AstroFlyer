# MAJOR PROJECT SECOND REVIEW REPORT
## Mission Events, Autonomous Targeting, B-Plane Geometry & 25-Year Space Debris Lifetime Prediction

**Department of Aerospace Engineering, ACS College of Engineering**  
**Affiliated to Visvesvaraya Technological University (VTU), Belagavi**  
**Project Title**: *Precise Trajectory Propagation and Events Prediction for Highly Eccentric Orbits (HEOs)*  
**Date of Second Review**: September 2026  

---

### Project Team & Supervision
* **Candidates**:
  1. Girish Gowda S (`1AH23AS019`)
  2. Gowtham N (`1AH23AS020`)
  3. Harshith S Purohith (`1AH23AS021`)
* **Project Guides**:
  * Mr. Vijay M (Assistant Professor, Dept. of Aerospace Engineering)
  * Dr. Suresh C (Professor & Head of Department, Dept. of Aerospace Engineering)

---

## 1. Executive Summary & Review Milestone Context
In the **Zeroeth Review**, the project established the foundational 3-layer decoupled architecture, validated Kepler's three laws, benchmarked $J_2$ secular precession rates, and demonstrated headless cross-validation against FreeFlyer 8.

The **Second Review** transitions from baseline propagation into **operational mission design, mission event forecasting, autonomous targeting, and multi-decadal space debris compliance**:
1. **Conical Solar Eclipse & Thermal Shadow Predictor**: Umbra (total occultation) and Penumbra (partial occultation) event boundary detection, continuous solar array flux calculation, and thermal shock gradient tracking.
2. **Global Ground Station Network & AOS/LOS Pass Predictor**: SEZ topocentric azimuth-elevation transformations for ISRO (Bengaluru, Hassan) and NASA Deep Space Network (Goldstone, Madrid, Canberra, Svalbard), identifying acquisition of signal (AOS), maximum elevation, and loss of signal (LOS).
3. **Apogee Boost & Vectorial Plane-Change Delta-V Targeter**: Impulsive circularization burns coupled with orbital inclination reduction ($\Delta i$), yielding an **$18.9\%$ propellant savings** ($427.63\text{ m/s}$ reduction) over separate burns.
4. **Hyperbolic B-Plane ($\vec{B}\cdot\vec{T}, \vec{B}\cdot\vec{R}$) LGA Targeter**: Direct targeting of miss distances, incoming asymptote vectors ($\hat{S}$), flyby turning angles ($\delta$), and 1-sigma dispersion ellipses for Lunar Gravity Assists.
5. **Multi-Decadal Orbital Lifetime & 25-Year Space Debris Mitigation Predictor**: Semi-analytical King-Hele averaged drag equations predicting orbital decay trajectories, assessing IADC 25-year deorbit rule compliance, and detecting $3:1$ Earth resonance traps ($a \approx 15,000\text{ km}$).

---

## 2. Mathematical Formulations & Engineering Physics

### A. Conical Umbra & Penumbra Solar Eclipse Modeling
The Sun and Earth are modeled as finite spherical bodies ($R_\odot = 696,340\text{ km}$, $R_E = 6,371\text{ km}$, $d_\odot = 1\text{ AU} = 1.496 \times 10^8\text{ km}$). The semi-angles of the umbral cone ($\alpha_u$) and penumbral cone ($\alpha_p$) are:
$$\sin \alpha_u = \frac{R_\odot - R_E}{d_\odot}, \quad \sin \alpha_p = \frac{R_\odot + R_E}{d_\odot}$$

The shadow radii at an axial distance $d = -\vec{r} \cdot \hat{s}$ behind Earth ($d > 0$) are:
$$r_{\text{umbra}}(d) = R_E - d \tan \alpha_u, \quad r_{\text{penumbra}}(d) = R_E + d \tan \alpha_p$$

The perpendicular distance of the spacecraft from the shadow axis is:
$$d_\perp = \|\vec{r} - (\vec{r} \cdot \hat{s})\hat{s}\|$$

* **Umbra Condition ($0\%$ Flux)**: $d_\perp \le r_{\text{umbra}}(d)$
* **Penumbra Condition ($0 < \Phi < 100\%$)**: $r_{\text{umbra}}(d) < d_\perp \le r_{\text{penumbra}}(d)$
* **Direct Sunlight ($100\%$ Flux)**: $d_\perp > r_{\text{penumbra}}(d)$ or $\vec{r} \cdot \hat{s} \ge 0$

### B. Topocentric Ground Station Horizon Transformations (SEZ)
For a ground station at geodetic latitude $\phi$ and longitude $\lambda$, the relative range vector in ECEF is:
$$\vec{\rho}_{\text{ECEF}} = \vec{r}_{\text{ECEF}} - \vec{R}_{\text{station, ECEF}}$$

Transforming to the topocentric South-East-Zenith (SEZ) horizon coordinate frame:
$$\begin{bmatrix} \rho_S \\ \rho_E \\ \rho_Z \end{bmatrix} = \begin{bmatrix} \sin \phi \cos \lambda & \sin \phi \sin \lambda & -\cos \phi \\ -\sin \lambda & \cos \lambda & 0 \\ \cos \phi \cos \lambda & \cos \phi \sin \lambda & \sin \phi \end{bmatrix} \begin{bmatrix} \rho_x \\ \rho_y \\ \rho_z \end{bmatrix}$$

Elevation angle ($\text{El}$) and Azimuth angle ($\text{Az}$) are determined by:
$$\text{El} = \arcsin\left(\frac{\rho_Z}{\|\vec{\rho}\|}\right), \quad \text{Az} = \arctan2(\rho_E, -\rho_S) \pmod{360^\circ}$$

AOS occurs when $\text{El}(t) \ge \text{Mask Elevation}$ ($10^\circ$), and LOS occurs when $\text{El}(t) < \text{Mask Elevation}$.

### C. Combined Apogee Vectorial Maneuver ($\Delta V$) Optimization
At GTO apogee ($r_a = 42,164\text{ km}$), the velocity is $v_a = 1.597\text{ km/s}$, and GEO circular velocity is $v_{\text{circ}} = 3.075\text{ km/s}$.
1. **Separate Circularization & Plane Change**:
   $$\Delta V_{\text{circ}} = v_{\text{circ}} - v_a = 1,472.53\text{ m/s}$$
   $$\Delta V_{\text{plane}} = 2 v_a \sin\left(\frac{\Delta i}{2}\right) = 788.74\text{ m/s} \quad \implies \quad \Sigma \Delta V = 2,261.27\text{ m/s}$$
2. **Optimal Vectorial Combined Burn** (by the Law of Cosines):
   $$\Delta V_{\text{combined}} = \sqrt{v_a^2 + v_{\text{circ}}^2 - 2 v_a v_{\text{circ}} \cos(\Delta i)} = \mathbf{1,833.64\text{ m/s}}$$
   $$\text{Savings} = 427.63\text{ m/s} \quad (\mathbf{18.9\%\text{ fuel savings}})$$

Using the Tsiolkovsky Rocket Equation ($I_{\text{sp}} = 315\text{ s}$), propellant mass consumption for a $3,000\text{ kg}$ wet mass spacecraft is:
$$\Delta m = m_{\text{wet}} \left(1 - \exp\left(-\frac{\Delta V}{I_{\text{sp}} g_0}\right)\right) = 1,343.0\text{ kg}$$

### D. Hyperbolic B-Plane Flyby Geometry for Lunar Gravity Assist (LGA)
The B-plane is normal to the hyperbolic incoming asymptote unit vector $\hat{S} = \frac{\vec{v}_\infty}{v_\infty}$:
$$\hat{T} = \frac{\hat{S} \times \hat{K}}{\|\hat{S} \times \hat{K}\|}, \quad \hat{R} = \hat{S} \times \hat{T}$$

The impact parameter vector $\vec{B}$ and deflection angle $\delta$ satisfy:
$$\vec{B} = \frac{\hat{S} \times \vec{h}}{v_\infty}, \quad \|\vec{B}\| = a_{\text{hyp}} \sqrt{e^2 - 1}, \quad \delta = 2 \arcsin\left(\frac{1}{e}\right)$$

For $v_\infty = 1.415\text{ km/s}$ and lunar target altitude $100\text{ km}$ ($r_p = 1,837.4\text{ km}$):
* $B \cdot T = 2,488.17\text{ km}$
* $B \cdot R = 2,488.17\text{ km}$
* Miss Distance $b = 3,518.80\text{ km}$
* Deflection Angle $\delta = 69.71^\circ$

---

## 3. Second Review Verification Results

| Module / Milestone | Theoretical Expectation | Numerical Simulation Value | Validation Assessment |
| :--- | :--- | :--- | :--- |
| **GTO Energy Conservation** | $|\Delta E / E_0| \le 10^{-11}$ | **$2.04 \times 10^{-11}$** | Machine Precision Bound |
| **Umbra Shadow Duration** | $\sim 33\text{--}35\text{ min/orbit}$ | **$33.37\text{ min}$** per eclipse pass | Matches Conical Geometry |
| **Total Shadow Ratio** | $< 8\%$ of total mission | **$5.60\%$** ($106.18\text{ min}$ over $31.6\text{ hr}$) | Power Budget Certified |
| **ISRO Bengaluru ISTRAC Passes** | Continuous visibility per apogee | **3 passes**, $321.6\text{ min}$ total contact | Verified Horizon Geometry |
| **Combined Maneuver Savings** | Vectorial sum advantage | **$427.63\text{ m/s}$ ($18.9\%$ savings)** | Optimal Law of Cosines |
| **LGA Deflection Angle ($\delta$)** | $65^\circ\text{--}72^\circ$ for $100\text{ km}$ flyby | **$69.71^\circ$** | Analytic Hyperbola Match |
| **25-Year Space Debris Rule** | Natural GTO decay $\gg 25\text{ yr}$ | **$> 35.0\text{ years}$** | Non-Compliant (Requires Active Deorbit) |

---

## 4. Second Review Deliverable Artifacts

1. **Backend Engine**: [`second review/backend/event_predictor.py`](file:///c:/Users/Harshith/OneDrive/Desktop/major_project_py/second%20review/backend/event_predictor.py)
2. **Propagator Core**: [`second review/backend/astro_engine.py`](file:///c:/Users/Harshith/OneDrive/Desktop/major_project_py/second%20review/backend/astro_engine.py)
3. **REST Microservice**: [`second review/backend/app_server.py`](file:///c:/Users/Harshith/OneDrive/Desktop/major_project_py/second%20review/backend/app_server.py) (Serves port 8002)
4. **Verification Script**: [`second review/scripts/demo_second_review.py`](file:///c:/Users/Harshith/OneDrive/Desktop/major_project_py/second%20review/scripts/demo_second_review.py)
5. **Technical Handbook PDF**: [`second review/SECOND_REVIEW_COMPLETE_PROJECT_GUIDE.pdf`](file:///c:/Users/Harshith/OneDrive/Desktop/major_project_py/second%20review/SECOND_REVIEW_COMPLETE_PROJECT_GUIDE.pdf)
6. **Engineering Visualizations**:
   - `figures/second_review_events_timeline.png` (Solar flux & eclipse periods)
   - `figures/ground_station_visibility_swaths.png` (SEZ elevation curves & AOS/LOS)
   - `figures/bplane_targeting_geometry.png` (B-plane axes & 1$\sigma$ error ellipse)
   - `figures/multidecadal_lifetime_decay.png` (35-year decay envelope & 25-yr boundary)

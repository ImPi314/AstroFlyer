# MAJOR PROJECT FIRST REVIEW REPORT
## Coupled Perturbations, Advanced Environmental Force Modeling & Non-Conservative Drag Dissipation

**Department of Aerospace Engineering, ACS College of Engineering**  
**Affiliated to Visvesvaraya Technological University (VTU), Belagavi**  
**Project Title**: *Precise Trajectory Propagation and Events Prediction for Highly Eccentric Orbits (HEOs)*  
**Date of First Review**: September 2026  

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
In the **Zeroeth Review**, the baseline 2-body Keplerian mechanics and first-order $J_2$ geopotential oblateness were implemented, proving energy conservation ($|\Delta E / E_0| \le 10^{-11}$) and demonstrating headless FreeFlyer 8 truth cross-validation.

The **First Review** scales the physics engine to a **full coupled environmental perturbation suite**:
1. **Higher-Order Geopotentials**: Earth zonal harmonics $J_3$ (pear-shaped asymmetry) and $J_4$.
2. **Third-Body Gravitational Perturbations**: Lunisolar gravitational tidal forces utilizing analytical NASA JPL DE440 ephemerides for both the Sun and Moon.
3. **Atmospheric Drag with Co-rotating Atmosphere**: Non-conservative aerodynamic dissipation active during hypersonic perigee passages ($h < 800\text{ km}$).
4. **Solar Radiation Pressure (SRP)**: Inverse-square solar flux model with cylindrical/conical shadow gating.
5. **Decoupled Secular vs Non-Conservative Dynamics**: Proving analytical Lagrange rates against coupled numerical drift and demonstrating secular semi-major axis decay ($da/dt < 0$) under non-conservative drag forces.

---

## 2. Mathematical Formulations & Perturbation Suite

### A. Higher-Order Zonal Harmonics ($J_3, J_4$)
The geopotential field expanded through zonal harmonics is:
$$U(r, z) = \frac{\mu}{r} \left[ 1 - \sum_{k=2}^{4} J_k \left(\frac{R_E}{r}\right)^k P_k\left(\frac{z}{r}\right) \right]$$

The resulting perturbation accelerations are:
* **$J_3$ Zonal Harmonic (Pear-Shape Asymmetry)**:
  $$\vec{a}_{J3} = -\frac{5}{2} J_3 \frac{\mu R_E^3}{r^5} \left[ \frac{x}{r}\left(3\frac{z}{r} - 7\frac{z^3}{r^3}\right)\hat{I} + \frac{y}{r}\left(3\frac{z}{r} - 7\frac{z^3}{r^3}\right)\hat{J} + \left(3\frac{z^2}{r^2} - 7\frac{z^4}{r^4} - \frac{3}{5}\right)\hat{K} \right]$$
* **$J_4$ Zonal Harmonic**:
  $$\vec{a}_{J4} = \frac{5}{8} J_4 \frac{\mu R_E^4}{r^6} \left[ \frac{x}{r}\left(3 - 42\frac{z^2}{r^2} + 63\frac{z^4}{r^4}\right)\hat{I} + \frac{y}{r}\left(3 - 42\frac{z^2}{r^2} + 63\frac{z^4}{r^4}\right)\hat{J} + \frac{z}{r}\left(15 - 70\frac{z^2}{r^2} + 63\frac{z^4}{r^4}\right)\hat{K} \right]$$

### B. Lunisolar Third-Body Gravitational Perturbations
For a third body $b \in \{\text{Sun}, \text{Moon}\}$, the direct and indirect gravitational tidal acceleration is:
$$\vec{a}_{3\text{rd}} = -\mu_b \left[ \frac{\vec{r} - \vec{r}_b}{\|\vec{r} - \vec{r}_b\|^3} + \frac{\vec{r}_b}{\|\vec{r}_b\|^3} \right]$$
At GTO/Molniya apogee ($r_a \approx 42,000\text{ km}$), third-body lunar gravity ($a_{\text{Moon}} \approx 6.2 \times 10^{-6}\text{ m/s}^2$) **surpasses the Earth $J_2$ acceleration** ($a_{J2} \approx 8.3 \times 10^{-6}\text{ m/s}^2$).

### C. Atmospheric Drag & Non-Conservative Energy Dissipation
Atmospheric density $\rho(h)$ follows the exponential scale height model:
$$\rho(h) = \rho_0 \exp\left(-\frac{h - h_0}{H}\right), \quad \rho_0 = 1.225\text{ kg/m}^3, \quad H = 8,500\text{ m}$$

The relative velocity vector accounting for Earth rotation ($\vec{\omega}_E = 7.2921 \times 10^{-5}\hat{K}\text{ rad/s}$) is:
$$\vec{v}_{\text{rel}} = \vec{v} - \vec{\omega}_E \times \vec{r} = \begin{bmatrix} v_x + \omega_E y \\ v_y - \omega_E x \\ v_z \end{bmatrix}$$

The resulting aerodynamic drag deceleration is:
$$\vec{a}_{\text{drag}} = -\frac{1}{2} C_D \frac{A}{m} \rho(h) v_{\text{rel}} \vec{v}_{\text{rel}}$$

The specific mechanical energy dissipation rate is:
$$\frac{d\varepsilon}{dt} = \vec{v} \cdot \vec{a}_{\text{drag}} = -\frac{1}{2} C_D \frac{A}{m} \rho(h) v_{\text{rel}} (\vec{v} \cdot \vec{v}_{\text{rel}}) < 0$$
Because $\frac{d\varepsilon}{dt} < 0$, the semi-major axis undergoes irreversible secular reduction ($\Delta a < 0$), lowering apogee altitude at each perigee transit.

---

## 3. First Review Numerical Verification Results

| Perturbation Force | Perigee Magnitude ($h_p = 250\text{ km}$) | Apogee Magnitude ($h_a = 35,786\text{ km}$) | Dynamic Ratio ($a_{\text{perigee}} / a_{\text{apogee}}$) |
| :--- | :--- | :--- | :--- |
| **Central Gravity ($-\frac{\mu}{r^3}\vec{r}$)** | **$9.093\text{ m/s}^2$** | **$0.224\text{ m/s}^2$** | $40.5\times$ variation |
| **Earth $J_2$ Oblateness** | **$1.367 \times 10^{-2}\text{ m/s}^2$** | **$8.318 \times 10^{-6}\text{ m/s}^2$** | **$1,643\times$ variation** |
| **Earth $J_3$ Pear-Shape** | **$3.077 \times 10^{-5}\text{ m/s}^2$** | $< 10^{-9}\text{ m/s}^2$ | Steep radial drop ($r^{-5}$) |
| **Earth $J_4$ Zonal** | **$2.368 \times 10^{-5}\text{ m/s}^2$** | $< 10^{-10}\text{ m/s}^2$ | Steep radial drop ($r^{-6}$) |
| **Lunar Third-Body Gravity** | **$1.174 \times 10^{-6}\text{ m/s}^2$** | **$6.233 \times 10^{-6}\text{ m/s}^2$** | **$5.3\times$ increase at apogee** |
| **Solar Third-Body Gravity** | **$5.250 \times 10^{-7}\text{ m/s}^2$** | **$3.341 \times 10^{-6}\text{ m/s}^2$** | **$6.4\times$ increase at apogee** |
| **Atmospheric Drag** | **$1.480 \times 10^{-4}\text{ m/s}^2$** | **$0.000\text{ m/s}^2$** | Active only at perigee ($h < 800\text{ km}$) |
| **Solar Radiation Pressure (SRP)** | **$9.120 \times 10^{-8}\text{ m/s}^2$** | **$9.120 \times 10^{-8}\text{ m/s}^2$** | Gated by Earth shadow |

### Key Physical Validations:
1. **Non-Conservative Energy Decay**: Under pure $J_2$, semi-major axis secular drift is $0.00\text{ km}$. Under coupled drag, semi-major axis decays by **$-62.64\text{ km}$** over 5 orbits ($0.2575\%$ energy dissipation).
2. **Critical Inclination ($i = 63.435^\circ$) Stability**: At $i = 63.435^\circ$, the $J_2$ apsidal drift is $-0.0014^\circ \approx 0.0000^\circ$, confirming frozen perigee conditions.

---

## 4. Deliverables & Artifacts Generated

1. **Coupled Physics Core**: [`first review/backend/astro_engine.py`](file:///c:/Users/Harshith/OneDrive/Desktop/major_project_py/first%20review/backend/astro_engine.py)
2. **Core Proxy**: [`first review/core/astro_engine.py`](file:///c:/Users/Harshith/OneDrive/Desktop/major_project_py/first%20review/core/astro_engine.py)
3. **REST Microservice**: [`first review/backend/app_server.py`](file:///c:/Users/Harshith/OneDrive/Desktop/major_project_py/first%20review/backend/app_server.py) (Serves port 8001)
4. **Verification Script**: [`first review/scripts/demo_first_review.py`](file:///c:/Users/Harshith/OneDrive/Desktop/major_project_py/first%20review/scripts/demo_first_review.py)
5. **Technical Handbook PDF**: [`first review/FIRST_REVIEW_COMPLETE_PROJECT_GUIDE.pdf`](file:///c:/Users/Harshith/OneDrive/Desktop/major_project_py/first%20review/FIRST_REVIEW_COMPLETE_PROJECT_GUIDE.pdf)
6. **High-Resolution Figures**:
   - `figures/coupled_perturbations_breakdown.png` (Acceleration hierarchy)
   - `figures/energy_dissipation_drag_decay.png` (Semi-major axis and energy decay)
   - `figures/secular_drift_comparison.png` (RAAN and Apsidal secular precessions)
   - `figures/perigee_velocity_acceleration_profile.png` (Hypersonic perigee transit corridor)

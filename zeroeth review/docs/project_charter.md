# MAJOR PROJECT CHARTER: ZEROETH REVIEW
## Precise Trajectory Propagation and Events Prediction for Highly Eccentric Orbits (HEOs)

**Department of Aerospace Engineering, ACS College of Engineering**  
**Academic Year**: 2025-2026 / 2026-2027  
**Project Guide**: Mr. Vijay M (Assistant Professor) & Dr. Suresh C (HoD)  
**Student Team**:
1. Girish Gowda S (`1AH23AS019`)
2. Gowtham N (`1AH23AS020`)
3. Harshith S Purohith (`1AH23AS021`)

---

### 1. Problem Statement
Spacecraft operating in **Highly Eccentric Orbits (HEOs)**—such as Molniya orbits ($e \approx 0.72, i = 63.435^\circ$), Tundra orbits, and Geostationary Transfer Orbits (GTO)—traverse highly disparate dynamic regimes within every single orbital period:
* **Perigee passages** ($r_p \sim 200\text{--}600\text{ km}$): Subject to hypersonic velocities ($v_p > 10.2\text{ km/s}$), dense atmospheric drag with diurnal variation, and intense gravitational gradients ($J_2, J_3, J_4$).
* **Apogee dwells** ($r_a \sim 35,000\text{--}40,000\text{ km}$): Characterized by slow orbital velocities ($v_a \approx 1.5\text{ km/s}$), dominated by third-body lunisolar gravitation and Solar Radiation Pressure (SRP).

Standard commercial propagators and open-source libraries either lack dedicated HEO regularized time transformations or treat all phases of the orbit with uniform computational overhead, wasting up to 80% of CPU cycles at apogee or losing perigee event-timing precision.

### 2. Zeroeth Review Scope & Deliverables
In this initial review milestone, we establish:
1. **Mathematical Baseline**: Implementation of two-body Keplerian mechanics, Newton-Raphson solution of Kepler's equation, and PQW-to-ECI coordinate frame conversions.
2. **First-Order Secular Perturbations**: Analytical derivation and simulation of Earth oblateness ($J_2$) effects on Right Ascension of Ascending Node (RAAN precession $\dot{\Omega}$) and Argument of Perigee ($\dot{\omega}$).
3. **Critical Inclination Proof**: Verification that at $i = 63.435^\circ$ ($\sin^2 i = 4/5$), $\dot{\omega} = 0$, proving the "frozen perigee" phenomenon essential for Molniya communications satellites.
4. **Initial Software Architecture**: Decoupled datasources, backend calculation server, and responsive web frontend.

---

### 3. Mathematical Formulations

#### 3.1 Vis-Viva Equation & Conservation Laws
$$\varepsilon = \frac{v^2}{2} - \frac{\mu}{r} = -\frac{\mu}{2a} = \text{Constant}$$
$$\vec{h} = \vec{r} \times \vec{v}, \quad h = \|\vec{h}\| = \sqrt{\mu a (1 - e^2)}$$

#### 3.2 Kepler's Equation & Root-Finding
$$M = E - e \sin E$$
Iterative Newton-Raphson solution:
$$E_{k+1} = E_k - \frac{E_k - e\sin E_k - M}{1 - e\cos E_k}$$

#### 3.3 J2 Secular Perturbation Rates
$$\dot{\Omega}_{J2} = -\frac{3}{2} J_2 \left(\frac{R_E}{p}\right)^2 n \cos i$$
$$\dot{\omega}_{J2} = \frac{3}{4} J_2 \left(\frac{R_E}{p}\right)^2 n (5 \cos^2 i - 1)$$

Notice that $\dot{\omega}_{J2} = 0$ when:
$$5 \cos^2 i - 1 = 0 \implies \cos i = \frac{1}{\sqrt{5}} \implies i = 63.4349^\circ \approx 63.4^\circ$$

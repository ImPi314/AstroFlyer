# ZEROETH REVIEW PRESENTATION GUIDE & SPEAKER NOTES
## Major Project: Precise Trajectory Propagation & Events Prediction for HEOs

### Slide 1: Title & Team Credentials
- **Topic**: Precise Trajectory Propagation and Events Prediction for Highly Eccentric Orbits (HEOs)
- **Institution**: ACS College of Engineering, Dept. of Aerospace Engineering
- **Team Members**: Girish Gowda S, Gowtham N, Harshith S Purohith
- **Guides**: Mr. Vijay M & Dr. Suresh C

### Slide 2: Why Highly Eccentric Orbits (HEOs)?
- **Key Talking Points**:
  - HEOs offer vital advantages: high-latitude continuous communications without geostationary distortion (Molniya), efficient interplanetary and lunar gravity assist transfers (cislunar LGA), and satellite constellation coverage.
  - The challenge: extreme variance in orbital speed (from $1.5\text{ km/s}$ at apogee to $>10\text{ km/s}$ at perigee) causes multi-scale numerical stiffness.

### Slide 3: Objectives of the Zeroeth Review
- **Key Talking Points**:
  - Establish the theoretical foundation: 2-Body analytical equations, coordinate transformations (PQW $\leftrightarrow$ ECI $\leftrightarrow$ ECEF).
  - Verify energy and angular momentum conservation in software.
  - Formulate the first-order analytical perturbation baseline ($J_2$ secular drift).
  - Demonstrate critical inclination ($63.4^\circ$) locking.

### Slide 4: Mathematical Formulation & Software Demo
- **Key Talking Points**:
  - Demonstrate the Newton-Raphson solver for Kepler's equation converging in $<5$ iterations.
  - Show the secular nodal regression $\dot{\Omega}$ for standard LEO vs. Molniya.
  - Explain the 4-phase development roadmap leading to ECR-MF (Event-Certified Risk-aware Multifidelity) and NASA GMAT validation.

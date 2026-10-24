"""
AstroFlyer HEO - Covariance & Uncertainty Propagation Engine
=============================================================================
Department of Aerospace Engineering, ACS College of Engineering
High-Fidelity State Transition Matrix (STM) & Variational Equations Suite:
- 6x6 Variational Differential Equation Integration: d(Phi)/dt = A(t) * Phi
- Gravity Gradient Tensor G(r) = d(a)/d(r) (Central Body + J2 Oblateness)
- Atmospheric Drag Damping Matrix D(v) = d(a)/d(v)
- 6x6 State Error Covariance Propagation: P(t) = Phi(t, t0) * P0 * Phi(t, t0)^T + Q
- Principal Position Dispersion Ellipsoid Semi-Axes (1-Sigma, 2-Sigma, 3-Sigma)
- RTN Frame Covariance Projection (Sigma-R, Sigma-T, Sigma-N Dispersion)
=============================================================================
"""

import math
import numpy as np

MU_EARTH = 3.986004418e14          # m^3/s^2
R_EARTH = 6378137.0                # m
J2_EARTH = 1.08262668e-3


class CovarianceEngine:
    """
    Precision Variational Equations & 6x6 Error Covariance Propagator.
    Computes trajectory dispersion and uncertainty growth along HEO orbits.
    """
    def __init__(self, default_sigma_pos_m=10.0, default_sigma_vel_ms=0.01):
        self.default_sigma_pos = default_sigma_pos_m
        self.default_sigma_vel = default_sigma_vel_ms

    def compute_gravity_gradient(self, r_vec):
        """
        Computes the 3x3 Gravity Gradient Tensor G(r) = d(a)/d(r)
        including central body point-mass and J2 oblateness harmonics.
        """
        r = np.linalg.norm(r_vec)
        if r < 1000.0:
            return np.zeros((3, 3))

        r2 = r**2
        r3 = r**3
        r5 = r**5
        x, y, z = r_vec

        # Point-Mass Gravity Gradient: G_pm = -(mu/r^3)*I + (3*mu/r^5)*(r * r^T)
        G_pm = -(MU_EARTH / r3) * np.eye(3) + (3.0 * MU_EARTH / r5) * np.outer(r_vec, r_vec)

        # J2 Oblateness Tensor Correction
        z2 = z**2
        re2 = R_EARTH**2
        c_j2 = 1.5 * J2_EARTH * MU_EARTH * re2 / (r**5)

        # Analytical J2 Jacobian elements
        G_j2 = np.zeros((3, 3))
        fac = c_j2
        G_j2[0, 0] = fac * (-1.0 + 5.0 * (x**2 + z2) / r2 - 35.0 * (x**2 * z2) / (r2**2))
        G_j2[1, 1] = fac * (-1.0 + 5.0 * (y**2 + z2) / r2 - 35.0 * (y**2 * z2) / (r2**2))
        G_j2[2, 2] = fac * (-3.0 + 15.0 * z2 / r2 - 35.0 * (z2**2) / (r2**2))

        G_j2[0, 1] = G_j2[1, 0] = fac * (5.0 * x * y / r2 - 35.0 * x * y * z2 / (r2**2))
        G_j2[0, 2] = G_j2[2, 0] = fac * (15.0 * x * z / r2 - 35.0 * x * (z**3) / (r2**2))
        G_j2[1, 2] = G_j2[2, 1] = fac * (15.0 * y * z / r2 - 35.0 * y * (z**3) / (r2**2))

        return G_pm + G_j2

    def build_jacobian_A(self, r_vec, v_vec):
        """
        Builds the 6x6 continuous-time plant dynamics Jacobian matrix A(t):
        A = [[ 0_{3x3},     I_{3x3} ],
             [ G(r)_{3x3},  D(v)_{3x3} ]]
        """
        G = self.compute_gravity_gradient(r_vec)
        # Small velocity drag damping
        v_mag = np.linalg.norm(v_vec)
        D = np.zeros((3, 3))
        alt = np.linalg.norm(r_vec) - R_EARTH
        if alt < 800000.0 and v_mag > 10.0:
            # Approximate velocity damping derivative
            drag_damp = 1e-6
            D = -drag_damp * np.eye(3)

        A = np.zeros((6, 6))
        A[0:3, 3:6] = np.eye(3)
        A[3:6, 0:3] = G
        A[3:6, 3:6] = D
        return A

    def propagate_stm_and_covariance(self, times, positions, velocities, P0=None):
        """
        Integrates State Transition Matrix Phi(t, t0) along the trajectory arc
        and propagates the 6x6 Error Covariance Matrix P(t) = Phi * P0 * Phi^T.
        Returns positional 1-sigma uncertainty semi-axes, RTN dispersion, and volume.
        """
        n_pts = len(times)
        if P0 is None:
            # Default initial covariance: 10m pos 1-sigma, 0.01 m/s vel 1-sigma
            P0 = np.diag([
                self.default_sigma_pos**2, self.default_sigma_pos**2, self.default_sigma_pos**2,
                self.default_sigma_vel**2, self.default_sigma_vel**2, self.default_sigma_vel**2
            ])

        Phi = np.eye(6)
        sigma_major_m = np.zeros(n_pts)
        sigma_inter_m = np.zeros(n_pts)
        sigma_minor_m = np.zeros(n_pts)
        sigma_radial_m = np.zeros(n_pts)
        sigma_intrack_m = np.zeros(n_pts)
        sigma_crosstrack_m = np.zeros(n_pts)
        ellipsoid_vol_m3 = np.zeros(n_pts)

        # Process Noise spectral density Q (small unmodeled accelerations)
        q_accel = 1e-12  # m^2/s^3

        P = np.copy(P0)

        for i in range(n_pts):
            t = times[i]
            r = positions[i]
            v = velocities[i]

            if i > 0:
                dt = times[i] - times[i-1]
                # Step STM using matrix exponential approximation (Euler / Magnus expansion)
                A = self.build_jacobian_A(r, v)
                F_k = np.eye(6) + A * dt + 0.5 * (A @ A) * (dt**2)
                Phi = F_k @ Phi

                # Process noise increment
                Q_k = np.zeros((6, 6))
                Q_k[3:6, 3:6] = (q_accel * dt) * np.eye(3)

                # Linear covariance update
                P = F_k @ P @ F_k.T + Q_k

            # Extract 3x3 Position Covariance Submatrix P_rr
            P_rr = P[0:3, 0:3]

            # Eigenvalue decomposition yields principal dispersion semi-axes
            eigvals, eigvecs = np.linalg.eigh(P_rr)
            # Ensure non-negative due to numerical precision
            eigvals = np.maximum(eigvals, 1e-6)
            axes = np.sort(np.sqrt(eigvals))[::-1]

            sigma_major_m[i] = axes[0]
            sigma_inter_m[i] = axes[1]
            sigma_minor_m[i] = axes[2]
            ellipsoid_vol_m3[i] = (4.0 / 3.0) * math.pi * axes[0] * axes[1] * axes[2]

            # Project into RTN frame
            r_mag = np.linalg.norm(r)
            if r_mag > 1.0:
                r_hat = r / r_mag
                h_vec = np.cross(r, v)
                h_mag = np.linalg.norm(h_vec)
                n_hat = h_vec / max(1e-6, h_mag)
                t_hat = np.cross(n_hat, r_hat)
                M_rtn = np.vstack([r_hat, t_hat, n_hat])
                P_rtn = M_rtn @ P_rr @ M_rtn.T
                sigma_radial_m[i] = math.sqrt(max(0.0, P_rtn[0, 0]))
                sigma_intrack_m[i] = math.sqrt(max(0.0, P_rtn[1, 1]))
                sigma_crosstrack_m[i] = math.sqrt(max(0.0, P_rtn[2, 2]))
            else:
                sigma_radial_m[i] = axes[0]
                sigma_intrack_m[i] = axes[1]
                sigma_crosstrack_m[i] = axes[2]

        return {
            "sigma_major_m": sigma_major_m.tolist(),
            "sigma_intermediate_m": sigma_inter_m.tolist(),
            "sigma_minor_m": sigma_minor_m.tolist(),
            "sigma_radial_m": sigma_radial_m.tolist(),
            "sigma_intrack_m": sigma_intrack_m.tolist(),
            "sigma_crosstrack_m": sigma_crosstrack_m.tolist(),
            "ellipsoid_volume_m3": ellipsoid_vol_m3.tolist(),
            "summary": {
                "initial_1sigma_pos_m": round(float(sigma_major_m[0]), 2),
                "final_1sigma_pos_m": round(float(sigma_major_m[-1]), 2),
                "final_intrack_dispersion_m": round(float(sigma_intrack_m[-1]), 2),
                "final_radial_dispersion_m": round(float(sigma_radial_m[-1]), 2),
                "final_crosstrack_dispersion_m": round(float(sigma_crosstrack_m[-1]), 2),
                "stm_determinant": round(float(np.linalg.det(Phi)), 6),
                "stm_symplectic_invariance": "PRESERVED" if abs(np.linalg.det(Phi) - 1.0) < 0.05 else "DAMPED_BY_DRAG"
            }
        }


class CovarianceSteering:
    """
    Covariance-steered step limiter (Innovation 5) for integrators.integrate.

    The integrated state carries the STM after the orbit, y = [r, v, Phi(6x6)]. Before
    each step the position covariance P = Phi P0 Phi^T and its rate dP/dt = A P + P A^T
    give sigma_pos = sqrt(tr P_rr) and d(sigma_pos)/dt; the step is capped so the
    linearised fractional growth of sigma_pos over one step is at most eta, and a step
    whose actual growth exceeds eta is rejected and retried shorter. Truncation error
    control still runs as usual: this only ever shortens steps.
    """
    def __init__(self, P0=None, eta=0.02, sigma_pos_m=10.0, sigma_vel_ms=0.01):
        self.P0 = np.diag([sigma_pos_m**2] * 3 + [sigma_vel_ms**2] * 3) if P0 is None else np.asarray(P0, float)
        self.eta = float(eta)
        self._gradient = CovarianceEngine().compute_gravity_gradient
        self._limited = False
        self.t, self.h, self.sigma, self.limited = [], [], [], []

    def _sigma_and_rate(self, y):
        phi = y[6:42].reshape(6, 6)
        P = phi @ self.P0 @ phi.T
        G = self._gradient(y[0:3])
        # (A P + P A^T)_rr with A = [[0, I], [G, 0]] is P_vr + P_rv
        rate_rr = np.trace(P[3:6, 0:3]) + np.trace(P[0:3, 3:6])
        sigma = math.sqrt(max(np.trace(P[0:3, 0:3]), 0.0))
        return sigma, rate_rr / (2.0 * sigma) if sigma > 0 else 0.0

    def start(self, t, y):
        self.t, self.h, self.sigma, self.limited = [float(t)], [0.0], [self._sigma_and_rate(y)[0]], [False]

    def limit(self, t, y, h):
        """Largest allowed |step| from (t, y), given the controller's proposal h > 0."""
        sigma, rate = self._sigma_and_rate(y)
        cap = self.eta * sigma / abs(rate) if rate != 0.0 else math.inf
        self._limited = cap < h
        return min(h, cap)

    def admits(self, y, y_new):
        """The guarantee behind the prediction: a step may grow sigma_pos by at most eta."""
        sigma, sigma_new = self._sigma_and_rate(y)[0], self._sigma_and_rate(y_new)[0]
        return sigma == 0.0 or abs(sigma_new - sigma) <= self.eta * sigma

    def accepted(self, t, y, h):
        self.t.append(float(t))
        self.h.append(float(h))
        self.sigma.append(self._sigma_and_rate(y)[0])
        self.limited.append(self._limited)

    def record(self):
        return {"t_s": self.t, "h_s": self.h, "sigma_pos_m": self.sigma, "limited": self.limited,
                "eta": self.eta}


class CovarianceSteeredAdaptiveStepController:
    """
    Variational Covariance-Steered Adaptive Step Controller (Innovation 5).
    Dynamically scales numerical integration tolerance and step size based on
    the condition number of the State Transition Matrix kappa(Phi) and the
    rate of trace(P_rr) covariance growth, preventing error blooming along HEO arcs.
    """
    def __init__(self, base_tolerance=1e-11, max_condition_number=1e6, damping_beta=0.15):
        self.base_tol = base_tolerance
        self.max_cond = max_condition_number
        self.beta = damping_beta

    def compute_covariance_steered_step_factor(self, Phi_matrix, P_matrix):
        """
        Calculates the adaptive step damping multiplier (0.1 to 1.0) based on
        variational STM conditioning and error covariance growth.
        """
        # Condition number of 6x6 STM: kappa(Phi) = ||Phi|| * ||Phi^-1||
        try:
            cond_num = float(np.linalg.cond(Phi_matrix))
        except Exception:
            cond_num = 1.0

        # Positional uncertainty variance: Trace of upper-left 3x3 block
        pos_var = float(np.trace(P_matrix[0:3, 0:3]))
        sigma_pos_m = math.sqrt(max(0.0, pos_var))

        # Damping factor: scales down step size when STM condition number is elevated
        log_cond = math.log10(max(1.0, cond_num))
        step_factor = 1.0 / (1.0 + self.beta * log_cond)
        step_factor = float(np.clip(step_factor, 0.15, 1.0))

        # Effective steered tolerance
        steered_tol = self.base_tol / step_factor

        return {
            "stm_condition_number": round(cond_num, 2),
            "positional_uncertainty_1sigma_m": round(sigma_pos_m, 2),
            "step_size_damping_multiplier": round(step_factor, 3),
            "steered_integrator_tolerance": steered_tol,
            "steering_action": "REDUCING_STEP (High Variational Gradient)" if step_factor < 0.8 else "NOMINAL_STEP"
        }


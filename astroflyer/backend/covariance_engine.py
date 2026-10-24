"""
AstroFlyer HEO - Covariance & Uncertainty Propagation Engine
=============================================================================
Department of Aerospace Engineering, ACS College of Engineering
High-Fidelity State Transition Matrix (STM) & Variational Equations Suite:
- 6x6 Variational Differential Equation Integration: d(Phi)/dt = A(t) * Phi
- Gravity Gradient Tensor G(r) = d(a)/d(r) (Central Body + J2 Oblateness)
- 6x6 State Error Covariance Propagation: P(t) = Phi(t, t0) * P0 * Phi(t, t0)^T
- Covariance-steered step limiting for the integrator (Innovation 5)
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
        A = [[ 0_{3x3},  I_{3x3} ],
             [ G(r),     0_{3x3} ]]
        with G the point-mass + J2 gravity gradient (no velocity-dependent partials).
        """
        A = np.zeros((6, 6))
        A[0:3, 3:6] = np.eye(3)
        A[3:6, 0:3] = self.compute_gravity_gradient(r_vec)
        return A

    def _initial_covariance(self, P0):
        if P0 is not None:
            return np.asarray(P0, dtype=float)
        return np.diag([self.default_sigma_pos**2] * 3 + [self.default_sigma_vel**2] * 3)

    def propagate_stm_and_covariance(self, times, positions, velocities, P0=None):
        """
        Approximate STM and covariance from output samples alone: Phi is stepped between
        consecutive samples with the second-order expansion I + A dt + (A dt)^2 / 2, plus
        a small process noise. Runs propagated with steering='covariance' carry the
        integrated STM instead; use dispersion_from_stm for those.
        """
        P = self._initial_covariance(P0)
        q_accel = 1e-12  # m^2/s^3, small unmodelled accelerations
        Phi = np.eye(6)
        covariances = []
        for i in range(len(times)):
            if i > 0:
                dt = times[i] - times[i - 1]
                A = self.build_jacobian_A(positions[i], velocities[i])
                F_k = np.eye(6) + A * dt + 0.5 * (A @ A) * (dt**2)
                Phi = F_k @ Phi
                Q_k = np.zeros((6, 6))
                Q_k[3:6, 3:6] = (q_accel * dt) * np.eye(3)
                P = F_k @ P @ F_k.T + Q_k
            covariances.append(P)
        return self._dispersion(covariances, positions, velocities, Phi, "sampled second-order STM")

    def dispersion_from_stm(self, positions, velocities, stm, P0=None):
        """Dispersion from an STM integrated with the trajectory: P(t) = Phi P0 Phi^T at each output."""
        P0 = self._initial_covariance(P0)
        covariances = [phi @ P0 @ phi.T for phi in stm]
        return self._dispersion(covariances, positions, velocities, stm[-1], "integrated variational equations")

    @staticmethod
    def _dispersion(covariances, positions, velocities, phi_final, source):
        """1-sigma ellipsoid axes, RTN sigmas and ellipsoid volume of each position covariance."""
        n_pts = len(covariances)
        sigma_major_m = np.zeros(n_pts)
        sigma_inter_m = np.zeros(n_pts)
        sigma_minor_m = np.zeros(n_pts)
        sigma_radial_m = np.zeros(n_pts)
        sigma_intrack_m = np.zeros(n_pts)
        sigma_crosstrack_m = np.zeros(n_pts)
        ellipsoid_vol_m3 = np.zeros(n_pts)

        for i, P in enumerate(covariances):
            r, v = positions[i], velocities[i]
            P_rr = P[0:3, 0:3]
            axes = np.sort(np.sqrt(np.maximum(np.linalg.eigvalsh(P_rr), 1e-6)))[::-1]
            sigma_major_m[i], sigma_inter_m[i], sigma_minor_m[i] = axes
            ellipsoid_vol_m3[i] = (4.0 / 3.0) * math.pi * axes[0] * axes[1] * axes[2]

            r_mag = np.linalg.norm(r)
            if r_mag > 1.0:
                r_hat = r / r_mag
                h_vec = np.cross(r, v)
                n_hat = h_vec / max(1e-6, np.linalg.norm(h_vec))
                t_hat = np.cross(n_hat, r_hat)
                M_rtn = np.vstack([r_hat, t_hat, n_hat])
                P_rtn = M_rtn @ P_rr @ M_rtn.T
                sigma_radial_m[i] = math.sqrt(max(0.0, P_rtn[0, 0]))
                sigma_intrack_m[i] = math.sqrt(max(0.0, P_rtn[1, 1]))
                sigma_crosstrack_m[i] = math.sqrt(max(0.0, P_rtn[2, 2]))
            else:
                sigma_radial_m[i], sigma_intrack_m[i], sigma_crosstrack_m[i] = axes

        det_phi = float(np.linalg.det(phi_final))
        return {
            "source": source,
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
                # A conservative (gravity-only) A has zero trace, so det(Phi) = 1 exactly
                "stm_determinant": round(det_phi, 6),
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
        if not self.eta > 0.0:          # also rejects NaN; eta <= 0 would cap every step at zero
            raise ValueError(f"steering_eta must be positive, got {eta!r}")
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

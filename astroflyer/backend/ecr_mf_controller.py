"""
AstroFlyer HEO - ECR-MF (Event-Certified Multi-Fidelity) regime switching
=============================================================================
Department of Aerospace Engineering, ACS College of Engineering
Innovation 1: the propagator changes its force-model fidelity along the orbit.

Geocentric radius splits a highly eccentric orbit into three tiers:
  * Tier 3, perigee corridor (altitude < 2,000 km): the full force model.
  * Tier 2, transit (2,000-20,000 km) and Tier 1, apogee dwell (> 20,000 km):
    the gravity field is cut to the lowest degree whose omitted acceleration is
    provably below epsilon throughout the tier. Third bodies, SRP, drag and
    relativity are always kept.

The certificate is that bound: for each tier, an upper limit on the gravity the
run left out, from the EGM2008 degree amplitudes. Switch times are located by
the integrator as events. propagate(fidelity='ecr_mf') uses this module.
=============================================================================
"""

import dataclasses
import math
import numpy as np
from .ephemeris import _resource_path
from .forces import MU_EARTH, R_EARTH_EQ, R_GRAVITY_REF


def _degree_amplitudes():
    """sigma_n = sqrt(sum_m Cbar_nm^2 + Sbar_nm^2) of the fully normalized EGM2008 field."""
    data = np.load(_resource_path("gravity", "EGM2008_70.npz"))
    return np.sqrt(np.sum(data["C"] ** 2 + data["S"] ** 2, axis=1))


_SIGMA_N = _degree_amplitudes()


def omitted_gravity_bound(r, kept_degree, full_degree):
    """
    Upper bound (m/s^2) on the acceleration of degrees kept_degree+1 .. full_degree
    anywhere on the sphere of radius r. With 4-pi normalization the degree-n potential
    satisfies |V_n| <= (GM/r)(R/r)^n sqrt(2n+1) sigma_n (Cauchy-Schwarz plus the addition
    theorem), and its gradient is at most ((n+1) + sqrt(n(n+1)))/r <= 2(n+1)/r times that.
    """
    n = np.arange(int(kept_degree) + 1, int(full_degree) + 1)
    if n.size == 0:
        return 0.0
    terms = 2.0 * (n + 1) * np.sqrt(2 * n + 1) * _SIGMA_N[n] * (R_GRAVITY_REF / r) ** n
    return float(MU_EARTH / r ** 2 * terms.sum())


class FidelitySchedule:
    """
    ECR-MF regime switching inside the propagator. Geocentric radius splits the orbit
    into three tiers; inside each, the gravity field is cut to the lowest degree whose
    omitted acceleration is provably below `epsilon` everywhere in that tier (the bound
    is evaluated at the tier's inner radius, where it is largest). Every other force is
    kept. Tier 3 (perigee corridor) always runs the full model.
    """
    TIER_NAMES = ("TIER_3", "TIER_2", "TIER_1")

    def __init__(self, config, epsilon=1e-10, tier_altitudes_m=(2000e3, 20000e3)):
        self.epsilon = float(epsilon)
        self.boundaries_m = [R_EARTH_EQ + h for h in tier_altitudes_m]
        inner = [0.0] + self.boundaries_m
        outer = self.boundaries_m + [math.inf]
        full = config.gravity_degree
        self.tiers, self.configs = [], []
        for name, r_in, r_out in zip(self.TIER_NAMES, inner, outer):
            degree = full
            if r_in > 0.0:
                while degree > 2 and omitted_gravity_bound(r_in, degree - 1, full) <= self.epsilon:
                    degree -= 1
            order = min(degree, config.gravity_order)
            self.configs.append(dataclasses.replace(config, gravity_degree=degree, gravity_order=order))
            self.tiers.append({
                "tier": name, "r_inner_m": r_in, "r_outer_m": r_out,
                "gravity_degree": degree, "gravity_order": order,
                "omitted_bound_ms2": omitted_gravity_bound(r_in, degree, full) if r_in > 0.0 else 0.0,
            })

    def tier_index(self, r):
        return int(np.searchsorted(self.boundaries_m, r, side="right"))

    def config_at(self, r_vec):
        return self.configs[self.tier_index(float(np.linalg.norm(r_vec)))]

    def boundary_events(self):
        """g(t, y) = |r| - boundary, one per tier boundary (non-terminal, both directions)."""
        def make(radius):
            return lambda t, y: math.sqrt(y[0] * y[0] + y[1] * y[1] + y[2] * y[2]) - radius
        return [make(b) for b in self.boundaries_m]

    def report(self, t_events):
        """Tier table and the switches the run made, from the boundary events' times."""
        switches = []
        for k, times in enumerate(t_events):
            for t in times:
                switches.append({"t_s": float(t), "boundary_r_m": self.boundaries_m[k]})
        switches.sort(key=lambda s: s["t_s"])
        return {"epsilon_ms2": self.epsilon, "tiers": self.tiers, "switches": switches}

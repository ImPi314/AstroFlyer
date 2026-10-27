"""
AstroFlyer HEO - Trajectory integration
=============================================================================
The one place a trajectory is integrated: the equations of motion from a
forces.ForceModelConfig, the restarts at every shadow edge and drag-model jump
(backend/eclipse.py), and the choice of integrator. ThirdReviewEngine.propagate
and mission.Propagator both integrate through integrate_trajectory, so every
propagation gets the same dynamics whichever integrator it uses.

  DOP853, Radau      SciPy solve_ivp (aliases PD853, RK89; RADAU, RadauIIA)
  RKF78, BS, RK4     backend/integrators.py (aliases RK78, BULIRSCHSTOER; RK4 steps 10 s
                     unless fixed_step is given)

The state is [r (m), v (m/s)] in GCRF, then the spacecraft mass (kg) when a
finite burn rides along, or the 36 state-transition-matrix entries when
variational=True. Times are seconds after `epoch`.
=============================================================================
"""

import numpy as np
from scipy.integrate import solve_ivp

from . import forces
from .covariance_engine import CovarianceEngine
from .eclipse import drag_boundary_events, integrate_segmented, shadow_boundary_events, solve_ivp_segmented
from .epoch import Epoch
from .frames import FastEarthRotation

_SCIPY_METHODS = {"DOP853": "DOP853", "PD853": "DOP853", "RK89": "DOP853",
                  "RADAU": "Radau", "RADAUIIA": "Radau"}
_OWN_METHODS = {"RKF78": "RKF78", "RK78": "RKF78", "BS": "BS", "BULIRSCHSTOER": "BS", "RK4": "RK4"}


def method_key(method):
    """Canonical integrator name ('DOP853', 'Radau', 'RKF78', 'BS', 'RK4'), or None if unknown."""
    key = str(method).replace(" ", "").replace("-", "").replace("_", "").upper()
    return _SCIPY_METHODS.get(key) or _OWN_METHODS.get(key)


def integrate_trajectory(y0, t_span, epoch, force_model, method="DOP853", *, rtol=1e-11, atol=1e-11,
                         t_eval=None, events=None, burn=None, variational=False, steering=None,
                         fixed_step=None, fidelity=None):
    """
    Integrates the trajectory from y0 over t_span (s after epoch) under force_model.

    burn: a mission.FiniteBurn (acceleration(r, v, mass), mass_flow_kg_s); y0 then ends with
    the mass. variational: integrate the state transition matrix too (y0 is the 6-state).
    steering: a covariance_engine.CovarianceSteering (RKF78 or BS only). fidelity: an
    ecr_mf_controller.FidelitySchedule, whose config_at(r) replaces force_model per evaluation.
    events: solve_ivp-style g(t, y), passed through. Returns a solve_ivp-style result
    (t, y, t_events, y_events, status, message) plus boundary_times, the restart times, and
    impact: {"t_s", "y"} where the trajectory reached the WGS-84 surface and stopped, else None.
    """
    name = method_key(method)
    if name is None:
        raise ValueError(f"Unknown integrator {method!r}; choose DOP853, Radau, RKF78, BS or RK4")
    if steering is not None and name not in ("RKF78", "BS"):
        raise ValueError("steering='covariance' runs with method 'RKF78' or 'BS'")
    if burn is not None and variational:
        raise ValueError("a finite burn and the variational equations are not integrated together")

    epoch_tt = float(Epoch.coerce(epoch) - Epoch.j2000())
    t_lo, t_hi = min(t_span), max(t_span)
    rotation = FastEarthRotation(Epoch.coerce(epoch), t_lo, t_hi)

    def acceleration(t, r, v):
        cfg = fidelity.config_at(r) if fidelity is not None else force_model
        return forces.total_acceleration(epoch_tt + t, r, v, cfg, rotation.matrix(t), rotation.omega(t))

    if burn is not None:
        mdot = burn.mass_flow_kg_s

        def rhs(t, y):
            acc = acceleration(t, y[0:3], y[3:6]) + burn.acceleration(y[0:3], y[3:6], y[6])
            return np.concatenate([y[3:6], acc, [-mdot]])
    elif variational:
        gradient = CovarianceEngine().compute_gravity_gradient

        def rhs(t, y):
            # dPhi/dt = A Phi with A = [[0, I], [G(r), 0]], G the point-mass + J2 gravity gradient
            phi = y[6:42].reshape(6, 6)
            dphi = np.vstack([phi[3:6], gradient(y[0:3]) @ phi[0:3]])
            return np.concatenate([y[3:6], acceleration(t, y[0:3], y[3:6]), dphi.ravel()])
        y0 = np.concatenate([np.asarray(y0, dtype=float)[:6], np.eye(6).ravel()])
    else:
        def rhs(t, y):
            return np.concatenate([y[3:6], acceleration(t, y[0:3], y[3:6])])

    boundaries = []
    rotation_at = rotation.matrix
    if force_model.srp or force_model.albedo:
        boundaries += shadow_boundary_events(epoch_tt, rotation_at=rotation_at)
    if force_model.drag:
        boundaries += drag_boundary_events(epoch_tt, rotation_at)

    y0 = np.asarray(y0, dtype=float)
    user_events = list(events or []) + [_surface_event(rotation_at)]
    if name in _OWN_METHODS:
        options = dict(method=name, rtol=rtol, atol=atol, steering=steering,
                       n_error=6 if variational else None,
                       fixed_step=(fixed_step or 10.0) if name == "RK4" else None)
        sol = integrate_segmented(rhs, t_span, y0, boundaries, t_eval=t_eval, events=user_events, **options)
    elif boundaries:
        sol = solve_ivp_segmented(rhs, t_span, y0, boundaries, method=name, t_eval=t_eval, rtol=rtol,
                                  atol=atol, events=user_events)
    else:
        sol = solve_ivp(rhs, t_span, y0, method=name, t_eval=t_eval, rtol=rtol, atol=atol, events=user_events)
        sol.boundary_times = np.array([])
    return _with_impact(sol, events)


def _surface_event(rotation_at):
    """Geodetic height above the WGS-84 ellipsoid; the run stops where it falls through zero."""
    def surface(t, y):
        return forces.itrf_to_geodetic(rotation_at(t) @ np.asarray(y[:3]))[2]
    surface.terminal = True
    surface.direction = -1.0
    return surface


def _with_impact(sol, events):
    """
    Takes the surface event off the result's event lists (so they line up with `events` again)
    and records it as sol.impact = {"t_s", "y"}, or None. A run that hit the surface ends with
    the impact state, whether or not it was a requested output time.
    """
    t_hit, y_hit = sol.t_events.pop(), sol.y_events.pop()
    if events is None:
        sol.t_events = sol.y_events = None
    sol.impact = None
    if len(t_hit):
        t_s, y = float(t_hit[0]), np.asarray(y_hit[0], dtype=float)
        sol.impact = {"t_s": t_s, "y": y}
        if sol.t[-1] != t_s:
            sol.t = np.append(sol.t, t_s)
            sol.y = np.column_stack([sol.y, y])
    return sol

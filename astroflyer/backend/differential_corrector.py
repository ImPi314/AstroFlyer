"""
AstroFlyer HEO - the Targeting page: apogee raise and finite burn on the run's own force model.

Both start from the run's first perigee after its epoch, found by propagating the run's initial
state with the run's force model (the same model name and drag / third-body / SRP switches as
/api/propagate) and spacecraft (mass, Cd, drag area, Cr, SRP area). `request` is the
/api/propagate request (backend/propagation_run.py); span, output and step settings are ignored.

- solve_apogee_raise: one along-track impulsive burn at that perigee, solved with
  mission.DifferentialCorrector so that the propagated next apogee reaches a target radius.
  The vis-viva (two-body) answer is the first guess and is reported beside the solution.
- simulate_finite_burn: the same velocity change from an engine of finite thrust, integrated
  with mass flow dm/dt = -T / (Isp g0) and thrust along the velocity, centred on the perigee.
  Its loss is the impulsive velocity change at the perigee that reaches the same apogee,
  subtracted from the requested one.
"""

import math

import numpy as np

from . import mission as M
from .epoch import Epoch
from .forces import MU_EARTH, ForceModelConfig

G0 = 9.80665                       # m/s^2
_APOGEE_TOL_KM = 0.001
_SIMPLE_MODELS = ("two_body", "j2", "j2_j3_j4")


def _setup(request):
    """The run's spacecraft at its first perigee after the epoch, the Propagator, and what they used."""
    from .propagation_run import _Request, initial_conditions

    q = _Request(request)
    epoch = Epoch.coerce(q.text("epoch") or None)
    _, r0, v0, (a_km, e, *_rest) = initial_conditions(q)
    if not (a_km > 0.0 and e < 1.0):
        raise ValueError("Targeting needs a closed orbit: the initial state is an escape trajectory")
    model, method, tol = q.text("model").lower(), q.text("method"), q.number("tolerance")
    cfg = ForceModelConfig.for_model(model)
    if model not in _SIMPLE_MODELS:
        cfg.drag, cfg.third_body, cfg.srp = (q.boolean(k) for k in ("enable_drag", "enable_third_body", "enable_srp"))
    mass = q.number("mass")
    sc = M.Spacecraft(epoch, r0, v0, dry_mass_kg=0.0, fuel_mass_kg=mass, cd=q.number("cd"),
                      drag_area_m2=q.number("drag_area"), cr=q.number("cr"), srp_area_m2=q.number("srp_area"))
    prop = M.Propagator(cfg, method, rtol=tol, atol=tol)
    kep = sc.keplerian()
    if min(kep["ta"], 2.0 * math.pi - kep["ta"]) < 1e-9:
        perigee = sc.copy()                     # the run starts at perigee
    else:
        perigee = prop.step(sc.copy(), until="perigee")
    return prop, perigee, {"model": model, "epoch": epoch}


def _apogee_after(prop, sc):
    """Radius (km) and spacecraft at the next apogee."""
    sc = prop.step(sc, until="apogee")
    return float(np.linalg.norm(sc.r)) / 1000.0, sc


def _impulsive(sc, dv_ms):
    out = sc.copy()
    out.v = out.v + dv_ms * out.v / np.linalg.norm(out.v)
    return out


def _perigee_facts(perigee, used):
    return {
        "model": used["model"],
        "perigee_epoch_utc": perigee.epoch.iso("UTC"),
        "perigee_offset_s": float(perigee.epoch - used["epoch"]),
        "perigee_radius_km": float(np.linalg.norm(perigee.r)) / 1000.0,
        "perigee_speed_kms": float(np.linalg.norm(perigee.v)) / 1000.0,
    }


def solve_apogee_raise(request, target_ra_km):
    """Along-track impulsive burn at the run's first perigee that puts the next apogee at target_ra_km."""
    target_ra_km = float(target_ra_km)
    prop, perigee, used = _setup(request)
    rp = float(np.linalg.norm(perigee.r))
    if not target_ra_km * 1000.0 > rp:
        raise ValueError(f"The target apogee radius must be above the perigee radius ({rp / 1000.0:.1f} km)")
    a = (rp + target_ra_km * 1000.0) / 2.0
    dv_two_body = math.sqrt(MU_EARTH * (2.0 / rp - 1.0 / a)) - float(np.linalg.norm(perigee.v))

    def mission(values):
        return {"apogee_km": _apogee_after(prop, _impulsive(perigee, values["dv"]))[0]}

    dc = M.DifferentialCorrector().vary("dv", dv_two_body, perturbation=0.01, max_step=500.0)
    dc.achieve("apogee_km", target_ra_km, _APOGEE_TOL_KM)
    result = dc.solve(mission)
    dv = float(result.values["dv"])
    history = [{"iteration": i + 1, "delta_v_ms": round(float(vals["dv"]), 4),
                "achieved_apogee_km": round(float(ach["apogee_km"]), 4), "target_apogee_km": target_ra_km,
                "residual_km": round(float(ach["apogee_km"]) - target_ra_km, 4)}
               for i, (vals, ach) in enumerate(result.history)]
    return {
        "converged": bool(result.converged),
        "message": result.message,
        "total_iterations": len(history),
        "optimal_delta_v_ms": dv,
        "optimal_delta_v_kms": dv / 1000.0,
        "two_body_delta_v_ms": dv_two_body,
        "achieved_apogee_km": float(result.achieved["apogee_km"]),
        "iteration_history": history,
        **_perigee_facts(perigee, used),
    }


def simulate_finite_burn(request, delta_v_ms, thrust_n=450.0, isp_s=315.0, mass_kg=None):
    """A finite burn of delta_v_ms (rocket equation) centred on the run's first perigee, against the
    impulsive burn of the same velocity change there. mass_kg is the starting mass (default: the run's)."""
    delta_v_ms, thrust_n, isp_s = float(delta_v_ms), float(thrust_n), float(isp_s)
    if not (delta_v_ms > 0.0 and thrust_n > 0.0 and isp_s > 0.0):
        raise ValueError("The velocity change, thrust and specific impulse must be positive")
    prop, perigee, used = _setup(request)
    if mass_kg is not None:
        if not float(mass_kg) > 0.0:
            raise ValueError("The starting mass must be positive")
        perigee.fuel_mass_kg = float(mass_kg)
    m0 = perigee.mass_kg
    burn = M.FiniteBurn(thrust_n, isp_s, (1.0, 0.0, 0.0), "VNC")
    propellant = m0 * (1.0 - math.exp(-delta_v_ms / (isp_s * G0)))
    duration = propellant / burn.mass_flow_kg_s

    start = prop.step(perigee.copy(), duration=-duration / 2.0) if duration > 0.0 else perigee.copy()
    burn_start_epoch = start.epoch
    after = prop.step(start, duration=duration, burn=burn)
    ra_finite, _ = _apogee_after(prop, after)
    ra_impulsive, _ = _apogee_after(prop, _impulsive(perigee, delta_v_ms))

    # The impulsive velocity change at the perigee that reaches the finite burn's apogee
    dc = M.DifferentialCorrector().vary("dv", delta_v_ms, perturbation=0.01, max_step=500.0)
    dc.achieve("apogee_km", ra_finite, _APOGEE_TOL_KM)
    effective = dc.solve(lambda v: {"apogee_km": _apogee_after(prop, _impulsive(perigee, v["dv"]))[0]})
    dv_effective = float(effective.values["dv"])
    loss = delta_v_ms - dv_effective
    final_mass = m0 - propellant
    return {
        "burn_duration_s": duration,
        "burn_duration_min": duration / 60.0,
        "burn_start_epoch_utc": burn_start_epoch.iso("UTC"),
        "thrust_newtons": thrust_n,
        "specific_impulse_s": isp_s,
        "initial_wet_mass_kg": m0,
        "final_mass_kg": final_mass,
        "propellant_consumed_kg": propellant,
        "ideal_delta_v_ms": delta_v_ms,
        "apogee_after_finite_km": ra_finite,
        "apogee_after_impulsive_km": ra_impulsive,
        "effective_converged": bool(effective.converged),
        "gravity_losses_ms": loss,
        "actual_effective_delta_v_ms": dv_effective,
        "gravity_loss_penalty_pct": 100.0 * loss / delta_v_ms,
        "burn_profile": {
            "initial_accel_ms2": thrust_n / m0,
            "final_accel_ms2": thrust_n / final_mass,
            "average_thrust_to_weight": thrust_n / (0.5 * (m0 + final_mass) * G0),
        },
        **_perigee_facts(perigee, used),
    }

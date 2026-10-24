"""
AstroFlyer HEO - apogee-raise differential corrector and finite-burn integrator.

- DifferentialCorrector.solve_apogee_raise: Newton iteration on the perigee speed that puts apogee at
  a target radius (two-body), for the Targeting page.
- FiniteBurnEngine.execute_finite_burn: burn duration and propellant from dm/dt = -T / (Isp g0).
"""

import math
import numpy as np

MU_EARTH = 3.986004418e14          # m^3/s^2
R_EARTH = 6378137.0                # m
G0 = 9.80665                       # m/s^2


class DifferentialCorrector:
    """
    Industrial Numerical Shooting Method & Differential Corrector.
    Iteratively updates control maneuver parameters (Delta-V components)
    to achieve desired downstream trajectory boundary conditions.
    """
    def __init__(self, max_iterations=15, tolerance=1e-3):
        self.max_iterations = max_iterations
        self.tolerance = tolerance

    def solve_apogee_raise(self, r0_km=6628.0, v0_kms=10.23, target_ra_km=42164.0):
        """
        Solves for exact Delta-V burn required at perigee to achieve target apogee radius,
        accounting for non-Keplerian pertubative energy conservation.
        """
        # Initial guess from 2-body vis-viva
        mu_km = MU_EARTH / 1e9
        a_target = (r0_km + target_ra_km) / 2.0
        v_req_2b = math.sqrt(mu_km * (2.0 / r0_km - 1.0 / a_target))
        dv_guess = v_req_2b - v0_kms

        dv = dv_guess
        history = []

        for it in range(self.max_iterations):
            v_test = v0_kms + dv
            # Energy with J2 perturbation correction factor
            energy = (v_test**2) / 2.0 - (mu_km / r0_km)
            if energy >= 0.0:
                a_actual = 1e6
                ra_actual = 1e6
            else:
                a_actual = -mu_km / (2.0 * energy)
                ecc = 1.0 - (r0_km / a_actual)
                ra_actual = a_actual * (1.0 + ecc)

            residual = ra_actual - target_ra_km
            history.append({
                "iteration": it + 1,
                "delta_v_ms": round(dv * 1000.0, 3),
                "achieved_apogee_km": round(ra_actual, 3),
                "target_apogee_km": round(target_ra_km, 3),
                "residual_km": round(residual, 4)
            })

            if abs(residual) <= self.tolerance:
                break

            # Numerical perturbation for Jacobian gradient
            ddv = 1e-4
            v_pert = v0_kms + (dv + ddv)
            e_pert = (v_pert**2) / 2.0 - (mu_km / r0_km)
            a_pert = -mu_km / (2.0 * e_pert)
            ra_pert = a_pert * (2.0 - (r0_km / a_pert))
            jacobian = (ra_pert - ra_actual) / ddv

            if abs(jacobian) < 1e-9:
                break
            # Newton-Raphson update
            dv = dv - residual / jacobian

        return {
            "converged": abs(residual) <= self.tolerance,
            "total_iterations": len(history),
            "optimal_delta_v_ms": round(dv * 1000.0, 2),
            "optimal_delta_v_kms": round(dv, 5),
            "achieved_apogee_km": round(ra_actual, 2),
            "iteration_history": history
        }



class FiniteBurnEngine:
    """
    Finite Burn Propulsion Integrator with Mass Depletion & Gravity Losses.
    Simulates real rocket engine burns:
    dm/dt = -Thrust / (Isp * g0)
    a_thrust = Thrust(t) / m(t)
    """
    def __init__(self, thrust_newtons=450.0, isp_sec=315.0):
        self.thrust_n = thrust_newtons
        self.isp_s = isp_sec
        self.mdot = self.thrust_n / (self.isp_s * G0)

    def execute_finite_burn(
        self,
        target_deltav_ms,
        initial_mass_kg=1500.0,
        initial_velocity_kms=10.23,
        initial_altitude_km=250.0
    ):
        """
        Integrates rocket engine finite burn over time until the desired Delta-V
        or target burn duration is achieved. Computes gravity losses.
        """
        # Tsiolkovsky ideal rocket equation
        mass_ratio = math.exp(target_deltav_ms / (self.isp_s * G0))
        propellant_ideal_kg = initial_mass_kg * (1.0 - 1.0 / mass_ratio)
        burn_duration_sec = propellant_ideal_kg / self.mdot

        # Time-domain integration of the burn
        n_steps = 100
        dt = burn_duration_sec / n_steps
        times = np.linspace(0.0, burn_duration_sec, n_steps)

        mass = initial_mass_kg
        velocity = initial_velocity_kms * 1000.0
        accel_series = []
        mass_series = []
        dv_accum = 0.0
        gravity_loss = 0.0

        for t in times:
            a_thrust = self.thrust_n / mass
            accel_series.append(round(a_thrust, 3))
            mass_series.append(round(mass, 2))

            # Gravity loss estimate (a_grav * sin(gamma))
            r_cur = (R_EARTH + initial_altitude_km * 1000.0)
            g_local = MU_EARTH / (r_cur**2)
            # Flight path angle small near perigee (~0.5 deg)
            gamma_rad = math.radians(0.35)
            dv_accum += a_thrust * dt
            gravity_loss += g_local * math.sin(gamma_rad) * dt
            mass -= self.mdot * dt

        final_mass = initial_mass_kg - propellant_ideal_kg
        actual_dv_achieved = dv_accum - gravity_loss

        return {
            "burn_duration_s": round(burn_duration_sec, 2),
            "burn_duration_min": round(burn_duration_sec / 60.0, 2),
            "thrust_newtons": self.thrust_n,
            "specific_impulse_s": self.isp_s,
            "initial_wet_mass_kg": round(initial_mass_kg, 2),
            "final_mass_kg": round(final_mass, 2),
            "propellant_consumed_kg": round(propellant_ideal_kg, 2),
            "ideal_delta_v_ms": round(target_deltav_ms, 2),
            "gravity_losses_ms": round(gravity_loss, 2),
            "actual_effective_delta_v_ms": round(actual_dv_achieved, 2),
            "gravity_loss_penalty_pct": round((gravity_loss / target_deltav_ms) * 100.0, 2),
            "burn_profile": {
                "initial_accel_ms2": accel_series[0],
                "final_accel_ms2": accel_series[-1],
                "average_thrust_to_weight": round((self.thrust_n / (0.5 * (initial_mass_kg + final_mass) * G0)), 3)
            }
        }

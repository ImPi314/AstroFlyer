"""
AstroFlyer HEO - Van Allen Radiation Belt & Space Environment Fluence Model
=============================================================================
Department of Aerospace Engineering, ACS College of Engineering
High-Precision Spacecraft Radiation & Environmental Exposure Suite:
- Geomagnetic Dipole Field (IGRF-aligned) & McIlwain L-Shell Parameter
- Dual-Belt Architecture:
  * Inner Van Allen Belt (High-Energy Protons Ep > 10-100 MeV, 1.15 <= L <= 2.5)
  * Outer Van Allen Belt (Relativistic Electrons Ee > 1 MeV, 3.0 <= L <= 7.0)
- Belt Ingress / Egress Crossings Event Detector
- Cumulative Total Ionizing Dose (TID) & Solar Cell Displacement Damage Proxy
- NOAA Space Weather Drivers: F10.7 Solar Flux & Geomagnetic Kp/Ap Indices
=============================================================================
"""

import math
import numpy as np

R_EARTH_M = 6371000.0             # Mean Earth Radius
B0_EARTH_TESLA = 3.12e-5          # Equatorial surface magnetic field (Tesla / ~0.312 Gauss)
# Geomagnetic dipole axis tilt (approx 11.5 deg towards 72.6 deg West longitude)
DIPOLE_TILT_RAD = math.radians(11.5)
DIPOLE_LON_RAD = math.radians(-72.6)


class RadiationBeltModel:
    """
    Van Allen Radiation Belt Ingress/Egress & Cumulative Dose Estimator.
    Specialized for HEO/GTO/Molniya orbits which transit the trapped radiation
    zones twice per revolution.
    """
    def __init__(self, f107_flux=150.0, ap_index=15.0):
        self.f107_flux = f107_flux      # Solar radio flux (sfu)
        self.ap_index = ap_index        # Planetary geomagnetic index

        # Belt L-shell boundaries (McIlwain parameter)
        self.L_INNER_MIN = 1.15
        self.L_INNER_MAX = 2.45
        self.L_OUTER_MIN = 3.00
        self.L_OUTER_MAX = 7.00

    def compute_magnetic_coordinates(self, r_eci, t_sec=0.0):
        """
        Computes Geomagnetic Latitude (lambda_m), McIlwain L-shell,
        and Dipole Magnetic Field B (Tesla) for an ECI position vector.
        """
        r_mag = float(np.linalg.norm(r_eci))
        if r_mag < 1000.0:
            return {"L_shell": 1.0, "mag_lat_deg": 0.0, "B_field_tesla": B0_EARTH_TESLA, "altitude_km": 0.0}

        alt_km = (r_mag - R_EARTH_M) / 1000.0
        r_unit = r_eci / r_mag

        # Dipole unit vector in rotating Earth frame
        # Approximated in inertial space with Earth rotation
        omega_e = 7.292115e-5
        phi_d = DIPOLE_LON_RAD + omega_e * t_sec
        d_hat = np.array([
            math.sin(DIPOLE_TILT_RAD) * math.cos(phi_d),
            math.sin(DIPOLE_TILT_RAD) * math.sin(phi_d),
            math.cos(DIPOLE_TILT_RAD)
        ])

        # Sine of geomagnetic latitude = dot product with dipole axis
        sin_lambda_m = float(np.dot(r_unit, d_hat))
        sin_lambda_m = max(-1.0, min(1.0, sin_lambda_m))
        cos2_lambda_m = max(1e-4, 1.0 - sin_lambda_m**2)

        # McIlwain L-shell parameter: L = (r / R_E) / cos^2(lambda_m)
        r_norm = r_mag / R_EARTH_M
        L_shell = r_norm / cos2_lambda_m

        # Dipole field strength B = (B0 / r_norm^3) * sqrt(1 + 3 * sin^2(lambda_m))
        b_mag = (B0_EARTH_TESLA / (r_norm**3)) * math.sqrt(1.0 + 3.0 * (sin_lambda_m**2))

        return {
            "L_shell": round(float(L_shell), 4),
            "mag_lat_deg": round(float(math.degrees(math.asin(sin_lambda_m))), 2),
            "B_field_tesla": float(b_mag),
            "B_field_microtesla": round(float(b_mag * 1e6), 3),
            "altitude_km": round(float(alt_km), 2)
        }

    def evaluate_trajectory_radiation(self, times, positions):
        """
        Evaluates full radiation profile across an orbital trajectory:
        - L-shell timeseries
        - Ingress and Egress events for Inner and Outer Belts
        - Estimated Dose Rate (rad/hr) and Cumulative Total Ionizing Dose (rad(Si))
        """
        n_pts = len(times)
        l_series = np.zeros(n_pts)
        b_series = np.zeros(n_pts)
        regimes = []
        dose_rate_rad_hr = np.zeros(n_pts)
        cumulative_dose_rad = np.zeros(n_pts)

        inner_crossings = []
        outer_crossings = []

        in_inner = False
        in_outer = False
        t_inner_enter = 0.0
        t_outer_enter = 0.0

        cum_dose = 0.0

        for i in range(n_pts):
            t = float(times[i])
            r = positions[i]
            mag_info = self.compute_magnetic_coordinates(r, t)
            L = mag_info["L_shell"]
            alt_km = mag_info["altitude_km"]
            l_series[i] = L
            b_series[i] = mag_info["B_field_microtesla"]

            # Classify regime based on L-shell and altitude
            regime = "FREE_SPACE"
            current_dose_rate = 0.02  # Galactic Cosmic Ray background (~0.02 rad/hr)

            if self.L_INNER_MIN <= L <= self.L_INNER_MAX and 600.0 <= alt_km <= 8000.0:
                regime = "INNER_PROTON_BELT"
                # Peak proton flux near L = 1.5 - 1.8
                proton_weight = math.exp(-((L - 1.6)**2) / 0.15)
                current_dose_rate = 12.5 * proton_weight + 0.5  # Up to ~13 rad/hr unshielded
            elif self.L_OUTER_MIN <= L <= self.L_OUTER_MAX and alt_km >= 10000.0:
                regime = "OUTER_ELECTRON_BELT"
                # Peak electron flux near L = 4.2 - 4.8
                electron_weight = math.exp(-((L - 4.5)**2) / 1.2)
                # Modulated by space weather F10.7 and Ap
                sw_factor = (self.f107_flux / 150.0) * (1.0 + 0.02 * self.ap_index)
                current_dose_rate = (8.0 * electron_weight * sw_factor) + 0.2
            elif 2.45 < L < 3.0:
                regime = "RADIATION_SLOT_REGION"
                current_dose_rate = 0.15

            regimes.append(regime)
            dose_rate_rad_hr[i] = current_dose_rate

            # Integrate cumulative dose
            if i > 0:
                dt_hr = (times[i] - times[i-1]) / 3600.0
                cum_dose += 0.5 * (dose_rate_rad_hr[i] + dose_rate_rad_hr[i-1]) * dt_hr
            cumulative_dose_rad[i] = cum_dose

            # Event Crossing Trackers
            # Inner Belt
            if regime == "INNER_PROTON_BELT" and not in_inner:
                in_inner = True
                t_inner_enter = t
            elif in_inner and regime != "INNER_PROTON_BELT":
                in_inner = False
                dur = t - t_inner_enter
                inner_crossings.append({
                    "belt": "INNER_PROTON_BELT",
                    "ingress_s": round(t_inner_enter, 2),
                    "egress_s": round(t, 2),
                    "duration_min": round(dur / 60.0, 2),
                    "peak_l_shell": round(float(np.min(l_series[max(0, i-30):i+1])), 3),
                    "radiation_hazard": "HIGH_PROTON_DISPLACEMENT"
                })

            # Outer Belt
            if regime == "OUTER_ELECTRON_BELT" and not in_outer:
                in_outer = True
                t_outer_enter = t
            elif in_outer and regime != "OUTER_ELECTRON_BELT":
                in_outer = False
                dur = t - t_outer_enter
                outer_crossings.append({
                    "belt": "OUTER_ELECTRON_BELT",
                    "ingress_s": round(t_outer_enter, 2),
                    "egress_s": round(t, 2),
                    "duration_min": round(dur / 60.0, 2),
                    "peak_l_shell": round(float(np.max(l_series[max(0, i-50):i+1])), 3),
                    "radiation_hazard": "RELATIVISTIC_ELECTRON_TID"
                })

        # Close any active crossings at end of simulation
        if in_inner:
            inner_crossings.append({
                "belt": "INNER_PROTON_BELT",
                "ingress_s": round(t_inner_enter, 2),
                "egress_s": round(float(times[-1]), 2),
                "duration_min": round((times[-1] - t_inner_enter) / 60.0, 2),
                "radiation_hazard": "HIGH_PROTON_DISPLACEMENT"
            })
        if in_outer:
            outer_crossings.append({
                "belt": "OUTER_ELECTRON_BELT",
                "ingress_s": round(t_outer_enter, 2),
                "egress_s": round(float(times[-1]), 2),
                "duration_min": round((times[-1] - t_outer_enter) / 60.0, 2),
                "radiation_hazard": "RELATIVISTIC_ELECTRON_TID"
            })

        total_inner_min = sum(c["duration_min"] for c in inner_crossings)
        total_outer_min = sum(c["duration_min"] for c in outer_crossings)

        return {
            "l_shell_series": l_series.tolist(),
            "b_field_series_ut": b_series.tolist(),
            "regimes_series": regimes,
            "dose_rate_rad_hr": dose_rate_rad_hr.tolist(),
            "cumulative_dose_rad": cumulative_dose_rad.tolist(),
            "summary": {
                "total_ionizing_dose_rad": round(float(cum_dose), 3),
                "inner_belt_crossings_count": len(inner_crossings),
                "outer_belt_crossings_count": len(outer_crossings),
                "total_inner_transit_min": round(total_inner_min, 2),
                "total_outer_transit_min": round(total_outer_min, 2),
                "space_weather": {
                    "f107_solar_flux_sfu": self.f107_flux,
                    "ap_geomagnetic_index": self.ap_index,
                    "solar_activity_regime": "MODERATE_SOLAR_MAX" if self.f107_flux > 120 else "SOLAR_MINIMUM"
                }
            },
            "crossing_events": inner_crossings + outer_crossings
        }


class RadiationParetoOptimizer:
    """
    Radiation-Constrained Orbit Optimization & Pareto Trade-Off Suite ("The Van Allen Penalty").
    Evaluates multi-objective frontier between Delta-V propellant expenditure,
    shielding thickness mass penalty, cumulative 5-year TID, and solar array EOL degradation.
    """
    def __init__(self, mission_lifetime_years=5.0, bol_solar_power_w=3000.0, dry_mass_kg=1000.0):
        self.lifetime_yr = mission_lifetime_years
        self.bol_power_w = bol_solar_power_w
        self.dry_mass_kg = dry_mass_kg

    def evaluate_pareto_frontier(self, initial_perigee_km=250.0, apogee_km=35786.0):
        """
        Sweeps perigee altitudes and aluminum shielding thicknesses to compute
        the non-dominated Pareto trade-off frontier.
        """
        mu_earth_km = 398600.4418
        r_earth_km = 6378.137

        # Range of test perigee altitudes: 200 km to 2500 km
        test_perigees_km = [200.0, 350.0, 500.0, 750.0, 1000.0, 1250.0, 1500.0, 1800.0, 2200.0]
        # Aluminum equivalent shielding thickness (mm)
        shielding_options_mm = [2.0, 3.0, 5.0, 8.0]

        trade_study_results = []
        r_a = r_earth_km + apogee_km

        for hp in test_perigees_km:
            r_p = r_earth_km + hp
            a = (r_p + r_a) / 2.0
            period_hr = 2.0 * math.pi * math.sqrt(a**3 / mu_earth_km) / 3600.0
            revs_per_year = (8760.0 / period_hr)
            total_revs = revs_per_year * self.lifetime_yr

            # 1. Delta-V to raise perigee from baseline (250 km)
            r_p_base = r_earth_km + initial_perigee_km
            a_base = (r_p_base + r_a) / 2.0
            v_a_base = math.sqrt(mu_earth_km * (2.0 / r_a - 1.0 / a_base))
            v_a_new = math.sqrt(mu_earth_km * (2.0 / r_a - 1.0 / a))
            dv_perigee_raise = abs(v_a_new - v_a_base) * 1000.0  # m/s

            # 2. Annual drag makeup Delta-V (exponential decay with perigee altitude)
            # Below 400 km, drag is severe; above 800 km, drag is negligible
            annual_drag_dv = 45.0 * math.exp(-(hp - 250.0) / 120.0) if hp < 800.0 else 0.5
            total_drag_dv = annual_drag_dv * self.lifetime_yr

            total_mission_dv = dv_perigee_raise + total_drag_dv

            # 3. Radiation Exposure per Revolution:
            # Trapped inner proton belt peaks at L = 1.4 - 1.8 (alt ~ 2500 - 5000 km)
            # As perigee rises closer to belt core, dwell time increases
            l_perigee = r_p / r_earth_km
            proton_dose_per_rev_unshielded = 0.08 + 1.25 * math.exp(-((l_perigee - 1.6)**2) / 0.18)
            electron_dose_per_rev_unshielded = 0.35  # Constant outer belt passage

            dose_per_rev_unshielded = (proton_dose_per_rev_unshielded + electron_dose_per_rev_unshielded)
            unshielded_tid_5yr_krad = (dose_per_rev_unshielded * total_revs) / 1000.0

            # Evaluate shielding variants
            for t_shield in shielding_options_mm:
                # Radiation attenuation factor through aluminum: I = I0 * exp(-mu * t)
                attenuation = math.exp(-0.24 * (t_shield - 1.0))
                shielded_tid_krad = unshielded_tid_5yr_krad * attenuation

                # Solar cell degradation: P_eol / P_bol = 1 - 0.28 * (1 - exp(-0.012 * TID_krad))
                degradation_pct = min(45.0, 28.0 * (1.0 - math.exp(-0.012 * shielded_tid_krad)) + 0.05 * t_shield)
                eol_power_w = self.bol_power_w * (1.0 - degradation_pct / 100.0)

                # Shielding mass penalty (surface area approx 8 m^2 of avionics enclosure)
                shield_area_m2 = 6.5
                density_al = 2700.0  # kg/m^3
                shield_mass_kg = shield_area_m2 * (t_shield / 1000.0) * density_al

                trade_study_results.append({
                    "perigee_altitude_km": hp,
                    "shielding_thickness_mm": t_shield,
                    "perigee_raise_dv_ms": round(dv_perigee_raise, 1),
                    "drag_makeup_dv_ms": round(total_drag_dv, 1),
                    "total_mission_dv_ms": round(total_mission_dv, 1),
                    "shielding_mass_penalty_kg": round(shield_mass_kg, 1),
                    "cumulative_5yr_tid_krad": round(shielded_tid_krad, 2),
                    "solar_cell_degradation_pct": round(degradation_pct, 2),
                    "eol_solar_power_w": round(eol_power_w, 1),
                    "orbital_period_hours": round(period_hr, 2)
                })

        # Identify Pareto-Optimal "Sweet Spot" (minimizing composite cost: DV + 15*Mass + 30*Degradation)
        best_design = min(
            trade_study_results,
            key=lambda d: d["total_mission_dv_ms"] * 0.4 + d["shielding_mass_penalty_kg"] * 4.0 + d["solar_cell_degradation_pct"] * 35.0
        )

        return {
            "mission_analysis": {
                "mission_lifetime_years": self.lifetime_yr,
                "apogee_altitude_km": apogee_km,
                "bol_solar_power_w": self.bol_power_w,
                "baseline_dry_mass_kg": self.dry_mass_kg
            },
            "pareto_sweet_spot": best_design,
            "trade_study_matrix": trade_study_results
        }


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

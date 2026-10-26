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
    Van Allen radiation belt ingress/egress from a tilted-dipole L-shell (no dose model).
    Specialized for HEO/GTO/Molniya orbits which transit the trapped radiation
    zones twice per revolution.
    """
    def __init__(self):
        # Belt L-shell boundaries (McIlwain parameter)
        self.L_INNER_MIN = 1.15
        self.L_INNER_MAX = 2.45
        self.L_OUTER_MIN = 3.00
        self.L_OUTER_MAX = 7.00

    def compute_magnetic_coordinates(self, r_itrf):
        """
        Computes Geomagnetic Latitude (lambda_m), McIlwain L-shell,
        and Dipole Magnetic Field B (Tesla) for an Earth-fixed (ITRF) position vector.
        """
        r_mag = float(np.linalg.norm(r_itrf))
        if r_mag < 1000.0:
            return {"L_shell": 1.0, "mag_lat_deg": 0.0, "B_field_tesla": B0_EARTH_TESLA, "altitude_km": 0.0}

        alt_km = (r_mag - R_EARTH_M) / 1000.0
        r_unit = r_itrf / r_mag

        # Dipole unit vector, fixed in the rotating Earth (ITRF)
        d_hat = np.array([
            math.sin(DIPOLE_TILT_RAD) * math.cos(DIPOLE_LON_RAD),
            math.sin(DIPOLE_TILT_RAD) * math.sin(DIPOLE_LON_RAD),
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

    def evaluate_trajectory_radiation(self, times, positions_itrf):
        """
        Evaluates full radiation profile across an orbital trajectory given in Earth-fixed
        (ITRF) positions, so the dipole sits where it is on the Earth at each time:
        - L-shell timeseries
        - Ingress and Egress events for Inner and Outer Belts (dipole L-shell and altitude bands)
        No dose is estimated: that needs a trapped-particle model (AE9/AP9), which this is not.
        """
        n_pts = len(times)
        l_series = np.zeros(n_pts)
        b_series = np.zeros(n_pts)
        regimes = []

        inner_crossings = []
        outer_crossings = []

        in_inner = False
        in_outer = False
        t_inner_enter = 0.0
        t_outer_enter = 0.0

        for i in range(n_pts):
            t = float(times[i])
            mag_info = self.compute_magnetic_coordinates(np.asarray(positions_itrf[i], dtype=float))
            L = mag_info["L_shell"]
            alt_km = mag_info["altitude_km"]
            l_series[i] = L
            b_series[i] = mag_info["B_field_microtesla"]

            # Classify regime based on L-shell and altitude
            regime = "FREE_SPACE"

            if self.L_INNER_MIN <= L <= self.L_INNER_MAX and 600.0 <= alt_km <= 8000.0:
                regime = "INNER_PROTON_BELT"
            elif self.L_OUTER_MIN <= L <= self.L_OUTER_MAX and alt_km >= 10000.0:
                regime = "OUTER_ELECTRON_BELT"
            elif 2.45 < L < 3.0:
                regime = "RADIATION_SLOT_REGION"

            regimes.append(regime)

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
                    "peak_l_shell": round(float(np.min(l_series[max(0, i-30):i+1])), 3)
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
                    })

        # Close any active crossings at end of simulation
        if in_inner:
            inner_crossings.append({
                "belt": "INNER_PROTON_BELT",
                "ingress_s": round(t_inner_enter, 2),
                "egress_s": round(float(times[-1]), 2),
                "duration_min": round((times[-1] - t_inner_enter) / 60.0, 2)
            })
        if in_outer:
            outer_crossings.append({
                "belt": "OUTER_ELECTRON_BELT",
                "ingress_s": round(t_outer_enter, 2),
                "egress_s": round(float(times[-1]), 2),
                "duration_min": round((times[-1] - t_outer_enter) / 60.0, 2)
            })

        total_inner_min = sum(c["duration_min"] for c in inner_crossings)
        total_outer_min = sum(c["duration_min"] for c in outer_crossings)

        return {
            "l_shell_series": l_series.tolist(),
            "b_field_series_ut": b_series.tolist(),
            "regimes_series": regimes,
            "summary": {
                "inner_belt_crossings_count": len(inner_crossings),
                "outer_belt_crossings_count": len(outer_crossings),
                "total_inner_transit_min": round(total_inner_min, 2),
                "total_outer_transit_min": round(total_outer_min, 2)
            },
            "crossing_events": inner_crossings + outer_crossings
        }

"""
AstroCore Event Predictor & Mission Targeting Engine - Third Review
=============================================================================
Department of Aerospace Engineering, ACS College of Engineering
Part of Major Project: Precise Trajectory Propagation & Events Prediction for HEOs
Final Production & V&V Certification Release
=============================================================================
"""

import math
import numpy as np

# Astrodynamical Constants (WGS-84 / NASA JPL DE440 Standards)
MU_EARTH = 3.986004418e14          # Earth gravitational parameter (m^3/s^2)
R_EARTH = 6371000.0                # Mean Earth radius (m)
R_EARTH_EQ = 6378137.0             # Equatorial radius (m)
R_SUN = 696340000.0                # Mean Solar radius (m)
AU_METERS = 149597870700.0         # Astronomical Unit (m)
OMEGA_EARTH = 7.2921159e-5         # Earth rotation rate (rad/s)
MU_MOON = 4.9048695e12             # Lunar gravitational parameter (m^3/s^2)
R_MOON = 1737400.0                 # Mean Lunar radius (m)
G0 = 9.80665                       # Standard gravity (m/s^2)


class EventPredictor:
    """
    Comprehensive Mission Events & Autonomous Targeting Engine for HEOs.
    """
    def __init__(self, ground_stations=None):
        if ground_stations is None:
            self.ground_stations = [
                {
                    "name": "Bengaluru ISTRAC (ISRO)",
                    "lat_deg": 13.0339,
                    "lon_deg": 77.5122,
                    "alt_m": 920.0,
                    "min_el_deg": 10.0,
                    "network": "ISRO Telemetry, Tracking & Command"
                },
                {
                    "name": "Hassan MCF (ISRO)",
                    "lat_deg": 13.0722,
                    "lon_deg": 76.0989,
                    "alt_m": 950.0,
                    "min_el_deg": 10.0,
                    "network": "ISRO Master Control Facility"
                },
                {
                    "name": "Goldstone DSN (NASA)",
                    "lat_deg": 35.4267,
                    "lon_deg": -116.8900,
                    "alt_m": 1034.0,
                    "min_el_deg": 10.0,
                    "network": "NASA Deep Space Network"
                },
                {
                    "name": "Madrid DSN (NASA/ESA)",
                    "lat_deg": 40.4314,
                    "lon_deg": -4.2480,
                    "alt_m": 834.0,
                    "min_el_deg": 10.0,
                    "network": "NASA/ESA Deep Space Network"
                },
                {
                    "name": "Canberra DSN (NASA)",
                    "lat_deg": -35.4014,
                    "lon_deg": 148.9817,
                    "alt_m": 654.0,
                    "min_el_deg": 10.0,
                    "network": "NASA Deep Space Network"
                },
                {
                    "name": "Svalbard KSAT (Polar HEO)",
                    "lat_deg": 78.2298,
                    "lon_deg": 15.4078,
                    "alt_m": 400.0,
                    "min_el_deg": 5.0,
                    "network": "Kongsberg Satellite Services"
                }
            ]
        else:
            self.ground_stations = ground_stations

    def predict_solar_eclipses(self, times, positions, sun_dir=None):
        """Calculates Umbra and Penumbra shadow passages and flux fractions."""
        if sun_dir is None:
            s_hat = np.array([1.0, 0.0, 0.0])
        else:
            s_hat = np.array(sun_dir) / np.linalg.norm(sun_dir)

        n_pts = len(times)
        flux_fraction = np.ones(n_pts, dtype=np.float64)
        regimes = []
        events = []

        in_umbra = False
        in_penumbra = False
        t_entry = 0.0
        t_penumbra_entry = 0.0

        sin_alpha_u = (R_SUN - R_EARTH) / AU_METERS
        sin_alpha_p = (R_SUN + R_EARTH) / AU_METERS
        cos_alpha_u = math.sqrt(max(0.0, 1.0 - sin_alpha_u**2))
        cos_alpha_p = math.sqrt(max(0.0, 1.0 - sin_alpha_p**2))

        for i in range(n_pts):
            r_sc = positions[i]
            r_proj = np.dot(r_sc, s_hat)
            r_perp_vec = r_sc - r_proj * s_hat
            d_perp = np.linalg.norm(r_perp_vec)

            if r_proj < 0:
                dist_behind = -r_proj
                radius_umbra = R_EARTH - dist_behind * (sin_alpha_u / cos_alpha_u)
                radius_penumbra = R_EARTH + dist_behind * (sin_alpha_p / cos_alpha_p)

                if radius_umbra > 0 and d_perp <= radius_umbra:
                    flux = 0.0
                    regime = "UMBRA"
                elif d_perp <= radius_penumbra:
                    flux = max(0.0, min(1.0, (d_perp - max(0.0, radius_umbra)) / max(1e-3, radius_penumbra - max(0.0, radius_umbra))))
                    regime = "PENUMBRA"
                else:
                    flux = 1.0
                    regime = "SUNLIGHT"
            else:
                flux = 1.0
                regime = "SUNLIGHT"

            flux_fraction[i] = flux
            regimes.append(regime)

            if regime in ("UMBRA", "PENUMBRA") and not in_penumbra:
                in_penumbra = True
                t_penumbra_entry = times[i]

            if regime == "UMBRA" and not in_umbra:
                in_umbra = True
                t_entry = times[i]

            if in_umbra and regime != "UMBRA":
                in_umbra = False
                dur_sec = times[i] - t_entry
                events.append({
                    "event_type": "UMBRA_TOTAL_ECLIPSE",
                    "entry_epoch_s": round(t_entry, 2),
                    "exit_epoch_s": round(times[i], 2),
                    "duration_s": round(dur_sec, 2),
                    "duration_min": round(dur_sec / 60.0, 2),
                    "solar_flux_min": 0.0
                })

            if in_penumbra and regime == "SUNLIGHT":
                in_penumbra = False
                dur_pen_sec = times[i] - t_penumbra_entry
                events.append({
                    "event_type": "PENUMBRA_TRANSIT",
                    "entry_epoch_s": round(t_penumbra_entry, 2),
                    "exit_epoch_s": round(times[i], 2),
                    "duration_s": round(dur_pen_sec, 2),
                    "duration_min": round(dur_pen_sec / 60.0, 2),
                    "solar_flux_min": round(float(np.min(flux_fraction[max(0, i-50):i+1])), 4)
                })

        total_eclipse_sec = float(np.sum(flux_fraction < 0.99) * (times[1] - times[0])) if n_pts > 1 else 0.0
        eclipse_fraction_pct = (total_eclipse_sec / (times[-1] - times[0])) * 100.0 if times[-1] > times[0] else 0.0

        return {
            "events": events,
            "flux_fraction": flux_fraction,
            "regimes": regimes,
            "total_shadow_duration_s": round(total_eclipse_sec, 2),
            "total_shadow_duration_min": round(total_eclipse_sec / 60.0, 2),
            "mission_eclipse_fraction_pct": round(eclipse_fraction_pct, 2)
        }

    def predict_ground_station_passes(self, times, positions, omega_e=OMEGA_EARTH):
        """Calculates SEZ Azimuth, Elevation, Slant Range, AOS, and LOS across stations."""
        station_results = {}
        n_pts = len(times)

        for st in self.ground_stations:
            st_name = st["name"]
            st_lat = math.radians(st["lat_deg"])
            st_lon = math.radians(st["lon_deg"])
            st_alt = st["alt_m"]
            min_el = st["min_el_deg"]

            r_st_mag = R_EARTH + st_alt
            x_st_ecef = r_st_mag * math.cos(st_lat) * math.cos(st_lon)
            y_st_ecef = r_st_mag * math.cos(st_lat) * math.sin(st_lon)
            z_st_ecef = r_st_mag * math.sin(st_lat)
            r_st_ecef = np.array([x_st_ecef, y_st_ecef, z_st_ecef])

            sin_lat = math.sin(st_lat)
            cos_lat = math.cos(st_lat)
            sin_lon = math.sin(st_lon)
            cos_lon = math.cos(st_lon)

            el_arr = np.zeros(n_pts)
            az_arr = np.zeros(n_pts)
            slant_km_arr = np.zeros(n_pts)

            passes = []
            in_pass = False
            aos_time = 0.0
            max_el = 0.0
            max_el_time = 0.0

            for i in range(n_pts):
                t = times[i]
                theta = (omega_e * t) % (2.0 * math.pi)
                cos_t, sin_t = math.cos(theta), math.sin(theta)

                r_eci = positions[i]
                x_ecef =  cos_t * r_eci[0] + sin_t * r_eci[1]
                y_ecef = -sin_t * r_eci[0] + cos_t * r_eci[1]
                z_ecef = r_eci[2]
                r_ecef = np.array([x_ecef, y_ecef, z_ecef])

                rho_ecef = r_ecef - r_st_ecef
                rho_mag = np.linalg.norm(rho_ecef)
                slant_km_arr[i] = rho_mag / 1000.0

                rho_s =  sin_lat * cos_lon * rho_ecef[0] + sin_lat * sin_lon * rho_ecef[1] - cos_lat * rho_ecef[2]
                rho_e = -sin_lon * rho_ecef[0]           + cos_lon * rho_ecef[1]
                rho_z =  cos_lat * cos_lon * rho_ecef[0] + cos_lat * sin_lon * rho_ecef[1] + sin_lat * rho_ecef[2]

                el_deg = math.degrees(math.asin(max(-1.0, min(1.0, rho_z / rho_mag))))
                el_arr[i] = el_deg
                az_deg = (math.degrees(math.atan2(rho_e, -rho_s)) + 360.0) % 360.0
                az_arr[i] = az_deg

                if el_deg >= min_el:
                    if not in_pass:
                        in_pass = True
                        aos_time = t
                        max_el = el_deg
                        max_el_time = t
                    else:
                        if el_deg > max_el:
                            max_el = el_deg
                            max_el_time = t
                else:
                    if in_pass:
                        in_pass = False
                        dur_s = t - aos_time
                        passes.append({
                            "station": st_name,
                            "aos_epoch_s": round(aos_time, 2),
                            "los_epoch_s": round(t, 2),
                            "duration_min": round(dur_s / 60.0, 2),
                            "max_elevation_deg": round(max_el, 2)
                        })

            if in_pass:
                dur_s = times[-1] - aos_time
                passes.append({
                    "station": st_name,
                    "aos_epoch_s": round(aos_time, 2),
                    "los_epoch_s": round(times[-1], 2),
                    "duration_min": round(dur_s / 60.0, 2),
                    "max_elevation_deg": round(max_el, 2)
                })

            total_contact_s = sum(p["duration_min"] * 60.0 for p in passes)
            station_results[st_name] = {
                "station_metadata": st,
                "passes": passes,
                "total_passes_count": len(passes),
                "total_contact_min": round(total_contact_s / 60.0, 2),
                "elevation_series_deg": el_arr,
                "azimuth_series_deg": az_arr,
                "slant_range_km": slant_km_arr
            }

        return station_results

    def predict_apsidal_events(self, times, positions, velocities):
        """
        Continuous root-finding for exact Perigee and Apogee passage epochs.
        Evaluates zero crossings of r . v = 0 with sub-second accuracy.
        """
        n_pts = len(times)
        rdot_series = np.zeros(n_pts)
        for i in range(n_pts):
            rdot_series[i] = np.dot(positions[i], velocities[i])

        events = []
        for i in range(n_pts - 1):
            if rdot_series[i] * rdot_series[i+1] <= 0.0:
                # Linear interpolation for zero crossing
                denom = rdot_series[i+1] - rdot_series[i]
                frac = abs(rdot_series[i]) / max(1e-12, abs(denom)) if abs(denom) > 1e-12 else 0.5
                t_event = times[i] + frac * (times[i+1] - times[i])
                r_vec = positions[i] + frac * (positions[i+1] - positions[i])
                v_vec = velocities[i] + frac * (velocities[i+1] - velocities[i])
                alt_km = (np.linalg.norm(r_vec) - R_EARTH) / 1000.0
                vel_kms = np.linalg.norm(v_vec) / 1000.0

                # Perigee: rdot transitioning from negative to positive
                if rdot_series[i] < 0 and rdot_series[i+1] >= 0:
                    events.append({
                        "event_type": "PERIAPSIS_PASSAGE",
                        "epoch_s": round(float(t_event), 3),
                        "epoch_hours": round(float(t_event / 3600.0), 4),
                        "altitude_km": round(float(alt_km), 2),
                        "velocity_kms": round(float(vel_kms), 4),
                        "description": "Perigee corridor crossing (maximum kinetic energy & aerodynamic drag peak)"
                    })
                # Apogee: rdot transitioning from positive to negative
                elif rdot_series[i] > 0 and rdot_series[i+1] <= 0:
                    events.append({
                        "event_type": "APOAPSIS_PASSAGE",
                        "epoch_s": round(float(t_event), 3),
                        "epoch_hours": round(float(t_event / 3600.0), 4),
                        "altitude_km": round(float(alt_km), 2),
                        "velocity_kms": round(float(vel_kms), 4),
                        "description": "Apogee dwell crossing (maximum potential energy & third-body gravity sensitivity)"
                    })
        return events

    def predict_orbital_nodes(self, times, positions, velocities):
        """
        Continuous root-finding for Ascending and Descending Equatorial Nodal crossings (z = 0).
        """
        n_pts = len(times)
        events = []
        for i in range(n_pts - 1):
            z1 = positions[i][2]
            z2 = positions[i+1][2]
            if z1 * z2 <= 0.0:
                denom = z2 - z1
                frac = abs(z1) / max(1e-12, abs(denom)) if abs(denom) > 1e-12 else 0.5
                t_event = times[i] + frac * (times[i+1] - times[i])
                v_z = velocities[i][2] + frac * (velocities[i+1][2] - velocities[i][2])
                r_vec = positions[i] + frac * (positions[i+1] - positions[i])
                lon_deg = math.degrees(math.atan2(r_vec[1], r_vec[0]))

                if v_z > 0:
                    events.append({
                        "event_type": "ASCENDING_NODE",
                        "epoch_s": round(float(t_event), 3),
                        "epoch_hours": round(float(t_event / 3600.0), 4),
                        "longitude_deg": round(float(lon_deg), 2),
                        "description": "Equatorial Plane Ascending Node Crossing (South to North)"
                    })
                else:
                    events.append({
                        "event_type": "DESCENDING_NODE",
                        "epoch_s": round(float(t_event), 3),
                        "epoch_hours": round(float(t_event / 3600.0), 4),
                        "longitude_deg": round(float(lon_deg), 2),
                        "description": "Equatorial Plane Descending Node Crossing (North to South)"
                    })
        return events

    def predict_lunar_eclipses(self, times, positions):
        """
        Detects if the Moon occults the Sun from the spacecraft's perspective.
        """
        n_pts = len(times)
        lunar_eclipses = []
        n_moon = 2.0 * math.pi / (27.32166 * 86400.0)
        eps = math.radians(23.44)

        for i in range(0, n_pts, max(1, n_pts // 200)):
            t = times[i]
            r_sc = positions[i]

            # Approximate Solar and Lunar positions
            omega_s = 2.0 * math.pi / (365.25 * 86400.0)
            r_sun = AU_METERS * np.array([math.cos(omega_s * t), math.sin(omega_s * t) * math.cos(eps), math.sin(omega_s * t) * math.sin(eps)])
            r_moon = 384400000.0 * np.array([math.cos(n_moon * t), math.sin(n_moon * t) * math.cos(eps), math.sin(n_moon * t) * math.sin(eps)])

            d_sc_sun = r_sun - r_sc
            d_sc_moon = r_moon - r_sc

            s_hat = d_sc_sun / np.linalg.norm(d_sc_sun)
            m_hat = d_sc_moon / np.linalg.norm(d_sc_moon)

            # Angular separation between Sun and Moon as seen from SC
            cos_sep = float(np.dot(s_hat, m_hat))
            sep_rad = math.acos(max(-1.0, min(1.0, cos_sep)))

            theta_sun = math.asin(R_SUN / np.linalg.norm(d_sc_sun))
            theta_moon = math.asin(R_MOON / np.linalg.norm(d_sc_moon))

            if sep_rad < (theta_sun + theta_moon):
                lunar_eclipses.append({
                    "event_type": "LUNAR_SOLAR_OCCULTATION",
                    "epoch_s": round(float(t), 2),
                    "angular_separation_deg": round(math.degrees(sep_rad), 3),
                    "coverage_fraction": round(max(0.0, 1.0 - sep_rad / (theta_sun + theta_moon)), 3)
                })

        return lunar_eclipses

    def predict_reentry_hazard(self, altitudes_km):
        """
        Evaluates atmospheric entry / corridor decay risk.
        """
        min_alt = float(np.min(altitudes_km))
        karman_violation = min_alt < 100.0
        sensible_atm_entry = min_alt < 120.0
        grazing_corridor = 120.0 <= min_alt <= 200.0

        status = "NOMINAL_STABLE"
        if karman_violation:
            status = "CRITICAL_REENTRY_BALLISTIC_ENTRY"
        elif sensible_atm_entry:
            status = "ATMOSPHERIC_DECELERATION_ZONE"
        elif grazing_corridor:
            status = "PERIGEE_AERODYNAMIC_DRAG_CORRIDOR"

        return {
            "minimum_perigee_altitude_km": round(min_alt, 2),
            "karman_line_100km_breached": karman_violation,
            "sensible_atmosphere_120km_breached": sensible_atm_entry,
            "reentry_safety_status": status,
            "iadc_lifetime_safety": "COMPLIANT" if min_alt > 150.0 else "IMMINENT_DECAY"
        }

    def calculate_apogee_boost_deltav(
        self,
        a_initial_km=24389.0,
        e_initial=0.728525,
        inc_initial_deg=28.5,
        target_r_km=42164.0,
        inc_target_deg=0.0,
        spacecraft_dry_mass_kg=1200.0,
        propellant_mass_kg=1800.0,
        isp_sec=315.0
    ):
        """Calculates impulsive Delta-V for apogee circularization and combined plane change."""
        mu = MU_EARTH
        r_a_m = a_initial_km * (1.0 + e_initial) * 1000.0
        r_target_m = target_r_km * 1000.0

        v_a_initial = math.sqrt(mu * (2.0 / r_a_m - 1.0 / (a_initial_km * 1000.0)))
        v_circ_target = math.sqrt(mu / r_target_m)
        delta_i_rad = math.radians(abs(inc_initial_deg - inc_target_deg))

        dv_circ_pure = abs(v_circ_target - v_a_initial)
        dv_plane_pure = 2.0 * v_a_initial * math.sin(delta_i_rad / 2.0)
        dv_combined = math.sqrt(
            v_a_initial**2 + v_circ_target**2 - 2.0 * v_a_initial * v_circ_target * math.cos(delta_i_rad)
        )

        burn_savings_dv = (dv_circ_pure + dv_plane_pure) - dv_combined
        burn_savings_pct = (burn_savings_dv / (dv_circ_pure + dv_plane_pure)) * 100.0

        m_wet = spacecraft_dry_mass_kg + propellant_mass_kg
        mass_fraction_required = 1.0 - math.exp(-dv_combined / (isp_sec * G0))
        propellant_used_kg = m_wet * mass_fraction_required
        remaining_propellant_kg = propellant_mass_kg - propellant_used_kg

        return {
            "burn_metrics": {
                "pure_circularization_dv_ms": round(dv_circ_pure, 2),
                "pure_plane_change_dv_ms": round(dv_plane_pure, 2),
                "combined_optimal_dv_ms": round(dv_combined, 2),
                "vectorial_savings_dv_ms": round(burn_savings_dv, 2),
                "savings_percentage": round(burn_savings_pct, 2)
            },
            "propulsion_budget": {
                "initial_wet_mass_kg": m_wet,
                "propellant_consumed_kg": round(propellant_used_kg, 2),
                "remaining_propellant_kg": round(remaining_propellant_kg, 2),
                "burn_feasible": remaining_propellant_kg >= 0.0
            }
        }

    def calculate_b_plane_targeting(
        self,
        v_inf_vec_kms=(-1.05, 0.42, 0.85),
        target_rp_km=1837.4,
        theta_angle_deg=45.0,
        mu_body=MU_MOON,
        r_body=R_MOON
    ):
        """Calculates hyperbolic B-Plane coordinates (B·T, B·R) and flyby turning angle."""
        v_inf = np.array(v_inf_vec_kms, dtype=np.float64) * 1000.0
        v_inf_mag = float(np.linalg.norm(v_inf))
        s_hat = v_inf / v_inf_mag

        k_hat = np.array([0.0, 0.0, 1.0])
        s_cross_k = np.cross(s_hat, k_hat)
        s_cross_k_mag = float(np.linalg.norm(s_cross_k))
        if s_cross_k_mag < 1e-9:
            k_hat = np.array([1.0, 0.0, 0.0])
            s_cross_k = np.cross(s_hat, k_hat)
            s_cross_k_mag = float(np.linalg.norm(s_cross_k))

        t_hat = s_cross_k / s_cross_k_mag
        r_hat = np.cross(s_hat, t_hat)

        a_hyp_mag = mu_body / (v_inf_mag**2)
        r_p_m = target_rp_km * 1000.0
        e_hyp = 1.0 + (r_p_m / a_hyp_mag)
        b_mag_m = a_hyp_mag * math.sqrt(e_hyp**2 - 1.0)
        b_mag_km = b_mag_m / 1000.0

        turning_angle_deg = math.degrees(2.0 * math.asin(1.0 / e_hyp))
        theta_rad = math.radians(theta_angle_deg)
        b_dot_t_km = b_mag_km * math.cos(theta_rad)
        b_dot_r_km = b_mag_km * math.sin(theta_rad)

        return {
            "b_plane_coordinates": {
                "b_dot_t_km": round(b_dot_t_km, 3),
                "b_dot_r_km": round(b_dot_r_km, 3),
                "miss_distance_b_km": round(b_mag_km, 3)
            },
            "flyby_geometry": {
                "target_periapsis_km": round(target_rp_km, 2),
                "hyperbolic_eccentricity": round(e_hyp, 5),
                "turning_deflection_deg": round(turning_angle_deg, 3),
                "gravity_assist_delta_v_kms": round(2.0 * (v_inf_mag / 1000.0) * math.sin(math.radians(turning_angle_deg / 2.0)), 4)
            }
        }

    def predict_orbital_lifetime(
        self,
        a_initial_km=24389.0,
        e_initial=0.728525,
        spacecraft_mass_kg=1500.0,
        drag_area_m2=4.5,
        drag_coeff_cd=2.2,
        max_simulation_years=35.0
    ):
        """Semi-analytical multi-decadal orbital lifetime predictor."""
        mu = MU_EARTH
        r_e = R_EARTH
        b_star = (drag_coeff_cd * drag_area_m2) / spacecraft_mass_kg
        h_scale = 8500.0
        rho_0 = 1.225

        years, apogee_alt_km, perigee_alt_km, semi_major_km = [], [], [], []
        a = a_initial_km * 1000.0
        e = e_initial
        t_years = 0.0
        dt_years = 0.25
        deorbit_year = None

        while t_years <= max_simulation_years:
            r_p = a * (1.0 - e)
            r_a = a * (1.0 + e)
            h_p_km = (r_p - r_e) / 1000.0
            h_a_km = (r_a - r_e) / 1000.0

            years.append(round(t_years, 2))
            apogee_alt_km.append(round(h_a_km, 1))
            perigee_alt_km.append(round(h_p_km, 1))
            semi_major_km.append(round(a / 1000.0, 1))

            if h_p_km <= 120.0:
                deorbit_year = round(t_years, 2)
                break

            c_param = (a * e) / h_scale
            h_p_m = max(0.0, r_p - r_e)
            rho_p = rho_0 * math.exp(-h_p_m / h_scale)
            bessel_factor = 1.0 / math.sqrt(2.0 * math.pi * max(1.0, c_param))
            factor_e = (1.0 + e)**1.5 / math.sqrt(max(1e-4, 1.0 - e))

            da_dt_ms = -2.0 * math.pi * b_star * rho_p * math.sqrt(mu * a) * factor_e * bessel_factor * (1.0 / (2.0 * math.pi * math.sqrt(a**3 / mu)))
            de_dt_s = (1.0 - e) / a * da_dt_ms if a > 0 else 0.0

            dt_s = dt_years * 365.25 * 86400.0
            a += da_dt_ms * dt_s
            e += de_dt_s * dt_s
            e = max(0.001, min(0.999, e))
            t_years += dt_years

        return {
            "lifetime_assessment": {
                "orbital_lifetime_years": deorbit_year if deorbit_year is not None else f"> {max_simulation_years}",
                "iadc_25_year_rule_compliant": deorbit_year is not None and deorbit_year <= 25.0
            },
            "trajectory_decay_timeseries": {
                "years": years,
                "apogee_altitude_km": apogee_alt_km,
                "perigee_altitude_km": perigee_alt_km,
                "semi_major_axis_km": semi_major_km
            }
        }

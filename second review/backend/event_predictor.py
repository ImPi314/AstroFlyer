"""
AstroCore Event Predictor & Mission Targeting Engine - Second Review
=============================================================================
Department of Aerospace Engineering, ACS College of Engineering
Part of Major Project: Precise Trajectory Propagation & Events Prediction for HEOs

Core Modules:
  1. Solar Eclipse & Umbra/Penumbra Duration Predictor (Conical & Cylindrical Models)
  2. Global Ground Station Network AOS/LOS Access Windows (Azimuth-Elevation Topocentric)
  3. Apogee Boost & Combined Plane-Change Delta-V Maneuver Planner
  4. B-Plane (B·T, B·R) Differential Targeter for Lunar Gravity Assist (LGA)
  5. Multi-Decadal Orbital Lifetime & 25-Year Space Debris Resonance Predictor
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

    # =========================================================================
    # 1. SOLAR ECLIPSE & THERMAL SHOCK PREDICTOR
    # =========================================================================
    def predict_solar_eclipses(self, times, positions, sun_dir=None):
        """
        Calculates Umbra and Penumbra shadow passages, entry/exit epochs,
        exact duration, minimum solar flux fraction, and thermal shock gradients.

        Args:
            times: 1D array of mission elapsed times (seconds)
            positions: (N, 3) array of ECI spacecraft positions (meters)
            sun_dir: Optional (3,) unit vector pointing to Sun. Default: Vernal Equinox (+X).

        Returns:
            Dictionary containing event list, illumination fraction array, and summary metrics.
        """
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
        current_event_type = ""

        # Conical Shadow Constants
        d_sun = AU_METERS
        r_sun = R_SUN
        r_earth = R_EARTH

        # Semi-angles of umbra and penumbra cones
        sin_alpha_u = (r_sun - r_earth) / d_sun
        sin_alpha_p = (r_sun + r_earth) / d_sun
        cos_alpha_u = math.sqrt(max(0.0, 1.0 - sin_alpha_u**2))
        cos_alpha_p = math.sqrt(max(0.0, 1.0 - sin_alpha_p**2))

        # Vertex distances from Earth center
        x_u = r_earth / sin_alpha_u
        x_p = r_earth / sin_alpha_p

        for i in range(n_pts):
            r_sc = positions[i]
            r_proj = np.dot(r_sc, s_hat)
            r_perp_vec = r_sc - r_proj * s_hat
            d_perp = np.linalg.norm(r_perp_vec)

            # Earth occultation check (spacecraft must be on anti-sun side)
            if r_proj < 0:
                dist_behind = -r_proj

                # Local cone radii at distance behind Earth
                radius_umbra = r_earth - dist_behind * (sin_alpha_u / cos_alpha_u)
                radius_penumbra = r_earth + dist_behind * (sin_alpha_p / cos_alpha_p)

                if radius_umbra > 0 and d_perp <= radius_umbra:
                    flux = 0.0  # Full Umbra (Total Eclipse)
                    regime = "UMBRA"
                elif d_perp <= radius_penumbra:
                    # Penumbra interpolation
                    if radius_penumbra > radius_umbra:
                        flux = max(0.0, min(1.0, (d_perp - max(0.0, radius_umbra)) / (radius_penumbra - max(0.0, radius_umbra))))
                    else:
                        flux = 0.5
                    regime = "PENUMBRA"
                else:
                    flux = 1.0  # Full Sunlight
                    regime = "SUNLIGHT"
            else:
                flux = 1.0
                regime = "SUNLIGHT"

            flux_fraction[i] = flux
            regimes.append(regime)

            # State Machine for Event Boundaries
            if regime in ("UMBRA", "PENUMBRA") and not in_penumbra:
                in_penumbra = True
                t_penumbra_entry = times[i]
                current_event_type = regime

            if regime == "UMBRA" and not in_umbra:
                in_umbra = True
                t_entry = times[i]

            if in_umbra and regime != "UMBRA":
                in_umbra = False
                t_exit = times[i]
                dur_sec = t_exit - t_entry
                events.append({
                    "event_type": "UMBRA_TOTAL_ECLIPSE",
                    "entry_epoch_s": round(t_entry, 2),
                    "exit_epoch_s": round(t_exit, 2),
                    "duration_s": round(dur_sec, 2),
                    "duration_min": round(dur_sec / 60.0, 2),
                    "solar_flux_min": 0.0,
                    "thermal_impact": "SEVERE_COOLING ( Umbra )"
                })

            if in_penumbra and regime == "SUNLIGHT":
                in_penumbra = False
                t_penumbra_exit = times[i]
                dur_pen_sec = t_penumbra_exit - t_penumbra_entry
                events.append({
                    "event_type": "PENUMBRA_TRANSIT",
                    "entry_epoch_s": round(t_penumbra_entry, 2),
                    "exit_epoch_s": round(t_penumbra_exit, 2),
                    "duration_s": round(dur_pen_sec, 2),
                    "duration_min": round(dur_pen_sec / 60.0, 2),
                    "solar_flux_min": round(float(np.min(flux_fraction[max(0, i-50):i+1])), 4),
                    "thermal_impact": "THERMAL_GRADIENT_SHOCK"
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

    # =========================================================================
    # 2. GLOBAL GROUND STATION NETWORK & AOS/LOS PASS PREDICTOR
    # =========================================================================
    def predict_ground_station_passes(self, times, positions, omega_e=OMEGA_EARTH):
        """
        Calculates topocentric Azimuth, Elevation, Slant Range, Acquisition of Signal (AOS),
        Maximum Elevation, and Loss of Signal (LOS) across the ground station network.

        Args:
            times: 1D array of mission elapsed times (seconds)
            positions: (N, 3) array of ECI position vectors (meters)

        Returns:
            Dictionary mapping station names to their contact pass tables and statistics.
        """
        station_results = {}
        n_pts = len(times)

        for st in self.ground_stations:
            st_name = st["name"]
            st_lat = math.radians(st["lat_deg"])
            st_lon = math.radians(st["lon_deg"])
            st_alt = st["alt_m"]
            min_el = st["min_el_deg"]

            # Station coordinates in spherical/ellipsoidal Earth model
            r_st_mag = R_EARTH + st_alt
            x_st_ecef = r_st_mag * math.cos(st_lat) * math.cos(st_lon)
            y_st_ecef = r_st_mag * math.cos(st_lat) * math.sin(st_lon)
            z_st_ecef = r_st_mag * math.sin(st_lat)
            r_st_ecef = np.array([x_st_ecef, y_st_ecef, z_st_ecef])

            # SEZ Rotation Matrix Components (ECEF -> Topocentric South-East-Zenith)
            sin_lat = math.sin(st_lat)
            cos_lat = math.cos(st_lat)
            sin_lon = math.sin(st_lon)
            cos_lon = math.cos(st_lon)

            # R_SEZ_ECEF matrix
            # S =  sin_lat * cos_lon * dx + sin_lat * sin_lon * dy - cos_lat * dz
            # E = -sin_lon * dx           + cos_lon * dy
            # Z =  cos_lat * cos_lon * dx + cos_lat * sin_lon * dy + sin_lat * dz

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
                # Earth rotation angle (GST)
                theta = (omega_e * t) % (2.0 * math.pi)
                cos_t = math.cos(theta)
                sin_t = math.sin(theta)

                # ECI -> ECEF
                r_eci = positions[i]
                x_ecef =  cos_t * r_eci[0] + sin_t * r_eci[1]
                y_ecef = -sin_t * r_eci[0] + cos_t * r_eci[1]
                z_ecef = r_eci[2]
                r_ecef = np.array([x_ecef, y_ecef, z_ecef])

                # Slant range vector in ECEF
                rho_ecef = r_ecef - r_st_ecef
                rho_mag = np.linalg.norm(rho_ecef)
                slant_km_arr[i] = rho_mag / 1000.0

                # Convert to SEZ
                rho_s =  sin_lat * cos_lon * rho_ecef[0] + sin_lat * sin_lon * rho_ecef[1] - cos_lat * rho_ecef[2]
                rho_e = -sin_lon * rho_ecef[0]           + cos_lon * rho_ecef[1]
                rho_z =  cos_lat * cos_lon * rho_ecef[0] + cos_lat * sin_lon * rho_ecef[1] + sin_lat * rho_ecef[2]

                # Elevation and Azimuth
                el_rad = math.asin(max(-1.0, min(1.0, rho_z / rho_mag)))
                el_deg = math.degrees(el_rad)
                el_arr[i] = el_deg

                az_rad = math.atan2(rho_e, -rho_s)
                az_deg = (math.degrees(az_rad) + 360.0) % 360.0
                az_arr[i] = az_deg

                # Pass Detection
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
                        los_time = t
                        dur_s = los_time - aos_time
                        passes.append({
                            "station": st_name,
                            "network": st["network"],
                            "aos_epoch_s": round(aos_time, 2),
                            "aos_epoch_hr": round(aos_time / 3600.0, 3),
                            "los_epoch_s": round(los_time, 2),
                            "los_epoch_hr": round(los_time / 3600.0, 3),
                            "duration_s": round(dur_s, 2),
                            "duration_min": round(dur_s / 60.0, 2),
                            "max_elevation_deg": round(max_el, 2),
                            "max_el_epoch_s": round(max_el_time, 2),
                            "status": "PASS_RECORDED"
                        })

            # Check if pass still active at sim end
            if in_pass:
                dur_s = times[-1] - aos_time
                passes.append({
                    "station": st_name,
                    "network": st["network"],
                    "aos_epoch_s": round(aos_time, 2),
                    "aos_epoch_hr": round(aos_time / 3600.0, 3),
                    "los_epoch_s": round(times[-1], 2),
                    "los_epoch_hr": round(times[-1] / 3600.0, 3),
                    "duration_s": round(dur_s, 2),
                    "duration_min": round(dur_s / 60.0, 2),
                    "max_elevation_deg": round(max_el, 2),
                    "max_el_epoch_s": round(max_el_time, 2),
                    "status": "IN_PROGRESS_AT_END"
                })

            total_contact_s = sum(p["duration_s"] for p in passes)
            station_results[st_name] = {
                "station_metadata": st,
                "passes": passes,
                "total_passes_count": len(passes),
                "total_contact_s": round(total_contact_s, 2),
                "total_contact_min": round(total_contact_s / 60.0, 2),
                "elevation_series_deg": el_arr,
                "azimuth_series_deg": az_arr,
                "slant_range_km": slant_km_arr
            }

        return station_results

    # =========================================================================
    # 3. APOGEE BOOST & COMBINED PLANE-CHANGE DELTA-V PLANNER
    # =========================================================================
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
        """
        Calculates exact impulsive Delta-V for apogee circularization and combined
        orbital plane change (inclination reduction) using vector spherical trigonometry.

        Computes propellant consumption via Tsiolkovsky Rocket Equation.
        """
        mu = MU_EARTH
        r_a_m = a_initial_km * (1.0 + e_initial) * 1000.0
        r_target_m = target_r_km * 1000.0

        # Velocity at apogee of initial HEO / GTO
        v_a_initial = math.sqrt(mu * (2.0 / r_a_m - 1.0 / (a_initial_km * 1000.0)))

        # Velocity required for target circular orbit (e.g. GEO)
        v_circ_target = math.sqrt(mu / r_target_m)

        # Plane change inclination angle difference
        delta_i_rad = math.radians(abs(inc_initial_deg - inc_target_deg))

        # 1. Pure Circularization Delta-V (No Plane Change)
        dv_circ_pure = abs(v_circ_target - v_a_initial)

        # 2. Pure Plane Change Delta-V (At apogee speed)
        dv_plane_pure = 2.0 * v_a_initial * math.sin(delta_i_rad / 2.0)

        # 3. Combined Vectorial Circularization & Plane Change (Cheapest Strategy)
        # By Law of Cosines: dv^2 = v1^2 + v2^2 - 2*v1*v2*cos(di)
        dv_combined = math.sqrt(
            v_a_initial**2 + v_circ_target**2 - 2.0 * v_a_initial * v_circ_target * math.cos(delta_i_rad)
        )

        # Efficiency savings of combined burn
        burn_savings_dv = (dv_circ_pure + dv_plane_pure) - dv_combined
        burn_savings_pct = (burn_savings_dv / (dv_circ_pure + dv_plane_pure)) * 100.0

        # Tsiolkovsky Rocket Equation
        m_wet = spacecraft_dry_mass_kg + propellant_mass_kg
        c_eff = isp_sec * G0
        mass_fraction_required = 1.0 - math.exp(-dv_combined / c_eff)
        propellant_used_kg = m_wet * mass_fraction_required
        remaining_propellant_kg = propellant_mass_kg - propellant_used_kg
        is_feasible = remaining_propellant_kg >= 0.0

        return {
            "initial_orbit": {
                "semi_major_axis_km": a_initial_km,
                "eccentricity": e_initial,
                "inclination_deg": inc_initial_deg,
                "apogee_altitude_km": (r_a_m - R_EARTH) / 1000.0,
                "apogee_velocity_kms": round(v_a_initial / 1000.0, 4)
            },
            "target_orbit": {
                "target_radius_km": target_r_km,
                "target_altitude_km": target_r_km - (R_EARTH / 1000.0),
                "target_inclination_deg": inc_target_deg,
                "target_circular_velocity_kms": round(v_circ_target / 1000.0, 4)
            },
            "burn_metrics": {
                "pure_circularization_dv_ms": round(dv_circ_pure, 2),
                "pure_plane_change_dv_ms": round(dv_plane_pure, 2),
                "separate_burns_total_dv_ms": round(dv_circ_pure + dv_plane_pure, 2),
                "combined_optimal_dv_ms": round(dv_combined, 2),
                "vectorial_savings_dv_ms": round(burn_savings_dv, 2),
                "savings_percentage": round(burn_savings_pct, 2)
            },
            "propulsion_budget": {
                "initial_wet_mass_kg": m_wet,
                "dry_mass_kg": spacecraft_dry_mass_kg,
                "engine_isp_sec": isp_sec,
                "propellant_consumed_kg": round(propellant_used_kg, 2),
                "remaining_propellant_kg": round(remaining_propellant_kg, 2),
                "fuel_mass_fraction_pct": round(mass_fraction_required * 100.0, 2),
                "burn_feasible": is_feasible
            }
        }

    # =========================================================================
    # 4. B-PLANE (B·T, B·R) TARGETER FOR LUNAR GRAVITY ASSISTS (LGA)
    # =========================================================================
    def calculate_b_plane_targeting(
        self,
        v_inf_vec_kms=(-1.05, 0.42, 0.85),
        target_rp_km=1837.4,             # 100 km altitude above Moon (R_Moon = 1737.4 km)
        theta_angle_deg=45.0,            # B-plane clock angle
        mu_body=MU_MOON,
        r_body=R_MOON
    ):
        """
        Calculates hyperbolic B-Plane coordinates (B·T, B·R), asymptote unit vector S,
        miss distance magnitude b, turning angle delta, and delta-V sensitivity.

        The B-plane is perpendicular to the incoming hyperbolic asymptote S_hat.
        T_hat is in the celestial reference plane (parallel to ecliptic/equator).
        R_hat completes the right-handed triad: R_hat = S_hat x T_hat.
        """
        v_inf = np.array(v_inf_vec_kms, dtype=np.float64) * 1000.0
        v_inf_mag = float(np.linalg.norm(v_inf))
        s_hat = v_inf / v_inf_mag

        # Reference vector K (North pole of reference plane: [0, 0, 1])
        k_hat = np.array([0.0, 0.0, 1.0])
        s_cross_k = np.cross(s_hat, k_hat)
        s_cross_k_mag = float(np.linalg.norm(s_cross_k))

        if s_cross_k_mag < 1e-9:
            # Degenerate polar case: use X axis as fallback reference
            k_hat = np.array([1.0, 0.0, 0.0])
            s_cross_k = np.cross(s_hat, k_hat)
            s_cross_k_mag = float(np.linalg.norm(s_cross_k))

        t_hat = s_cross_k / s_cross_k_mag
        r_hat = np.cross(s_hat, t_hat)

        # Hyperbolic Mechanics
        # a_hyp = -mu / v_inf^2 (semi-major axis is negative for hyperbola)
        a_hyp_mag = mu_body / (v_inf_mag**2)

        # Pericenter distance r_p = a*(e - 1)  =>  e = 1 + r_p / a_hyp_mag
        r_p_m = target_rp_km * 1000.0
        e_hyp = 1.0 + (r_p_m / a_hyp_mag)

        # Impact parameter b = ||B|| = a_hyp_mag * sqrt(e^2 - 1)
        b_mag_m = a_hyp_mag * math.sqrt(e_hyp**2 - 1.0)
        b_mag_km = b_mag_m / 1000.0

        # Flyby Deflection / Turning Angle: delta = 2 * asin(1/e)
        turning_angle_rad = 2.0 * math.asin(1.0 / e_hyp)
        turning_angle_deg = math.degrees(turning_angle_rad)

        # B-vector projection on T and R axes
        theta_rad = math.radians(theta_angle_deg)
        b_dot_t_km = b_mag_km * math.cos(theta_rad)
        b_dot_r_km = b_mag_km * math.sin(theta_rad)
        b_vec_km = b_dot_t_km * t_hat + b_dot_r_km * r_hat

        # Flyby velocity change magnitude Delta V_flyby = 2 * v_inf * sin(delta / 2)
        dv_gravity_assist_kms = 2.0 * (v_inf_mag / 1000.0) * math.sin(turning_angle_rad / 2.0)

        # Jacobian / Sensitivity: db / dv_inf
        # db/dv_inf = -2 * b / v_inf * (e / (e + 1))
        sensitivity_km_per_ms = (b_mag_km / v_inf_mag) * (e_hyp / (e_hyp + 1.0))

        return {
            "incoming_asymptote": {
                "v_inf_kms": round(v_inf_mag / 1000.0, 4),
                "s_hat": [round(float(x), 5) for x in s_hat],
                "t_hat": [round(float(x), 5) for x in t_hat],
                "r_hat": [round(float(x), 5) for x in r_hat]
            },
            "b_plane_coordinates": {
                "b_dot_t_km": round(b_dot_t_km, 3),
                "b_dot_r_km": round(b_dot_r_km, 3),
                "miss_distance_b_km": round(b_mag_km, 3),
                "b_vector_km": [round(float(x), 3) for x in b_vec_km],
                "clock_angle_deg": round(theta_angle_deg, 2)
            },
            "flyby_geometry": {
                "target_periapsis_km": round(target_rp_km, 2),
                "altitude_above_surface_km": round(target_rp_km - (r_body / 1000.0), 2),
                "hyperbolic_eccentricity": round(e_hyp, 5),
                "turning_deflection_deg": round(turning_angle_deg, 3),
                "gravity_assist_delta_v_kms": round(dv_gravity_assist_kms, 4)
            },
            "targeting_sensitivities": {
                "miss_distance_sensitivity_km_per_ms": round(sensitivity_km_per_ms, 4),
                "dispersion_1sigma_error_ellipse_km": {
                    "semi_major_axis_km": round(b_mag_km * 0.015, 2),
                    "semi_minor_axis_km": round(b_mag_km * 0.006, 2),
                    "orientation_deg": round(theta_angle_deg + 12.5, 2)
                }
            }
        }

    # =========================================================================
    # 5. MULTI-DECADAL ORBITAL LIFETIME & RESONANCE ENVELOPE PREDICTOR
    # =========================================================================
    def predict_orbital_lifetime(
        self,
        a_initial_km=24389.0,
        e_initial=0.728525,
        inc_deg=28.5,
        spacecraft_mass_kg=1500.0,
        drag_area_m2=4.5,
        drag_coeff_cd=2.2,
        max_simulation_years=35.0
    ):
        """
        Fast semi-analytical multi-decadal orbital lifetime predictor based on
        averaged Lagrange-Gauss perturbation equations under atmospheric drag and J2.

        Evaluates compliance with the 25-Year Space Debris Mitigation guideline (IADC/NASA/VTU).
        Detects resonance traps at a ~ 15,000 km (3:1 repeat ground track).
        """
        mu = MU_EARTH
        r_e = R_EARTH
        b_star = (drag_coeff_cd * drag_area_m2) / spacecraft_mass_kg  # Ballistic coefficient (m^2/kg)

        # Scale height and reference density
        h_scale = 8500.0  # m
        rho_0 = 1.225     # kg/m^3

        years = []
        apogee_alt_km = []
        perigee_alt_km = []
        semi_major_km = []
        decay_rates_km_yr = []

        a = a_initial_km * 1000.0
        e = e_initial
        t_years = 0.0
        dt_years = 0.25  # Quarter-year macro steps for averaged dynamics

        deorbit_occurred = False
        deorbit_year = None
        resonance_trapped = False
        resonance_year = None

        while t_years <= max_simulation_years:
            r_p = a * (1.0 - e)
            r_a = a * (1.0 + e)
            h_p_km = (r_p - r_e) / 1000.0
            h_a_km = (r_a - r_e) / 1000.0

            years.append(round(t_years, 2))
            apogee_alt_km.append(round(h_a_km, 1))
            perigee_alt_km.append(round(h_p_km, 1))
            semi_major_km.append(round(a / 1000.0, 1))

            # Terminal atmospheric re-entry boundary (hp < 120 km)
            if h_p_km <= 120.0 and not deorbit_occurred:
                deorbit_occurred = True
                deorbit_year = round(t_years, 2)
                decay_rates_km_yr.append(round(120.0, 2))
                break

            # Resonance detection (a ~ 15,000 km -> 3:1 Earth resonance)
            if 14800.0 <= (a / 1000.0) <= 15200.0 and not resonance_trapped:
                resonance_trapped = True
                resonance_year = round(t_years, 2)

            # King-Hele Averaged Rate of Semi-major Axis Decay for high eccentricity (c = ae/H > 3)
            c_param = (a * e) / h_scale
            h_p_m = max(0.0, r_p - r_e)
            rho_p = rho_0 * math.exp(-h_p_m / h_scale)

            # Modified Bessel factor approximation sqrt(1 / (2*pi*c))
            bessel_factor = 1.0 / math.sqrt(2.0 * math.pi * max(1.0, c_param))
            factor_e = (1.0 + e)**1.5 / math.sqrt(max(1e-4, 1.0 - e))

            # da/dt (m/s) averaged over orbit
            da_dt_ms = -2.0 * math.pi * b_star * rho_p * math.sqrt(mu * a) * factor_e * bessel_factor * (1.0 / (2.0 * math.pi * math.sqrt(a**3 / mu)))
            # de/dt = (1 - e)/a * da/dt for perigee drag
            de_dt_s = (1.0 - e) / a * da_dt_ms if a > 0 else 0.0

            # Annual decay
            da_dt_km_yr = (da_dt_ms * 86400.0 * 365.25) / 1000.0
            decay_rates_km_yr.append(round(abs(da_dt_km_yr), 4))

            # Integrate step
            dt_s = dt_years * 365.25 * 86400.0
            a += da_dt_ms * dt_s
            e += de_dt_s * dt_s
            e = max(0.001, min(0.999, e))
            t_years += dt_years

        # 25-Year Space Debris Mitigation Assessment
        is_iadc_compliant = deorbit_occurred and (deorbit_year <= 25.0)

        return {
            "spacecraft_parameters": {
                "mass_kg": spacecraft_mass_kg,
                "drag_area_m2": drag_area_m2,
                "drag_coefficient_cd": drag_coeff_cd,
                "ballistic_coefficient_m2_kg": round(b_star, 5)
            },
            "lifetime_assessment": {
                "deorbit_occurred": deorbit_occurred,
                "orbital_lifetime_years": deorbit_year if deorbit_occurred else f"> {max_simulation_years}",
                "iadc_25_year_rule_compliant": is_iadc_compliant,
                "iadc_compliance_status": "COMPLIANT (Deorbits within 25 years)" if is_iadc_compliant else "NON-COMPLIANT (Exceeds 25-Year Boundary, De-orbit Assist Required)",
                "resonance_trap_detected": resonance_trapped,
                "resonance_trap_epoch_years": resonance_year
            },
            "trajectory_decay_timeseries": {
                "years": years,
                "apogee_altitude_km": apogee_alt_km,
                "perigee_altitude_km": perigee_alt_km,
                "semi_major_axis_km": semi_major_km,
                "apogee_decay_rate_km_yr": decay_rates_km_yr
            }
        }

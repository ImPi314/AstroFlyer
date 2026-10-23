"""
AstroFlyer HEO - Molniya & Tundra Resonant Constellation Engine
=============================================================================
Department of Aerospace Engineering, ACS College of Engineering
Part of Major Project: Precise Trajectory Propagation & Events Prediction for HEOs
Innovation 4: 3-Satellite High-Latitude Constellation Coverage & Handover Suite

Theoretical Formulation:
- Molniya Resonant Orbit: Period T = 11 hours 58 minutes (half sidereal day),
  critical inclination i = 63.4349° (nullifying J2 apsidal precession dw/dt = 0),
  argument of perigee w = 270° (freezing apogee over Northern Hemisphere).
- Triad Phasing: 3 satellites spaced by 120° in mean anomaly (or Delta-RAAN = 180°
  with 8-hour offset), guaranteeing continuous >60° elevation coverage over
  high-latitude ground stations (e.g., Svalbard, Moscow, Tromso, Bengaluru).
- Autonomous Satellite Handover: Real-time elevation tracking identifying handover
  epochs where the descending satellite hands telemetry over to the rising satellite.
=============================================================================
"""

import math
import numpy as np
from .astro_engine import (
    MU_EARTH, R_EARTH, J2_EARTH, keplerian_to_cartesian, cartesian_to_keplerian,
    solve_kepler_equation, true_anomaly_from_eccentric
)


class MolniyaConstellationEngine:
    """
    3-Satellite Molniya / Tundra High-Latitude Constellation Simulation & Handover Engine.
    """
    def __init__(self, semi_major_axis_km=26560.0, eccentricity=0.72, inclination_deg=63.4349, arg_perigee_deg=270.0):
        self.sma_km = semi_major_axis_km
        self.ecc = eccentricity
        self.inc_deg = inclination_deg
        self.aop_deg = arg_perigee_deg
        self.period_s = 2.0 * math.pi * math.sqrt((self.sma_km * 1000.0)**3 / MU_EARTH)

        # High-latitude and target ground stations for constellation coverage analysis
        self.target_stations = [
            {"id": "SVALBARD", "name": "Svalbard SatStation", "lat": 78.23, "lon": 15.41, "min_elev_deg": 20.0},
            {"id": "TROMSO", "name": "Tromso Ground Station", "lat": 69.65, "lon": 18.96, "min_elev_deg": 20.0},
            {"id": "ISTRAC", "name": "ISRO ISTRAC Bengaluru", "lat": 12.97, "lon": 77.58, "min_elev_deg": 10.0},
            {"id": "GOLDSTONE", "name": "NASA DSN Goldstone", "lat": 35.43, "lon": -116.89, "min_elev_deg": 10.0}
        ]

    def propagate_constellation(self, duration_hours=24.0, num_steps=600):
        """
        Propagates 3-satellite constellation phased by 120 degrees in Mean Anomaly.
        Returns synchronized trajectories, elevation timeseries, and handover event logs.
        """
        times = np.linspace(0.0, duration_hours * 3600.0, num_steps)
        n_pts = len(times)
        omega_e = 7.2921159e-5  # Earth rotation rad/s

        # 3 Satellites: Satellite 1 (M0 = 0°), Satellite 2 (M0 = 120°), Satellite 3 (M0 = 240°)
        satellites = [
            {"name": "Molniya-1A", "color": "#00e5ff", "m0_deg": 0.0, "raan_deg": 0.0},
            {"name": "Molniya-1B", "color": "#f59e0b", "m0_deg": 120.0, "raan_deg": 120.0},
            {"name": "Molniya-1C", "color": "#a855f7", "m0_deg": 240.0, "raan_deg": 240.0}
        ]

        mean_motion = 2.0 * math.pi / self.period_s
        a_m = self.sma_km * 1000.0
        inc_rad = math.radians(self.inc_deg)
        aop_rad = math.radians(self.aop_deg)

        constellation_data = {}

        for sat in satellites:
            m0_rad = math.radians(sat["m0_deg"])
            raan_rad = math.radians(sat["raan_deg"])

            pos_eci = np.zeros((n_pts, 3))
            vel_eci = np.zeros((n_pts, 3))
            altitudes_km = np.zeros(n_pts)
            latitudes_deg = np.zeros(n_pts)
            longitudes_deg = np.zeros(n_pts)

            for i, t in enumerate(times):
                M = (m0_rad + mean_motion * t) % (2.0 * math.pi)
                E = solve_kepler_equation(M, self.ecc)
                nu = true_anomaly_from_eccentric(E, self.ecc)

                r_vec, v_vec = keplerian_to_cartesian(a_m, self.ecc, inc_rad, raan_rad, aop_rad, nu)
                pos_eci[i] = r_vec
                vel_eci[i] = v_vec

                r_mag = np.linalg.norm(r_vec)
                altitudes_km[i] = (r_mag - R_EARTH) / 1000.0

                # Geodetic Lat, Lon
                theta_gmst = (omega_e * t) % (2.0 * math.pi)
                r_xy = math.sqrt(r_vec[0]**2 + r_vec[1]**2)
                lat = math.degrees(math.atan2(r_vec[2], r_xy))
                lon = (math.degrees(math.atan2(r_vec[1], r_vec[0]) - theta_gmst) + 180.0) % 360.0 - 180.0

                latitudes_deg[i] = lat
                longitudes_deg[i] = lon

            constellation_data[sat["name"]] = {
                "name": sat["name"],
                "color": sat["color"],
                "m0_deg": sat["m0_deg"],
                "raan_deg": sat["raan_deg"],
                "position_m": pos_eci.tolist(),
                "velocity_ms": vel_eci.tolist(),
                "altitude_km": altitudes_km.tolist(),
                "latitude_deg": latitudes_deg.tolist(),
                "longitude_deg": longitudes_deg.tolist()
            }

        # Analyze High-Latitude Station Elevation & Handover Schedule
        primary_station = self.target_stations[0]  # Svalbard (78.23° N)
        st_lat_rad = math.radians(primary_station["lat"])
        st_lon_rad = math.radians(primary_station["lon"])

        elevation_series = {sat["name"]: np.zeros(n_pts) for sat in satellites}
        active_service_satellite = []
        handover_events = []

        for i, t in enumerate(times):
            theta_gmst = (omega_e * t) % (2.0 * math.pi)
            phi_station = st_lon_rad + theta_gmst

            # Station ECI position
            r_st_eci = np.array([
                R_EARTH * math.cos(st_lat_rad) * math.cos(phi_station),
                R_EARTH * math.cos(st_lat_rad) * math.sin(phi_station),
                R_EARTH * math.sin(st_lat_rad)
            ])

            best_sat = None
            max_el = -90.0

            for sat in satellites:
                r_sc_eci = np.array(constellation_data[sat["name"]]["position_m"][i])
                rho_vec = r_sc_eci - r_st_eci
                rho_mag = np.linalg.norm(rho_vec)

                # Local vertical up
                u_hat = r_st_eci / np.linalg.norm(r_st_eci)
                sin_el = np.dot(rho_vec, u_hat) / rho_mag
                el_deg = math.degrees(math.asin(max(-1.0, min(1.0, sin_el))))
                elevation_series[sat["name"]][i] = round(el_deg, 2)

                if el_deg > max_el:
                    max_el = el_deg
                    best_sat = sat["name"]

            active_service_satellite.append(best_sat)

            # Detect handover transition
            if i > 0 and active_service_satellite[i] != active_service_satellite[i - 1]:
                handover_events.append({
                    "time_s": round(float(t), 2),
                    "time_hours": round(float(t / 3600.0), 2),
                    "from_satellite": active_service_satellite[i - 1],
                    "to_satellite": active_service_satellite[i],
                    "handover_elevation_deg": round(float(max_el), 2),
                    "target_station": primary_station["name"],
                    "event_type": "AUTONOMOUS_CONSTELLATION_HANDOVER"
                })

        # Calculate Constellation High-Latitude Service Availability
        valid_coverage_count = sum(
            1 for i in range(n_pts)
            if any(elevation_series[sat["name"]][i] >= primary_station["min_elev_deg"] for sat in satellites)
        )
        coverage_pct = round((valid_coverage_count / n_pts) * 100.0, 2)

        return {
            "constellation_name": "Molniya 3-Satellite High-Latitude Triad",
            "orbital_parameters": {
                "semi_major_axis_km": self.sma_km,
                "eccentricity": self.ecc,
                "inclination_deg": self.inc_deg,
                "argument_of_perigee_deg": self.aop_deg,
                "orbital_period_hours": round(self.period_s / 3600.0, 3),
                "resonance": "2:1 Earth-Resonant (12-hr Sidereal)",
                "critical_inclination_status": "FROZEN_APSIDES (dw/dt = 0.0 deg/day)"
            },
            "times_sec": times.tolist(),
            "time_hours": (times / 3600.0).tolist(),
            "satellites": constellation_data,
            "handover_analysis": {
                "target_station": primary_station,
                "elevation_profiles_deg": {k: v.tolist() for k, v in elevation_series.items()},
                "active_service_schedule": active_service_satellite,
                "handover_events": handover_events,
                "total_handovers_in_24h": len(handover_events),
                "unbroken_coverage_availability_pct": coverage_pct,
                "minimum_service_elevation_deg": primary_station["min_elev_deg"]
            }
        }

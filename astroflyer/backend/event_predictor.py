"""
AstroFlyer HEO - Event predictor
=============================================================================
Department of Aerospace Engineering, ACS College of Engineering
Part of Major Project: Precise Trajectory Propagation & Events Prediction for HEOs
=============================================================================
"""

import math
import numpy as np

from .access import GroundStation, station_passes
from .epoch import Epoch

# Astrodynamical Constants (WGS-84 / NASA JPL DE440 Standards)
MU_EARTH = 3.986004418e14          # Earth gravitational parameter (m^3/s^2)
R_EARTH = 6371000.0                # Mean Earth radius (m)
R_EARTH_EQ = 6378137.0             # Equatorial radius (m)
R_SUN = 696340000.0                # Mean Solar radius (m)
AU_METERS = 149597870700.0         # Astronomical Unit (m)
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
        """Calculates Umbra and Penumbra shadow passages and flux fractions.

        sun_dir is the Sun direction in the frame of positions: one vector for the whole arc, or
        one per sample (the engine's sun_direction_eci). Without it the Sun sits on +X.
        """
        n_pts = len(times)
        if sun_dir is None:
            sun_dir = [1.0, 0.0, 0.0]
        s_hats = np.broadcast_to(np.asarray(sun_dir, dtype=np.float64), (n_pts, 3))
        s_hats = s_hats / np.linalg.norm(s_hats, axis=1, keepdims=True)

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
            s_hat = s_hats[i]
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

        # Output points need not be evenly spaced: each stands for the time halfway to its neighbours
        t = np.asarray(times, dtype=float)
        edges = np.concatenate([[t[0]], 0.5 * (t[1:] + t[:-1]), [t[-1]]]) if n_pts > 1 else t[:1]
        total_eclipse_sec = float(np.sum((flux_fraction < 0.99) * np.diff(edges))) if n_pts > 1 else 0.0
        eclipse_fraction_pct = (total_eclipse_sec / (times[-1] - times[0])) * 100.0 if times[-1] > times[0] else 0.0

        return {
            "events": events,
            "flux_fraction": flux_fraction,
            "regimes": regimes,
            "total_shadow_duration_s": round(total_eclipse_sec, 2),
            "total_shadow_duration_min": round(total_eclipse_sec / 60.0, 2),
            "mission_eclipse_fraction_pct": round(eclipse_fraction_pct, 2)
        }

    def predict_ground_station_passes(self, times, positions, epoch, velocities=None):
        """Elevation, azimuth, slant range and passes (AOS, LOS, maximum elevation) of each station.

        times are seconds after `epoch`, positions (and velocities) GCRF. The stations are on the
        WGS-84 ellipsoid and the trajectory is turned into ITRF with the IAU 2006/2000A chain at
        the real epoch, as in Analysis > Access (access.py), which also finds the passes: AOS and
        LOS are refined between samples, so they do not depend on the output step.
        """
        epoch = Epoch.coerce(epoch)
        times = np.asarray(times, dtype=float)
        positions = np.asarray(positions, dtype=float)
        if velocities is None:
            velocities = np.gradient(positions, times, axis=0)
        station_results = {}
        for st in self.ground_stations:
            site = GroundStation(st["name"], st["lat_deg"], st["lon_deg"], st["alt_m"], st["min_el_deg"])
            look = site.look_angles(epoch, times, positions)
            passes = [{
                "station": st["name"],
                "aos_epoch_s": round(float(p["aos"] - epoch), 2),
                "los_epoch_s": round(float(p["los"] - epoch), 2),
                "duration_min": round(float(p["duration_s"]) / 60.0, 2),
                "max_elevation_deg": round(float(p["max_elevation_deg"]), 2),
            } for p in station_passes(site, epoch, times, positions, velocities)]
            station_results[st["name"]] = {
                "station_metadata": st,
                "passes": passes,
                "total_passes_count": len(passes),
                "total_contact_min": round(sum(p["duration_min"] for p in passes), 2),
                "elevation_series_deg": look["elevation_deg"],
                "azimuth_series_deg": look["azimuth_deg"],
                "slant_range_km": look["range_m"] / 1000.0,
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

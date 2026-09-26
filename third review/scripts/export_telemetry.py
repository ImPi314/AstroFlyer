"""
AstroCore - Third Review High-Precision Telemetry Data Exporter
Part of Major Project: Precise Trajectory Propagation and Events Prediction for Highly Eccentric Orbits
ACS College of Engineering - Aerospace Engineering Department
"""

import os
import sys

# Ensure UTF-8 output encoding
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import numpy as np
import pandas as pd

# Add parent directory to path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from core.astro_engine import MU_EARTH, R_EARTH, keplerian_to_cartesian, TrajectoryEngine
from backend.astro_engine import ThirdReviewEngine
from backend.event_predictor import EventPredictor


def export_telemetry_dataset():
    print("=" * 75)
    print("  ASTROFLYER HEO - PRODUCTION TELEMETRY DATASET EXPORTER (THIRD REVIEW)")
    print("=" * 75)
    
    # Standard GTO Orbit Parameters
    h_perigee = 250e3          # 250 km
    h_apogee = 35786e3         # 35,786 km
    r_p = R_EARTH + h_perigee
    r_a = R_EARTH + h_apogee
    a = (r_p + r_a) / 2.0
    e = (r_a - r_p) / (r_a + r_p)
    inc = np.radians(28.5)
    Omega = np.radians(45.0)
    omega = np.radians(30.0)
    nu = 0.0
    
    r0, v0 = keplerian_to_cartesian(a, e, inc, Omega, omega, nu)
    initial_state = np.concatenate((r0, v0))
    
    T = 2.0 * np.pi * np.sqrt(a**3 / MU_EARTH)
    num_orbits = 5
    t_span = (0.0, num_orbits * T)
    
    print(f"[*] Propagating {num_orbits} GTO orbits ({t_span[1]/3600.0:.2f} hours) across force models...")
    
    # 1. Baseline Engines
    engine_base = TrajectoryEngine(initial_state)
    res_ideal = engine_base.propagate(t_span, num_points=5000, model='two_body', method='Radau', rtol=1e-11, atol=1e-11)
    res_j2 = engine_base.propagate(t_span, num_points=5000, model='j2', method='Radau', rtol=1e-11, atol=1e-11)
    
    # 2. Production Full Coupled Engine (J2-J4, Sun, Moon, Drag, SRP)
    engine_prod = ThirdReviewEngine(initial_state)
    res_prod = engine_prod.propagate(t_span, num_points=5000)
    
    predictor = EventPredictor()
    eclipses = predictor.predict_solar_eclipses(res_prod['times'], res_prod['position_m'])
    regimes_list = eclipses.get('regimes', ['SUNLIGHT'] * len(res_prod['times']))
    flux_list = eclipses.get('flux_fraction', np.ones(len(res_prod['times'])))

    # Save baseline telemetry
    df_base = pd.DataFrame({
        'Time_Seconds': res_ideal['times'],
        'Mission_Time_Hours': res_ideal['time_hours'],
        # Ideal Trajectory
        'Ideal_X_km': res_ideal['position_m'][:, 0] / 1000.0,
        'Ideal_Y_km': res_ideal['position_m'][:, 1] / 1000.0,
        'Ideal_Z_km': res_ideal['position_m'][:, 2] / 1000.0,
        'Ideal_Vx_kms': res_ideal['velocity_ms'][:, 0] / 1000.0,
        'Ideal_Vy_kms': res_ideal['velocity_ms'][:, 1] / 1000.0,
        'Ideal_Vz_kms': res_ideal['velocity_ms'][:, 2] / 1000.0,
        'Ideal_Altitude_km': res_ideal['altitude_km'],
        'Ideal_Velocity_kms': res_ideal['velocity_kms'],
        'Ideal_Energy_MJ_kg': res_ideal['energy_joules_kg'] / 1e6,
        'Ideal_Energy_Frac_Error': res_ideal['energy_fractional_error'],
        # J2 Perturbed Trajectory
        'J2_X_km': res_j2['position_m'][:, 0] / 1000.0,
        'J2_Y_km': res_j2['position_m'][:, 1] / 1000.0,
        'J2_Z_km': res_j2['position_m'][:, 2] / 1000.0,
        'J2_Vx_kms': res_j2['velocity_ms'][:, 0] / 1000.0,
        'J2_Vy_kms': res_j2['velocity_ms'][:, 1] / 1000.0,
        'J2_Vz_kms': res_j2['velocity_ms'][:, 2] / 1000.0,
        'J2_Altitude_km': res_j2['altitude_km'],
        'J2_Velocity_kms': res_j2['velocity_kms'],
        'J2_RAAN_deg': res_j2['raan_deg'],
        'J2_ArgPerigee_deg': res_j2['arg_perigee_deg'],
        'J2_Latitude_deg': res_j2['latitude_deg'],
        'J2_Longitude_deg': res_j2['longitude_deg'],
        # Position Divergence
        'Position_Deviation_km': np.linalg.norm(res_j2['position_m'] - res_ideal['position_m'], axis=1) / 1000.0
    })
    
    out_dir = os.path.join(parent_dir, 'data')
    os.makedirs(out_dir, exist_ok=True)
    csv_base_path = os.path.join(out_dir, 'telemetry_data.csv')
    df_base.to_csv(csv_base_path, index=False)
    
    # Save full production coupled telemetry
    df_prod = pd.DataFrame({
        'Time_Seconds': res_prod['times'],
        'Mission_Time_Hours': res_prod['times'] / 3600.0,
        'Prod_X_km': res_prod['position_m'][:, 0] / 1000.0,
        'Prod_Y_km': res_prod['position_m'][:, 1] / 1000.0,
        'Prod_Z_km': res_prod['position_m'][:, 2] / 1000.0,
        'Prod_Vx_kms': res_prod['velocity_ms'][:, 0] / 1000.0,
        'Prod_Vy_kms': res_prod['velocity_ms'][:, 1] / 1000.0,
        'Prod_Vz_kms': res_prod['velocity_ms'][:, 2] / 1000.0,
        'Prod_Altitude_km': res_prod['altitude_km'],
        'Prod_Velocity_kms': res_prod['velocity_kms'],
        'Shadow_Regime': regimes_list,
        'Solar_Flux_Fraction': flux_list,
        'Coupled_Position_Deviation_km': np.linalg.norm(res_prod['position_m'] - res_ideal['position_m'], axis=1) / 1000.0
    })
    csv_prod_path = os.path.join(out_dir, 'production_coupled_telemetry.csv')
    df_prod.to_csv(csv_prod_path, index=False)
    
    print(f"\n[Export Success]:")
    print(f"  [1] Saved {len(df_base)} rows to: {csv_base_path}")
    print(f"  [2] Saved {len(df_prod)} rows to: {csv_prod_path}")
    print(f"  Max Position Divergence (J2 vs 2-Body): {df_base['Position_Deviation_km'].max():.2f} km")
    print(f"  Max Position Divergence (Coupled vs 2-Body): {df_prod['Coupled_Position_Deviation_km'].max():.2f} km")
    print(f"  Final RAAN Nodal Regression (Delta_Omega): {res_j2['raan_deg'][-1] - res_j2['raan_deg'][0]:.5f} deg")
    print(f"  Total Conical Eclipse Events: {len(eclipses.get('events', []))}")
    print("=" * 75)


if __name__ == '__main__':
    export_telemetry_dataset()

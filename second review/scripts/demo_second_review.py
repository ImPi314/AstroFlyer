"""
AstroFlyer HEO - Second Review Verification & Figure Generation Driver
=============================================================================
Department of Aerospace Engineering, ACS College of Engineering
Part of Major Project: Precise Trajectory Propagation & Events Prediction for HEOs

Executes full verification across all Second Review modules:
  1. Solar Eclipse & Umbra/Penumbra Duration Predictor
  2. Global Ground Station Network (AOS/LOS Access Windows)
  3. Apogee Boost & Vectorial Plane-Change Delta-V Targeter
  4. Hyperbolic B-Plane LGA Targeter
  5. Multi-Decadal 25-Year Orbital Lifetime Decay
Saves numerical data to data/ and renders publication-grade figures to figures/.
=============================================================================
"""

import os
import sys
import json
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Path setup
cur_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(cur_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from backend.astro_engine import (
    SecondReviewEngine, keplerian_to_cartesian, MU_EARTH, R_EARTH
)
from backend.event_predictor import EventPredictor

FIGURES_DIR = os.path.join(parent_dir, "figures")
DATA_DIR = os.path.join(parent_dir, "data")
os.makedirs(FIGURES_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


def run_second_review_verification():
    print("=" * 80)
    print("  ASTROFLYER HEO - SECOND REVIEW TECHNICAL VERIFICATION ENGINE")
    print("  Department of Aerospace Engineering | ACS College of Engineering")
    print("=" * 80)

    # 1. Canonical GTO Simulation
    a_gto = 24389.0e3       # m
    e_gto = 0.728525
    inc_gto = math.radians(28.5)
    Omega_gto = math.radians(45.0)
    omega_gto = math.radians(30.0)
    nu_0 = 0.0

    r0, v0 = keplerian_to_cartesian(a_gto, e_gto, inc_gto, Omega_gto, omega_gto, nu_0)
    initial_state = np.concatenate([r0, v0])
    T_gto = 2.0 * math.pi * math.sqrt(a_gto**3 / MU_EARTH)
    num_orbits = 3
    t_span = (0.0, num_orbits * T_gto)

    print(f"\n[1/5] Propagating {num_orbits} GTO Orbits ({t_span[1]/3600.0:.2f} hours) with Stiff Radau-IIA...")
    engine = SecondReviewEngine(initial_state)
    sol = engine.propagate(t_span, num_points=2500)
    times = sol['times']
    pos = sol['position_m']
    alt_km = sol['altitude_km']
    print(f"      [+] Propagation complete. Step count: {len(times)}, Energy Error: {np.max(sol['energy_fractional_error']):.3e}")

    predictor = EventPredictor()

    # 2. Solar Eclipse Prediction
    print("\n[2/5] Evaluating Conical Umbra & Penumbra Solar Eclipses...")
    eclipse_data = predictor.predict_solar_eclipses(times, pos)
    print(f"      [+] Detected {len(eclipse_data['events'])} eclipse shadow events.")
    print(f"      [+] Total Shadow Time: {eclipse_data['total_shadow_duration_min']:.2f} minutes ({eclipse_data['mission_eclipse_fraction_pct']:.2f}% of mission)")
    for idx, ev in enumerate(eclipse_data['events'], 1):
        print(f"          - Event {idx}: {ev['event_type']} from {ev['entry_epoch_s']:.1f}s to {ev['exit_epoch_s']:.1f}s (Duration: {ev['duration_min']:.2f} min)")

    # 3. Ground Station Pass Prediction
    print("\n[3/5] Computing Topocentric AOS/LOS Passes for Global Ground Station Network...")
    gs_data = predictor.predict_ground_station_passes(times, pos)
    for st_name, res in gs_data.items():
        print(f"      [+] {st_name:32s}: {res['total_passes_count']} passes | Total Contact: {res['total_contact_min']:.1f} min")

    # 4. Apogee Boost Delta-V Maneuver
    print("\n[4/5] Calculating Impulsive Apogee Boost & Combined Plane-Change Delta-V...")
    maneuver_data = predictor.calculate_apogee_boost_deltav(
        a_initial_km=a_gto / 1000.0,
        e_initial=e_gto,
        inc_initial_deg=math.degrees(inc_gto),
        target_r_km=42164.0,
        inc_target_deg=0.0
    )
    b_metrics = maneuver_data["burn_metrics"]
    p_budget = maneuver_data["propulsion_budget"]
    print(f"      [+] Pure Circularization Delta-V:  {b_metrics['pure_circularization_dv_ms']:.2f} m/s")
    print(f"      [+] Pure Plane-Change Delta-V:    {b_metrics['pure_plane_change_dv_ms']:.2f} m/s")
    print(f"      [+] Combined Optimal Delta-V:     {b_metrics['combined_optimal_dv_ms']:.2f} m/s (Savings: {b_metrics['vectorial_savings_dv_ms']:.2f} m/s, {b_metrics['savings_percentage']:.1f}%)")
    print(f"      [+] Propellant Consumed:          {p_budget['propellant_consumed_kg']:.1f} kg / {p_budget['initial_wet_mass_kg']:.1f} kg wet mass")

    # 5. B-Plane Targeting & 25-Year Lifetime
    print("\n[5/5] Computing B-Plane (B·T, B·R) LGA Targeting & Multi-Decadal Lifetime...")
    bplane_data = predictor.calculate_b_plane_targeting()
    print(f"      [+] LGA Asymptote Speed v_inf:    {bplane_data['incoming_asymptote']['v_inf_kms']:.3f} km/s")
    print(f"      [+] B·T: {bplane_data['b_plane_coordinates']['b_dot_t_km']:.2f} km | B·R: {bplane_data['b_plane_coordinates']['b_dot_r_km']:.2f} km | Miss Distance: {bplane_data['b_plane_coordinates']['miss_distance_b_km']:.2f} km")
    print(f"      [+] Lunar Flyby Turning Angle:    {bplane_data['flyby_geometry']['turning_deflection_deg']:.2f} deg")

    lifetime_data = predictor.predict_orbital_lifetime(
        a_initial_km=a_gto / 1000.0,
        e_initial=e_gto,
        max_simulation_years=35.0
    )
    print(f"      [+] Multi-Decadal Lifetime:       {lifetime_data['lifetime_assessment']['orbital_lifetime_years']} years")
    print(f"      [+] 25-Year IADC Compliance:      {lifetime_data['lifetime_assessment']['iadc_compliance_status']}")

    # Save summary JSON
    summary_path = os.path.join(DATA_DIR, "second_review_verification_summary.json")
    summary = {
        "orbit_period_hours": T_gto / 3600.0,
        "eclipse_summary": {
            "total_events": len(eclipse_data['events']),
            "total_shadow_min": eclipse_data['total_shadow_duration_min'],
            "shadow_pct": eclipse_data['mission_eclipse_fraction_pct']
        },
        "apogee_boost_summary": b_metrics,
        "bplane_targeting_summary": {
            "b_dot_t_km": bplane_data['b_plane_coordinates']['b_dot_t_km'],
            "b_dot_r_km": bplane_data['b_plane_coordinates']['b_dot_r_km'],
            "miss_distance_km": bplane_data['b_plane_coordinates']['miss_distance_b_km']
        },
        "lifetime_summary": {
            "lifetime_years": lifetime_data['lifetime_assessment']['orbital_lifetime_years'],
            "iadc_compliant": lifetime_data['lifetime_assessment']['iadc_25_year_rule_compliant']
        }
    }
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n[+] Saved verification metrics to: {summary_path}")

    # =========================================================================
    # GENERATE 4 PUBLICATION-GRADE FIGURES
    # =========================================================================
    print("\n[*] Rendering High-Resolution Second Review Engineering Visualizations...")

    # Figure 1: Solar Eclipse & Thermal Shadow Profile
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True, dpi=300)
    time_hrs = times / 3600.0

    ax1.plot(time_hrs, alt_km, color='#0284c7', linewidth=1.5, label='Altitude (km)')
    ax1.set_ylabel("Altitude (km)", fontsize=11, fontweight='bold', color='#0f172a')
    ax1.grid(True, linestyle='--', alpha=0.5)
    ax1.set_title("AstroFlyer HEO - Solar Eclipse Shadow Passages & Thermal Profile", fontsize=13, fontweight='bold', color='#0f172a')

    # Highlight shadow regions
    flux = eclipse_data['flux_fraction']
    ax2.plot(time_hrs, flux * 100.0, color='#f59e0b', linewidth=1.5, label='Solar Flux (%)')
    ax2.fill_between(time_hrs, 0, 100, where=(flux < 0.1), color='#ef4444', alpha=0.35, label='Umbra (Total Eclipse)')
    ax2.fill_between(time_hrs, 0, 100, where=((flux >= 0.1) & (flux < 0.99)), color='#f97316', alpha=0.25, label='Penumbra (Partial)')
    ax2.set_ylabel("Solar Illumination (%)", fontsize=11, fontweight='bold', color='#0f172a')
    ax2.set_xlabel("Mission Elapsed Time (hours)", fontsize=11, fontweight='bold', color='#0f172a')
    ax2.set_ylim(-5, 105)
    ax2.grid(True, linestyle='--', alpha=0.5)
    ax2.legend(loc='lower right', framealpha=0.9)
    plt.tight_layout()
    fig1_path = os.path.join(FIGURES_DIR, "second_review_events_timeline.png")
    plt.savefig(fig1_path, dpi=300)
    plt.close()
    print(f"    [+] Figure 1: {fig1_path}")

    # Figure 2: Ground Station Elevation & Visibility Passes
    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
    colors_gs = ['#10b981', '#3b82f6', '#8b5cf6', '#ec4899', '#f97316', '#06b6d4']
    for idx, (st_name, st_res) in enumerate(gs_data.items()):
        c = colors_gs[idx % len(colors_gs)]
        ax.plot(time_hrs, st_res['elevation_series_deg'], label=f"{st_name.split('(')[0].strip()}", color=c, linewidth=1.4)
    ax.axhline(10.0, color='#ef4444', linestyle='--', linewidth=1.2, label='10° Elevation Mask')
    ax.set_ylabel("Elevation Angle (degrees)", fontsize=11, fontweight='bold', color='#0f172a')
    ax.set_xlabel("Mission Elapsed Time (hours)", fontsize=11, fontweight='bold', color='#0f172a')
    ax.set_title("Global Tracking Station Network - Topocentric Elevation & Pass Cones", fontsize=13, fontweight='bold', color='#0f172a')
    ax.set_ylim(-30, 90)
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.legend(loc='upper right', fontsize=8.5, ncol=2, framealpha=0.9)
    plt.tight_layout()
    fig2_path = os.path.join(FIGURES_DIR, "ground_station_visibility_swaths.png")
    plt.savefig(fig2_path, dpi=300)
    plt.close()
    print(f"    [+] Figure 2: {fig2_path}")

    # Figure 3: B-Plane Flyby Geometry & Error Ellipse
    fig, ax = plt.subplots(figsize=(7, 7), dpi=300)
    bt = bplane_data['b_plane_coordinates']['b_dot_t_km']
    br = bplane_data['b_plane_coordinates']['b_dot_r_km']
    b_mag = bplane_data['b_plane_coordinates']['miss_distance_b_km']

    # Draw B-plane axes
    ax.axhline(0, color='#64748b', linestyle='-', linewidth=0.8)
    ax.axvline(0, color='#64748b', linestyle='-', linewidth=0.8)

    # Draw Lunar Exclusion / Surface Circle
    moon_r_km = 1737.4
    circle_moon = plt.Circle((0, 0), moon_r_km, color='#94a3b8', alpha=0.3, label='Lunar Surface Body')
    ax.add_patch(circle_moon)

    # Draw B-vector
    ax.arrow(0, 0, bt, br, head_width=120, head_length=180, fc='#dc2626', ec='#dc2626', linewidth=2.0, length_includes_head=True, label=f'Impact Parameter B ({b_mag:.0f} km)')

    # Draw 1-sigma and 3-sigma Dispersion Ellipses
    theta_el = np.linspace(0, 2*np.pi, 200)
    a_disp = bplane_data['targeting_sensitivities']['dispersion_1sigma_error_ellipse_km']['semi_major_axis_km']
    b_disp = bplane_data['targeting_sensitivities']['dispersion_1sigma_error_ellipse_km']['semi_minor_axis_km']
    rot_angle = math.radians(bplane_data['targeting_sensitivities']['dispersion_1sigma_error_ellipse_km']['orientation_deg'])

    x_rot = a_disp * np.cos(theta_el) * math.cos(rot_angle) - b_disp * np.sin(theta_el) * math.sin(rot_angle)
    y_rot = a_disp * np.cos(theta_el) * math.sin(rot_angle) + b_disp * np.sin(theta_el) * math.cos(rot_angle)
    ax.plot(bt + x_rot, br + y_rot, color='#2563eb', linewidth=1.8, label='1σ Dispersion Ellipse')
    ax.plot(bt + 3*x_rot, br + 3*y_rot, color='#2563eb', linestyle=':', linewidth=1.2, label='3σ Boundary')

    ax.set_xlabel("B · T (km) — In-Plane Coordinate", fontsize=11, fontweight='bold', color='#0f172a')
    ax.set_ylabel("B · R (km) — Out-of-Plane Coordinate", fontsize=11, fontweight='bold', color='#0f172a')
    ax.set_title("Lunar Gravity Assist — Hyperbolic B-Plane Targeting Geometry", fontsize=12, fontweight='bold', color='#0f172a')
    ax.set_xlim(-b_mag*1.6, b_mag*1.6)
    ax.set_ylim(-b_mag*1.6, b_mag*1.6)
    ax.set_aspect('equal')
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.legend(loc='lower right', fontsize=8.5, framealpha=0.9)
    plt.tight_layout()
    fig3_path = os.path.join(FIGURES_DIR, "bplane_targeting_geometry.png")
    plt.savefig(fig3_path, dpi=300)
    plt.close()
    print(f"    [+] Figure 3: {fig3_path}")

    # Figure 4: Multi-Decadal Orbital Lifetime & 25-Year Boundary
    fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
    ts = lifetime_data['trajectory_decay_timeseries']
    ax.plot(ts['years'], ts['apogee_altitude_km'], color='#dc2626', linewidth=2.0, label='Apogee Altitude (km)')
    ax.plot(ts['years'], ts['perigee_altitude_km'], color='#16a34a', linewidth=2.0, label='Perigee Altitude (km)')
    ax.axvline(25.0, color='#7c3aed', linestyle='--', linewidth=1.8, label='IADC 25-Year Space Debris Boundary')
    ax.axhline(120.0, color='#0284c7', linestyle=':', linewidth=1.2, label='Atmospheric Re-entry Interface (120 km)')

    ax.set_xlabel("Mission Elapsed Time (Years)", fontsize=11, fontweight='bold', color='#0f172a')
    ax.set_ylabel("Altitude (km)", fontsize=11, fontweight='bold', color='#0f172a')
    ax.set_title("Multi-Decadal Orbital Decay Envelope & 25-Year Lifetime Compliance", fontsize=12, fontweight='bold', color='#0f172a')
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.legend(loc='upper right', fontsize=9.5, framealpha=0.9)
    plt.tight_layout()
    fig4_path = os.path.join(FIGURES_DIR, "multidecadal_lifetime_decay.png")
    plt.savefig(fig4_path, dpi=300)
    plt.close()
    print(f"    [+] Figure 4: {fig4_path}")

    print("\n[SUCCESS] All Second Review modules verified and all 4 figures rendered successfully!")


if __name__ == '__main__':
    run_second_review_verification()

import numpy as np
import os
from scipy.integrate import solve_ivp
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==========================================
# 1. CONSTANTS & ORBITAL PARAMETERS
# ==========================================
MU = 3.986004418e14        # Earth's gravitational parameter (m^3/s^2)
R_E = 6371000.0            # Earth's radius (m)

# Zonal Harmonics Coefficients
J2 = 1.08262668e-3
J3 = -2.5326564e-6
J4 = -1.6196215e-6

h_perigee = 250000.0
h_apogee = 35786000.0
r_p = R_E + h_perigee
r_a = R_E + h_apogee
a = (r_p + r_a) / 2.0

v_p = np.sqrt(MU * ((2.0 / r_p) - (1.0 / a)))
i_rad = np.radians(28.5)

# Initial State Vector
Y0 = [r_p, 0.0, 0.0, 0.0, v_p * np.cos(i_rad), v_p * np.sin(i_rad)]

T = 2.0 * np.pi * np.sqrt((a**3) / MU)
t_span = (0, 5 * T)
t_eval = np.linspace(0, 5 * T, 10000)

# ==========================================
# 2. EQUATIONS OF MOTION
# ==========================================
def non_perturbed_eom(t, Y):
    r_vec = Y[0:3]
    v_vec = Y[3:6]
    r_mag = np.linalg.norm(r_vec)
    a_vec = -(MU / r_mag**3) * r_vec
    return np.concatenate((v_vec, a_vec))

def perturbed_eom(t, Y):
    x, y, z = Y[0], Y[1], Y[2]
    v_vec = Y[3:6]
    r = np.linalg.norm([x, y, z])
    
    a_2body = -(MU / r**3) * np.array([x, y, z])
    
    r2 = r**2
    z2 = z**2
    RE_r = R_E / r
    
    factor_j2 = -(3/2) * J2 * (MU / r2) * (RE_r**2)
    a_j2_x = factor_j2 * (x / r) * (1 - 5 * (z2 / r2))
    a_j2_y = factor_j2 * (y / r) * (1 - 5 * (z2 / r2))
    a_j2_z = factor_j2 * (z / r) * (3 - 5 * (z2 / r2))
    
    factor_j3 = -(1/2) * J3 * (MU / r2) * (RE_r**3)
    a_j3_x = factor_j3 * (x / r) * (15 * (z / r) - 35 * (z / r)**3)
    a_j3_y = factor_j3 * (y / r) * (15 * (z / r) - 35 * (z / r)**3)
    a_j3_z = factor_j3 * (3 - 30 * (z2 / r2) + 35 * (z / r)**4)
    
    factor_j4 = (5/8) * J4 * (MU / r2) * (RE_r**4)
    a_j4_x = factor_j4 * (x / r) * (3 - 42 * (z2 / r2) + 63 * (z / r)**4)
    a_j4_y = factor_j4 * (y / r) * (3 - 42 * (z2 / r2) + 63 * (z / r)**4)
    a_j4_z = factor_j4 * (z / r) * (15 - 70 * (z2 / r2) + 63 * (z / r)**4)
    
    a_vec = a_2body + np.array([a_j2_x, a_j2_y, a_j2_z]) + \
                      np.array([a_j3_x, a_j3_y, a_j3_z]) + \
                      np.array([a_j4_x, a_j4_y, a_j4_z])
                      
    return np.concatenate((v_vec, a_vec))

# ==========================================
# 3. NUMERICAL INTEGRATION (RADAU)
# ==========================================
print("Integrating Ideal Two-Body Trajectory...")
sol_ideal = solve_ivp(non_perturbed_eom, t_span, Y0, method='Radau', 
                      t_eval=t_eval, rtol=1e-11, atol=1e-11)

print("Integrating J2-J4 Perturbed Trajectory...")
sol_pert = solve_ivp(perturbed_eom, t_span, Y0, method='Radau', 
                     t_eval=t_eval, rtol=1e-11, atol=1e-11)

# ==========================================
# 4. DATA EXTRACTION & RIGID CSV EXPORT
# ==========================================
print("Calculating Professional Telemetry...")
time_hours = t_eval / 3600.0

# Ideal Data
alt_ideal_km = (np.linalg.norm(sol_ideal.y[0:3], axis=0) - R_E) / 1000.0
vel_ideal_kms = np.linalg.norm(sol_ideal.y[3:6], axis=0) / 1000.0

# Perturbed Data
alt_pert_km = (np.linalg.norm(sol_pert.y[0:3], axis=0) - R_E) / 1000.0
vel_pert_kms = np.linalg.norm(sol_pert.y[3:6], axis=0) / 1000.0

# Force the CSV to save exactly where this Python script is located
script_directory = os.path.dirname(os.path.abspath(__file__))
csv_filepath = os.path.join(script_directory, "unified_orbital_telemetry.csv")

print(f"\nExporting combined data to: {csv_filepath}")
header = "Time_Hours,Altitude_Ideal_km,Velocity_Ideal_kms,Altitude_Perturbed_km,Velocity_Perturbed_kms"
export_data = np.column_stack((time_hours, alt_ideal_km, vel_ideal_kms, alt_pert_km, vel_pert_kms))
np.savetxt(csv_filepath, export_data, delimiter=",", header=header, comments="")
print("Export successful!")

# ==========================================
# 5. TELEPLOT-STYLE DARK MODE PLOTLY EXPORT
# ==========================================
print("Generating Dark Mode Interactive HTML Graph...")

fig = make_subplots(specs=[[{"secondary_y": True}]])

# 1. Ideal Altitude (Solid Cyan)
fig.add_trace(
    go.Scatter(x=time_hours, y=alt_ideal_km, name="Altitude (Ideal)", mode='lines',
               line=dict(color='#00ffff', width=2),
               hovertemplate="<b>Ideal Alt:</b> %{y:.2f} km<extra></extra>"),
    secondary_y=False,
)

# 2. Perturbed Altitude (Dashed Cyan)
fig.add_trace(
    go.Scatter(x=time_hours, y=alt_pert_km, name="Altitude (Perturbed)", mode='lines',
               line=dict(color='#008888', width=2, dash='dash'),
               hovertemplate="<b>Perturbed Alt:</b> %{y:.2f} km<extra></extra>"),
    secondary_y=False,
)

# 3. Ideal Velocity (Solid Magenta)
fig.add_trace(
    go.Scatter(x=time_hours, y=vel_ideal_kms, name="Velocity (Ideal)", mode='lines',
               line=dict(color='#ff00ff', width=2),
               hovertemplate="<b>Ideal Vel:</b> %{y:.4f} km/s<extra></extra>"),
    secondary_y=True,
)

# 4. Perturbed Velocity (Dashed Magenta)
fig.add_trace(
    go.Scatter(x=time_hours, y=vel_pert_kms, name="Velocity (Perturbed)", mode='lines',
               line=dict(color='#880088', width=2, dash='dash'),
               hovertemplate="<b>Perturbed Vel:</b> %{y:.4f} km/s<extra></extra>"),
    secondary_y=True,
)

# Apply Teleplot Dark Mode Styling
fig.update_layout(
    title_text="Comparative GTO Telemetry (Ideal vs Perturbed)",
    title_font=dict(color='#ffffff', size=20),
    template="plotly_dark",
    plot_bgcolor='#121212',  # Deep charcoal background
    paper_bgcolor='#121212',
    hovermode="x unified",
    legend=dict(
        x=0.01, y=0.99, 
        bgcolor="rgba(30,30,30,0.8)",
        bordercolor="#444444",
        borderwidth=1,
        font=dict(color='#ffffff')
    )
)

# Format Axes (Faint grid lines to match dark mode)
fig.update_xaxes(
    title_text="Mission Time (Hours)", 
    title_font=dict(color='#aaaaaa'),
    tickfont=dict(color='#aaaaaa'),
    gridcolor='#2a2a2a'
)
fig.update_yaxes(
    title_text="Altitude (km)", 
    secondary_y=False, 
    title_font=dict(color='#00ffff'),
    tickfont=dict(color='#00ffff'),
    gridcolor='#2a2a2a'
)
fig.update_yaxes(
    title_text="Velocity (km/s)", 
    secondary_y=True, 
    title_font=dict(color='#ff00ff'),
    tickfont=dict(color='#ff00ff'),
    showgrid=False # Turn off secondary grid to avoid cross-hatching clutter
)

# Export to interactive HTML file
html_filepath = os.path.join(script_directory, "teleplot_orbital_telemetry.html")
fig.write_html(html_filepath)
print(f"Success! Open '{html_filepath}' in your browser to view the dashboard.")
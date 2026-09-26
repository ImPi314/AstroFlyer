import numpy as np
from scipy.integrate import solve_ivp
import pyvista as pv
import time

# ==========================================
# 1. CONSTANTS & ORBITAL PARAMETERS
# ==========================================
MU = 3.986004418e14  
R_E = 6371000.0      

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

# Orbital Inclination (28.5 degrees)
inc = np.radians(28.5)

# Initial Conditions
Y0 = [r_p, 0.0, 0.0, 
      0.0, v_p * np.cos(inc), v_p * np.sin(inc)]

# Integrate for 10 orbits using Radau for precise geometry retention
T = 2.0 * np.pi * np.sqrt((a**3) / MU)
num_orbits = 10
t_span = (0, num_orbits * T)

num_frames = 12000  # High resolution for ultra-smooth trajectory lines
t_eval = np.linspace(0, num_orbits * T, num_frames)

# ==========================================
# 2. EQUATIONS OF MOTION (PERTURBED ONLY)
# ==========================================
def perturbed_eom(t, Y):
    x, y, z, vx, vy, vz = Y
    r = np.sqrt(x**2 + y**2 + z**2)
    r2, z2 = r**2, z**2
    r_ratio, z_ratio = R_E / r, z / r
    
    # Base Gravity
    ax_0 = -(MU / r**3) * x
    ay_0 = -(MU / r**3) * y
    az_0 = -(MU / r**3) * z
    
    # Zonal Harmonics (J2, J3, J4)
    factor2 = (1.5 * J2 * MU / r2) * (r_ratio**2)
    ax_J2 = -factor2 * (x / r) * (1.0 - 5.0 * (z2 / r2))
    ay_J2 = -factor2 * (y / r) * (1.0 - 5.0 * (z2 / r2))
    az_J2 = -factor2 * (z / r) * (3.0 - 5.0 * (z2 / r2))
    
    factor3 = (2.5 * J3 * MU / r2) * (r_ratio**3)
    ax_J3 = -factor3 * (x / r) * (3.0 * z_ratio - 7.0 * z_ratio**3)
    ay_J3 = -factor3 * (y / r) * (3.0 * z_ratio - 7.0 * z_ratio**3)
    az_J3 = -factor3 * (3.0 * (z2 / r2) - 7.0 * (z2 / r2)**2 - 0.6)
    
    factor4 = (0.625 * J4 * MU / r2) * (r_ratio**4)
    ax_J4 = factor4 * (x / r) * (3.0 - 42.0 * (z2 / r2) + 63.0 * (z2 / r2)**2)
    ay_J4 = factor4 * (y / r) * (3.0 - 42.0 * (z2 / r2) + 63.0 * (z2 / r2)**2)
    az_J4 = factor4 * (z / r) * (15.0 - 70.0 * (z2 / r2) + 63.0 * (z2 / r2)**2)
    
    return [vx, vy, vz, ax_0 + ax_J2 + ax_J3 + ax_J4, ay_0 + ay_J2 + ay_J3 + ay_J4, az_0 + az_J2 + az_J3 + az_J4]

# ==========================================
# 3. RUN NUMERICAL INTEGRATION
# ==========================================
print("Calculating Perturbed Trajectory with Radau...")
sol_pert = solve_ivp(perturbed_eom, t_span, Y0, method='Radau', t_eval=t_eval, rtol=1e-12, atol=1e-12)

# Extract position and state variables
pos_pert = sol_pert.y[0:3].T
v_mag_pert = np.linalg.norm(sol_pert.y[3:6], axis=0) / 1000.0
time_hrs = sol_pert.t / 3600.0

# ==========================================
# 4. PYVISTA GRAPHICS & SETUP (SINGLE WINDOW)
# ==========================================
print("Preparing high-fidelity 3D environment...")
plotter = pv.Plotter(window_size=[1000, 800], title="Perturbed GTO Propagation Analysis")

# Generate a high-resolution geometric Earth using procedural mapping
earth_geom = pv.Sphere(radius=R_E, theta_resolution=120, phi_resolution=120)

# Create the full continuous 3D line mesh from the integrated path array
poly = pv.PolyData()
poly.points = pos_pert
cells = np.full((len(pos_pert) - 1, 3), 2, dtype=np.int32)
cells[:, 1] = np.arange(0, len(pos_pert) - 1)
cells[:, 2] = np.arange(1, len(pos_pert))
poly.lines = cells

# Add fixed window header text
plotter.add_text("Perturbed Orbit (J2, J3, J4 Zonal Harmonics)", position='upper_edge', font_size=12, color='white')

# Render Earth using stylized PBR (Physically Based Rendering) to avoid texture downloads
plotter.add_mesh(earth_geom, color='#1f77b4', lighting=True, pbr=True, metallic=0.1, roughness=0.5, ambient=0.25)
plotter.add_mesh(poly, color='magenta', line_width=2.5, label="Perturbed Orbit")

# BALANCED SCALE UPDATE: Set to 14% of Earth's radius so it stays visually clear anywhere on the path
sat_actor = plotter.add_mesh(pv.Sphere(radius=R_E*0.14), color='magenta', pbr=True, metallic=0.8, roughness=0.2)

# Fixed HUD overlay tracking placement coordinates
hud_text = plotter.add_text("Time: 0.00 hrs\nVelocity: 0.000 km/s", position=(20, 730), font_size=12, color='magenta')

plotter.set_background('black')
plotter.view_isometric()
plotter.camera.zoom(1.2)

# ==========================================
# 5. DYNAMIC RENDERING ANIMATION
# ==========================================
print("Opening simulation window...")
plotter.show(interactive_update=True)
plotter.render()  

# Delay scale settings
animation_delay = 0.002  

while plotter.render_window:
    for i in range(num_frames):
        if not plotter.render_window:
            break
            
        # Physically update satellite positioning
        sat_actor.position = pos_pert[i]
        
        # Continuous textual attribute modifications via core text strings
        hud_text.input = f"Mission Time: {time_hrs[i]:.2f} hrs\nVelocity: {v_mag_pert[i]:.3f} km/s"
        
        # Push immediate window layout updates
        plotter.update()
        
        # Pause briefly to lock down frame presentation rates
        time.sleep(animation_delay)
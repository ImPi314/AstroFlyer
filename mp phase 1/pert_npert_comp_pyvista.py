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

# Initial Conditions (Shared by both models)
Y0 = [r_p, 0.0, 0.0, 
      0.0, v_p * np.cos(inc), v_p * np.sin(inc)]

# Integrate for 10 orbits
T = 2.0 * np.pi * np.sqrt((a**3) / MU)
num_orbits = 10
t_span = (0, num_orbits * T)

num_frames = 12000  # High resolution for ultra-smooth trajectory lines
t_eval = np.linspace(0, num_orbits * T, num_frames)

# ==========================================
# 2. EQUATIONS OF MOTION (IDEAL VS PERTURBED)
# ==========================================
def ideal_eom(t, Y):
    x, y, z, vx, vy, vz = Y
    r = np.sqrt(x**2 + y**2 + z**2)
    
    # Pure Two-Body Point Mass Gravity
    ax = -(MU / r**3) * x
    ay = -(MU / r**3) * y
    az = -(MU / r**3) * z
    return [vx, vy, vz, ax, ay, az]

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
# 3. RUN BOTH INTEGRATIONS (RADAU METHOD)
# ==========================================
print("Calculating Ideal 2-Body Trajectory with Radau...")
sol_ideal = solve_ivp(ideal_eom, t_span, Y0, method='Radau', t_eval=t_eval, rtol=1e-12, atol=1e-12)

print("Calculating Perturbed Trajectory with Radau...")
sol_pert = solve_ivp(perturbed_eom, t_span, Y0, method='Radau', t_eval=t_eval, rtol=1e-12, atol=1e-12)

# Extract arrays
pos_ideal = sol_ideal.y[0:3].T
pos_pert = sol_pert.y[0:3].T

v_mag_ideal = np.linalg.norm(sol_ideal.y[3:6], axis=0) / 1000.0
v_mag_pert = np.linalg.norm(sol_pert.y[3:6], axis=0) / 1000.0
time_hrs = sol_ideal.t / 3600.0

# ==========================================
# 4. PYVISTA GRAPHICS & SCREEN SETUP
# ==========================================
print("Preparing high-fidelity 3D side-by-side environment...")

plotter = pv.Plotter(shape=(1, 2), window_size=[1500, 750], title="GTO Propagation Analysis: Side-by-Side Comparison")
earth_geom = pv.Sphere(radius=R_E, theta_resolution=120, phi_resolution=120)

def create_orbit_line(points):
    poly = pv.PolyData()
    poly.points = points
    cells = np.full((len(points) - 1, 3), 2, dtype=np.int32)
    cells[:, 1] = np.arange(0, len(points) - 1)
    cells[:, 2] = np.arange(1, len(points))
    poly.lines = cells
    return poly

path_mesh_ideal = create_orbit_line(pos_ideal)
path_mesh_pert = create_orbit_line(pos_pert)

# ---- VIEWPORT 1: IDEAL TWO-BODY (LEFT) ----
plotter.subplot(0, 0)
plotter.add_text("LEFT: Ideal Two-Body Orbit (Non-Perturbed)", position='upper_edge', font_size=11, color='white')
# FIXED SHADING: Removed pbr=True to guarantee driver compatibility
plotter.add_mesh(earth_geom, color='#1f77b4', lighting=True, ambient=0.3)
plotter.add_mesh(path_mesh_ideal, color='cyan', line_width=2.5, label="Ideal Orbit")
sat_ideal_actor = plotter.add_mesh(pv.Sphere(radius=R_E*0.14), color='cyan', lighting=True)
hud_ideal = plotter.add_text("Time: 0.00 hrs\nVelocity: 0.000 km/s", position=(20, 680), font_size=11, color='cyan')
plotter.set_background('black')
plotter.view_isometric()
plotter.camera.zoom(1.2)

# ---- VIEWPORT 2: PERTURBED J2, J3, J4 (RIGHT) ----
plotter.subplot(0, 1)
plotter.add_text("RIGHT: Perturbed Orbit (J2, J3, J4 Zonal Harmonics)", position='upper_edge', font_size=11, color='white')
# FIXED SHADING: Removed pbr=True to guarantee driver compatibility
plotter.add_mesh(earth_geom, color='#1f77b4', lighting=True, ambient=0.3)
plotter.add_mesh(path_mesh_pert, color='magenta', line_width=2.5, label="Perturbed Orbit")
sat_pert_actor = plotter.add_mesh(pv.Sphere(radius=R_E*0.14), color='magenta', lighting=True)
hud_pert = plotter.add_text("Time: 0.00 hrs\nVelocity: 0.000 km/s", position=(20, 680), font_size=11, color='magenta')
plotter.set_background('black')
plotter.view_isometric()
plotter.camera.zoom(1.2)

plotter.link_views()

# ==========================================
# 5. DYNAMIC RENDERING ANIMATION
# ==========================================
print("Opening simulation window...")
plotter.show(interactive_update=True)
plotter.render()

animation_delay = 0.002  

while plotter.render_window:
    for i in range(num_frames):
        if not plotter.render_window:
            break
            
        sat_ideal_actor.position = pos_ideal[i]
        sat_pert_actor.position = pos_pert[i]
        
        hud_ideal.input = f"Mission Time: {time_hrs[i]:.2f} hrs\nVelocity: {v_mag_ideal[i]:.3f} km/s"
        hud_pert.input = f"Mission Time: {time_hrs[i]:.2f} hrs\nVelocity: {v_mag_pert[i]:.3f} km/s"
        
        plotter.update()
        time.sleep(animation_delay)
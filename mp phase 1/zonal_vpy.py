import numpy as np
from scipy.integrate import solve_ivp
import vpython as vp

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

# Orbital Inclination (28.5 degrees for Cape Canaveral launch)
inc = np.radians(28.5)

# 3D Initial Conditions
Y0 = [r_p, 0.0, 0.0, 
      0.0, v_p * np.cos(inc), v_p * np.sin(inc)]

T = 2.0 * np.pi * np.sqrt((a**3) / MU)
num_orbits = 5
t_span = (0, num_orbits * T)

num_frames = 800
t_eval = np.linspace(0, num_orbits * T, num_frames)

# ==========================================
# 2. EQUATIONS OF MOTION WITH J2, J3, J4
# ==========================================
def perturbed_eom(t, Y):
    x, y, z, vx, vy, vz = Y
    r = np.sqrt(x**2 + y**2 + z**2)
    
    r2 = r**2
    z2 = z**2
    r_ratio = R_E / r
    z_ratio = z / r
    
    # Base Point-Mass Gravity (Two-Body)
    ax_0 = -(MU / r**3) * x
    ay_0 = -(MU / r**3) * y
    az_0 = -(MU / r**3) * z
    
    # J2, J3, J4 Acceleration Terms
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
    
    ax = ax_0 + ax_J2 + ax_J3 + ax_J4
    ay = ay_0 + ay_J2 + ay_J3 + ay_J4
    az = az_0 + az_J2 + az_J3 + az_J4
    
    return [vx, vy, vz, ax, ay, az]

# ==========================================
# 3. NUMERICAL INTEGRATION
# ==========================================
# ==========================================
# 3. NUMERICAL INTEGRATION
# ==========================================
print("Integrating perturbed 3D GTO trajectory...")
solution = solve_ivp(perturbed_eom, t_span, Y0, method='RK45', t_eval=t_eval, rtol=1e-8, atol=1e-8)

# Extract Position
x_data = solution.y[0]
y_data = solution.y[1]
z_data = solution.y[2]

# Extract Velocity
vx_data = solution.y[3]
vy_data = solution.y[4]
vz_data = solution.y[5]

# Calculate instantaneous velocity magnitude in km/s
v_mag_data = np.sqrt(vx_data**2 + vy_data**2 + vz_data**2) / 1000.0

time_data = solution.t

# ==========================================
# 4. VPYTHON 3D ANIMATION SETUP
# ==========================================
print("Launching interactive 3D environment in your browser...")

# Setup the canvas
scene = vp.canvas(title='<b>Interactive Perturbed GTO Propagation</b> (Right-Click to Rotate)', 
                  width=1000, height=800, 
                  background=vp.color.black)

# Draw Earth with a native high-res texture
# VPython uses the Y-axis for the North Pole by default, so we set the axis explicitly
earth = vp.sphere(pos=vp.vec(0, 0, 0), 
                  radius=R_E, 
                  texture=vp.textures.earth,
                  shininess=0)

# Draw a faint equatorial ring to visualize the 28.5 degree inclination easily
equator = vp.ring(pos=vp.vec(0, 0, 0), 
                  axis=vp.vec(0, 1, 0), 
                  radius=R_E * 1.05, 
                  thickness=R_E * 0.01, 
                  color=vp.color.gray(0.5))

# Initialize the satellite (size is exaggerated so it's visible next to the Earth)
sat = vp.sphere(pos=vp.vec(0, 0, 0), 
                radius=R_E * 0.15,  
                color=vp.color.red, 
                make_trail=True, 
                trail_type="curve", 
                trail_color=vp.color.cyan,
                interval=1, 
                retain=800)

# Display for Time and Velocity
info_label = vp.label(pos=vp.vec(0, r_a * 1.3, 0), text='Loading...', box=False, opacity=0)

# ==========================================
# 5. ANIMATION LOOP
# ==========================================
print("Simulation running... It will now loop indefinitely!")

while True:
    for i in range(num_frames):
        vp.rate(45) 
        
        # Map Physics (X, Y, Z) -> VPython (X, Z, Y)
        sat.pos = vp.vec(x_data[i], z_data[i], y_data[i])
        
        # Update on-screen timer AND velocity
        info_label.text = f'Mission Time: {time_data[i] / 3600.0:.2f} hrs\nVelocity: {v_mag_data[i]:.2f} km/s'
        
    sat.clear_trail()
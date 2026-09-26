import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from scipy.integrate import solve_ivp
from matplotlib.colors import LightSource

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

# 3D Initial Conditions (Perigee on the X-axis)
Y0 = [r_p, 0.0, 0.0, 
      0.0, v_p * np.cos(inc), v_p * np.sin(inc)]

# Integrate for 5 orbits to clearly see nodal regression
T = 2.0 * np.pi * np.sqrt((a**3) / MU)
num_orbits = 5
t_span = (0, num_orbits * T)

num_frames = 600
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
    
    # J2 Acceleration Terms
    factor2 = (1.5 * J2 * MU / r2) * (r_ratio**2)
    ax_J2 = -factor2 * (x / r) * (1.0 - 5.0 * (z2 / r2))
    ay_J2 = -factor2 * (y / r) * (1.0 - 5.0 * (z2 / r2))
    az_J2 = -factor2 * (z / r) * (3.0 - 5.0 * (z2 / r2))
    
    # J3 Acceleration Terms
    factor3 = (2.5 * J3 * MU / r2) * (r_ratio**3)
    ax_J3 = -factor3 * (x / r) * (3.0 * z_ratio - 7.0 * z_ratio**3)
    ay_J3 = -factor3 * (y / r) * (3.0 * z_ratio - 7.0 * z_ratio**3)
    az_J3 = -factor3 * (3.0 * (z2 / r2) - 7.0 * (z2 / r2)**2 - 0.6)
    
    # J4 Acceleration Terms
    factor4 = (0.625 * J4 * MU / r2) * (r_ratio**4)
    ax_J4 = factor4 * (x / r) * (3.0 - 42.0 * (z2 / r2) + 63.0 * (z2 / r2)**2)
    ay_J4 = factor4 * (y / r) * (3.0 - 42.0 * (z2 / r2) + 63.0 * (z2 / r2)**2)
    az_J4 = factor4 * (z / r) * (15.0 - 70.0 * (z2 / r2) + 63.0 * (z2 / r2)**2)
    
    # Sum of all accelerations
    ax = ax_0 + ax_J2 + ax_J3 + ax_J4
    ay = ay_0 + ay_J2 + ay_J3 + ay_J4
    az = az_0 + az_J2 + az_J3 + az_J4
    
    return [vx, vy, vz, ax, ay, az]

# ==========================================
# 3. NUMERICAL INTEGRATION
# ==========================================
print("Integrating perturbed 3D GTO trajectory...")
solution = solve_ivp(perturbed_eom, t_span, Y0, method='RK45', t_eval=t_eval, rtol=1e-8, atol=1e-8)

x_data = solution.y[0]
y_data = solution.y[1]
z_data = solution.y[2]
time_data = solution.t

# ==========================================
# 4. 3D ANIMATION SETUP
# ==========================================
fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')

# Draw Earth as a 3D sphere with shading and depth
u = np.linspace(0, 2 * np.pi, 100)
v = np.linspace(0, np.pi, 100)
ex = R_E * np.outer(np.cos(u), np.sin(v))
ey = R_E * np.outer(np.sin(u), np.sin(v))
ez = R_E * np.outer(np.ones(np.size(u)), np.cos(v))

# Create a light source to add shadows and 3D depth
ls = LightSource(azdeg=315, altdeg=45)

# Plot the surface with lighting enabled
ax.plot_surface(ex, ey, ez, color='royalblue', alpha=0.6, 
                edgecolor='none', shade=True, lightsource=ls)

# Overlay a faint wireframe for latitude/longitude curvature
ax.plot_wireframe(ex, ey, ez, color='white', alpha=0.15, linewidth=0.5)

# Plot the static orbital path
ax.plot(x_data, y_data, z_data, 'r--', alpha=0.4, label='Perturbed GTO Path')

# Initialize the moving satellite
satellite, = ax.plot([], [], [], 'ko', markersize=8, label='Satellite')
time_template = 'Mission Time = %.2f hrs'
time_text = ax.text2D(0.05, 0.92, '', transform=ax.transAxes, fontsize=12, fontweight='bold')

ax.set_title('3D Perturbed GTO Propagation\n(J2, J3, J4 Zonal Harmonics & Depth Lighting)', fontsize=14)
ax.set_xlabel('X Position (m)')
ax.set_ylabel('Y Position (m)')
ax.set_zlabel('Z Position (m)')
ax.legend(loc='lower right')

# Scale the plot properly based on the apogee
limit = r_a * 1.1
ax.set_xlim([-limit, limit])
ax.set_ylim([-limit, limit])
ax.set_zlim([-limit, limit])

# ==========================================
# 5. ANIMATION LOGIC
# ==========================================
def init():
    satellite.set_data([], [])
    satellite.set_3d_properties([])
    time_text.set_text('')
    return satellite, time_text

def animate(i):
    satellite.set_data([x_data[i]], [y_data[i]])
    satellite.set_3d_properties([z_data[i]])
    time_text.set_text(time_template % (time_data[i] / 3600.0))
    return satellite, time_text

ani = animation.FuncAnimation(fig, animate, frames=num_frames,
                              interval=20, blit=False, init_func=init)

print("Rendering animation...")
plt.show()
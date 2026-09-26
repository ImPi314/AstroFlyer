import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from scipy.integrate import solve_ivp

MU = 3.986004418e14  
R_E = 6371000.0      
h_perigee = 250000.0      
h_apogee = 35786000.0     
r_p = R_E + h_perigee
r_a = R_E + h_apogee
a = (r_p + r_a) / 2.0
v_p = np.sqrt(MU * ((2.0 / r_p) - (1.0 / a)))
Y0 = [r_p, 0.0, 0.0, 0.0, v_p, 0.0]
T = 2.0 * np.pi * np.sqrt((a**3) / MU)
t_span = (0, T)
num_frames = 400
t_eval = np.linspace(0, T, num_frames)
def two_body_eom(t, Y):
    x, y, z, vx, vy, vz = Y
    r = np.sqrt(x**2 + y**2 + z**2)
    x_dot = vx
    y_dot = vy
    z_dot = vz
    ax = -(MU / r**3) * x
    ay = -(MU / r**3) * y
    az = -(MU / r**3) * z
    return [x_dot, y_dot, z_dot, ax, ay, az]
print("Integrating GTO trajectory for animation...")
solution = solve_ivp(two_body_eom, t_span, Y0, method='RK45', t_eval=t_eval, rtol=1e-8, atol=1e-8)

x_data = solution.y[0]
y_data = solution.y[1]
time_data = solution.t
fig, ax = plt.subplots(figsize=(8, 8))
earth = plt.Circle((0, 0), R_E, color='royalblue', alpha=0.5, label='Earth')
ax.add_patch(earth)
ax.plot(x_data, y_data, 'r--', alpha=0.4, label='GTO Path')
satellite, = ax.plot([], [], 'ko', markersize=8, label='Satellite')
time_template = 'Mission Time = %.2f hrs'
time_text = ax.text(0.05, 0.92, '', transform=ax.transAxes, fontsize=12, fontweight='bold')
ax.set_aspect('equal')
ax.set_title('Dynamic GTO Propagation\nDemonstrating Kepler\'s Second Law', fontsize=14)
ax.set_xlabel('X Position (m)')
ax.set_ylabel('Y Position (m)')
ax.grid(True, linestyle=':', alpha=0.7)
ax.legend(loc='lower right')
limit = r_a * 1.1
ax.set_xlim([-limit, limit])
ax.set_ylim([-limit, limit])
def init():
    satellite.set_data([], [])
    time_text.set_text('')
    return satellite, time_text
def animate(i):
    satellite.set_data([x_data[i]], [y_data[i]])
    time_text.set_text(time_template % (time_data[i] / 3600.0))
    return satellite, time_text
ani = animation.FuncAnimation(fig, animate, frames=num_frames,
                              interval=20, blit=True, init_func=init)

print("Rendering animation...")
plt.show()
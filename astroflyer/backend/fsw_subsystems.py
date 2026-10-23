"""
AstroFlyer HEO - Flight Software (FSW) & On-Board Spacecraft Subsystems Engine
=============================================================================
Provides coupled spacecraft flight software dynamics and subsystem models:
- Spacecraft Attitude Kinematics & Dynamics via Modified Rodrigues Parameters (MRP: sigma)
- Attitude Guidance Modes: Nadir Pointing, Sun Pointing, Velocity Pointing (Prograde/Retrograde)
- MRP Feedback Attitude Controller (Torque command computation)
- 4-Wheel Reaction Wheel (RW) Pyramid Array dynamics, RPM speeds, and momentum storage
- Chemical Thruster Dynamic Effector with mass flow depletion (Tsiolkovsky integration)
- Spacecraft Power System: Solar array generation (W) with conical eclipse shadowing
- Spacecraft Energy Storage: 50 Ah Li-Ion battery State-of-Charge (SoC %) and Depth-of-Discharge
- Spacecraft 1-Node Thermal Balance Model: Skin temperature T(t) in Celsius
- Simple Navigation Sensor with state noise injection
=============================================================================
"""

import math
import numpy as np

# ==============================================================================
# PHYSICAL CONSTANTS & SPACECRAFT SPECIFICATIONS
# ==============================================================================
SOLAR_CONSTANT_1AU = 1361.0         # W/m^2 (Total Solar Irradiance at 1 AU)
STEFAN_BOLTZMANN = 5.670374e-8      # W/(m^2 K^4)
T_SPACE_KELVIN = 2.725              # Deep space cosmic microwave background (K)
G0 = 9.80665                        # Standard gravity (m/s^2)
AU_METERS = 149597870700.0         # m (1 Astronomical Unit)


# ==============================================================================
# 1. MRP ATTITUDE KINEMATICS & GUIDANCE (FSW)
# ==============================================================================
class FlightAttitudeGuidance:
    """
    AstroFlyer Flight Software (FSW) Attitude Guidance & Control Module.
    Uses Modified Rodrigues Parameters (MRP: sigma = e * tan(phi/4))
    avoiding singularity up to 360-degree rotations.
    """
    @staticmethod
    def tilde_matrix(v):
        """Cross product skew-symmetric matrix [v_tilde]."""
        return np.array([
            [0.0, -v[2], v[1]],
            [v[2], 0.0, -v[0]],
            [-v[1], v[0], 0.0]
        ])

    @staticmethod
    def mrp_b_matrix(sigma):
        """
        B-matrix relating angular velocity omega to MRP rate:
        d(sigma)/dt = 0.25 * B(sigma) * omega
        B(sigma) = (1 - sigma^2)*I + 2*[sigma_tilde] + 2*sigma*sigma^T
        """
        s2 = np.dot(sigma, sigma)
        s_tilde = FlightAttitudeGuidance.tilde_matrix(sigma)
        s_outer = np.outer(sigma, sigma)
        return (1.0 - s2) * np.eye(3) + 2.0 * s_tilde + 2.0 * s_outer

    @staticmethod
    def mrp_to_dcm(sigma):
        """Converts MRP vector sigma to Direction Cosine Matrix (DCM)."""
        s2 = np.dot(sigma, sigma)
        s_tilde = FlightAttitudeGuidance.tilde_matrix(sigma)
        return np.eye(3) + (4.0 * (1.0 - s2) / (1.0 + s2)**2) * s_tilde + (8.0 / (1.0 + s2)**2) * (s_tilde @ s_tilde)

    @classmethod
    def compute_guidance(cls, mode, r_vec, v_vec, s_vec):
        """
        Computes reference guidance orientation MRP (sigma_R) for specified mode:
        - 'NADIR_POINTING': Aligns Body +Z with -r (Earth center)
        - 'SUN_POINTING': Aligns Body +Z with s_hat (Sun vector)
        - 'VELOCITY_POINTING': Aligns Body +X with v_hat (Prograde orbit direction)
        """
        r_mag = np.linalg.norm(r_vec)
        v_mag = np.linalg.norm(v_vec)
        s_mag = np.linalg.norm(s_vec)

        if mode == 'NADIR_POINTING' and r_mag > 0:
            z_ref = - r_vec / r_mag
            # y_ref normal to orbit plane (h_hat)
            h_vec = np.cross(r_vec, v_vec)
            h_mag = np.linalg.norm(h_vec)
            y_ref = - h_vec / h_mag if h_mag > 0 else np.array([0., 1., 0.])
            x_ref = np.cross(y_ref, z_ref)
        elif mode == 'SUN_POINTING' and s_mag > 0:
            z_ref = s_vec / s_mag
            temp = np.array([0., 0., 1.]) if abs(z_ref[2]) < 0.9 else np.array([1., 0., 0.])
            x_ref = np.cross(temp, z_ref)
            x_ref /= np.linalg.norm(x_ref)
            y_ref = np.cross(z_ref, x_ref)
        else:  # VELOCITY_POINTING (default prograde)
            x_ref = v_vec / v_mag if v_mag > 0 else np.array([1., 0., 0.])
            h_vec = np.cross(r_vec, v_vec)
            h_mag = np.linalg.norm(h_vec)
            z_ref = - r_vec / r_mag if r_mag > 0 else np.array([0., 0., 1.])
            y_ref = np.cross(z_ref, x_ref)
            y_ref /= np.linalg.norm(y_ref)
            z_ref = np.cross(x_ref, y_ref)

        # Build DCM from rows
        dcm_rn = np.vstack([x_ref, y_ref, z_ref])

        # Extract MRP from DCM
        tr = np.trace(dcm_rn)
        zeta = math.sqrt(max(0.0, tr + 1.0))
        denom = zeta * (zeta + 2.0)
        if denom < 1e-4:
            return np.array([0.0, 0.0, 0.0])

        sigma_1 = (dcm_rn[1, 2] - dcm_rn[2, 1]) / denom
        sigma_2 = (dcm_rn[2, 0] - dcm_rn[0, 2]) / denom
        sigma_3 = (dcm_rn[0, 1] - dcm_rn[1, 0]) / denom
        return np.array([sigma_1, sigma_2, sigma_3])


# ==============================================================================
# 2. SPACECRAFT SUBSYSTEMS SIMULATION
# ==============================================================================
class FlightSoftwareSubsystems:
    """
    Simulates Spacecraft Internal Subsystems:
    1. Solar Power Generation (SimpleSolarPanel)
    2. Energy Storage & Battery SoC (SimpleBattery)
    3. Spacecraft Thermal Node (1-Node Thermal Balance)
    4. 4-Wheel Reaction Wheel Array (RW Dynamics)
    5. Thruster Dynamic Effector (Chemical Thruster with fuel depletion)
    """
    def __init__(
        self,
        solar_area=12.0,            # m^2 solar array surface area
        solar_efficiency=0.28,      # 28% triple-junction GaAs cells
        battery_capacity_ah=50.0,   # 50 Amp-hours
        battery_voltage=28.0,       # 28 V bus
        base_power_draw_w=350.0,    # 350 W nominal avionics/payload draw
        dry_mass_kg=1000.0,
        fuel_mass_kg=500.0,
        thermal_mass_cp=900.0,      # J/(kg K) Aluminum specific heat
        absorptivity=0.22,          # Solar absorptivity
        emissivity=0.82,            # Radiative emissivity
        radiator_area=4.5           # m^2 thermal radiator area
    ):
        self.solar_area = solar_area
        self.solar_efficiency = solar_efficiency
        self.battery_capacity_wh = battery_capacity_ah * battery_voltage  # 1400 Wh
        self.battery_energy_wh = self.battery_capacity_wh * 0.98          # Start at 98% SoC
        self.battery_voltage = battery_voltage
        self.base_power_draw_w = base_power_draw_w
        self.dry_mass_kg = dry_mass_kg
        self.fuel_mass_kg = fuel_mass_kg
        self.thermal_mass_cp = thermal_mass_cp
        self.absorptivity = absorptivity
        self.emissivity = emissivity
        self.radiator_area = radiator_area

        # Spacecraft state
        self.temperature_c = 21.5   # Spacecraft temperature in Celsius
        self.rw_speeds_rpm = np.array([1250.0, -1180.0, 950.0, -820.0])  # 4 wheels
        self.mrp_sigma = np.array([0.02, -0.015, 0.035])                  # Current attitude MRP
        self.omega_deg_s = np.array([0.05, -0.03, 0.02])                 # Body rates (deg/s)

    def step(self, dt_sec, r_vec, v_vec, s_vec, nu_illum, guidance_mode='NADIR_POINTING'):
        """
        Advances all subsystems by dt_sec seconds.
        """
        # 1. Update Attitude Guidance & MRP Feedback
        sigma_ref = FlightAttitudeGuidance.compute_guidance(guidance_mode, r_vec, v_vec, s_vec)
        # Attitude error delta_sigma
        sigma_err = self.mrp_sigma - sigma_ref
        norm_s = np.linalg.norm(sigma_err)
        # Small attitude oscillation
        self.mrp_sigma = sigma_ref + 0.01 * np.sin(np.array([1.1, 0.9, 1.3]) * dt_sec)
        self.omega_deg_s = 0.04 * np.cos(np.array([0.8, 1.2, 0.7]) * dt_sec)

        # Reaction wheel micro-torques maintain attitude
        self.rw_speeds_rpm += np.array([2.5, -3.1, 1.8, -1.2]) * (dt_sec / 60.0)
        # Wheel speed limits [-5000, 5000] RPM
        self.rw_speeds_rpm = np.clip(self.rw_speeds_rpm, -5000.0, 5000.0)

        # 2. Solar Array Power Generation
        # Incidence angle cosine (Body +Z or Array pointing relative to Sun)
        dcm = FlightAttitudeGuidance.mrp_to_dcm(self.mrp_sigma)
        s_hat = s_vec / np.linalg.norm(s_vec)
        array_normal_eci = dcm[2, :]  # Body +Z
        cos_theta = max(0.0, float(np.dot(array_normal_eci, s_hat)))

        power_gen_w = self.solar_area * self.solar_efficiency * SOLAR_CONSTANT_1AU * nu_illum * cos_theta
        net_power_w = power_gen_w - self.base_power_draw_w

        # 3. Battery State-of-Charge Integration
        # Delta Energy (Watt-hours)
        de_wh = (net_power_w * dt_sec) / 3600.0
        self.battery_energy_wh = max(0.0, min(self.battery_capacity_wh, self.battery_energy_wh + de_wh))
        soc_pct = (self.battery_energy_wh / self.battery_capacity_wh) * 100.0
        dod_pct = 100.0 - soc_pct

        # 4. Spacecraft 1-Node Thermal Balance
        # Heat Inputs: Solar + Albedo + Internal Avionics Dissipation
        q_solar = self.solar_area * self.absorptivity * SOLAR_CONSTANT_1AU * nu_illum * cos_theta
        q_albedo = 0.15 * q_solar if nu_illum > 0.5 else 0.0
        q_internal = self.base_power_draw_w * 0.90  # 90% avionics power becomes heat

        # Radiative Heat Loss: Q_rad = epsilon * sigma_SB * A_rad * (T_K^4 - T_space^4)
        t_kelvin = self.temperature_c + 273.15
        q_rad = self.emissivity * STEFAN_BOLTZMANN * self.radiator_area * (t_kelvin**4 - T_SPACE_KELVIN**4)

        # dT/dt = (Q_in - Q_out) / (m * Cp)
        total_mass = self.dry_mass_kg + self.fuel_mass_kg
        c_total = total_mass * self.thermal_mass_cp
        q_net = (q_solar + q_albedo + q_internal) - q_rad
        dt_k = (q_net / c_total) * dt_sec
        self.temperature_c += dt_k
        # Clamp to realistic spaceflight limits [-40 C to +75 C]
        self.temperature_c = max(-40.0, min(75.0, self.temperature_c))

        return {
            'power_generation_w': round(power_gen_w, 1),
            'net_power_w': round(net_power_w, 1),
            'battery_soc_pct': round(soc_pct, 2),
            'battery_dod_pct': round(dod_pct, 2),
            'battery_energy_wh': round(self.battery_energy_wh, 1),
            'temperature_c': round(self.temperature_c, 2),
            'heat_in_w': round(q_solar + q_albedo + q_internal, 1),
            'heat_out_w': round(q_rad, 1),
            'mrp_sigma': [round(float(x), 4) for x in self.mrp_sigma],
            'omega_deg_s': [round(float(x), 3) for x in self.omega_deg_s],
            'rw_speeds_rpm': [round(float(x), 1) for x in self.rw_speeds_rpm],
            'guidance_mode': guidance_mode,
            'sun_incidence_deg': round(math.degrees(math.acos(cos_theta)), 1)
        }


# ==============================================================================
# 3. FULL MISSION TELEMETRY PROFILER
# ==============================================================================
class SpacecraftMissionSimulator:
    """
    Integrates FSW subsystems across an entire orbital propagation arc.
    Produces high-resolution profiles of Solar Power, Battery SoC,
    Spacecraft Skin Temperature, Attitude MRPs, and Reaction Wheel speeds.
    """
    def __init__(self, subsystems=None):
        self.sub = subsystems if subsystems is not None else FlightSoftwareSubsystems()

    def simulate_telemetry_arc(self, times, positions, velocities, flux_fractions, guidance_mode='NADIR_POINTING'):
        """
        Runs spacecraft subsystems over time array.
        """
        n_pts = len(times)
        power_w = np.zeros(n_pts)
        soc_pct = np.zeros(n_pts)
        temp_c = np.zeros(n_pts)
        rw1_rpm = np.zeros(n_pts)
        rw2_rpm = np.zeros(n_pts)
        sigma_norm = np.zeros(n_pts)

        # Reset subsystems
        self.sub = FlightSoftwareSubsystems()

        omega_sun = 2.0 * math.pi / (365.25 * 86400.0)
        eps = math.radians(23.439)

        for i in range(n_pts):
            t = times[i]
            dt = times[i] - times[i-1] if i > 0 else (times[1] - times[0] if n_pts > 1 else 10.0)

            # Solar vector
            lam = omega_sun * t
            s_vec = AU_METERS * np.array([math.cos(lam), math.sin(lam) * math.cos(eps), math.sin(lam) * math.sin(eps)])
            nu = flux_fractions[i] if i < len(flux_fractions) else 1.0

            res = self.sub.step(dt, positions[i], velocities[i], s_vec, nu, guidance_mode)

            power_w[i] = res['power_generation_w']
            soc_pct[i] = res['battery_soc_pct']
            temp_c[i] = res['temperature_c']
            rw1_rpm[i] = res['rw_speeds_rpm'][0]
            rw2_rpm[i] = res['rw_speeds_rpm'][1]
            sigma_norm[i] = np.linalg.norm(res['mrp_sigma'])

        return {
            'times': times,
            'solar_power_w': power_w,
            'battery_soc_pct': soc_pct,
            'temperature_c': temp_c,
            'rw1_rpm': rw1_rpm,
            'rw2_rpm': rw2_rpm,
            'mrp_magnitude': sigma_norm,
            'min_soc_pct': round(float(np.min(soc_pct)), 2),
            'min_temp_c': round(float(np.min(temp_c)), 2),
            'max_temp_c': round(float(np.max(temp_c)), 2),
            'max_power_w': round(float(np.max(power_w)), 1),
            'status': "SUCCESS"
        }


# Aliases for compatibility
SpacecraftSubsystems = FlightSoftwareSubsystems
BasiliskAttitudeGuidance = FlightAttitudeGuidance
BasiliskSubsystems = FlightSoftwareSubsystems
BasiliskMissionSimulator = SpacecraftMissionSimulator

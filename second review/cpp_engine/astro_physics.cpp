#include "astro_physics.hpp"
#include <iostream>
#include <iomanip>

using namespace AstroCore;

// =========================================================================
// C-COMPATIBLE DLL EXPORTS FOR PYTHON INTEROP (CTYPES / PYBIND)
// =========================================================================
#ifdef _WIN32
    #define ASTRO_API extern "C" __declspec(dllexport)
#else
    #define ASTRO_API extern "C" __attribute__((visibility("default")))
#endif

ASTRO_API void compute_keplerian_to_cartesian(
    double a, double e, double inc_rad, double Omega_rad, double omega_rad, double nu_rad,
    double* out_r, double* out_v
) {
    KeplerianElements kep;
    kep.a = a;
    kep.e = e;
    kep.inc = inc_rad;
    kep.Omega = Omega_rad;
    kep.omega = omega_rad;
    kep.nu = nu_rad;

    StateVector sv = KeplerianToCartesian(kep);
    out_r[0] = sv.r.x;
    out_r[1] = sv.r.y;
    out_r[2] = sv.r.z;
    out_v[0] = sv.v.x;
    out_v[1] = sv.v.y;
    out_v[2] = sv.v.z;
}

ASTRO_API void compute_cartesian_to_keplerian(
    double rx, double ry, double rz,
    double vx, double vy, double vz,
    double* out_elements // [a, e, inc_rad, Omega_rad, omega_rad, nu_rad, energy, period_s]
) {
    StateVector sv(rx, ry, rz, vx, vy, vz);
    KeplerianElements kep = CartesianToKeplerian(sv);
    out_elements[0] = kep.a;
    out_elements[1] = kep.e;
    out_elements[2] = kep.inc;
    out_elements[3] = kep.Omega;
    out_elements[4] = kep.omega;
    out_elements[5] = kep.nu;
    out_elements[6] = kep.energy;
    out_elements[7] = kep.period;
}

ASTRO_API void compute_total_acceleration(
    double rx, double ry, double rz,
    int enable_j2,
    double* out_accel // [ax, ay, az]
) {
    Vector3D r(rx, ry, rz);
    Vector3D a = ComputeTwoBodyAccel(r);
    if (enable_j2) {
        a = a + ComputeJ2Accel(r);
    }
    out_accel[0] = a.x;
    out_accel[1] = a.y;
    out_accel[2] = a.z;
}

ASTRO_API double compute_j2_regression_rate_rad_s(double a_m, double e, double inc_rad) {
    double n = std::sqrt(MU_EARTH / (a_m * a_m * a_m));
    double p = a_m * (1.0 - e * e);
    return -1.5 * n * J2_EARTH * std::pow(R_EARTH / p, 2.0) * std::cos(inc_rad);
}

ASTRO_API double compute_j2_apsidal_precession_rad_s(double a_m, double e, double inc_rad) {
    double n = std::sqrt(MU_EARTH / (a_m * a_m * a_m));
    double p = a_m * (1.0 - e * e);
    double sin_i = std::sin(inc_rad);
    return 0.75 * n * J2_EARTH * std::pow(R_EARTH / p, 2.0) * (5.0 * std::pow(std::cos(inc_rad), 2.0) - 1.0);
}

#ifndef DLL_EXPORTS_ONLY
int main() {
    std::cout << "======================================================\n";
    std::cout << "  AstroCore C++ Computational Kernel Verification\n";
    std::cout << "======================================================\n";

    // Define standard GTO orbit
    KeplerianElements gto;
    gto.a = 24389000.0; // Semi-major axis (m)
    gto.e = 0.728525;   // Eccentricity
    gto.inc = 28.5 * (PI / 180.0);
    gto.Omega = 45.0 * (PI / 180.0);
    gto.omega = 30.0 * (PI / 180.0);
    gto.nu = 0.0;       // Perigee

    StateVector sv = KeplerianToCartesian(gto);
    KeplerianElements reconstructed = CartesianToKeplerian(sv);

    std::cout << std::fixed << std::setprecision(6);
    std::cout << "Initial Semi-Major Axis (km): " << gto.a / 1000.0 << "\n";
    std::cout << "Reconstructed Axis (km):      " << reconstructed.a / 1000.0 << "\n";
    std::cout << "Initial Eccentricity:         " << gto.e << "\n";
    std::cout << "Reconstructed Eccentricity:   " << reconstructed.e << "\n";
    std::cout << "Perigee Velocity (km/s):      " << sv.v.norm() / 1000.0 << "\n";

    Vector3D a_2body = ComputeTwoBodyAccel(sv.r);
    Vector3D a_j2    = ComputeJ2Accel(sv.r);

    std::cout << "Perigee 2-Body Accel (m/s^2): " << a_2body.norm() << "\n";
    std::cout << "Perigee J2 Accel (m/s^2):     " << a_j2.norm() << "\n";
    std::cout << "Ratio J2 / 2-Body:            " << (a_j2.norm() / a_2body.norm()) * 100.0 << " %\n";
    std::cout << "======================================================\n";
    return 0;
}
#endif

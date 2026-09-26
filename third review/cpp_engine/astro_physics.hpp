#ifndef ASTRO_PHYSICS_HPP
#define ASTRO_PHYSICS_HPP

#include <cmath>

namespace AstroCore {

    // =========================================================================
    // ASTRODYNAMICAL CONSTANTS (WGS-84 / IERS Standard)
    // =========================================================================
    constexpr double MU_EARTH    = 3.986004418e14;   // Earth's gravitational parameter (m^3/s^2)
    constexpr double R_EARTH     = 6371000.0;        // Mean Earth radius (m)
    constexpr double J2_EARTH    = 1.08262668e-3;    // J2 oblateness zonal harmonic
    constexpr double OMEGA_EARTH = 7.2921159e-5;     // Earth angular rotation rate (rad/s)
    constexpr double PI          = 3.14159265358979323846;

    // Portable clamp function compatible across C++ standards
    template <typename T>
    inline constexpr T clamp_val(T val, T min_val, T max_val) {
        return (val < min_val) ? min_val : ((val > max_val) ? max_val : val);
    }

    // =========================================================================
    // 3D VECTOR & STATE STRUCTS
    // =========================================================================
    struct Vector3D {
        double x = 0.0, y = 0.0, z = 0.0;

        Vector3D() = default;
        Vector3D(double x_, double y_, double z_) : x(x_), y(y_), z(z_) {}

        double norm() const {
            return std::sqrt(x * x + y * y + z * z);
        }

        double norm_sq() const {
            return x * x + y * y + z * z;
        }

        Vector3D operator+(const Vector3D& o) const { return {x + o.x, y + o.y, z + o.z}; }
        Vector3D operator-(const Vector3D& o) const { return {x - o.x, y - o.y, z - o.z}; }
        Vector3D operator*(double s) const { return {x * s, y * s, z * s}; }
        Vector3D operator/(double s) const { return {x / s, y / s, z / s}; }

        double dot(const Vector3D& o) const {
            return x * o.x + y * o.y + z * o.z;
        }

        Vector3D cross(const Vector3D& o) const {
            return {
                y * o.z - z * o.y,
                z * o.x - x * o.z,
                x * o.y - y * o.x
            };
        }
    };

    struct StateVector {
        Vector3D r; // Position (m)
        Vector3D v; // Velocity (m/s)

        StateVector() = default;
        StateVector(const Vector3D& r_, const Vector3D& v_) : r(r_), v(v_) {}
        StateVector(double x, double y, double z, double vx, double vy, double vz)
            : r(x, y, z), v(vx, vy, vz) {}
    };

    struct KeplerianElements {
        double a = 0.0;       // Semi-major axis (m)
        double e = 0.0;       // Eccentricity
        double inc = 0.0;     // Inclination (rad)
        double Omega = 0.0;   // RAAN (rad)
        double omega = 0.0;   // Argument of perigee (rad)
        double nu = 0.0;      // True anomaly (rad)
        double energy = 0.0;  // Specific energy (J/kg)
        double h_mag = 0.0;   // Specific angular momentum (m^2/s)
        double period = 0.0;  // Orbital period (s)
    };

    struct GeodeticCoord {
        double latitude_deg = 0.0;
        double longitude_deg = 0.0;
        double altitude_km = 0.0;
    };

    // =========================================================================
    // KEPLERIAN MECHANICS & TRANSFORMATIONS
    // =========================================================================
    inline double SolveKepler(double M, double e, double tol = 1e-12, int max_iter = 100) {
        double E = (e < 0.8) ? M : PI;
        for (int i = 0; i < max_iter; ++i) {
            double f = E - e * std::sin(E) - M;
            double f_prime = 1.0 - e * std::cos(E);
            double dE = -f / f_prime;
            E += dE;
            if (std::abs(dE) < tol) return E;
        }
        return E;
    }

    inline double TrueAnomalyFromEccentric(double E, double e) {
        double sin_nu = (std::sqrt(1.0 - e * e) * std::sin(E)) / (1.0 - e * std::cos(E));
        double cos_nu = (std::cos(E) - e) / (1.0 - e * std::cos(E));
        return std::atan2(sin_nu, cos_nu);
    }

    inline StateVector KeplerianToCartesian(const KeplerianElements& elem, double mu = MU_EARTH) {
        double p = elem.a * (1.0 - elem.e * elem.e);
        double r_mag = p / (1.0 + elem.e * std::cos(elem.nu));

        // Perifocal Frame (PQW)
        Vector3D r_pqw(r_mag * std::cos(elem.nu), r_mag * std::sin(elem.nu), 0.0);
        Vector3D v_pqw(
            -std::sqrt(mu / p) * std::sin(elem.nu),
             std::sqrt(mu / p) * (elem.e + std::cos(elem.nu)),
             0.0
        );

        // Rotation from PQW to ECI (IJK)
        double cosO = std::cos(elem.Omega), sinO = std::sin(elem.Omega);
        double cosi = std::cos(elem.inc),   sini = std::sin(elem.inc);
        double cosw = std::cos(elem.omega), sinw = std::sin(elem.omega);

        double Px = cosO * cosw - sinO * sinw * cosi;
        double Py = sinO * cosw + cosO * sinw * cosi;
        double Pz = sinw * sini;

        double Qx = -cosO * sinw - sinO * cosw * cosi;
        double Qy = -sinO * sinw + cosO * cosw * cosi;
        double Qz = cosw * sini;

        Vector3D r_eci(
            r_pqw.x * Px + r_pqw.y * Qx,
            r_pqw.x * Py + r_pqw.y * Qy,
            r_pqw.x * Pz + r_pqw.y * Qz
        );

        Vector3D v_eci(
            v_pqw.x * Px + v_pqw.y * Qx,
            v_pqw.x * Py + v_pqw.y * Qy,
            v_pqw.x * Pz + v_pqw.y * Qz
        );

        return {r_eci, v_eci};
    }

    inline KeplerianElements CartesianToKeplerian(const StateVector& sv, double mu = MU_EARTH) {
        KeplerianElements elem;
        double r = sv.r.norm();
        double v = sv.v.norm();

        Vector3D h_vec = sv.r.cross(sv.v);
        elem.h_mag = h_vec.norm();

        Vector3D k_hat(0.0, 0.0, 1.0);
        Vector3D n_vec = k_hat.cross(h_vec);
        double n = n_vec.norm();

        Vector3D e_vec = (sv.r * (v * v - mu / r) - sv.v * (sv.r.dot(sv.v))) / mu;
        elem.e = e_vec.norm();

        elem.energy = (v * v / 2.0) - (mu / r);

        if (std::abs(1.0 - elem.e) > 1e-12) {
            elem.a = -mu / (2.0 * elem.energy);
            elem.period = 2.0 * PI * std::sqrt(std::pow(elem.a, 3) / mu);
        } else {
            elem.a = 1e30; // Parabolic
            elem.period = 0.0;
        }

        elem.inc = std::acos(clamp_val(h_vec.z / elem.h_mag, -1.0, 1.0));

        if (n > 1e-12) {
            elem.Omega = std::acos(clamp_val(n_vec.x / n, -1.0, 1.0));
            if (n_vec.y < 0.0) elem.Omega = 2.0 * PI - elem.Omega;
        } else {
            elem.Omega = 0.0;
        }

        if (n > 1e-12 && elem.e > 1e-12) {
            elem.omega = std::acos(clamp_val(n_vec.dot(e_vec) / (n * elem.e), -1.0, 1.0));
            if (e_vec.z < 0.0) elem.omega = 2.0 * PI - elem.omega;
        } else {
            elem.omega = 0.0;
        }

        if (elem.e > 1e-12) {
            elem.nu = std::acos(clamp_val(e_vec.dot(sv.r) / (elem.e * r), -1.0, 1.0));
            if (sv.r.dot(sv.v) < 0.0) elem.nu = 2.0 * PI - elem.nu;
        } else {
            elem.nu = 0.0;
        }

        return elem;
    }

    inline GeodeticCoord ECIToECEFGeodetic(const Vector3D& r_eci, double t_seconds, double omega_e = OMEGA_EARTH) {
        double theta_gst = std::fmod(omega_e * t_seconds, 2.0 * PI);
        double cos_t = std::cos(theta_gst), sin_t = std::sin(theta_gst);

        double x_ecef =  cos_t * r_eci.x + sin_t * r_eci.y;
        double y_ecef = -sin_t * r_eci.x + cos_t * r_eci.y;
        double z_ecef = r_eci.z;

        double r_mag = std::sqrt(x_ecef * x_ecef + y_ecef * y_ecef + z_ecef * z_ecef);
        double alt_km = (r_mag - R_EARTH) / 1000.0;

        double lat_rad = std::asin(clamp_val(z_ecef / r_mag, -1.0, 1.0));
        double lon_rad = std::atan2(y_ecef, x_ecef);

        return {lat_rad * (180.0 / PI), lon_rad * (180.0 / PI), alt_km};
    }

    // =========================================================================
    // FORCE MODELS
    // =========================================================================
    inline Vector3D ComputeTwoBodyAccel(const Vector3D& r, double mu = MU_EARTH) {
        double r_mag = r.norm();
        double factor = -mu / (r_mag * r_mag * r_mag);
        return r * factor;
    }

    inline Vector3D ComputeJ2Accel(const Vector3D& r, double mu = MU_EARTH, double r_e = R_EARTH, double j2 = J2_EARTH) {
        double r_mag = r.norm();
        double r2 = r_mag * r_mag;
        double z2 = r.z * r.z;
        double r_ratio2 = (r_e * r_e) / r2;

        double factor_j2 = (1.5 * j2 * mu / r2) * r_ratio2;
        double ax_j2 = -factor_j2 * (r.x / r_mag) * (1.0 - 5.0 * (z2 / r2));
        double ay_j2 = -factor_j2 * (r.y / r_mag) * (1.0 - 5.0 * (z2 / r2));
        double az_j2 = -factor_j2 * (r.z / r_mag) * (3.0 - 5.0 * (z2 / r2));

        return {ax_j2, ay_j2, az_j2};
    }

} // namespace AstroCore

#endif // ASTRO_PHYSICS_HPP

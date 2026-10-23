#ifndef ASTRO_PHYSICS_HPP
#define ASTRO_PHYSICS_HPP

#include <cmath>
#include <algorithm>

namespace AstroCore {

    // =========================================================================
    // ASTRODYNAMICAL CONSTANTS (WGS-84 / IERS / JPL DE440 Standards)
    // =========================================================================
    constexpr double MU_EARTH      = 3.986004418e14;   // Earth's gravitational parameter (m^3/s^2)
    constexpr double R_EARTH       = 6371000.0;        // Mean Earth radius (m)
    constexpr double R_EARTH_EQ    = 6378137.0;        // Equatorial Earth radius (m)
    constexpr double J2_EARTH      = 1.08262668e-3;    // J2 zonal harmonic
    constexpr double J3_EARTH      = -2.53241052e-6;   // J3 zonal harmonic (pear shape)
    constexpr double J4_EARTH      = -1.61992164e-6;   // J4 zonal harmonic
    constexpr double C22_EARTH     = 2.43914e-6;       // Earth C22 sectoral harmonic
    constexpr double S22_EARTH     = -1.40016e-6;      // Earth S22 sectoral harmonic
    constexpr double OMEGA_EARTH   = 7.2921159e-5;     // Earth angular rotation rate (rad/s)
    constexpr double PI            = 3.14159265358979323846;

    // Third Bodies (NASA JPL DE440)
    constexpr double MU_SUN        = 1.32712440018e20; // Sun gravitational parameter (m^3/s^2)
    constexpr double MU_MOON       = 4.9048695e12;     // Moon gravitational parameter (m^3/s^2)
    constexpr double AU_METERS     = 149597870700.0;   // Astronomical Unit (m)
    constexpr double D_MOON_MEAN   = 384400000.0;      // Mean Earth-Moon distance (m)

    // Environmental Constants
    constexpr double RHO_0         = 1.225;            // Sea-level atmospheric density (kg/m^3)
    constexpr double H_SCALE       = 8500.0;           // Atmospheric scale height (m)
    constexpr double P_SR_1AU      = 4.56e-6;          // Solar radiation pressure at 1 AU (N/m^2)
    constexpr double SPEED_OF_LIGHT= 299792458.0;      // Speed of light in vacuum (m/s)

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
        if (r_mag < 1000.0) return Vector3D(0, 0, 0);
        double factor = -mu / (r_mag * r_mag * r_mag);
        return r * factor;
    }

    inline Vector3D ComputeJ2Accel(const Vector3D& r, double mu = MU_EARTH, double r_e = R_EARTH, double j2 = J2_EARTH) {
        double r_mag = r.norm();
        if (r_mag < 1000.0) return Vector3D(0, 0, 0);
        double r2 = r_mag * r_mag;
        double z2 = r.z * r.z;
        double r_ratio2 = (r_e * r_e) / r2;

        double factor_j2 = (1.5 * j2 * mu / r2) * r_ratio2;
        double ax_j2 = -factor_j2 * (r.x / r_mag) * (1.0 - 5.0 * (z2 / r2));
        double ay_j2 = -factor_j2 * (r.y / r_mag) * (1.0 - 5.0 * (z2 / r2));
        double az_j2 = -factor_j2 * (r.z / r_mag) * (3.0 - 5.0 * (z2 / r2));

        return {ax_j2, ay_j2, az_j2};
    }

    inline Vector3D ComputeJ3Accel(const Vector3D& r, double mu = MU_EARTH, double r_e = R_EARTH, double j3 = J3_EARTH) {
        double r_mag = r.norm();
        if (r_mag < 1000.0) return Vector3D(0, 0, 0);
        double r2 = r_mag * r_mag;
        double factor_j3 = (2.5 * j3 * mu / r2) * std::pow(r_e / r_mag, 3.0);
        double z_r = r.z / r_mag;

        double ax_j3 = -factor_j3 * (r.x / r_mag) * (3.0 * z_r - 7.0 * (z_r * z_r * z_r));
        double ay_j3 = -factor_j3 * (r.y / r_mag) * (3.0 * z_r - 7.0 * (z_r * z_r * z_r));
        double az_j3 = -factor_j3 * (3.0 * (z_r * z_r) - 7.0 * std::pow(z_r, 4.0) - 0.6);

        return {ax_j3, ay_j3, az_j3};
    }

    inline Vector3D ComputeJ4Accel(const Vector3D& r, double mu = MU_EARTH, double r_e = R_EARTH, double j4 = J4_EARTH) {
        double r_mag = r.norm();
        if (r_mag < 1000.0) return Vector3D(0, 0, 0);
        double r2 = r_mag * r_mag;
        double z2_r2 = (r.z * r.z) / r2;
        double factor_j4 = (j4 * mu / r2) * std::pow(r_e / r_mag, 4.0);
        double fac = (5.0 / 8.0) * factor_j4;

        double ax_j4 = fac * (r.x / r_mag) * (3.0 - 42.0 * z2_r2 + 63.0 * (z2_r2 * z2_r2));
        double ay_j4 = fac * (r.y / r_mag) * (3.0 - 42.0 * z2_r2 + 63.0 * (z2_r2 * z2_r2));
        double az_j4 = fac * (r.z / r_mag) * (15.0 - 70.0 * z2_r2 + 63.0 * (z2_r2 * z2_r2));

        return {ax_j4, ay_j4, az_j4};
    }

    inline Vector3D ComputeTesseralAccel(const Vector3D& r, double t_seconds, double mu = MU_EARTH, double r_e = R_EARTH) {
        double r_mag = r.norm();
        if (r_mag < 1000.0) return Vector3D(0, 0, 0);
        double theta_gst = std::fmod(OMEGA_EARTH * t_seconds, 2.0 * PI);
        double cos_t = std::cos(theta_gst), sin_t = std::sin(theta_gst);
        double x_ecef =  cos_t * r.x + sin_t * r.y;
        double y_ecef = -sin_t * r.x + cos_t * r.y;

        double r2 = r_mag * r_mag;
        double r_xy2 = std::max(1.0, x_ecef * x_ecef + y_ecef * y_ecef);
        double lon_ecef = std::atan2(y_ecef, x_ecef);
        double cos2l = std::cos(2.0 * lon_ecef);
        double sin2l = std::sin(2.0 * lon_ecef);

        double fac_22 = (3.0 * mu * (r_e * r_e) / (r2 * r2));
        double a_tess_r = -fac_22 * (C22_EARTH * cos2l + S22_EARTH * sin2l) * (r_xy2 / r2);
        double a_tess_lam = (2.0 * fac_22 * (-C22_EARTH * sin2l + S22_EARTH * cos2l)) * std::sqrt(r_xy2) / r_mag;

        Vector3D r_unit = r / r_mag;
        Vector3D east_unit(-std::sin(theta_gst + lon_ecef), std::cos(theta_gst + lon_ecef), 0.0);
        return r_unit * a_tess_r + east_unit * a_tess_lam;
    }

    inline Vector3D GetSunPosition(double t_seconds) {
        double n_sun = 2.0 * PI / (365.25 * 86400.0);
        double lam = n_sun * t_seconds;
        double eps = 23.44 * (PI / 180.0);
        return Vector3D(
            AU_METERS * std::cos(lam),
            AU_METERS * std::sin(lam) * std::cos(eps),
            AU_METERS * std::sin(lam) * std::sin(eps)
        );
    }

    inline Vector3D GetMoonPosition(double t_seconds) {
        double n_moon = 2.0 * PI / (27.32166 * 86400.0);
        double lam = n_moon * t_seconds;
        double inc_moon = (23.44 + 5.14) * (PI / 180.0);
        return Vector3D(
            D_MOON_MEAN * std::cos(lam),
            D_MOON_MEAN * std::sin(lam) * std::cos(inc_moon),
            D_MOON_MEAN * std::sin(lam) * std::sin(inc_moon)
        );
    }

    inline Vector3D ComputeThirdBodyAccel(const Vector3D& r_sc, const Vector3D& r_body, double mu_body) {
        Vector3D d_vec = r_sc - r_body;
        double d_mag = d_vec.norm();
        double r_b_mag = r_body.norm();
        if (d_mag < 1.0 || r_b_mag < 1.0) return Vector3D(0, 0, 0);
        Vector3D term1 = d_vec / (d_mag * d_mag * d_mag);
        Vector3D term2 = r_body / (r_b_mag * r_b_mag * r_b_mag);
        return (term1 + term2) * (-mu_body);
    }

    inline Vector3D ComputeDragAccel(const Vector3D& r, const Vector3D& v, double b_star) {
        double r_mag = r.norm();
        double alt_m = r_mag - R_EARTH;
        if (alt_m > 850000.0 || alt_m <= 0.0) return Vector3D(0, 0, 0);
        double rho = RHO_0 * std::exp(-alt_m / H_SCALE);
        Vector3D v_rel(
            v.x + OMEGA_EARTH * r.y,
            v.y - OMEGA_EARTH * r.x,
            v.z
        );
        double v_rel_mag = v_rel.norm();
        double factor_drag = -0.5 * rho * b_star * v_rel_mag;
        return v_rel * factor_drag;
    }

    inline Vector3D ComputeSRPAccel(const Vector3D& r, const Vector3D& r_sun, double cr_area_over_m) {
        double d_sun = (r - r_sun).norm();
        if (d_sun < 1000.0) return Vector3D(0, 0, 0);
        Vector3D s_hat = (r - r_sun) / d_sun;

        // Shadow cone test
        double r_mag = r.norm();
        Vector3D sun_dir = r_sun / r_sun.norm();
        double r_proj = r.dot(sun_dir);
        double d_perp_sq = r_mag * r_mag - r_proj * r_proj;
        if (r_proj < 0.0 && d_perp_sq < (R_EARTH * R_EARTH)) {
            return Vector3D(0, 0, 0); // Total shadow
        }
        double p_flux = P_SR_1AU * std::pow(AU_METERS / d_sun, 2.0);
        return s_hat * (p_flux * cr_area_over_m);
    }

    struct AccelerationBreakdown {
        Vector3D a_total;
        double a_central_mag = 0.0;
        double a_j2_mag = 0.0;
        double a_j3_mag = 0.0;
        double a_j4_mag = 0.0;
        double a_tesseral_mag = 0.0;
        double a_sun_mag = 0.0;
        double a_moon_mag = 0.0;
        double a_drag_mag = 0.0;
        double a_srp_mag = 0.0;
        double a_total_mag = 0.0;
    };

    inline AccelerationBreakdown ComputeFullAcceleration(
        const Vector3D& r,
        const Vector3D& v,
        double t_sec,
        int gravity_degree,
        bool enable_sun,
        bool enable_moon,
        bool enable_drag,
        bool enable_srp,
        double b_star,
        double cr_area_over_m
    ) {
        AccelerationBreakdown ab;

        // 1. Central Body
        Vector3D a_central = ComputeTwoBodyAccel(r);
        ab.a_central_mag = a_central.norm();
        ab.a_total = a_central;

        // 2. Geopotentials
        if (gravity_degree >= 2) {
            Vector3D a_j2 = ComputeJ2Accel(r);
            ab.a_j2_mag = a_j2.norm();
            ab.a_total = ab.a_total + a_j2;
        }
        if (gravity_degree >= 3) {
            Vector3D a_j3 = ComputeJ3Accel(r);
            ab.a_j3_mag = a_j3.norm();
            ab.a_total = ab.a_total + a_j3;
        }
        if (gravity_degree >= 4) {
            Vector3D a_j4 = ComputeJ4Accel(r);
            ab.a_j4_mag = a_j4.norm();
            ab.a_total = ab.a_total + a_j4;
        }
        if (gravity_degree >= 2) {
            Vector3D a_tess = ComputeTesseralAccel(r, t_sec);
            ab.a_tesseral_mag = a_tess.norm();
            ab.a_total = ab.a_total + a_tess;
        }

        // 3. Third Bodies
        if (enable_sun) {
            Vector3D r_sun = GetSunPosition(t_sec);
            Vector3D a_sun = ComputeThirdBodyAccel(r, r_sun, MU_SUN);
            ab.a_sun_mag = a_sun.norm();
            ab.a_total = ab.a_total + a_sun;
        }
        if (enable_moon) {
            Vector3D r_moon = GetMoonPosition(t_sec);
            Vector3D a_moon = ComputeThirdBodyAccel(r, r_moon, MU_MOON);
            ab.a_moon_mag = a_moon.norm();
            ab.a_total = ab.a_total + a_moon;
        }

        // 4. Drag
        if (enable_drag) {
            Vector3D a_drag = ComputeDragAccel(r, v, b_star);
            ab.a_drag_mag = a_drag.norm();
            ab.a_total = ab.a_total + a_drag;
        }

        // 5. SRP
        if (enable_srp) {
            Vector3D r_sun = GetSunPosition(t_sec);
            Vector3D a_srp = ComputeSRPAccel(r, r_sun, cr_area_over_m);
            ab.a_srp_mag = a_srp.norm();
            ab.a_total = ab.a_total + a_srp;
        }

        ab.a_total_mag = ab.a_total.norm();
        return ab;
    }

} // namespace AstroCore

#endif // ASTRO_PHYSICS_HPP

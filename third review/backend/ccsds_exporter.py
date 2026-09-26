"""
AstroFlyer HEO - CCSDS & TLE Space Data Interoperability Suite
=============================================================================
Department of Aerospace Engineering, ACS College of Engineering
Official Spaceflight Data Standards (CCSDS 502.0-B-2 & NASA/NORAD):
- CCSDS OEM (Orbit Ephemeris Message, Version 2.0 / 3.0 KVN Standard)
- CCSDS OPM (Orbit Parameter Message, Keplerian & Cartesian State)
- NORAD Two-Line Element (TLE) Formatter with Modulo-10 Checksum Verification
- STK (.e) Ephemeris Format Exporter
=============================================================================
"""

import math
import datetime

MU_EARTH_KM = 398600.4418  # km^3/s^2


class CCSDSExporter:
    """
    Generates fully compliant CCSDS OEM, OPM, and NORAD TLE ephemeris files.
    """
    @staticmethod
    def _tle_checksum(line):
        """Calculates standard NORAD modulo-10 checksum for a 69-character TLE line."""
        csum = 0
        for char in line[:68]:
            if char.isdigit():
                csum += int(char)
            elif char == '-':
                csum += 1
        return csum % 10

    @classmethod
    def generate_tle(
        cls,
        sat_name="ASTROFLYER-1",
        sat_num=99881,
        epoch_dt=None,
        sma_km=24389.0,
        ecc=0.728525,
        inc_deg=28.5,
        raan_deg=45.0,
        aop_deg=30.0,
        ta_deg=0.0,
        b_star=0.00015
    ):
        """
        Synthesizes a valid NORAD Two-Line Element Set (TLE) with compliant checksums.
        """
        if epoch_dt is None:
            epoch_dt = datetime.datetime(2026, 9, 24, 0, 0, 0)

        # Day of year fraction
        doy = epoch_dt.timetuple().tm_yday
        fraction_of_day = (epoch_dt.hour * 3600 + epoch_dt.minute * 60 + epoch_dt.second) / 86400.0
        epoch_str = f"{epoch_dt.year % 100:02d}{doy + fraction_of_day:012.8f}"

        # Mean Motion (revolutions per day)
        period_sec = 2.0 * math.pi * math.sqrt((sma_km**3) / MU_EARTH_KM)
        mean_motion_rev_day = 86400.0 / period_sec

        # Mean Anomaly from True Anomaly
        ta_rad = math.radians(ta_deg)
        cos_e = (ecc + math.cos(ta_rad)) / (1.0 + ecc * math.cos(ta_rad))
        sin_e = (math.sqrt(max(0.0, 1.0 - ecc**2)) * math.sin(ta_rad)) / (1.0 + ecc * math.cos(ta_rad))
        E_rad = math.atan2(sin_e, cos_e)
        M_rad = E_rad - ecc * math.sin(E_rad)
        M_deg = (math.degrees(M_rad) + 360.0) % 360.0

        # Eccentricity without decimal point (7 digits)
        ecc_str = f"{int(ecc * 1e7):07d}"

        # B* drag term formatting
        b_star_val = b_star
        b_star_exp = 0
        if b_star_val > 0:
            b_star_exp = int(math.floor(math.log10(b_star_val))) + 1
            b_star_mant = int(round(b_star_val / (10**b_star_exp) * 100000.0))
            b_star_str = f" {b_star_mant:05d}{b_star_exp:+1d}"
        else:
            b_star_str = " 00000-0"

        # Line 1:
        line1_raw = f"1 {sat_num:05d}U 26999A   {epoch_str}  .00000100  00000-0 {b_star_str} 0  999"
        csum1 = cls._tle_checksum(line1_raw)
        line1 = f"{line1_raw}{csum1}"

        # Line 2:
        line2_raw = f"2 {sat_num:05d} {inc_deg:8.4f} {raan_deg:8.4f} {ecc_str} {aop_deg:8.4f} {M_deg:8.4f} {mean_motion_rev_day:11.8f}    1"
        csum2 = cls._tle_checksum(line2_raw)
        line2 = f"{line2_raw}{csum2}"

        return f"{sat_name}\n{line1}\n{line2}\n"

    @staticmethod
    def generate_ccsds_oem(
        times_sec,
        positions_m,
        velocities_ms,
        sat_name="ASTROFLYER-1",
        sat_id="2026-999A",
        epoch_str="2026-09-24T00:00:00.000",
        step_interval_s=60.0
    ):
        """
        Generates standard CCSDS OEM (Orbit Ephemeris Message, V2.0 KVN format).
        State coordinates in km and km/s in J2000 (EME2000) frame.
        """
        t0_dt = datetime.datetime.fromisoformat(epoch_str.replace("Z", ""))

        lines = [
            "CCSDS_OEM_VERS = 2.0",
            f"CREATION_DATE  = {datetime.datetime.utcnow().isoformat()}Z",
            "ORIGINATOR     = ASTROFLYER_HEO_STUDIO_ACS_CE",
            "",
            "META_START",
            f"OBJECT_NAME          = {sat_name}",
            f"OBJECT_ID            = {sat_id}",
            "CENTER_NAME          = EARTH",
            "REF_FRAME            = EME2000",
            "TIME_SYSTEM          = UTC",
            f"START_TIME           = {epoch_str}",
            f"STOP_TIME            = {(t0_dt + datetime.timedelta(seconds=float(times_sec[-1]))).isoformat()}Z",
            "INTERPOLATION        = HERMITE",
            "INTERPOLATION_DEGREE = 7",
            "META_STOP",
            ""
        ]

        n_pts = len(times_sec)
        last_t = -1e9

        for i in range(n_pts):
            t = float(times_sec[i])
            if t - last_t >= step_interval_s or i == 0 or i == n_pts - 1:
                cur_dt = t0_dt + datetime.timedelta(seconds=t)
                t_str = cur_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
                # Convert m to km and m/s to km/s
                x_km, y_km, z_km = positions_m[i] / 1000.0
                vx_kms, vy_kms, vz_kms = velocities_ms[i] / 1000.0
                lines.append(f"{t_str}  {x_km:14.6f}  {y_km:14.6f}  {z_km:14.6f}  {vx_kms:12.8f}  {vy_kms:12.8f}  {vz_kms:12.8f}")
                last_t = t

        return "\n".join(lines) + "\n"

    @staticmethod
    def generate_ccsds_opm(
        sma_km=24389.0,
        ecc=0.728525,
        inc_deg=28.5,
        raan_deg=45.0,
        aop_deg=30.0,
        ta_deg=0.0,
        r_vec_km=(6628.0, 0.0, 0.0),
        v_vec_kms=(0.0, 10.23, 0.0),
        sat_name="ASTROFLYER-1",
        sat_id="2026-999A",
        epoch_str="2026-09-24T00:00:00.000",
        mass_kg=1500.0,
        cd=2.2,
        cr=1.2,
        drag_area_m2=15.0,
        srp_area_m2=15.0
    ):
        """
        Generates standard CCSDS OPM (Orbit Parameter Message, V2.0 KVN format).
        """
        lines = [
            "CCSDS_OPM_VERS = 2.0",
            f"CREATION_DATE  = {datetime.datetime.utcnow().isoformat()}Z",
            "ORIGINATOR     = ASTROFLYER_HEO_STUDIO_ACS_CE",
            "",
            "% Spacecraft Metadata",
            f"OBJECT_NAME          = {sat_name}",
            f"OBJECT_ID            = {sat_id}",
            "CENTER_NAME          = EARTH",
            "REF_FRAME            = EME2000",
            "TIME_SYSTEM          = UTC",
            "",
            "% Spacecraft Physical Parameters",
            f"MASS                 = {mass_kg:.1f} [kg]",
            f"SOLAR_RAD_COEFF      = {cr:.2f}",
            f"SOLAR_RAD_AREA       = {srp_area_m2:.2f} [m**2]",
            f"DRAG_COEFF           = {cd:.2f}",
            f"DRAG_AREA            = {drag_area_m2:.2f} [m**2]",
            "",
            "% State Vector Epoch",
            f"EPOCH                = {epoch_str}",
            "",
            "% Cartesian State Vector (km, km/s)",
            f"X                    = {r_vec_km[0]:14.6f} [km]",
            f"Y                    = {r_vec_km[1]:14.6f} [km]",
            f"Z                    = {r_vec_km[2]:14.6f} [km]",
            f"X_DOT                = {v_vec_kms[0]:12.8f} [km/s]",
            f"Y_DOT                = {v_vec_kms[1]:12.8f} [km/s]",
            f"Z_DOT                = {v_vec_kms[2]:12.8f} [km/s]",
            "",
            "% Osculating Keplerian Elements",
            f"SEMI_MAJOR_AXIS      = {sma_km:14.6f} [km]",
            f"ECCENTRICITY         = {ecc:12.8f}",
            f"INCLINATION          = {inc_deg:10.5f} [deg]",
            f"RA_OF_ASC_NODE       = {raan_deg:10.5f} [deg]",
            f"ARG_OF_PERICENTER    = {aop_deg:10.5f} [deg]",
            f"TRUE_ANOMALY         = {ta_deg:10.5f} [deg]",
            f"GM                   = {MU_EARTH_KM:.4f} [km**3/s**2]",
            ""
        ]
        return "\n".join(lines) + "\n"

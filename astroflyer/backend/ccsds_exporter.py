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

import numpy as np

from .epoch import Epoch
from .frames import transform_state
from .mission import keplerian_from_state

MU_EARTH_KM = 398600.4418  # km^3/s^2
_MU_WGS72 = 398600.8e9      # m^3/s^2, the constant SGP4 is defined with


def _nonsingular(r, v):
    """a, e cos w, e sin w, i, RAAN, w + M from a state (WGS-72 GM)."""
    k = keplerian_from_state(r, v, _MU_WGS72)
    e, nu = k["e"], k["ta"]
    ecc_anom = math.atan2(math.sqrt(1.0 - e * e) * math.sin(nu), e + math.cos(nu))
    ma = ecc_anom - e * math.sin(ecc_anom)
    return np.array([k["a"], e * math.cos(k["argp"]), e * math.sin(k["argp"]), k["inc"], k["raan"],
                     k["argp"] + ma])


def _from_nonsingular(q):
    a, ek, eh, inc, raan, lam = q
    argp = math.atan2(eh, ek)
    return a, math.hypot(ek, eh), inc, raan % (2.0 * math.pi), argp % (2.0 * math.pi), (lam - argp) % (2.0 * math.pi)


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

    @staticmethod
    def _tle_epoch(epoch):
        """The TLE epoch field YYDDD.DDDDDDDD (UTC) and the Epoch it stands for."""
        year = int(epoch.iso("UTC")[:4])
        jan1 = Epoch.from_calendar(year, 1, 1, 0, 0, 0.0, "UTC")
        day = round((epoch.jd_value("UTC") - jan1.jd_value("UTC")) + 1.0, 8)
        printed = jan1 + (day - 1.0) * 86400.0
        return f"{year % 100:02d}{day:012.8f}", printed

    @classmethod
    def format_tle(cls, sat_name, sat_num, epoch_field, inc_deg, raan_deg, ecc, aop_deg, ma_deg,
                   mean_motion_rev_day, intl_designator=""):
        """Two-line element set text (fixed columns, modulo-10 checksums), B* and its derivatives zero."""
        line1_raw = f"1 {sat_num:05d}U {intl_designator:<8s} {epoch_field}  .00000000  00000-0  00000-0 0  999"
        line2_raw = (f"2 {sat_num:05d} {inc_deg:8.4f} {raan_deg % 360.0:8.4f} {round(ecc * 1e7):07d} "
                     f"{aop_deg % 360.0:8.4f} {ma_deg % 360.0:8.4f} {mean_motion_rev_day:11.8f}    1")
        line1 = f"{line1_raw}{cls._tle_checksum(line1_raw)}"
        line2 = f"{line2_raw}{cls._tle_checksum(line2_raw)}"
        return f"{sat_name}\n{line1}\n{line2}\n"

    @classmethod
    def generate_tle(cls, epoch, r_gcrf_m, v_gcrf_ms, sat_name="ASTROFLYER-1", sat_num=99881):
        """
        A TLE whose SGP4 state at `epoch` is the given GCRF state.

        SGP4 works with its own mean elements (WGS-72, TEME frame), not osculating ones, so they are
        fitted: starting from the osculating elements of the TEME state, the elements are corrected
        by the difference between the target's osculating elements and those of SGP4's state until
        SGP4 reproduces the state. The iteration runs on nonsingular elements (a, e cos w, e sin w,
        i, RAAN, w + M) so near-circular orbits converge too. B* is zero: the TLE carries no drag.
        Returns {"tle": text, "position_error_m", "velocity_error_ms"}, the errors of the printed TLE
        (rounded to its columns) at `epoch`.
        """
        from sgp4.api import WGS72, Satrec

        epoch = Epoch.coerce(epoch)
        epoch_field, printed = cls._tle_epoch(epoch)
        r_teme, v_teme = transform_state(np.asarray(r_gcrf_m, dtype=float), np.asarray(v_gcrf_ms, dtype=float),
                                         epoch, "GCRF", "TEME")
        jd1, jd2 = printed.jd("UTC")
        offset_days = (epoch.jd_value("UTC") - printed.jd_value("UTC"))

        def satrec(q):
            a, e, inc, raan, argp, ma = _from_nonsingular(q)
            sat = Satrec()
            sat.sgp4init(WGS72, "i", sat_num, (jd1 - 2433281.5) + jd2, 0.0, 0.0, 0.0, e, argp, inc, ma,
                         math.sqrt(_MU_WGS72 / a ** 3) * 60.0, raan)
            return sat

        def sgp4_state(sat):
            err, r_km, v_kms = sat.sgp4(jd1, jd2 + offset_days)
            if err:
                raise ValueError(f"SGP4 cannot represent this orbit (error {err})")
            return np.array(r_km) * 1e3, np.array(v_kms) * 1e3

        target = _nonsingular(r_teme, v_teme)
        q = target.copy()
        for _ in range(100):
            d = target - _nonsingular(*sgp4_state(satrec(q)))
            d[3:] = (d[3:] + math.pi) % (2.0 * math.pi) - math.pi
            q = q + d
            if abs(d[0]) < 1e-6 and np.max(np.abs(d[1:])) < 1e-13:
                break
        else:
            raise ValueError("The SGP4 mean elements did not converge for this orbit")

        a, e, inc, raan, argp, ma = _from_nonsingular(q)
        text = cls.format_tle(sat_name, sat_num, epoch_field, math.degrees(inc), math.degrees(raan), e,
                              math.degrees(argp), math.degrees(ma),
                              86400.0 / (2.0 * math.pi * math.sqrt(a ** 3 / _MU_WGS72)),
                              intl_designator=f"{epoch_field[:2]}999A")
        line1, line2 = text.splitlines()[1:3]
        r_tle, v_tle = sgp4_state(Satrec.twoline2rv(line1, line2, WGS72))
        return {"tle": text, "position_error_m": float(np.linalg.norm(r_tle - r_teme)),
                "velocity_error_ms": float(np.linalg.norm(v_tle - v_teme))}

    @staticmethod
    def generate_ccsds_oem(
        times_sec,
        positions_m,
        velocities_ms,
        epoch_str,
        sat_name="ASTROFLYER-1",
        sat_id="2026-999A",
        step_interval_s=60.0
    ):
        """
        Generates standard CCSDS OEM (Orbit Ephemeris Message, V2.0 KVN format).
        State coordinates in km and km/s in the engine's GCRF frame; epoch_str is the UTC epoch of
        times_sec = 0.
        """
        t0_dt = datetime.datetime.fromisoformat(epoch_str.replace("Z", ""))

        lines = [
            "CCSDS_OEM_VERS = 2.0",
            f"CREATION_DATE  = {datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat()}Z",
            "ORIGINATOR     = ASTROFLYER_HEO_STUDIO_ACS_CE",
            "",
            "META_START",
            f"OBJECT_NAME          = {sat_name}",
            f"OBJECT_ID            = {sat_id}",
            "CENTER_NAME          = EARTH",
            "REF_FRAME            = GCRF",
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
        epoch,
        r_vec_km,
        v_vec_kms,
        sma_km,
        ecc,
        inc_deg,
        raan_deg,
        aop_deg,
        ta_deg,
        gm_km3s2=MU_EARTH_KM,
        sat_name="ASTROFLYER-1",
        sat_id="2026-999A",
        mass_kg=1500.0,
        cd=2.2,
        cr=1.2,
        drag_area_m2=15.0,
        srp_area_m2=15.0
    ):
        """
        Generates a CCSDS OPM (Orbit Parameter Message, V2.0 KVN format) for the state at `epoch`
        (GCRF, km and km/s) with its osculating elements for the given GM.
        """
        epoch_str = Epoch.coerce(epoch).iso("UTC", 3).rstrip("Z")
        lines = [
            "CCSDS_OPM_VERS = 2.0",
            f"CREATION_DATE  = {datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat()}Z",
            "ORIGINATOR     = ASTROFLYER_HEO_STUDIO_ACS_CE",
            "",
            "% Spacecraft Metadata",
            f"OBJECT_NAME          = {sat_name}",
            f"OBJECT_ID            = {sat_id}",
            "CENTER_NAME          = EARTH",
            "REF_FRAME            = GCRF",
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
            f"X                    = {r_vec_km[0]:17.9f} [km]",
            f"Y                    = {r_vec_km[1]:17.9f} [km]",
            f"Z                    = {r_vec_km[2]:17.9f} [km]",
            f"X_DOT                = {v_vec_kms[0]:15.12f} [km/s]",
            f"Y_DOT                = {v_vec_kms[1]:15.12f} [km/s]",
            f"Z_DOT                = {v_vec_kms[2]:15.12f} [km/s]",
            "",
            "% Osculating Keplerian Elements",
            f"SEMI_MAJOR_AXIS      = {sma_km:14.6f} [km]",
            f"ECCENTRICITY         = {ecc:12.8f}",
            f"INCLINATION          = {inc_deg:10.5f} [deg]",
            f"RA_OF_ASC_NODE       = {raan_deg:10.5f} [deg]",
            f"ARG_OF_PERICENTER    = {aop_deg:10.5f} [deg]",
            f"TRUE_ANOMALY         = {ta_deg:10.5f} [deg]",
            f"GM                   = {gm_km3s2:.4f} [km**3/s**2]",
            ""
        ]
        return "\n".join(lines) + "\n"

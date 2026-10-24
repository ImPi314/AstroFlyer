"""
HEO validation cases and the force-model ladder (see the validation plan).

Every case starts from the same Cartesian GCRF state in both AstroFlyer and
the reference propagator; only the force model level changes.
"""

import math
from dataclasses import dataclass

EPOCH_ISO_TT = "2026-01-01T00:00:00"

ORBITS = {
    # name: (a [m], e, i [deg], RAAN [deg], argp [deg], nu0 [deg])
    "molniya": (26600.0e3, 0.74, 63.435, 90.0, 270.0, 0.0),
    "tundra": (42164.0e3, 0.27, 63.4, 90.0, 270.0, 0.0),
    "gto": (24396.137e3, 0.72832, 28.5, 45.0, 30.0, 0.0),
    "heo_stress": (60000.0e3, 0.88, 28.5, 0.0, 0.0, 0.0),
}


@dataclass(frozen=True)
class Level:
    """One rung of the force-model ladder."""
    name: str
    description: str
    gravity_degree: int = 0
    gravity_order: int = 0
    third_body: bool = False
    srp: bool = False
    drag: bool = False
    relativity: bool = False

    @property
    def needs_ephemeris(self):
        # Drag does not: the reference atmosphere uses the mean Sun (see orekit_crosscheck)
        return self.third_body or self.srp


LEVELS = {
    "L0": Level("L0", "two-body"),
    "L1": Level("L1", "J2 only", 2, 0),
    "L2": Level("L2", "zonal 4x0", 4, 0),
    "L3": Level("L3", "gravity 8x8", 8, 8),
    "L4": Level("L4", "8x8 + Sun/Moon (DE440)", 8, 8, third_body=True),
    "L5": Level("L5", "L4 + SRP, conical shadow", 8, 8, third_body=True, srp=True),
    "L6": Level("L6", "L5 + NRLMSISE-00 drag", 8, 8, third_body=True, srp=True, drag=True),
    "L7": Level("L7", "L6 + relativity (full model)", 8, 8, third_body=True, srp=True, drag=True,
                relativity=True),
}

# Spacecraft and space weather shared by both propagators
CR_AREA_OVER_M = 0.02   # Cr*A/m, m^2/kg
CD_AREA_OVER_M = 0.01   # Cd*A/m, m^2/kg
F107 = 150.0
F107A = 150.0
AP = 15.0

# Pass thresholds on max 3D position difference (m), by arc length in days
THRESHOLDS_M = {1: 10.0, 7: 100.0}


def threshold_for(days):
    """Position threshold for an arc: the tightest listed arc at least this long."""
    for arc in sorted(THRESHOLDS_M):
        if days <= arc:
            return THRESHOLDS_M[arc]
    return THRESHOLDS_M[max(THRESHOLDS_M)] * days / max(THRESHOLDS_M)


def period_s(orbit, mu):
    return 2.0 * math.pi * math.sqrt(ORBITS[orbit][0] ** 3 / mu)

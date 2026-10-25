"""
AstroFlyer HEO - Mission script interpreter
=============================================================================
Runs mission scripts written in the GMAT-style syntax that AstroFlyer's script
editor produces (the language of NASA's open-source GMAT). Resources are created
and configured first; the mission sequence after BeginMissionSequence runs on the
AstroFlyer engine (backend/mission.py).

Supported
  Resources   Create Spacecraft | ChemicalTank | ChemicalThruster | ForceModel |
              Propagator | ImpulsiveBurn | FiniteBurn | DifferentialCorrector |
              ReportFile | Variable | GroundStation (stored only)
  Sequence    Propagate Prop(Sat) {Sat.ElapsedSecs = n | Sat.ElapsedDays = n |
              Sat.Apoapsis | Sat.Periapsis}
              Maneuver Burn(Sat); BeginFiniteBurn FB(Sat); EndFiniteBurn FB(Sat)
              Target DC; Vary DC(...); Achieve DC(...); EndTarget
              Report File p1 p2 ...; Report 'text'
              If / Else / EndIf, For i = a:b[:c] / EndFor, While / EndWhile
              x = expr; Obj.Field = expr; Stop
Units follow the script convention: km, km/s, deg, kg, N, s.

    result = run_script(text)      # dict: log, reports, spacecraft, ephemeris, targets
    python -m astroflyer.backend.script_runner mission.script --json out.json --oem outdir
=============================================================================
"""

import ast
import copy
import json
import math
import os
import re
import sys
from datetime import datetime

import numpy as np

from . import mission as M
from .epoch import Epoch
from .forces import R_EARTH_EQ, ForceModelConfig

# A script runs in the app's server: one Propagate and the whole script are bounded in time
MAX_PROPAGATE_S = 30 * 86400.0
MAX_SCRIPT_PROPAGATION_S = 366 * 86400.0
from .frames import gcrf_to_geodetic, transform_state

KM = 1000.0
GMAT_MJD_OFFSET = 2430000.0          # script ModJulian dates: JD - 2430000.0
A1_MINUS_TAI = 0.0343817             # A.1 time scale offset (s)


class ScriptError(Exception):
    def __init__(self, message, line=None):
        super().__init__(message if line is None else f"line {line}: {message}")
        self.message = message
        self.line = line


# ==============================================================================
# PARSING
# ==============================================================================
class Statement:
    def __init__(self, keyword, text, line):
        self.keyword = keyword
        self.text = text
        self.line = line
        self.body = []
        self.else_body = []

    def __repr__(self):
        return f"Statement({self.keyword!r}, {self.text!r}, line={self.line})"


def _split_statements(source):
    """Yields (text, line) for each statement; strips % comments, joins '...' continuations."""
    pending, start_line = "", None
    for number, raw in enumerate(source.splitlines(), start=1):
        line = _strip_comment(raw).rstrip()
        if not line.strip():
            continue
        if start_line is None:
            start_line = number
        if line.endswith("..."):
            pending += line[:-3] + " "
            continue
        pending += line
        for part in _split_outside(pending, ";"):
            if part.strip():
                yield part.strip(), start_line
        pending, start_line = "", None
    if pending.strip():
        yield pending.strip(), start_line


def _strip_comment(line):
    quote = False
    for i, ch in enumerate(line):
        if ch == "'":
            quote = not quote
        elif ch == "%" and not quote:
            return line[:i]
    return line


def _split_outside(text, sep):
    """Splits on `sep` outside quotes, braces and parentheses."""
    parts, depth, quote, cur = [], 0, False, []
    for ch in text:
        if ch == "'":
            quote = not quote
        elif not quote and ch in "({[":
            depth += 1
        elif not quote and ch in ")}]":
            depth -= 1
        if ch == sep and depth == 0 and not quote:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return parts


_BLOCK_OPEN = {"Target": "EndTarget", "If": "EndIf", "For": "EndFor", "While": "EndWhile"}


def parse(source):
    """Returns (resource_statements, sequence_statements) with nested block bodies."""
    resources, sequence = [], []
    in_sequence = False
    stack = []
    for text, line in _split_statements(source):
        if text.startswith("GMAT "):
            text = text[5:].strip()
        keyword = text.split(None, 1)[0].split("(")[0]
        if keyword == "BeginMissionSequence":
            in_sequence = True
            continue
        if not in_sequence and keyword != "Create" and "=" not in text:
            # A command before BeginMissionSequence starts the sequence implicitly
            in_sequence = True
        if not in_sequence:
            resources.append(Statement(keyword, text, line))
            continue
        stmt = Statement(keyword, text, line)
        target = stack[-1].else_body if stack and getattr(stack[-1], "_in_else", False) else (
            stack[-1].body if stack else sequence)
        if keyword in _BLOCK_OPEN:
            target.append(stmt)
            stack.append(stmt)
        elif keyword == "Else":
            if not stack or stack[-1].keyword != "If":
                raise ScriptError("Else without If", line)
            stack[-1]._in_else = True
        elif keyword in _BLOCK_OPEN.values():
            if not stack or _BLOCK_OPEN[stack[-1].keyword] != keyword:
                raise ScriptError(f"{keyword} does not close an open block", line)
            stack.pop()
        else:
            target.append(stmt)
    if stack:
        raise ScriptError(f"{stack[-1].keyword} is never closed", stack[-1].line)
    return resources, sequence


# ==============================================================================
# VALUES AND EXPRESSIONS
# ==============================================================================
def _parse_value(text):
    text = text.strip()
    if text.startswith("'") and text.endswith("'"):
        return text[1:-1]
    if text.startswith("{") and text.endswith("}"):
        inner = text[1:-1].strip()
        return [_parse_value(x) for x in _split_outside(inner, ",")] if inner else []
    if text.startswith("[") and text.endswith("]"):
        return [_parse_value(x) for x in re.split(r"[,\s]+", text[1:-1].strip()) if x]
    low = text.lower()
    if low in ("on", "true"):
        return True
    if low in ("off", "false"):
        return False
    try:
        return float(text)
    except ValueError:
        return text


_FUNCTIONS = {name: getattr(math, name) for name in (
    "sqrt", "sin", "cos", "tan", "asin", "acos", "atan", "atan2", "exp", "log", "log10", "floor", "ceil")}
_FUNCTIONS.update({"abs": abs, "min": min, "max": max, "mod": math.fmod, "DegToRad": math.radians,
                   "RadToDeg": math.degrees})
_CONSTANTS = {"pi": math.pi}


def _to_python_expression(text):
    text = text.replace("~=", "!=").replace("^", "**")
    text = re.sub(r"(?<![=!<>])&(?!&)", " and ", text).replace("&&", " and ")
    text = re.sub(r"(?<!\|)\|(?!\|)", " or ", text).replace("||", " or ")
    text = re.sub(r"(?<![=!<>])~", " not ", text)
    return text


def _dotted(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


# ==============================================================================
# RUNTIME OBJECTS
# ==============================================================================
class ScriptSpacecraft:
    """Script-facing spacecraft: element fields until the sequence starts, then a mission.Spacecraft."""

    def __init__(self, name):
        self.name = name
        self.fields = {"DateFormat": "TAIModJulian", "Epoch": "21545", "CoordinateSystem": "EarthMJ2000Eq",
                       "DisplayStateType": "Cartesian", "X": 7100.0, "Y": 0.0, "Z": 1300.0, "VX": 0.0,
                       "VY": 7.35, "VZ": 1.0, "DryMass": 850.0, "Cd": 2.2, "Cr": 1.8, "DragArea": 15.0,
                       "SRPArea": 1.0, "Tanks": [], "Thrusters": []}
        self.sc = None
        self.start_epoch = None

    def build(self, interp):
        f = self.fields
        epoch = _parse_script_epoch(str(f["Epoch"]), str(f["DateFormat"]))
        frame = _frame_name(f.get("CoordinateSystem", "EarthMJ2000Eq"))
        keplerian_keys = ("SMA", "ECC", "INC", "RAAN", "AOP", "TA")
        if str(f.get("DisplayStateType", "")).lower() == "keplerian" or all(k in f for k in keplerian_keys):
            r, v = M.state_from_keplerian(float(f["SMA"]) * KM, float(f["ECC"]), math.radians(float(f["INC"])),
                                          math.radians(float(f["RAAN"])), math.radians(float(f["AOP"])),
                                          math.radians(float(f["TA"])))
        else:
            r = np.array([float(f[k]) for k in ("X", "Y", "Z")]) * KM
            v = np.array([float(f[k]) for k in ("VX", "VY", "VZ")]) * KM
        if frame != "GCRF":
            r, v = transform_state(r, v, epoch, frame, "GCRF")
        fuel = sum(float(interp.object(t, "ChemicalTank", None).fields.get("FuelMass", 756.0)) for t in f["Tanks"])
        self.sc = M.Spacecraft(epoch, r, v, dry_mass_kg=float(f["DryMass"]), fuel_mass_kg=fuel, cd=float(f["Cd"]),
                               drag_area_m2=float(f["DragArea"]), cr=float(f["Cr"]), srp_area_m2=float(f["SRPArea"]))
        self.start_epoch = epoch


class Resource:
    def __init__(self, kind, name, defaults=None):
        self.kind = kind
        self.name = name
        self.fields = dict(defaults or {})


_DEFAULTS = {
    "ChemicalTank": {"FuelMass": 756.0},
    "ChemicalThruster": {"Thrust": 10.0, "Isp": 300.0, "Axes": "VNB", "ThrustDirection1": 1.0,
                         "ThrustDirection2": 0.0, "ThrustDirection3": 0.0},
    "ForceModel": {"CentralBody": "Earth", "PointMasses": [], "GravityField.Earth.Degree": 4,
                   "GravityField.Earth.Order": 4, "SRP": False, "Drag.AtmosphereModel": "None",
                   "RelativisticCorrection": False},
    "Propagator": {"FM": None, "Type": "RungeKutta89", "Accuracy": 1e-11},
    "ImpulsiveBurn": {"Axes": "VNB", "CoordinateSystem": "Local", "Element1": 0.0, "Element2": 0.0,
                      "Element3": 0.0, "DecrementMass": False, "Isp": 300.0, "Tank": []},
    "FiniteBurn": {"Thrusters": []},
    "DifferentialCorrector": {"MaximumIterations": 25},
    "ReportFile": {"Filename": ""},
    "GroundStation": {},
    "Variable": {"Value": 0.0},
}

_PROPAGATOR_TYPES = {"BULIRSCHSTOER": "BS", "RUNGEKUTTA4": "RK4"}


def _frame_name(coordinate_system):
    cs = str(coordinate_system).replace(" ", "").lower()
    if cs in ("earthmj2000eq", "eme2000", "j2000"):
        return "EME2000"
    if cs in ("earthicrf", "gcrf", "icrf"):
        return "GCRF"
    if cs in ("earthfixed", "itrf", "ecef"):
        return "ITRF"
    if cs in ("earthmj2000ec",):
        return "ECLIPJ2000"
    raise ValueError(f"Unsupported coordinate system {coordinate_system!r}")


def _parse_script_epoch(text, date_format):
    fmt = date_format.replace(" ", "")
    scale = "UTC" if fmt.upper().startswith("UTC") else "TAI" if fmt.upper().startswith(("TAI", "A1")) else \
        "TT" if fmt.upper().startswith("TT") else "TDB" if fmt.upper().startswith("TDB") else "UTC"
    if fmt.endswith("Gregorian"):
        text = text.strip().strip("'")
        for pattern in ("%d %b %Y %H:%M:%S.%f", "%d %b %Y %H:%M:%S"):
            try:
                dt = datetime.strptime(text, pattern)
                break
            except ValueError:
                continue
        else:
            return Epoch.from_iso(text, scale=scale)
        sec = dt.second + dt.microsecond / 1e6
        epoch = Epoch.from_calendar(dt.year, dt.month, dt.day, dt.hour, dt.minute, sec, scale)
    elif fmt.endswith("ModJulian"):
        mjd = float(text)
        epoch = Epoch.from_jd(GMAT_MJD_OFFSET + math.floor(mjd), mjd - math.floor(mjd), scale)
    else:
        return Epoch.from_iso(text)
    return epoch - A1_MINUS_TAI if fmt.upper().startswith("A1") else epoch


def _gregorian(epoch, scale="UTC"):
    iso = epoch.iso(scale, 3)
    dt = datetime.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S")
    return dt.strftime("%d %b %Y %H:%M:%S") + iso[19:23]


# ==============================================================================
# INTERPRETER
# ==============================================================================
class Interpreter:

    def __init__(self, record_points_per_orbit=180, max_loop_iterations=100000):
        self.objects = {}
        self.variables = {}
        self.log = []
        self.reports = {}
        self.targets = []
        self.active_finite_burns = {}       # spacecraft name -> list of FiniteBurn resource names
        self.record_points_per_orbit = record_points_per_orbit
        self.max_loop_iterations = max_loop_iterations
        self.quiet = False                  # inside targeter iterations: no reports or ephemeris
        self.mission_start = None
        self.propagated_s = 0.0          # across the whole script, see MAX_SCRIPT_PROPAGATION_S

    # ---------------------------------------------------------------- resources
    def object(self, name, kind=None, line=None):
        obj = self.objects.get(name)
        if obj is None:
            raise ScriptError(f"Unknown object {name!r}", line)
        if kind is not None and getattr(obj, "kind", "Spacecraft") != kind and not (
                kind == "Spacecraft" and isinstance(obj, ScriptSpacecraft)):
            raise ScriptError(f"{name!r} is not a {kind}", line)
        return obj

    def create(self, stmt):
        parts = stmt.text.split()
        if len(parts) < 3:
            raise ScriptError("Create needs a type and at least one name", stmt.line)
        kind = parts[1]
        for name in " ".join(parts[2:]).replace(",", " ").split():
            if kind == "Spacecraft":
                self.objects[name] = ScriptSpacecraft(name)
            elif kind == "Array" or kind == "String":
                self.variables[name.split("[")[0]] = 0.0
            elif kind == "Variable":
                self.variables[name] = 0.0
            elif kind in _DEFAULTS:
                self.objects[name] = Resource(kind, name, _DEFAULTS[kind])
                if kind == "ReportFile":
                    self.reports[name] = {"columns": None, "rows": []}
            else:
                self.objects[name] = Resource(kind, name)
                self.log.append(f"line {stmt.line}: {kind} {name} is stored but not modelled")

    def configure(self, stmt):
        target, value = (s.strip() for s in stmt.text.split("=", 1))
        if "." not in target:
            if target in self.variables:
                self.variables[target] = self.evaluate(value, stmt.line)
                return
            raise ScriptError(f"Unknown variable {target!r}", stmt.line)
        name, field = target.split(".", 1)
        obj = self.object(name, line=stmt.line)
        obj.fields[field] = _parse_value(value)

    # ---------------------------------------------------------------- sequence
    def start_sequence(self):
        for obj in self.objects.values():
            if isinstance(obj, ScriptSpacecraft):
                try:
                    obj.build(self)
                except (KeyError, ValueError) as exc:
                    raise ScriptError(f"Spacecraft {obj.name}: {exc}") from exc
                if self.mission_start is None:
                    self.mission_start = obj.start_epoch
                self._record(obj)

    def run(self, statements):
        for stmt in statements:
            handler = getattr(self, f"_do_{stmt.keyword}", None)
            if handler is not None:
                handler(stmt)
            elif "=" in stmt.text and not stmt.text.startswith(("Propagate", "Achieve", "Vary")):
                self._assign(stmt)
            else:
                raise ScriptError(f"Unsupported command {stmt.keyword!r}", stmt.line)

    def _assign(self, stmt):
        target, expr = (s.strip() for s in stmt.text.split("=", 1))
        owner = self.objects.get(target.split(".")[0])
        if isinstance(owner, Resource) and "." in target:
            # Resource fields take literal settings (Axes = VNB, Thrusters = {...}) or expressions
            try:
                value = self.evaluate(expr, stmt.line)
            except ScriptError:
                value = _parse_value(expr)
            owner.fields[target.split(".", 1)[1]] = value
            return
        value = self.evaluate(expr, stmt.line)
        if "." in target:
            self.set_parameter(target, value, stmt.line)
        elif target in self.variables:
            self.variables[target] = value
        else:
            raise ScriptError(f"Unknown variable {target!r} (declare it with Create Variable)", stmt.line)

    _CALL = re.compile(r"^\s*(\w+)\s*\(([^)]*)\)\s*(\{.*\})?\s*$")

    def _call(self, stmt, command):
        rest = stmt.text[len(command):].strip()
        match = self._CALL.match(rest)
        if not match:
            raise ScriptError(f"Cannot read {command} arguments: {rest!r}", stmt.line)
        return match.group(1), [a.strip() for a in match.group(2).split(",") if a.strip()], match.group(3)

    def _do_Propagate(self, stmt):
        text = re.sub(r"^Propagate\s+(Synchronized|BackProp)\s+", "Propagate ", stmt.text)
        prop_name, sats, stop = self._call(Statement("Propagate", text, stmt.line), "Propagate")
        if len(sats) != 1:
            raise ScriptError("Propagate takes exactly one spacecraft here", stmt.line)
        prop_res = self.object(prop_name, "Propagator", stmt.line)
        sat = self.object(sats[0], "Spacecraft", stmt.line)
        if not stop:
            raise ScriptError("Propagate needs a stopping condition, e.g. {Sat.ElapsedDays = 1}", stmt.line)
        conditions = [c.strip() for c in _split_outside(stop.strip()[1:-1], ",") if c.strip()]
        if len(conditions) != 1:
            raise ScriptError("Use one stopping condition per Propagate", stmt.line)
        cond = conditions[0]
        param = cond.split("=")[0].strip()
        short = param.split(".")[-1]
        qualifiers = param.split(".")[1:-1]
        if qualifiers and qualifiers[0] != "Earth":
            raise ScriptError(f"Stopping condition {param!r}: only Earth-centred conditions are supported, "
                              f"not {qualifiers[0]}", stmt.line)
        duration, until = None, None
        if short in ("Apoapsis", "Periapsis"):
            until = "apogee" if short == "Apoapsis" else "perigee"
        elif short in ("ElapsedSecs", "ElapsedDays") and "=" in cond:
            value = float(self.evaluate(cond.split("=", 1)[1], stmt.line))
            duration = value * (86400.0 if short == "ElapsedDays" else 1.0)
            if not abs(duration) <= MAX_PROPAGATE_S:
                raise ScriptError("One Propagate can run at most 30 days", stmt.line)
        else:
            raise ScriptError(f"Unsupported stopping condition {cond!r}", stmt.line)

        propagator = self._propagator(prop_res, stmt.line)
        burns = self.active_finite_burns.get(sat.name, [])
        finite = self._combined_finite_burn(burns, stmt.line) if burns else None
        period = sat.sc.keplerian()["period"]
        record = None if self.quiet else max(1.0, period / self.record_points_per_orbit)
        left = MAX_SCRIPT_PROPAGATION_S - self.propagated_s
        if left <= 0.0 or (abs(duration) if duration is not None else 0.0) > left:
            raise ScriptError("The script has propagated a year in total, the most one run may", stmt.line)
        # A search for an apsis stops after three orbits, and never beyond the limits above
        search = None
        if until is not None:
            orbits = 3.0 * max(period, 3600.0) if math.isfinite(period) else MAX_PROPAGATE_S
            search = min(orbits, MAX_PROPAGATE_S, left)
        started = sat.sc.epoch
        try:
            propagator.step(sat.sc, duration=duration, until=until, burn=finite, record_step=record,
                            max_duration=search)
        except (RuntimeError, ValueError) as exc:
            raise ScriptError(str(exc), stmt.line) from exc
        self.propagated_s += abs(sat.sc.epoch - started)
        self._sync_tanks(sat)

    def _do_Maneuver(self, stmt):
        burn_name, sats, _ = self._call(stmt, "Maneuver")
        burn = self.object(burn_name, "ImpulsiveBurn", stmt.line)
        sat = self.object(sats[0], "Spacecraft", stmt.line)
        f = burn.fields
        axes = str(f.get("Axes", "VNB")).upper()
        frame = {"VNB": "VNC", "VNC": "VNC", "RTN": "RTN", "RIC": "RTN", "MJ2000EQ": "GCRF", "ICRF": "GCRF"}.get(axes)
        if frame is None:
            raise ScriptError(f"Unsupported burn axes {axes!r}", stmt.line)
        dv = [float(f[f"Element{i}"]) * KM for i in (1, 2, 3)]
        isp = float(f.get("Isp", 300.0)) if f.get("DecrementMass") else 1e12
        try:
            M.ImpulsiveBurn(dv, frame, isp).apply(sat.sc)
        except ValueError as exc:
            raise ScriptError(str(exc), stmt.line) from exc
        self._sync_tanks(sat)
        self._record(sat)

    def _do_BeginFiniteBurn(self, stmt):
        burn_name, sats, _ = self._call(stmt, "BeginFiniteBurn")
        self.object(burn_name, "FiniteBurn", stmt.line)
        self.active_finite_burns.setdefault(sats[0], []).append(burn_name)

    def _do_EndFiniteBurn(self, stmt):
        burn_name, sats, _ = self._call(stmt, "EndFiniteBurn")
        active = self.active_finite_burns.get(sats[0], [])
        if burn_name in active:
            active.remove(burn_name)

    def _do_Report(self, stmt):
        rest = stmt.text[len("Report"):].strip()
        if rest.startswith("'"):
            if not self.quiet:
                self.log.append(rest.strip("'"))
            return
        parts = rest.split()
        if not parts:
            raise ScriptError("Report needs a ReportFile and parameters", stmt.line)
        name, params = parts[0], parts[1:]
        if name not in self.reports:
            # Report straight to the log when no ReportFile of that name exists
            params, name = parts, None
        values = [self.evaluate(p, stmt.line) for p in params]
        if self.quiet:
            return
        if name is None:
            self.log.append("  ".join(f"{p} = {_fmt(v)}" for p, v in zip(params, values)))
            return
        report = self.reports[name]
        if report["columns"] is None:
            report["columns"] = params
        report["rows"].append([_jsonable(v) for v in values])

    def _do_Create(self, stmt):
        self.create(stmt)
        for name in stmt.text.split()[2:]:
            obj = self.objects.get(name.strip(","))
            if isinstance(obj, ScriptSpacecraft):
                raise ScriptError("Create Spacecraft before BeginMissionSequence", stmt.line)

    def _do_Stop(self, stmt):
        raise _StopScript()

    def _do_If(self, stmt):
        cond = stmt.text[2:].strip()
        if self.evaluate(cond, stmt.line):
            self.run(stmt.body)
        else:
            self.run(stmt.else_body)

    def _do_While(self, stmt):
        cond = stmt.text[5:].strip()
        for _ in range(self.max_loop_iterations):
            if not self.evaluate(cond, stmt.line):
                return
            self.run(stmt.body)
        raise ScriptError("While loop exceeded the iteration limit", stmt.line)

    def _do_For(self, stmt):
        match = re.match(r"For\s+(\w+)\s*=\s*(.+)$", stmt.text)
        if not match:
            raise ScriptError("For needs the form: For i = start:stop[:step] (or start:step:stop)", stmt.line)
        var = match.group(1)
        pieces = [self.evaluate(p, stmt.line) for p in _split_outside(match.group(2), ":")]
        if len(pieces) == 2:
            start, stop, step = pieces[0], pieces[1], 1.0
        elif len(pieces) == 3:
            start, step, stop = pieces          # start:step:stop, as in the script language
        else:
            raise ScriptError("For range must be start:stop or start:step:stop", stmt.line)
        if step == 0:
            raise ScriptError("For step cannot be zero", stmt.line)
        if var not in self.variables:
            raise ScriptError(f"Unknown loop variable {var!r} (declare it with Create Variable)", stmt.line)
        value, count = start, 0
        while (value <= stop + 1e-12) if step > 0 else (value >= stop - 1e-12):
            self.variables[var] = value
            self.run(stmt.body)
            value += step
            count += 1
            if count > self.max_loop_iterations:
                raise ScriptError("For loop exceeded the iteration limit", stmt.line)

    def _do_Target(self, stmt):
        dc_name = stmt.text.split()[1].strip(";") if len(stmt.text.split()) > 1 else None
        dc_res = self.object(dc_name, "DifferentialCorrector", stmt.line)
        varies, achieves = [], []
        self._collect_target_commands(stmt.body, varies, achieves)
        if not varies or not achieves:
            raise ScriptError("A Target block needs at least one Vary and one Achieve", stmt.line)

        corrector = M.DifferentialCorrector(max_iterations=int(dc_res.fields.get("MaximumIterations", 25)))
        for v in varies:
            corrector.vary(v["key"], v["initial"], perturbation=v["perturbation"], max_step=v["max_step"],
                           lower=v["lower"], upper=v["upper"])
        for a in achieves:
            corrector.achieve(a["key"], a["goal"], a["tolerance"])

        snapshot = self._snapshot()

        def mission(values):
            self._restore(snapshot)
            self.quiet = True
            self._target_values = values
            self._achieved = {}
            try:
                self.run(stmt.body)
            finally:
                self.quiet = False
            missing = [a["key"] for a in achieves if a["key"] not in self._achieved]
            if missing:
                raise RuntimeError(f"Achieve not reached for {missing}")
            return dict(self._achieved)

        try:
            result = corrector.solve(mission)
        except ScriptError:
            raise
        except (RuntimeError, ValueError) as exc:
            raise ScriptError(f"Target {dc_name}: {exc}", stmt.line) from exc

        # Run the block once more with the solution, this time recording reports and ephemeris
        self._restore(snapshot)
        self._target_values = result.values
        self._achieved = {}
        self.run(stmt.body)
        self._target_values = None
        self.targets.append({
            "name": dc_name, "line": stmt.line, "converged": result.converged, "message": result.message,
            "iterations": result.iterations,
            "variables": {v["label"]: float(result.values[v["key"]]) for v in varies},
            "goals": {a["label"]: {"target": a["goal"], "achieved": float(result.achieved[a["key"]]),
                                   "tolerance": a["tolerance"]} for a in achieves},
        })
        self.log.append(f"Target {dc_name}: {result.message} after {result.iterations} iterations")

    def _collect_target_commands(self, body, varies, achieves):
        for s in body:
            if s.keyword == "Vary":
                v = self._parse_vary(s)
                s._key = v["key"]
                varies.append(v)
            elif s.keyword == "Achieve":
                a = self._parse_achieve(s)
                s._key = a["key"]
                achieves.append(a)
            self._collect_target_commands(s.body, varies, achieves)
            self._collect_target_commands(s.else_body, varies, achieves)

    def _options(self, args, line):
        opts = {}
        for item in args:
            item = item.strip().strip("{}").strip()
            if not item:
                continue
            for piece in _split_outside(item, ","):
                if "=" in piece:
                    key, value = (x.strip().strip("{}") for x in piece.split("=", 1))
                    opts[key] = float(self.evaluate(value, line))
        return opts

    def _parse_vary(self, stmt):
        inner = stmt.text[stmt.text.index("(") + 1:stmt.text.rindex(")")]
        args = _split_outside(inner, ",")
        head = args[0].strip()
        if "=" in head:
            target, init = (x.strip() for x in head.split("=", 1))
            initial = float(self.evaluate(init, stmt.line))
        else:
            target = head
            initial = None
        opts = self._options(args[1:], stmt.line)
        if initial is None:
            initial = opts.get("InitialValue", float(self.get_parameter(target, stmt.line)))
        return {"key": f"vary:{stmt.line}:{target}", "label": target, "target": target, "initial": initial,
                "perturbation": opts.get("Perturbation", 1e-4), "max_step": opts.get("MaxStep", 0.2),
                "lower": opts.get("Lower", -math.inf), "upper": opts.get("Upper", math.inf)}

    def _parse_achieve(self, stmt):
        inner = stmt.text[stmt.text.index("(") + 1:stmt.text.rindex(")")]
        args = _split_outside(inner, ",")
        head = args[0].strip()
        if "=" not in head:
            raise ScriptError("Achieve needs Param = goal", stmt.line)
        param, goal = (x.strip() for x in head.split("=", 1))
        opts = self._options(args[1:], stmt.line)
        return {"key": f"achieve:{stmt.line}:{param}", "label": param, "param": param,
                "goal": float(self.evaluate(goal, stmt.line)), "tolerance": opts.get("Tolerance", 0.1)}

    def _do_Vary(self, stmt):
        values = getattr(self, "_target_values", None)
        if values is None:
            raise ScriptError("Vary outside a Target block", stmt.line)
        target = stmt._key.split(":", 2)[2]
        self.set_parameter(target, values[stmt._key], stmt.line) if "." in target else \
            self.variables.__setitem__(target, values[stmt._key])

    def _do_Achieve(self, stmt):
        if getattr(self, "_target_values", None) is None:
            raise ScriptError("Achieve outside a Target block", stmt.line)
        param = stmt._key.split(":", 2)[2]
        self._achieved[stmt._key] = float(self.evaluate(param, stmt.line))

    # ---------------------------------------------------------------- helpers
    def _snapshot(self):
        return copy.deepcopy((self.objects, self.variables, self.active_finite_burns))

    def _restore(self, snapshot):
        objects, variables, burns = copy.deepcopy(snapshot)
        self.objects, self.variables, self.active_finite_burns = objects, variables, burns

    def _propagator(self, prop_res, line):
        f = prop_res.fields
        fm_name = f.get("FM")
        fm = self.object(fm_name, "ForceModel", line).fields if fm_name else _DEFAULTS["ForceModel"]
        masses = [str(b).lower() for b in (fm.get("PointMasses") or [])]
        degree = int(float(fm.get("GravityField.Earth.Degree", 4)))
        order = int(float(fm.get("GravityField.Earth.Order", degree)))
        cfg = ForceModelConfig(
            gravity_degree=degree, gravity_order=min(order, degree),
            third_body=any(b in ("sun", "luna", "moon") for b in masses),
            srp=bool(fm.get("SRP", False)),
            drag=str(fm.get("Drag.AtmosphereModel", fm.get("Drag", "None"))).lower() not in ("none", "false", "off"),
            relativity=bool(fm.get("RelativisticCorrection", False)),
            albedo=False,
        )
        kind = str(f.get("Type", "RungeKutta89")).replace(" ", "").upper()
        method = _PROPAGATOR_TYPES.get(kind, "RKF78")
        accuracy = float(f.get("Accuracy", 1e-11))
        return M.Propagator(cfg, method=method, rtol=accuracy, atol=accuracy)

    def _combined_finite_burn(self, burn_names, line):
        thrust_vec, mdot = np.zeros(3), 0.0
        frame = None
        for name in burn_names:
            for thr_name in self.object(name, "FiniteBurn", line).fields.get("Thrusters", []):
                t = self.object(thr_name, "ChemicalThruster", line).fields
                thrust = float(t.get("Thrust", t.get("C1", 10.0)))
                isp = float(t.get("Isp", t.get("K1", 300.0)))
                direction = np.array([float(t.get(f"ThrustDirection{i}", 1.0 if i == 1 else 0.0)) for i in (1, 2, 3)])
                axes = {"VNB": "VNC", "MJ2000EQ": "GCRF"}.get(str(t.get("Axes", "VNB")).upper(), None)
                if axes is None:
                    raise ScriptError(f"Unsupported thruster axes {t.get('Axes')!r}", line)
                if frame not in (None, axes):
                    raise ScriptError("All active thrusters must use the same axes", line)
                frame = axes
                thrust_vec += thrust * direction / np.linalg.norm(direction)
                mdot += thrust / (isp * M.G0)
        total = float(np.linalg.norm(thrust_vec))
        if total == 0.0:
            raise ScriptError("Active finite burn has no thrust", line)
        return M.FiniteBurn(thrust_n=total, isp_s=total / (mdot * M.G0), direction=tuple(thrust_vec / total),
                            frame=frame)

    def _sync_tanks(self, sat):
        tanks = sat.fields.get("Tanks") or []
        if not tanks:
            return
        total = sum(float(self.objects[t].fields.get("FuelMass", 0.0)) for t in tanks)
        for t in tanks:
            share = float(self.objects[t].fields.get("FuelMass", 0.0)) / total if total > 0 else 1.0 / len(tanks)
            self.objects[t].fields["FuelMass"] = sat.sc.fuel_mass_kg * share

    def _record(self, sat):
        if self.quiet:
            return
        if not sat.sc.ephemeris or abs(sat.sc.ephemeris[-1][0] - sat.sc.epoch) > 1e-6:
            sat.sc.ephemeris.append((sat.sc.epoch, sat.sc.r.copy(), sat.sc.v.copy()))
        else:
            sat.sc.ephemeris[-1] = (sat.sc.epoch, sat.sc.r.copy(), sat.sc.v.copy())

    # ---------------------------------------------------------------- parameters
    def get_parameter(self, dotted, line=None):
        parts = dotted.split(".")
        obj = self.objects.get(parts[0])
        if obj is None:
            raise ScriptError(f"Unknown object {parts[0]!r}", line)
        field = parts[-1]
        if isinstance(obj, ScriptSpacecraft):
            if obj.sc is None:
                return obj.fields.get(field)
            return self._spacecraft_parameter(obj, field, line)
        if field not in obj.fields:
            raise ScriptError(f"{obj.kind} {obj.name} has no field {field!r}", line)
        return obj.fields[field]

    def set_parameter(self, dotted, value, line=None):
        parts = dotted.split(".")
        obj = self.objects.get(parts[0])
        if obj is None:
            raise ScriptError(f"Unknown object {parts[0]!r}", line)
        field = ".".join(parts[1:])
        if isinstance(obj, ScriptSpacecraft) and obj.sc is not None:
            self._set_spacecraft_parameter(obj, field.split(".")[-1], float(value), line)
        else:
            obj.fields[field] = value

    def _spacecraft_parameter(self, sat, field, line):
        sc = sat.sc
        k = sc.keplerian()
        if field in ("X", "Y", "Z", "VX", "VY", "VZ"):
            r, v = transform_state(sc.r, sc.v, sc.epoch, "GCRF", "EME2000")
            vec = r if field in ("X", "Y", "Z") else v
            return float(vec["XYZ".index(field[-1])] / KM)
        table = {
            "SMA": k["a"] / KM, "ECC": k["e"], "INC": math.degrees(k["inc"]), "RAAN": math.degrees(k["raan"]),
            "AOP": math.degrees(k["argp"]), "TA": math.degrees(k["ta"]),
            "RMAG": np.linalg.norm(sc.r) / KM, "VMAG": np.linalg.norm(sc.v) / KM,
            "RadPer": k["rp"] / KM, "RadApo": k["ra"] / KM, "OrbitPeriod": k["period"],
            "Altitude": None, "TotalMass": sc.mass_kg, "DryMass": sc.dry_mass_kg, "FuelMass": sc.fuel_mass_kg,
            "ElapsedSecs": sc.epoch - self.mission_start, "ElapsedDays": (sc.epoch - self.mission_start) / 86400.0,
            "Energy": float(sc.v @ sc.v / 2.0 - M.MU_EARTH / np.linalg.norm(sc.r)) / 1e6,
            "HMAG": float(np.linalg.norm(np.cross(sc.r, sc.v))) / 1e6,
        }
        if field in table and table[field] is not None:
            return float(table[field])
        if field in ("MA", "EA"):
            e, ta = k["e"], k["ta"]
            ea = 2.0 * math.atan2(math.sqrt(1 - e) * math.sin(ta / 2), math.sqrt(1 + e) * math.cos(ta / 2))
            return math.degrees((ea - e * math.sin(ea)) % (2 * math.pi) if field == "MA" else ea % (2 * math.pi))
        if field in ("Altitude", "Latitude", "Longitude"):
            lat, lon, h = gcrf_to_geodetic(sc.r, sc.epoch)
            return float({"Altitude": h / KM, "Latitude": lat, "Longitude": lon}[field])
        if field in ("UTCModJulian", "TAIModJulian", "TTModJulian", "A1ModJulian"):
            scale = field[:-len("ModJulian")]
            jd1, jd2 = sc.epoch.jd("TAI" if scale == "A1" else scale)
            mjd = (jd1 - GMAT_MJD_OFFSET) + jd2
            return mjd + (A1_MINUS_TAI / 86400.0 if scale == "A1" else 0.0)
        if field in ("UTCGregorian", "TAIGregorian", "TTGregorian", "Epoch"):
            return _gregorian(sc.epoch, "UTC" if field == "Epoch" else field[:-len("Gregorian")])
        raise ScriptError(f"Unknown spacecraft parameter {field!r}", line)

    def _set_spacecraft_parameter(self, sat, field, value, line):
        sc = sat.sc
        if field in ("SMA", "ECC", "INC", "RAAN", "AOP", "TA"):
            k = sc.keplerian()
            el = {"SMA": k["a"] / KM, "ECC": k["e"], "INC": math.degrees(k["inc"]), "RAAN": math.degrees(k["raan"]),
                  "AOP": math.degrees(k["argp"]), "TA": math.degrees(k["ta"])}
            el[field] = value
            sc.r, sc.v = M.state_from_keplerian(el["SMA"] * KM, el["ECC"], *(math.radians(el[x]) for x in
                                                                                   ("INC", "RAAN", "AOP", "TA")))
        elif field in ("X", "Y", "Z", "VX", "VY", "VZ"):
            r, v = transform_state(sc.r, sc.v, sc.epoch, "GCRF", "EME2000")
            vec = r if field in ("X", "Y", "Z") else v
            vec["XYZ".index(field[-1])] = value * KM
            sc.r, sc.v = transform_state(r, v, sc.epoch, "EME2000", "GCRF")
        elif field == "DryMass":
            sc.dry_mass_kg = value
        elif field in ("Cd", "Cr", "DragArea", "SRPArea"):
            setattr(sc, {"Cd": "cd", "Cr": "cr", "DragArea": "drag_area_m2", "SRPArea": "srp_area_m2"}[field], value)
        else:
            raise ScriptError(f"Cannot set spacecraft parameter {field!r} during the mission", line)

    # ---------------------------------------------------------------- expressions
    def evaluate(self, text, line=None):
        text = text.strip()
        if text.startswith("'") and text.endswith("'"):
            return text[1:-1]
        try:
            tree = ast.parse(_to_python_expression(text), mode="eval")
        except SyntaxError as exc:
            raise ScriptError(f"Cannot read expression {text!r}", line) from exc
        return self._eval(tree.body, line)

    def _eval(self, node, line):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, str)):
            return node.value
        if isinstance(node, ast.Name):
            if node.id in self.variables:
                return self.variables[node.id]
            if node.id in _CONSTANTS:
                return _CONSTANTS[node.id]
            raise ScriptError(f"Unknown name {node.id!r}", line)
        if isinstance(node, ast.Attribute):
            dotted = _dotted(node)
            if dotted is None:
                raise ScriptError("Unsupported expression", line)
            return self.get_parameter(dotted, line)
        if isinstance(node, ast.BinOp):
            a, b = self._eval(node.left, line), self._eval(node.right, line)
            if isinstance(node.op, ast.Add) and isinstance(a, str) and isinstance(b, str):
                return a + b
            if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (a, b)):
                raise ScriptError("Arithmetic needs numbers", line)
            # Powers in floating point: an integer power such as 9^9^9 would never finish
            ops = {ast.Add: lambda: a + b, ast.Sub: lambda: a - b, ast.Mult: lambda: a * b,
                   ast.Div: lambda: a / b, ast.Pow: lambda: float(a) ** float(b), ast.Mod: lambda: a % b}
            if type(node.op) not in ops:
                raise ScriptError("Unsupported operator", line)
            try:
                return ops[type(node.op)]()
            except OverflowError:
                raise ScriptError("Number too large", line) from None
            except ZeroDivisionError:
                raise ScriptError("Division by zero", line) from None
        if isinstance(node, ast.UnaryOp):
            val = self._eval(node.operand, line)
            if isinstance(node.op, ast.USub):
                return -val
            if isinstance(node.op, ast.UAdd):
                return val
            if isinstance(node.op, ast.Not):
                return not val
        if isinstance(node, ast.BoolOp):
            vals = [self._eval(v, line) for v in node.values]
            return all(vals) if isinstance(node.op, ast.And) else any(vals)
        if isinstance(node, ast.Compare):
            left = self._eval(node.left, line)
            for op, comp in zip(node.ops, node.comparators):
                right = self._eval(comp, line)
                ok = {ast.Eq: left == right, ast.NotEq: left != right, ast.Lt: left < right,
                      ast.LtE: left <= right, ast.Gt: left > right, ast.GtE: left >= right}.get(type(op))
                if ok is None:
                    raise ScriptError("Unsupported comparison", line)
                if not ok:
                    return False
                left = right
            return True
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCTIONS:
            return _FUNCTIONS[node.func.id](*(self._eval(a, line) for a in node.args))
        raise ScriptError("Unsupported expression", line)

    # ---------------------------------------------------------------- results
    def results(self):
        spacecraft, ephemeris = {}, {}
        for name, obj in self.objects.items():
            if not isinstance(obj, ScriptSpacecraft) or obj.sc is None:
                continue
            sc = obj.sc
            k = sc.keplerian()
            spacecraft[name] = {
                "epoch_utc": sc.epoch.iso("UTC"), "position_m": sc.r.tolist(), "velocity_ms": sc.v.tolist(),
                "sma_km": k["a"] / KM, "ecc": k["e"], "inc_deg": math.degrees(k["inc"]),
                "raan_deg": math.degrees(k["raan"]), "aop_deg": math.degrees(k["argp"]),
                "ta_deg": math.degrees(k["ta"]), "altitude_km": sc.altitude_km(), "mass_kg": sc.mass_kg,
                "fuel_mass_kg": sc.fuel_mass_kg,
            }
            ephemeris[name] = {
                "epochs_utc": [e.iso("UTC", 6) for e, _, _ in sc.ephemeris],
                "t_s": [e - self.mission_start for e, _, _ in sc.ephemeris],
                "position_m": [r.tolist() for _, r, _ in sc.ephemeris],
                "velocity_ms": [v.tolist() for _, _, v in sc.ephemeris],
            }
        return {"log": self.log, "reports": self.reports, "spacecraft": spacecraft, "ephemeris": ephemeris,
                "targets": self.targets}


class _StopScript(Exception):
    pass


def _fmt(value):
    return f"{value:.10g}" if isinstance(value, float) else str(value)


def _jsonable(value):
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    return value


# ==============================================================================
# ENTRY POINTS
# ==============================================================================
def run_script(text, record_points_per_orbit=180):
    """Runs a mission script; returns the results dict, with "error" set if it stopped on one."""
    interp = Interpreter(record_points_per_orbit=record_points_per_orbit)
    error = None
    try:
        resources, sequence = parse(text)
        for stmt in resources:
            if stmt.keyword == "Create":
                interp.create(stmt)
            elif "=" in stmt.text:
                interp.configure(stmt)
            else:
                raise ScriptError(f"Unexpected statement before BeginMissionSequence: {stmt.text!r}", stmt.line)
        interp.start_sequence()
        interp.run(sequence)
    except _StopScript:
        interp.log.append("Stopped by Stop command")
    except ScriptError as exc:
        error = {"message": exc.message, "line": exc.line}
    out = interp.results() if interp.mission_start is not None else {
        "log": interp.log, "reports": interp.reports, "spacecraft": {}, "ephemeris": {}, "targets": interp.targets}
    out["error"] = error
    return out


def main(argv=None):
    import argparse

    from .ephemeris_io import write_oem

    parser = argparse.ArgumentParser(description="Run an AstroFlyer mission script without the UI.")
    parser.add_argument("script", help="mission script file")
    parser.add_argument("--json", help="write the full results to this JSON file")
    parser.add_argument("--oem", help="write one CCSDS OEM per spacecraft into this folder")
    args = parser.parse_args(argv)

    with open(args.script) as fh:
        result = run_script(fh.read())
    for line in result["log"]:
        print(line)
    for name, rep in result["reports"].items():
        if rep["columns"]:
            print(f"\n[{name}]")
            print("  ".join(rep["columns"]))
            for row in rep["rows"]:
                print("  ".join(_fmt(v) for v in row))
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(result, fh, indent=2)
    if args.oem:
        os.makedirs(args.oem, exist_ok=True)
        for name, eph in result["ephemeris"].items():
            if len(eph["epochs_utc"]) >= 2:
                write_oem(os.path.join(args.oem, f"{name}.oem"), eph["epochs_utc"], eph["position_m"],
                          eph["velocity_ms"], object_name=name)
    if result["error"]:
        err = result["error"]
        print(f"error: line {err['line']}: {err['message']}" if err["line"] else f"error: {err['message']}",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
AstroFlyer HEO — Mission Plan I/O Engine
=============================================================================
Provides bidirectional, strongly typed, and XSD-validated XML serialization
and deserialization of FreeFlyer-compliant Mission Plans (.MissionPlan XML).
Optional XSD validation when a user-supplied schema is present.
=============================================================================
"""

import logging
import os
import sys
from typing import Any, Optional, Tuple, Dict

try:
    from lxml import etree
    HAS_LXML = True
except ImportError:
    import xml.etree.ElementTree as etree  # type: ignore
    HAS_LXML = False

logger = logging.getLogger(__name__)

# Optional user-supplied schema. No schema ships with AstroFlyer; when absent,
# XSD validation is skipped and only XML well-formedness is checked.
_XSD_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "schemas", "mission_plan.xsd"))


def get_schema_validator() -> Optional[Any]:
    """Returns an lxml XMLSchema validator if lxml is available and XSD exists."""
    if not HAS_LXML:
        logger.info("Mission Plan XSD validation skipped: lxml not installed.")
        return None
    if not os.path.exists(_XSD_PATH):
        logger.info("Mission Plan XSD validation skipped: no schema at %s.", _XSD_PATH)
        return None
    try:
        xsd_doc = etree.parse(_XSD_PATH)
        return etree.XMLSchema(xsd_doc)
    except Exception:
        return None


def validate_mission_plan(xml_source: str) -> Tuple[bool, list[str]]:
    """
    Validates a MissionPlan XML file path or XML string against mission_plan.xsd.
    Returns (is_valid, list_of_errors).
    """
    validator = get_schema_validator()
    if validator is None:
        return True, ["Notice: XSD validation skipped (no schema present or lxml missing)."]

    try:
        if os.path.exists(xml_source):
            doc = etree.parse(xml_source)
        else:
            doc = etree.fromstring(xml_source.encode('utf-8'))
        is_valid = validator.validate(doc)
        errors = [str(err) for err in validator.error_log] if not is_valid else []
        return is_valid, errors
    except Exception as e:
        return False, [f"XML Parsing/Validation Exception: {e}"]


def _create_minimal_mission_plan_tree(
    spacecraft_name: str,
    a_km: float,
    e: float,
    inc_deg: float,
    raan_deg: float,
    argp_deg: float,
    nu_deg: float,
    epoch_str: str = "Jan 01 2026 00:00:00.000",
    propagator_name: str = "PrinceDormand853"
) -> Any:
    """Builds a compliant FreeFlyerMissionPlan DOM element tree from scratch."""
    root = etree.Element("FreeFlyerMissionPlan", schemaVersion="8.0.0.12")
    project_objects = etree.SubElement(root, "ProjectObjects")

    # 1. MissionPlanSettings
    obj_mp = etree.SubElement(project_objects, "Object")
    mps = etree.SubElement(obj_mp, "MissionPlanSettings", isConstant="false", isGlobal="true", name="MissionPlan")
    etree.SubElement(mps, "Name").text = "MissionPlan"
    etree.SubElement(mps, "Title").text = "AstroFlyer HEO Mission Plan"

    # 2. Spacecraft Object
    obj_sc = etree.SubElement(project_objects, "Object")
    sc = etree.SubElement(obj_sc, "Spacecraft", isConstant="false", isGlobal="true", name=spacecraft_name)
    etree.SubElement(sc, "Name").text = spacecraft_name
    etree.SubElement(sc, "Epoch").text = epoch_str

    orbit_state = etree.SubElement(sc, "OrbitState")
    etree.SubElement(orbit_state, "CentralBody").text = "Earth"
    etree.SubElement(orbit_state, "CoordinateSystem").text = "EarthMJ2000Eq"
    etree.SubElement(orbit_state, "DisplayStateType").text = "Keplerian"

    kep = etree.SubElement(orbit_state, "Keplerian")
    elem_a = etree.SubElement(kep, "A", units="km", displayed_units="km")
    elem_a.text = f"{a_km:.6f}"
    elem_e = etree.SubElement(kep, "E", units="", displayed_units="")
    elem_e.text = f"{e:.6f}"
    elem_i = etree.SubElement(kep, "I", units="deg", displayed_units="deg")
    elem_i.text = f"{inc_deg:.6f}"
    elem_raan = etree.SubElement(kep, "RAAN", units="deg", displayed_units="deg")
    elem_raan.text = f"{raan_deg:.6f}"
    elem_w = etree.SubElement(kep, "W", units="deg", displayed_units="deg")
    elem_w.text = f"{argp_deg:.6f}"
    elem_ta = etree.SubElement(kep, "TA", units="deg", displayed_units="deg")
    elem_ta.text = f"{nu_deg:.6f}"

    # Propagator
    prop_elem = etree.SubElement(sc, "Propagator")
    rk_elem = etree.SubElement(prop_elem, propagator_name, isConstant="false", isGlobal="false", name=f"{spacecraft_name}_|prop|")
    etree.SubElement(rk_elem, "Name").text = f"{spacecraft_name}_|prop|"
    ss = etree.SubElement(rk_elem, "StepSize", units="s", displayed_units="s")
    ss.text = "60.0"
    tol = etree.SubElement(rk_elem, "Tolerance")
    tol.text = "1e-11"

    # Mass Properties
    etree.SubElement(sc, "DryMass", units="kg", displayed_units="kg").text = "1000.0"
    etree.SubElement(sc, "TotalMass", units="kg", displayed_units="kg").text = "1500.0"
    etree.SubElement(sc, "Cd", units="", displayed_units="").text = "2.20"
    etree.SubElement(sc, "Cr", units="", displayed_units="").text = "1.20"
    etree.SubElement(sc, "DragArea", units="m^2", displayed_units="m^2").text = "15.00"
    etree.SubElement(sc, "SRPArea", units="m^2", displayed_units="m^2").text = "15.00"

    # Script section
    script_elem = etree.SubElement(root, "Script")
    etree.SubElement(script_elem, "ScriptLine").text = f"// AstroFlyer HEO Mission Script"
    etree.SubElement(script_elem, "ScriptLine").text = f"While ({spacecraft_name}.ElapsedTime < TS(24 hours));"
    etree.SubElement(script_elem, "ScriptLine").text = f"    Step({spacecraft_name});"
    etree.SubElement(script_elem, "ScriptLine").text = f"End;"

    return etree.ElementTree(root)


def export_to_mission_plan(
    orbit_params: dict,
    output_path: str,
    duration_hours: float = 24.0,
    mission_title: str = "AstroFlyer HEO Mission Plan",
    propagator_type: str = "PrinceDormand853",
    validate_xsd: bool = True
) -> Dict[str, Any]:
    """
    Exports AstroFlyer orbit configuration and mission parameters to a standard .MissionPlan XML.
    Uses strongly typed DOM Element tree construction with optional XSD validation.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    a_km = float(orbit_params.get("a", orbit_params.get("sma", orbit_params.get("sma_km", 24389.0))))
    e = float(orbit_params.get("e", orbit_params.get("ecc", 0.728525)))
    inc_deg = float(orbit_params.get("inc", orbit_params.get("inc_deg", 28.5)))
    raan_deg = float(orbit_params.get("raan", orbit_params.get("raan_deg", 45.0)))
    argp_deg = float(orbit_params.get("arg_perigee", orbit_params.get("aop_deg", 30.0)))
    nu_deg = float(orbit_params.get("true_anomaly", orbit_params.get("ta_deg", 0.0)))
    sc_name = str(orbit_params.get("spacecraft_name", "Spacecraft1"))
    dry_mass = float(orbit_params.get("dry_mass", 1000.0))
    fuel_mass = float(orbit_params.get("fuel_mass", 500.0))
    cd = float(orbit_params.get("cd", 2.2))
    cr = float(orbit_params.get("cr", 1.2))
    drag_area = float(orbit_params.get("drag_area", 15.0))
    srp_area = float(orbit_params.get("srp_area", 15.0))

    tree = _create_minimal_mission_plan_tree(
        spacecraft_name=sc_name,
        a_km=a_km, e=e, inc_deg=inc_deg, raan_deg=raan_deg, argp_deg=argp_deg, nu_deg=nu_deg,
        propagator_name=propagator_type
    )
    root = tree.getroot()
    root.find(".//Title").text = mission_title
    for line in root.findall(".//ScriptLine"):
        if line.text and "ElapsedTime < TS(" in line.text:
            line.text = f"While ({sc_name}.ElapsedTime < TS({duration_hours:.2f} hours));"

    # Serialize DOM Tree to output XML file
    if HAS_LXML:
        tree.write(output_path, encoding="utf-8", xml_declaration=True, pretty_print=True)
    else:
        tree.write(output_path, encoding="utf-8", xml_declaration=True)

    # Validate against mission_plan.xsd
    is_valid, validation_errors = True, []
    if validate_xsd:
        is_valid, validation_errors = validate_mission_plan(output_path)

    return {
        "status": "SUCCESS",
        "output_path": output_path,
        "is_schema_valid": is_valid,
        "validation_errors": validation_errors,
        "orbit_elements": {
            "a_km": a_km, "e": e, "inc_deg": inc_deg,
            "raan_deg": raan_deg, "argp_deg": argp_deg, "nu_deg": nu_deg
        },
        "mission_title": mission_title,
        "duration_hours": duration_hours
    }


def import_from_mission_plan(mission_plan_path: str, validate_xsd: bool = True) -> Dict[str, Any]:
    """
    Parses a .MissionPlan XML file using strongly typed DOM elements and extracts
    spacecraft Keplerian elements, physical properties, and simulation parameters.
    """
    if not os.path.exists(mission_plan_path):
        raise FileNotFoundError(f"Mission Plan file not found: {mission_plan_path}")

    # Parse XML DOM tree
    tree = etree.parse(mission_plan_path)
    root = tree.getroot()

    # 1. Mission Metadata
    title_elem = root.find(".//MissionPlanSettings/Title")
    if title_elem is None:
        title_elem = root.find(".//Title")
    mission_title = title_elem.text if title_elem is not None and title_elem.text else "AstroFlyer HEO Mission"

    # 2. Spacecraft Elements
    sc_elem = root.find(".//Spacecraft")
    if sc_elem is None:
        raise ValueError("No Spacecraft entity found in Mission Plan XML.")

    sc_name = sc_elem.attrib.get("name", "Spacecraft1")
    epoch_elem = sc_elem.find("Epoch")
    epoch_str = epoch_elem.text if epoch_elem is not None and epoch_elem.text else "Jan 01 2026 00:00:00.000"

    # Keplerian Orbital Elements
    kep_elem = sc_elem.find(".//Keplerian")
    if kep_elem is None:
        raise ValueError("Spacecraft node does not define a Keplerian orbit state.")

    def _get_float_child(parent, tag, default):
        el = parent.find(tag)
        if el is not None and el.text:
            try:
                return float(el.text.strip())
            except ValueError:
                return default
        return default

    a_km = _get_float_child(kep_elem, "A", 24389.0)
    e = _get_float_child(kep_elem, "E", 0.728525)
    inc_deg = _get_float_child(kep_elem, "I", 28.5)
    raan_deg = _get_float_child(kep_elem, "RAAN", 45.0)
    argp_deg = _get_float_child(kep_elem, "W", 30.0)
    nu_deg = _get_float_child(kep_elem, "TA", 0.0)

    # Propagator Type & Tolerance
    prop_elem = sc_elem.find(".//Propagator")
    prop_type = "PrinceDormand853"
    tol = 1e-11
    if prop_elem is not None and len(prop_elem) > 0:
        first_child = prop_elem[0]
        prop_type = first_child.tag
        tol = _get_float_child(first_child, "Tolerance", 1e-11)

    # Mass & Physical Parameters
    dry_mass = _get_float_child(sc_elem, "DryMass", 1000.0)
    total_mass = _get_float_child(sc_elem, "TotalMass", 1500.0)
    fuel_mass = max(0.0, total_mass - dry_mass)
    cd = _get_float_child(sc_elem, "Cd", 2.2)
    cr = _get_float_child(sc_elem, "Cr", 1.2)
    drag_area = _get_float_child(sc_elem, "DragArea", 15.0)
    srp_area = _get_float_child(sc_elem, "SRPArea", 15.0)

    # 3. Optional Schema Validation
    is_valid, validation_errors = True, []
    if validate_xsd:
        is_valid, validation_errors = validate_mission_plan(mission_plan_path)

    return {
        "status": "SUCCESS",
        "mission_title": mission_title,
        "spacecraft_name": sc_name,
        "epoch": epoch_str,
        "a": a_km,
        "sma_km": a_km,
        "e": e,
        "ecc": e,
        "inc": inc_deg,
        "inc_deg": inc_deg,
        "raan": raan_deg,
        "raan_deg": raan_deg,
        "arg_perigee": argp_deg,
        "aop_deg": argp_deg,
        "true_anomaly": nu_deg,
        "ta_deg": nu_deg,
        "dry_mass": dry_mass,
        "fuel_mass": fuel_mass,
        "total_mass": total_mass,
        "cd": cd,
        "cr": cr,
        "drag_area": drag_area,
        "srp_area": srp_area,
        "propagator": prop_type,
        "integrator_tolerance": tol,
        "is_schema_valid": is_valid,
        "validation_errors": validation_errors,
        "source_file": os.path.basename(mission_plan_path)
    }

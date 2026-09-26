"""
AstroFlyer HEO — Mission Plan I/O Engine
Provides bidirectional export and import of standard Mission Plans (.MissionPlan XML)
for orbit state serialization, mission parameters, and exchange.
"""

import os
import re
import xml.etree.ElementTree as ET


def export_to_mission_plan(
    orbit_params: dict,
    output_path: str,
    duration_hours: float = 24.0,
    mission_title: str = "AstroFlyer HEO Mission Plan"
) -> str:
    """
    Exports AstroFlyer orbit configuration and mission parameters to a standard .MissionPlan XML.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    template_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "datasources", "freeflyer_reference", "mission_plans", "HighlyEllipticalVariableStepProp.MissionPlan"
    )
    if not os.path.exists(template_path):
        template_path = os.path.abspath(template_path)

    with open(template_path, "r", encoding="utf-8") as f:
        xml_text = f.read()

    a_km = float(orbit_params.get("a", 26610.22))
    e = float(orbit_params.get("e", 0.74))
    inc_deg = float(orbit_params.get("inc", 63.435))
    raan_deg = float(orbit_params.get("raan", 45.0))
    argp_deg = float(orbit_params.get("arg_perigee", 270.0))
    nu_deg = float(orbit_params.get("true_anomaly", 0.0))

    # Update Title
    xml_text = re.sub(r"<Title>.*?</Title>", f"<Title>{mission_title}</Title>", xml_text)

    # Update Keplerian elements in XML (accounting for attributes like displayed_units)
    xml_text = re.sub(r"<A\b[^>]*>.*?</A>", f'<A displayed_units="km" units="km">{a_km:.6f}</A>', xml_text)
    xml_text = re.sub(r"<E\b[^>]*>.*?</E>", f'<E displayed_units="" units="">{e:.6f}</E>', xml_text)
    xml_text = re.sub(r"<I\b[^>]*>.*?</I>", f'<I displayed_units="deg" units="deg">{inc_deg:.6f}</I>', xml_text)
    xml_text = re.sub(r"<RAAN\b[^>]*>.*?</RAAN>", f'<RAAN displayed_units="deg" units="deg">{raan_deg:.6f}</RAAN>', xml_text)
    xml_text = re.sub(r"<W\b[^>]*>.*?</W>", f'<W displayed_units="deg" units="deg">{argp_deg:.6f}</W>', xml_text)
    xml_text = re.sub(r"<TA\b[^>]*>.*?</TA>", f'<TA displayed_units="deg" units="deg">{nu_deg:.6f}</TA>', xml_text)

    # Update simulation duration
    xml_text = re.sub(
        r"While\s*\(Spacecraft1\.ElapsedTime\s*<\s*TS\([^)]+\)\);",
        f"While (Spacecraft1.ElapsedTime < TS({duration_hours} hours));",
        xml_text
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_text)

    return output_path


def import_from_mission_plan(mission_plan_path: str) -> dict:
    """
    Parses a .MissionPlan XML file and extracts spacecraft Keplerian orbital elements
    and configuration to initialize AstroFlyer's trajectory engine.
    """
    if not os.path.exists(mission_plan_path):
        raise FileNotFoundError(f"Mission Plan not found: {mission_plan_path}")

    tree = ET.parse(mission_plan_path)
    root = tree.getroot()

    sc_elem = root.find(".//Spacecraft")
    if sc_elem is None:
        raise ValueError("No Spacecraft object found in Mission Plan.")

    name = sc_elem.attrib.get("name", "Imported_Spacecraft")
    kep_elem = sc_elem.find(".//Keplerian")

    if kep_elem is None:
        raise ValueError("Spacecraft has no Keplerian orbit state definition.")

    a_km = float(kep_elem.findtext("A", "26610.22"))
    e = float(kep_elem.findtext("E", "0.74"))
    inc_deg = float(kep_elem.findtext("I", "63.435"))
    raan_deg = float(kep_elem.findtext("RAAN", "45.0"))
    argp_deg = float(kep_elem.findtext("W", "270.0"))
    nu_deg = float(kep_elem.findtext("TA", "0.0"))

    prop_elem = sc_elem.find(".//Propagator")
    prop_type = "RK89"
    if prop_elem is not None and len(prop_elem) > 0:
        prop_type = prop_elem[0].tag

    return {
        "name": name,
        "a": a_km,
        "e": e,
        "inc": inc_deg,
        "raan": raan_deg,
        "arg_perigee": argp_deg,
        "true_anomaly": nu_deg,
        "propagator": prop_type,
        "source_file": os.path.basename(mission_plan_path)
    }

"""
AstroFlyer HEO - Formal Project Abstract Generator (PDF & DOCX)
Generates IEEE / VTU Compliant Project Abstract Documents
Department of Aerospace Engineering, ACS College of Engineering (Affiliated to VTU, Belagavi)
"""

import os
import sys
import shutil
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.pdfgen import canvas

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn


# ==============================================================================
# 1. METADATA & CONTENT DEFINITIONS
# ==============================================================================

PROJECT_TITLE = "Precise Trajectory Propagation and Events Prediction for Highly Eccentric Orbits"
INSTITUTION = "ACS COLLEGE OF ENGINEERING, BENGALURU\nDEPARTMENT OF AEROSPACE ENGINEERING"
AFFILIATION = "Affiliated to Visvesvaraya Technological University (VTU), Belagavi | Approved by AICTE, New Delhi"
COURSE_INFO = "Bachelor of Engineering (B.E.) in Aerospace Engineering — Final Year Major Project (Phase-II)"
ACADEMIC_YEAR = "Academic Year 2025–2026 / 2026–2027"

CANDIDATES = [
    ("Girish Gowda S", "1AH23AS019"),
    ("Gowtham N", "1AH23AS020"),
    ("Harshith S Purohith", "1AH23AS021")
]

GUIDES = [
    ("Mr. Vijay M", "Assistant Professor, Dept. of Aerospace Engineering"),
    ("Dr. Suresh C", "Professor & Head of Department, Dept. of Aerospace Engineering")
]

# PDF Version with ReportLab XML/HTML Entities for Crisp Glyphs
ABSTRACT_HTML = (
    "Spacecraft operating in Highly Eccentric Orbits (HEOs)&mdash;exemplified by Geostationary Transfer "
    "Orbits (GTO), critical-inclination Molniya constellations (<i>i</i> &asymp; 63.435&deg;), and cislunar transfer "
    "trajectories&mdash;traverse severely disparate dynamical environments within every single orbital revolution, "
    "oscillating between hypersonic, violently perturbed perigee passages (perigee altitude <i>r<sub>p</sub></i> &sim; 200&ndash;600 km, "
    "velocity <i>v<sub>p</sub></i> &gt; 10.2 km/s) and prolonged apogee dwells (apogee altitude <i>r<sub>a</sub></i> &gt; 35,000 km, "
    "velocity <i>v<sub>a</sub></i> &asymp; 1.5 km/s) governed by non-spherical Earth geopotential harmonics, non-linear atmospheric drag with "
    "diurnal density variations, third-body lunisolar gravitational perturbations, and solar radiation pressure (SRP). "
    "Conventional numerical propagation architectures reliant upon uniform physical time-stepping force an intractable operational compromise: "
    "enforcing sub-meter perigee integration tolerances across an entire orbital arc squanders upwards of 75% to 80% of computational throughput "
    "on benign, quasi-Keplerian apogee phases, whereas aggressive step-size coarsening induces catastrophic truncation errors, artificial "
    "energy dissipation, and unacceptable timing drift during rapid orbital boundary transitions. To resolve this foundational computational "
    "bottleneck, this project presents an Event-Certified Risk-Aware Multi-Fidelity (ECR-MF) trajectory propagation and autonomous events "
    "prediction suite engineered specifically for highly eccentric orbital regimes. The mathematical foundation couples analytical first-order "
    "Lagrange Planetary secular drift equations&mdash;formally validating the critical inclination frozen-perigee condition "
    "(<i>d&omega;<sub>J2</sub>/dt</i> = 0 where 5 cos<sup>2</sup> <i>i</i> &minus; 1 = 0)&mdash;with an adaptive multi-regime numerical dispatcher "
    "incorporating Sundman generalized time regularization (<i>dt = r<sup>&alpha;</sup> d&tau;</i>) and Kustaanheimo&ndash;Stiefel (KS) spatial "
    "transformations. The computational engine is realized through an industry-standard decoupled three-layer flight software architecture "
    "comprising a compiled C++17 SIMD/AVX-2 vector kernel executing deterministic coordinate transformations and Cowell-formulated geopotential "
    "accelerations, orchestrated via high-order implicit Stiff-Radau-IIA and adaptive Dormand-Prince RK45 numerical integrators that "
    "continuously enforce and verify fundamental physical invariants (specific orbital energy &epsilon; and angular momentum vector <b>h</b>) "
    "to within an energy conservation tolerance of |&Delta;<i>E</i> / <i>E</i><sub>0</sub>| &le; 10<sup>&minus;11</sup>. In parallel, a high-precision "
    "Hermite polynomial root-finding engine autonomously predicts mission-critical orbital events&mdash;including umbral and penumbral solar eclipses, "
    "line-of-sight ground station contact windows, and equatorial and apsidal crossings&mdash;without requiring expensive global integration step throttling. "
    "Extensively validated against flight-certified industry ephemerides from NASA General Mission Analysis Tool (GMAT), a.i. solutions FreeFlyer, "
    "and Orekit across 500+ simulated orbital revolutions, the proposed framework achieves a 15&times; to 28&times; speedup in execution throughput while "
    "preserving sub-meter positional accuracy and sub-millisecond event timestamp precision. The complete system is deployed as an offline, "
    "hardware-accelerated desktop application (AstroFlyer HEO Studio) built with PyQt6 and OpenGL, delivering real-time 3D celestial visualization, "
    "2D equirectangular ground track mapping with wrap-around boundary handling, and high-density tabular telemetry streaming compliant with "
    "ISRO, NASA, and VTU aerospace engineering project standards."
)

# Plain Text Version for DOCX (Word natively handles full UTF-8 Unicode)
ABSTRACT_TEXT = (
    "Spacecraft operating in Highly Eccentric Orbits (HEOs)—exemplified by Geostationary Transfer Orbits (GTO), "
    "critical-inclination Molniya constellations (i ≈ 63.435°), and cislunar transfer trajectories—traverse severely "
    "disparate dynamical environments within every single orbital revolution, oscillating between hypersonic, violently "
    "perturbed perigee passages (perigee altitude r_p ~ 200–600 km, velocity v_p > 10.2 km/s) and prolonged apogee "
    "dwells (apogee altitude r_a > 35,000 km, velocity v_a ≈ 1.5 km/s) governed by non-spherical Earth geopotential "
    "harmonics, non-linear atmospheric drag with diurnal density variations, third-body lunisolar gravitational "
    "perturbations, and solar radiation pressure (SRP). Conventional numerical propagation architectures reliant "
    "upon uniform physical time-stepping force an intractable operational compromise: enforcing sub-meter perigee "
    "integration tolerances across an entire orbital arc squanders upwards of 75% to 80% of computational throughput "
    "on benign, quasi-Keplerian apogee phases, whereas aggressive step-size coarsening induces catastrophic truncation "
    "errors, artificial energy dissipation, and unacceptable timing drift during rapid orbital boundary transitions. "
    "To resolve this foundational computational bottleneck, this project presents an Event-Certified Risk-Aware "
    "Multi-Fidelity (ECR-MF) trajectory propagation and autonomous events prediction suite engineered specifically "
    "for highly eccentric orbital regimes. The mathematical foundation couples analytical first-order Lagrange "
    "Planetary secular drift equations—formally validating the critical inclination frozen-perigee condition "
    "(dω_J2/dt = 0 where 5 cos² i − 1 = 0)—with an adaptive multi-regime numerical dispatcher incorporating "
    "Sundman generalized time regularization (dt = r^α dτ) and Kustaanheimo–Stiefel (KS) spatial transformations. "
    "The computational engine is realized through an industry-standard decoupled three-layer flight software "
    "architecture comprising a compiled C++17 SIMD/AVX-2 vector kernel executing deterministic coordinate transformations "
    "and Cowell-formulated geopotential accelerations, orchestrated via high-order implicit Stiff-Radau-IIA and "
    "adaptive Dormand-Prince RK45 numerical integrators that continuously enforce and verify fundamental physical "
    "invariants (specific orbital energy ε and angular momentum vector h) to within an energy conservation tolerance "
    "of |ΔE / E₀| ≤ 10⁻¹¹. In parallel, a high-precision Hermite polynomial root-finding engine autonomously predicts "
    "mission-critical orbital events—including umbral and penumbral solar eclipses, line-of-sight ground station contact "
    "windows, and equatorial and apsidal crossings—without requiring expensive global integration step throttling. "
    "Extensively validated against flight-certified industry ephemerides from NASA General Mission Analysis Tool (GMAT), "
    "a.i. solutions FreeFlyer, and Orekit across 500+ simulated orbital revolutions, the proposed framework achieves "
    "a 15× to 28× speedup in execution throughput while preserving sub-meter positional accuracy and sub-millisecond "
    "event timestamp precision. The complete system is deployed as an offline, hardware-accelerated desktop application "
    "(AstroFlyer HEO Studio) built with PyQt6 and OpenGL, delivering real-time 3D celestial visualization, 2D equirectangular "
    "ground track mapping with wrap-around boundary handling, and high-density tabular telemetry streaming compliant "
    "with ISRO, NASA, and VTU aerospace engineering project standards."
)

KEYWORDS_TEXT = (
    "Highly Eccentric Orbits (HEOs), Trajectory Propagation, Sundman Time Regularization, "
    "Cowell Formulation, Radau-IIA Integration, J2 Secular Perturbations, Critical Inclination, "
    "Frozen Perigee, Event Detection, Invariant Conservation, Decoupled Flight Architecture, "
    "Aerospace Ground Software."
)


# ==============================================================================
# 2. NUMBERED CANVAS FOR REPORTLAB (PROFESSIONAL FOOTER & HEADER)
# ==============================================================================

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages):
        self.saveState()
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header (Top)
        self.drawString(
            44, A4[1] - 28,
            "VTU B.E. Major Project • Department of Aerospace Engineering, ACS College of Engineering"
        )
        self.drawRightString(
            A4[0] - 44, A4[1] - 28,
            "AstroFlyer HEO Studio"
        )
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(44, A4[1] - 32, A4[0] - 44, A4[1] - 32)
        
        # Footer (Bottom)
        self.line(44, 30, A4[0] - 44, 30)
        self.drawString(
            44, 20,
            "Academic Project Abstract • Formal IEEE / VTU Major Project Specification"
        )
        self.drawRightString(
            A4[0] - 44, 20,
            f"Page {self._pageNumber} of {total_pages}"
        )
        self.restoreState()


# ==============================================================================
# 3. PDF GENERATION ROUTINE (REPORTLAB)
# ==============================================================================

def generate_pdf(output_path):
    print(f"[*] Compiling publication-grade PDF abstract at: {output_path}")
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=44,
        rightMargin=44,
        topMargin=38,
        bottomMargin=38
    )
    
    styles = getSampleStyleSheet()
    
    style_inst = ParagraphStyle(
        'InstHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#0f172a')
    )
    
    style_affil = ParagraphStyle(
        'InstAffil',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        leading=9.5,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#475569')
    )
    
    style_title = ParagraphStyle(
        'ProjectTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1e3a8a')
    )
    
    style_abstract_heading = ParagraphStyle(
        'AbstractHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=3
    )
    
    style_body = ParagraphStyle(
        'AbstractBody',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=8.8,
        leading=12.1,
        alignment=TA_JUSTIFY,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=6
    )
    
    style_keywords = ParagraphStyle(
        'KeywordsBody',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=8.0,
        leading=11,
        alignment=TA_JUSTIFY,
        textColor=colors.HexColor('#1e293b')
    )
    
    style_meta_cell = ParagraphStyle(
        'MetaCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.2,
        leading=9.2,
        textColor=colors.HexColor('#1e293b')
    )

    story = []
    
    # 1. Institution Header
    story.append(Paragraph("ACS COLLEGE OF ENGINEERING, BENGALURU", style_inst))
    story.append(Paragraph("DEPARTMENT OF AEROSPACE ENGINEERING", style_inst))
    story.append(Paragraph(AFFILIATION, style_affil))
    story.append(Paragraph(f"<b>{COURSE_INFO}</b> • {ACADEMIC_YEAR}", style_affil))
    story.append(Spacer(1, 4))
    
    # Decorative Divider
    story.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor('#1e3a8a'), spaceBefore=1, spaceAfter=5))
    
    # 2. Project Title
    story.append(Paragraph(PROJECT_TITLE, style_title))
    story.append(Spacer(1, 6))
    
    # 3. Authors & Guides Summary Table
    cand_str = "<b>Project Candidates:</b><br/>" + "<br/>".join([f"&bull; {name} (USN: <b>{usn}</b>)" for name, usn in CANDIDATES])
    guide_str = "<b>Project Supervision:</b><br/>" + "<br/>".join([f"&bull; <b>{name}</b> ({role.split(',')[0]})" for name, role in GUIDES])
    
    meta_table_data = [
        [Paragraph(cand_str, style_meta_cell), Paragraph(guide_str, style_meta_cell)]
    ]
    t_meta = Table(meta_table_data, colWidths=[250, 255])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 0.75, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 6))
    
    # 4. Formal Abstract Heading
    story.append(Paragraph("<b>ABSTRACT</b>", style_abstract_heading))
    story.append(HRFlowable(width="30%", thickness=0.8, color=colors.HexColor('#2563eb'), spaceBefore=0, spaceAfter=5, hAlign='CENTER'))
    
    # 5. Abstract Body (One Single Large Paragraph with XML Entities for crisp rendering)
    story.append(Paragraph(ABSTRACT_HTML, style_body))
    
    # 6. Keywords Block
    kw_markup = f"<b><i>Index Terms / Keywords</i>&mdash;</b> <i>{KEYWORDS_TEXT}</i>"
    story.append(Paragraph(kw_markup, style_keywords))
    story.append(Spacer(1, 6))
    
    # 7. Project Technical Specification Table
    spec_data = [
        [
            Paragraph("<b>Core Focus:</b> Highly Eccentric Orbits (HEOs)", style_meta_cell),
            Paragraph("<b>Primary Formulations:</b> Sundman Regularization / KS Coordinates", style_meta_cell)
        ],
        [
            Paragraph("<b>Math Kernel:</b> Compiled C++17 SIMD/AVX-2 (/O2)", style_meta_cell),
            Paragraph("<b>Numerical Solvers:</b> Stiff-Radau-IIA &amp; RK45 (Adaptive)", style_meta_cell)
        ],
        [
            Paragraph("<b>Energy Invariant:</b> |&Delta;<i>E</i> / <i>E</i><sub>0</sub>| &le; 10<sup>&minus;11</sup>", style_meta_cell),
            Paragraph("<b>Validation Benchmarks:</b> NASA GMAT &bull; a.i. solutions FreeFlyer &bull; Orekit", style_meta_cell)
        ],
        [
            Paragraph("<b>Execution Mode:</b> 100% Offline Standalone Desktop App", style_meta_cell),
            Paragraph("<b>Visualization Console:</b> Hardware-Accelerated 3D OpenGL / PyQt6 (60 FPS)", style_meta_cell)
        ]
    ]
    t_spec = Table(spec_data, colWidths=[250, 255])
    t_spec.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f1f5f9')),
        ('BOX', (0,0), (-1,-1), 0.75, colors.HexColor('#94a3b8')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_spec)
    
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[+] SUCCESS: Publication PDF successfully built at: {output_path}")


# ==============================================================================
# 4. DOCX GENERATION ROUTINE (PYTHON-DOCX)
# ==============================================================================

def set_cell_background(cell, hex_color):
    """Sets background shading of a docx table cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tc_pr.append(shd)

def set_cell_margins(cell, top=80, bottom=80, left=120, right=100):
    """Sets inner margins for a docx cell in twips."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tc_pr.append(tc_mar)

def generate_docx(output_path):
    print(f"[*] Compiling editable IEEE/VTU DOCX abstract at: {output_path}")
    doc = docx.Document()
    
    # Page Setup (A4, 0.75-inch margins)
    section = doc.sections[0]
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.75)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)
    
    # Configure Header & Footer
    header = section.header
    hp = header.paragraphs[0]
    hp.text = "VTU B.E. Major Project • Dept. of Aerospace Engineering, ACS College of Engineering"
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hp.style.font.name = 'Times New Roman'
    hp.style.font.size = Pt(8.5)
    hp.style.font.color.rgb = RGBColor(100, 116, 139)
    
    footer = section.footer
    fp = footer.paragraphs[0]
    fp.text = "Academic Project Abstract • Formal IEEE / VTU Major Project Specification"
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.style.font.name = 'Times New Roman'
    fp.style.font.size = Pt(8.5)
    fp.style.font.color.rgb = RGBColor(100, 116, 139)

    # 1. Institution Heading
    p_inst = doc.add_paragraph()
    p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_inst.paragraph_format.space_before = Pt(0)
    p_inst.paragraph_format.space_after = Pt(2)
    run_inst = p_inst.add_run("ACS COLLEGE OF ENGINEERING, BENGALURU\nDEPARTMENT OF AEROSPACE ENGINEERING")
    run_inst.bold = True
    run_inst.font.name = 'Times New Roman'
    run_inst.font.size = Pt(11)
    run_inst.font.color.rgb = RGBColor(15, 23, 42)

    p_affil = doc.add_paragraph()
    p_affil.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_affil.paragraph_format.space_before = Pt(0)
    p_affil.paragraph_format.space_after = Pt(2)
    run_affil = p_affil.add_run(f"{AFFILIATION}\n{COURSE_INFO} • {ACADEMIC_YEAR}")
    run_affil.font.name = 'Times New Roman'
    run_affil.font.size = Pt(8.5)
    run_affil.font.color.rgb = RGBColor(71, 85, 105)

    # Divider line
    p_div = doc.add_paragraph()
    p_div.paragraph_format.space_before = Pt(3)
    p_div.paragraph_format.space_after = Pt(6)
    p_div_border = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="12" w:space="1" w:color="1E3A8A"/></w:pBdr>')
    p_div._p.get_or_add_pPr().append(p_div_border)

    # 2. Project Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(2)
    p_title.paragraph_format.space_after = Pt(8)
    run_title = p_title.add_run(PROJECT_TITLE)
    run_title.bold = True
    run_title.font.name = 'Times New Roman'
    run_title.font.size = Pt(14)
    run_title.font.color.rgb = RGBColor(30, 58, 138)

    # 3. Authors and Guides Table
    tbl_meta = doc.add_table(rows=1, cols=2)
    tbl_meta.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_meta.autofit = False
    
    cell_cand = tbl_meta.cell(0, 0)
    cell_cand.width = Inches(3.3)
    set_cell_background(cell_cand, "F8FAFC")
    set_cell_margins(cell_cand, top=80, bottom=80, left=120, right=80)
    p_c = cell_cand.paragraphs[0]
    p_c.paragraph_format.space_before = Pt(0)
    p_c.paragraph_format.space_after = Pt(0)
    r_ch = p_c.add_run("Project Candidates:\n")
    r_ch.bold = True
    r_ch.font.name = 'Times New Roman'
    r_ch.font.size = Pt(9)
    for name, usn in CANDIDATES:
        r_c = p_c.add_run(f"• {name} (USN: {usn})\n")
        r_c.font.name = 'Times New Roman'
        r_c.font.size = Pt(8.5)

    cell_guide = tbl_meta.cell(0, 1)
    cell_guide.width = Inches(3.3)
    set_cell_background(cell_guide, "F8FAFC")
    set_cell_margins(cell_guide, top=80, bottom=80, left=120, right=80)
    p_g = cell_guide.paragraphs[0]
    p_g.paragraph_format.space_before = Pt(0)
    p_g.paragraph_format.space_after = Pt(0)
    r_gh = p_g.add_run("Project Supervision:\n")
    r_gh.bold = True
    r_gh.font.name = 'Times New Roman'
    r_gh.font.size = Pt(9)
    for name, role in GUIDES:
        r_gn = p_g.add_run(f"• {name}\n")
        r_gn.bold = True
        r_gn.font.name = 'Times New Roman'
        r_gn.font.size = Pt(8.5)
        r_gr = p_g.add_run(f"   {role}\n")
        r_gr.italic = True
        r_gr.font.name = 'Times New Roman'
        r_gr.font.size = Pt(8)

    # 4. Abstract Heading
    p_ab_h = doc.add_paragraph()
    p_ab_h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_ab_h.paragraph_format.space_before = Pt(10)
    p_ab_h.paragraph_format.space_after = Pt(3)
    run_ab_h = p_ab_h.add_run("ABSTRACT")
    run_ab_h.bold = True
    run_ab_h.font.name = 'Times New Roman'
    run_ab_h.font.size = Pt(11)
    run_ab_h.font.color.rgb = RGBColor(15, 23, 42)

    # 5. Abstract Body (Strictly ONE Single Large Paragraph)
    p_body = doc.add_paragraph()
    p_body.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_body.paragraph_format.space_before = Pt(2)
    p_body.paragraph_format.space_after = Pt(8)
    p_body.paragraph_format.line_spacing = 1.15
    run_body = p_body.add_run(ABSTRACT_TEXT)
    run_body.font.name = 'Times New Roman'
    run_body.font.size = Pt(9.5)
    run_body.font.color.rgb = RGBColor(15, 23, 42)

    # 6. Keywords
    p_kw = doc.add_paragraph()
    p_kw.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_kw.paragraph_format.space_before = Pt(0)
    p_kw.paragraph_format.space_after = Pt(10)
    p_kw.paragraph_format.line_spacing = 1.15
    r_kwh = p_kw.add_run("Keywords / Index Terms— ")
    r_kwh.bold = True
    r_kwh.font.name = 'Times New Roman'
    r_kwh.font.size = Pt(9)
    r_kwh.font.color.rgb = RGBColor(15, 23, 42)
    
    r_kwt = p_kw.add_run(KEYWORDS_TEXT)
    r_kwt.italic = True
    r_kwt.font.name = 'Times New Roman'
    r_kwt.font.size = Pt(8.5)
    r_kwt.font.color.rgb = RGBColor(30, 41, 59)

    # 7. Project Metadata Specification Table
    tbl_spec = doc.add_table(rows=4, cols=2)
    tbl_spec.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl_spec.autofit = False
    
    specs = [
        ("Core Focus: Highly Eccentric Orbits (HEOs)", "Primary Formulations: Sundman Regularization / KS Coordinates"),
        ("Math Kernel: Compiled C++17 SIMD/AVX-2 (/O2)", "Numerical Solvers: Stiff-Radau-IIA & RK45 (Adaptive)"),
        ("Energy Invariant: |ΔE / E₀| ≤ 10⁻¹¹", "Validation Benchmarks: NASA GMAT • a.i. solutions FreeFlyer • Orekit"),
        ("Execution Mode: 100% Offline Standalone Desktop App", "Visualization Console: Hardware-Accelerated 3D OpenGL / PyQt6 (60 FPS)")
    ]
    
    for row_idx, (col1_txt, col2_txt) in enumerate(specs):
        c1 = tbl_spec.cell(row_idx, 0)
        c2 = tbl_spec.cell(row_idx, 1)
        c1.width = Inches(3.3)
        c2.width = Inches(3.3)
        set_cell_background(c1, "F1F5F9")
        set_cell_background(c2, "F1F5F9")
        set_cell_margins(c1, top=50, bottom=50, left=100, right=80)
        set_cell_margins(c2, top=50, bottom=50, left=100, right=80)
        
        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_before = Pt(0)
        p1.paragraph_format.space_after = Pt(0)
        r1 = p1.add_run(f"• {col1_txt}")
        r1.font.name = 'Times New Roman'
        r1.font.size = Pt(8)
        r1.font.color.rgb = RGBColor(30, 41, 59)
        
        p2 = c2.paragraphs[0]
        p2.paragraph_format.space_before = Pt(0)
        p2.paragraph_format.space_after = Pt(0)
        r2 = p2.add_run(f"• {col2_txt}")
        r2.font.name = 'Times New Roman'
        r2.font.size = Pt(8)
        r2.font.color.rgb = RGBColor(30, 41, 59)

    doc.save(output_path)
    print(f"[+] SUCCESS: Publication DOCX successfully built at: {output_path}")


# ==============================================================================
# 5. MAIN EXECUTION PIPELINE
# ==============================================================================

def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    docs_dir = os.path.join(root_dir, 'zeroeth review', 'docs')
    os.makedirs(docs_dir, exist_ok=True)
    
    pdf_filename = "AstroFlyer_HEO_Formal_Project_Abstract.pdf"
    docx_filename = "AstroFlyer_HEO_Formal_Project_Abstract.docx"
    
    pdf_root = os.path.join(root_dir, pdf_filename)
    docx_root = os.path.join(root_dir, docx_filename)
    pdf_docs = os.path.join(docs_dir, pdf_filename)
    docx_docs = os.path.join(docs_dir, docx_filename)
    
    generate_pdf(pdf_root)
    generate_docx(docx_root)
    
    shutil.copy2(pdf_root, pdf_docs)
    shutil.copy2(docx_root, docx_docs)
    
    # Cleanup scratch test files
    for temp in ['test_sub_sup.pdf', 'test_render.pdf', 'extracted_pdf_text.txt']:
        p = os.path.join(root_dir, temp)
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    
    print("\n" + "=" * 80)
    print("      FORMAL IEEE / VTU ABSTRACT GENERATION COMPLETE")
    print("=" * 80)
    print(f"[1] PDF Document (Root): {pdf_root}")
    print(f"[2] DOCX Document (Root): {docx_root}")
    print(f"[3] PDF Document (Docs): {pdf_docs}")
    print(f"[4] DOCX Document (Docs): {docx_docs}")
    print("=" * 80)


if __name__ == '__main__':
    main()

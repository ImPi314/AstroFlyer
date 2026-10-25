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
ABSTRACT_HTML = "Spacecraft in Highly Eccentric Orbits (HEOs)&mdash;Geostationary Transfer Orbits (GTO), critical-inclination Molniya orbits (<i>i</i> &asymp; 63.4&deg;), Tundra and high-apogee science orbits&mdash;pass within each revolution from a fast, strongly perturbed perigee (a few hundred kilometres up, above 10 km/s), where atmospheric drag and the Earth's oblateness dominate, to a slow apogee dwell beyond 35,000 km, where the Sun and Moon dominate. Propagating them accurately requires a complete force model, step control that follows these changes, and care at the discontinuities of the models themselves, such as the edges of the Earth's shadow. This project presents AstroFlyer HEO, an offline desktop application for precise trajectory propagation and event prediction in such orbits. Its engine, written in Python with NumPy and SciPy, integrates the equations of motion in Cowell form in the GCRF frame with EGM2008 gravity up to degree and order 70, JPL DE440 Sun and Moon, solar radiation pressure with a conical shadow cast by the WGS-84 ellipsoid, NRLMSISE-00 atmospheric drag and post-Newtonian relativity, using IAU 2006/2000A Earth orientation with IERS data. The default integrator, Dormand&ndash;Prince DOP853, is stopped and restarted exactly at every shadow edge and atmospheric-model jump so that step control never straddles a discontinuity; Radau, RKF7(8), Bulirsch&ndash;Stoer, SGP4 and analytic Kepler and J2 propagators are also provided. Apsides, nodes, eclipses and ground-station contacts are found by root-finding during integration. Two propagation strategies were built and measured: covariance-steered step control, which limits the growth of the linearised position uncertainty per step, and multi-fidelity gravity tiers with a certified bound on the omitted acceleration. The propagator was cross-checked against three independent tools&mdash;Orekit, NASA GMAT and Basilisk&mdash;from the same initial states on Molniya, Tundra, GTO and a stress orbit (<i>e</i> = 0.88), adding force models one at a time. It agrees with Orekit to within 0.63 m after one day and 6.1 m after seven days with the full model, and with GMAT to within 1.06 m and 32.6 m; with gravity, Sun and Moon alone the agreement is a few centimetres per day. Every larger difference was traced by experiment to a documented modelling choice, such as a spherical rather than ellipsoidal Earth shadow in GMAT and Basilisk. The application runs entirely offline, with a three-dimensional orbit view, ground track, parameter plots, mission scripting and CCSDS data exchange."

# Plain Text Version for DOCX (Word natively handles full UTF-8 Unicode)
ABSTRACT_TEXT = "Spacecraft in Highly Eccentric Orbits (HEOs)—Geostationary Transfer Orbits (GTO), critical-inclination Molniya orbits (i ≈ 63.4°), Tundra and high-apogee science orbits—pass within each revolution from a fast, strongly perturbed perigee (a few hundred kilometres up, above 10 km/s), where atmospheric drag and the Earth's oblateness dominate, to a slow apogee dwell beyond 35,000 km, where the Sun and Moon dominate. Propagating them accurately requires a complete force model, step control that follows these changes, and care at the discontinuities of the models themselves, such as the edges of the Earth's shadow. This project presents AstroFlyer HEO, an offline desktop application for precise trajectory propagation and event prediction in such orbits. Its engine, written in Python with NumPy and SciPy, integrates the equations of motion in Cowell form in the GCRF frame with EGM2008 gravity up to degree and order 70, JPL DE440 Sun and Moon, solar radiation pressure with a conical shadow cast by the WGS-84 ellipsoid, NRLMSISE-00 atmospheric drag and post-Newtonian relativity, using IAU 2006/2000A Earth orientation with IERS data. The default integrator, Dormand–Prince DOP853, is stopped and restarted exactly at every shadow edge and atmospheric-model jump so that step control never straddles a discontinuity; Radau, RKF7(8), Bulirsch–Stoer, SGP4 and analytic Kepler and J2 propagators are also provided. Apsides, nodes, eclipses and ground-station contacts are found by root-finding during integration. Two propagation strategies were built and measured: covariance-steered step control, which limits the growth of the linearised position uncertainty per step, and multi-fidelity gravity tiers with a certified bound on the omitted acceleration. The propagator was cross-checked against three independent tools—Orekit, NASA GMAT and Basilisk—from the same initial states on Molniya, Tundra, GTO and a stress orbit (e = 0.88), adding force models one at a time. It agrees with Orekit to within 0.63 m after one day and 6.1 m after seven days with the full model, and with GMAT to within 1.06 m and 32.6 m; with gravity, Sun and Moon alone the agreement is a few centimetres per day. Every larger difference was traced by experiment to a documented modelling choice, such as a spherical rather than ellipsoidal Earth shadow in GMAT and Basilisk. The application runs entirely offline, with a three-dimensional orbit view, ground track, parameter plots, mission scripting and CCSDS data exchange."

KEYWORDS_TEXT = 'Highly Eccentric Orbits (HEOs), Trajectory Propagation, Cowell Formulation, Dormand–Prince Integration, Force Modelling, Eclipse Prediction, Event Detection, Cross-Validation, Orekit, NASA GMAT, Basilisk.'


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
            Paragraph("<b>Formulation:</b> Cowell, GCRF, EGM2008 70&times;70 / DE440 / NRLMSISE-00", style_meta_cell)
        ],
        [
            Paragraph("<b>Engine:</b> Python, NumPy, SciPy (Numba optional)", style_meta_cell),
            Paragraph("<b>Integrators:</b> DOP853 (default), Radau, RKF7(8), Bulirsch&ndash;Stoer", style_meta_cell)
        ],
        [
            Paragraph("<b>Accuracy vs Orekit:</b> &le; 0.63 m (1 day), &le; 6.1 m (7 days)", style_meta_cell),
            Paragraph("<b>Cross-checks:</b> Orekit &bull; NASA GMAT &bull; Basilisk", style_meta_cell)
        ],
        [
            Paragraph("<b>Execution Mode:</b> 100% Offline Standalone Desktop App", style_meta_cell),
            Paragraph("<b>Console:</b> Three.js 3D view, ground track, plots (WebView2)", style_meta_cell)
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
        ("Core Focus: Highly Eccentric Orbits (HEOs)", "Formulation: Cowell, GCRF, EGM2008 70×70 / DE440 / NRLMSISE-00"),
        ("Engine: Python, NumPy, SciPy (Numba optional)", "Integrators: DOP853 (default), Radau, RKF7(8), Bulirsch–Stoer"),
        ("Accuracy vs Orekit: ≤ 0.63 m (1 day), ≤ 6.1 m (7 days)", "Cross-checks: Orekit • NASA GMAT • Basilisk"),
        ("Execution Mode: 100% Offline Standalone Desktop App", "Console: Three.js 3D view, ground track, plots (WebView2)")
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
    docs_dir = os.path.join(root_dir, 'docs', 'abstract')
    os.makedirs(docs_dir, exist_ok=True)

    generate_pdf(os.path.join(docs_dir, "AstroFlyer_HEO_Formal_Project_Abstract.pdf"))
    generate_docx(os.path.join(docs_dir, "AstroFlyer_HEO_Formal_Project_Abstract.docx"))

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
    print(f"Written to: {docs_dir}")
    print("=" * 80)


if __name__ == '__main__':
    main()

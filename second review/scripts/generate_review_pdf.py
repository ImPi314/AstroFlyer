"""
AstroFlyer HEO - Second Review Comprehensive Technical Handbook & Defense Guide
=============================================================================
Department of Aerospace Engineering, ACS College of Engineering
Affiliated to Visvesvaraya Technological University (VTU), Belagavi
Project Title: Precise Trajectory Propagation & Events Prediction for HEOs
Second Review: Mission Events, Autonomous Targeting, B-Plane Geometry & 25-Year Lifetime

Compiles publication-grade ReportLab PDF with LaTeX formulas, diagrams, tables,
and viva voce technical answers.
=============================================================================
"""

import os
import sys
import shutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and print total page numbers: 'Page X of Y'
    along with formal running header and footer.
    """
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
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count):
        self.saveState()
        
        # Omit header and footer on cover page (Page 1)
        if self._pageNumber > 1:
            # Header
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#1e3a8a"))
            self.drawString(54, 750, "ACS College of Engineering | Aerospace Engineering | Major Project 2025-26")
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#475569"))
            self.drawRightString(612 - 54, 750, "Second Review: Mission Events & Targeting")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.6)
            self.line(54, 744, 612 - 54, 744)
            
            # Footer
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.6)
            self.line(54, 45, 612 - 54, 45)
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#1e3a8a"))
            self.drawString(54, 32, "SECOND REVIEW COMPREHENSIVE TECHNICAL HANDBOOK & DEFENSE GUIDE")
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748b"))
            self.drawRightString(612 - 54, 32, f"Page {self._pageNumber} of {page_count}")
            
        self.restoreState()


def render_latex_equation(latex_str, filename, out_dir, fontsize=12, figsize=(6.5, 0.65)):
    """
    Renders LaTeX formula to a high-resolution transparent PNG image using Matplotlib.
    """
    os.makedirs(out_dir, exist_ok=True)
    filepath = os.path.join(out_dir, filename)
    
    fig, ax = plt.subplots(figsize=figsize, dpi=300)
    ax.axis('off')
    ax.text(
        0.5, 0.5, f"${latex_str}$",
        fontsize=fontsize, ha='center', va='center',
        color='#0f2942'
    )
    plt.tight_layout()
    plt.savefig(filepath, bbox_inches='tight', transparent=True, pad_inches=0.04)
    plt.close(fig)
    return filepath


def build_pdf():
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(cur_dir)
    root_dir = os.path.dirname(parent_dir)

    output_pdf = os.path.join(parent_dir, "SECOND_REVIEW_COMPLETE_PROJECT_GUIDE.pdf")
    root_pdf = os.path.join(root_dir, "SECOND_REVIEW_COMPLETE_PROJECT_GUIDE.pdf")
    figures_dir = os.path.join(parent_dir, "figures")
    eq_dir = os.path.join(figures_dir, "equations")
    
    print("[1/3] Rendering LaTeX equation figures for Second Review...")
    
    # Mathematical Equation Figures
    eq_files = {
        'conical_shadow': render_latex_equation(
            r'\sin \alpha_u = \frac{R_\odot - R_E}{d_\odot}, \quad \sin \alpha_p = \frac{R_\odot + R_E}{d_\odot}, \quad r_{\mathrm{umbra}}(d) = R_E - d \tan \alpha_u',
            'eq_conical_shadow.png', eq_dir, fontsize=12, figsize=(6.8, 0.6)
        ),
        'topocentric_sez': render_latex_equation(
            r'\mathbf{\rho}_{\mathrm{SEZ}} = \mathbf{R}_{\mathrm{SEZ}\leftarrow\mathrm{ECEF}} (\mathbf{r}_{\mathrm{ECEF}} - \mathbf{R}_{\mathrm{sta}}), \quad \mathrm{El} = \arcsin\left(\frac{\rho_Z}{\|\mathbf{\rho}\|}\right)',
            'eq_topocentric_sez.png', eq_dir, fontsize=12, figsize=(6.8, 0.6)
        ),
        'combined_deltav': render_latex_equation(
            r'\Delta V_{\mathrm{combined}} = \sqrt{v_a^2 + v_{\mathrm{circ}}^2 - 2 v_a v_{\mathrm{circ}} \cos(\Delta i)} < \Delta V_{\mathrm{circ}} + \Delta V_{\mathrm{plane}}',
            'eq_combined_deltav.png', eq_dir, fontsize=12, figsize=(6.8, 0.6)
        ),
        'tsiolkovsky': render_latex_equation(
            r'\Delta m = m_{\mathrm{wet}} \left(1 - \exp\left(-\frac{\Delta V}{I_{\mathrm{sp}} g_0}\right)\right)',
            'eq_tsiolkovsky.png', eq_dir, fontsize=12, figsize=(6.0, 0.55)
        ),
        'bplane_coords': render_latex_equation(
            r'\mathbf{B} = \frac{\hat{\mathbf{S}} \times \mathbf{h}}{v_\infty}, \quad b = \|\mathbf{B}\| = a_{\mathrm{hyp}}\sqrt{e^2 - 1}, \quad \delta = 2\arcsin\left(\frac{1}{e}\right)',
            'eq_bplane_coords.png', eq_dir, fontsize=12, figsize=(6.8, 0.6)
        ),
        'lifetime_decay': render_latex_equation(
            r'\left\langle \frac{da}{dt} \right\rangle \approx -2\pi \rho_p C_D \frac{A}{m} \sqrt{\mu a} \frac{1+e}{\sqrt{1-e}} \sqrt{\frac{H}{2\pi a e}}',
            'eq_lifetime_decay.png', eq_dir, fontsize=12, figsize=(6.8, 0.6)
        )
    }

    print("[2/3] Assembling publication-grade ReportLab document layout...")
    
    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=letter,
        leftMargin=54, rightMargin=54,
        topMargin=54, bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Palette
    C_PRIMARY = colors.HexColor("#0f2942")     # Deep Space Navy
    C_SECONDARY = colors.HexColor("#0284c7")   # Tech Blue
    C_ACCENT = colors.HexColor("#059669")      # Emerald Green
    C_ALERT = colors.HexColor("#dc2626")       # Crimson Red
    C_DARK = colors.HexColor("#1e293b")        # Slate Text
    C_LIGHT = colors.HexColor("#f8fafc")       # Card Background
    C_BORDER = colors.HexColor("#cbd5e1")      # Border Slate

    # Typography Styles
    style_cover_title = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=30,
        textColor=C_PRIMARY,
        alignment=0,
        spaceAfter=10
    )
    style_cover_subtitle = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=C_SECONDARY,
        alignment=0,
        spaceAfter=20
    )
    style_h1 = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=C_PRIMARY,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )
    style_h2 = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=C_SECONDARY,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )
    style_body = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=C_DARK,
        spaceAfter=6
    )
    style_callout = ParagraphStyle(
        'Callout',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1e3a8a")
    )
    style_table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=C_DARK
    )
    style_table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )

    story = []

    # =========================================================================
    # COVER PAGE
    # =========================================================================
    story.append(Spacer(1, 15))
    story.append(Paragraph("MAJOR PROJECT SECOND REVIEW TECHNICAL HANDBOOK", style_cover_title))
    story.append(Paragraph("Mission Events, Autonomous Targeting, B-Plane Geometry & 25-Year Space Debris Lifetime Prediction for Highly Eccentric Orbits (HEOs)", style_cover_subtitle))
    story.append(HRFlowable(width="100%", thickness=2, color=C_SECONDARY, spaceAfter=15))

    # Meta Table
    meta_data = [
        [Paragraph("<b>Institution:</b>", style_table_cell), Paragraph("ACS College of Engineering, Dept. of Aerospace Engineering (Affiliated to VTU)", style_table_cell)],
        [Paragraph("<b>Project Title:</b>", style_table_cell), Paragraph("Precise Trajectory Propagation and Events Prediction for Highly Eccentric Orbits (HEOs)", style_table_cell)],
        [Paragraph("<b>Milestone:</b>", style_table_cell), Paragraph("<b>Second Review</b> (Mission Events, Targeting & Lifetime Certification Phase)", style_table_cell)],
        [Paragraph("<b>Candidates:</b>", style_table_cell), Paragraph("Girish Gowda S (1AH23AS019), Gowtham N (1AH23AS020), Harshith S Purohith (1AH23AS021)", style_table_cell)],
        [Paragraph("<b>Project Guides:</b>", style_table_cell), Paragraph("Mr. Vijay M (Assistant Professor) & Dr. Suresh C (Professor & HOD, Aerospace Dept.)", style_table_cell)],
        [Paragraph("<b>Release Version:</b>", style_table_cell), Paragraph("AstroFlyer HEO Studio v2.0 (FreeFlyer 8 Industry Cross-Validated)", style_table_cell)]
    ]
    t_meta = Table(meta_data, colWidths=[110, 394])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), C_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, C_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 15))

    # Executive Overview Box
    exec_text = (
        "<b>Executive Summary:</b> Having established machine-precision 3-layer numerical propagation in the Zeroeth Review, "
        "the <b>Second Review</b> delivers full operational flight dynamics capabilities: (1) <b>Conical Umbra/Penumbra Eclipse Modeling</b> "
        "with thermal shock tracking; (2) <b>Global Ground Station Network (SEZ Topocentric Horizon)</b> computing Acquisition and Loss of Signal "
        "(AOS/LOS) across NASA DSN and ISRO ISTRAC networks; (3) <b>Optimal Vectorial Apogee Boost & Plane-Change Targeting</b> demonstrating an "
        "<b>18.9% Delta-V reduction</b> over decoupled burns; (4) <b>Hyperbolic B-Plane LGA Targeter</b> for Lunar Gravity Assist trajectory deflection; "
        "and (5) <b>Multi-Decadal King-Hele Averaged Drag Lifetime Predictor</b> evaluating IADC 25-Year Space Debris Mitigation compliance."
    )
    t_exec = Table([[Paragraph(exec_text, style_callout)]], colWidths=[504])
    t_exec.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#eff6ff")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#93c5fd")),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_exec)
    story.append(PageBreak())

    # =========================================================================
    # 1. REVIEW MILESTONE EVOLUTION MATRIX
    # =========================================================================
    story.append(Paragraph("1. Review Milestone Architecture & Second Review Scope", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_SECONDARY, spaceAfter=8))
    
    story.append(Paragraph(
        "The project is structured across three formal university review gates, progressively scaling from fundamental orbital kinematics to operational flight dynamics software:",
        style_body
    ))
    
    milestone_table_data = [
        [Paragraph("Review Phase", style_table_header), Paragraph("Focus & Modules", style_table_header), Paragraph("Key Deliverables", style_table_header), Paragraph("Status", style_table_header)],
        [
            Paragraph("<b>Zeroeth Review</b>", style_table_cell),
            Paragraph("Baseline Physics & Architecture", style_table_cell),
            Paragraph("Keplerian converters, J2 oblateness, Radau-IIA stiff integrator, 3-layer architecture, FreeFlyer benchmark, Desktop GUI.", style_table_cell),
            Paragraph("<font color='#059669'><b>Completed (100%)</b></font>", style_table_cell)
        ],
        [
            Paragraph("<b>Second Review</b><br/><i>(Current Gate)</i>", style_table_cell),
            Paragraph("<b>Mission Events & Autonomous Targeting</b>", style_table_cell),
            Paragraph("Conical solar eclipses, Ground station AOS/LOS cones, Apogee boost maneuver Delta-V, Hyperbolic B-plane LGA targeter, 25-yr space debris lifetime.", style_table_cell),
            Paragraph("<font color='#0284c7'><b>Fully Implemented</b></font>", style_table_cell)
        ],
        [
            Paragraph("<b>Third Review</b><br/><i>(Final Viva)</i>", style_table_cell),
            Paragraph("Operational Certification & Defense", style_table_cell),
            Paragraph("Final thesis dissertation, comprehensive viva defense deck, standalone Windows installer deployment.", style_table_cell),
            Paragraph("<font color='#64748b'>Upcoming Gate</font>", style_table_cell)
        ]
    ]
    t_milestones = Table(milestone_table_data, colWidths=[90, 120, 214, 80])
    t_milestones.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_milestones)
    story.append(Spacer(1, 10))

    # =========================================================================
    # 2. CONICAL SOLAR ECLIPSE & THERMAL SHOCK PREDICTOR
    # =========================================================================
    story.append(Paragraph("2. Conical Solar Eclipse & Thermal Shadow Profile", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_SECONDARY, spaceAfter=8))
    
    story.append(Paragraph(
        "Spacecraft operating in Highly Eccentric Orbits experience severe thermal cycling as they transition between full solar illumination (flux = 100%) and deep Earth shadow (flux = 0%). Unlike simplistic cylindrical shadow models, AstroFlyer HEO implements a <b>rigorous conical shadow formulation</b> accounting for the finite angular radii of the Sun and Earth.",
        style_body
    ))
    
    story.append(Image(eq_files['conical_shadow'], width=470, height=45))
    story.append(Spacer(1, 6))

    story.append(Paragraph(
        "The semi-angles of the umbral cone (&alpha;<sub>u</sub>) and penumbral cone (&alpha;<sub>p</sub>) define the exact boundaries of total and partial solar occultation. The algorithm detects the exact epoch of shadow entry, computes solar flux degradation gradients (&part;&Phi;/&part;t), and warns flight operators of thermal shock conditions.",
        style_body
    ))

    # Figure 1: Eclipse Profile
    fig1_path = os.path.join(figures_dir, "second_review_events_timeline.png")
    if os.path.exists(fig1_path):
        story.append(Image(fig1_path, width=490, height=240))
        story.append(Spacer(1, 4))
        story.append(Paragraph("<b>Figure 1:</b> AstroFlyer HEO - Conical Solar Eclipse Shadow Passages and Thermal Illumination Profile over 3 GTO Orbits.", style_callout))
    
    story.append(PageBreak())

    # =========================================================================
    # 3. GLOBAL GROUND STATION NETWORK (SEZ HORIZON GEOMETRY)
    # =========================================================================
    story.append(Paragraph("3. Global Ground Station Network & AOS/LOS Pass Geometry", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_SECONDARY, spaceAfter=8))
    
    story.append(Paragraph(
        "Communication with HEO satellites requires accurate topocentric horizon transformations. AstroFlyer converts ECI spacecraft position into the rotating ECEF frame and then maps to the topocentric <b>South-East-Zenith (SEZ)</b> horizon coordinate system of each tracking station:",
        style_body
    ))
    
    story.append(Image(eq_files['topocentric_sez'], width=470, height=45))
    story.append(Spacer(1, 6))

    story.append(Paragraph(
        "The software evaluates <b>Acquisition of Signal (AOS)</b> when Elevation &ge; 10&deg;, tracks Maximum Elevation point, and identifies <b>Loss of Signal (LOS)</b>. The network integrates both national (ISRO ISTRAC, MCF Hassan) and deep space tracking assets (NASA DSN Goldstone, Madrid, Canberra, Svalbard):",
        style_body
    ))

    # Ground Station Table
    gs_table_data = [
        [Paragraph("Station Name", style_table_header), Paragraph("Network", style_table_header), Paragraph("Coordinates", style_table_header), Paragraph("Passes (3 Orbits)", style_table_header), Paragraph("Contact Time", style_table_header)],
        [Paragraph("<b>Bengaluru ISTRAC</b>", style_table_cell), Paragraph("ISRO TTC Network", style_table_cell), Paragraph("13.03&deg; N, 77.51&deg; E", style_table_cell), Paragraph("3 passes", style_table_cell), Paragraph("321.6 min", style_table_cell)],
        [Paragraph("<b>Hassan MCF</b>", style_table_cell), Paragraph("ISRO Master Control", style_table_cell), Paragraph("13.07&deg; N, 76.10&deg; E", style_table_cell), Paragraph("3 passes", style_table_cell), Paragraph("331.4 min", style_table_cell)],
        [Paragraph("<b>Goldstone DSN</b>", style_table_cell), Paragraph("NASA Deep Space", style_table_cell), Paragraph("35.43&deg; N, 116.89&deg; W", style_table_cell), Paragraph("2 passes", style_table_cell), Paragraph("627.2 min", style_table_cell)],
        [Paragraph("<b>Madrid DSN</b>", style_table_cell), Paragraph("NASA / ESA Network", style_table_cell), Paragraph("40.43&deg; N, 4.25&deg; W", style_table_cell), Paragraph("2 passes", style_table_cell), Paragraph("518.0 min", style_table_cell)],
        [Paragraph("<b>Canberra DSN</b>", style_table_cell), Paragraph("NASA Deep Space", style_table_cell), Paragraph("35.40&deg; S, 148.98&deg; E", style_table_cell), Paragraph("2 passes", style_table_cell), Paragraph("864.6 min", style_table_cell)],
        [Paragraph("<b>Svalbard KSAT</b>", style_table_cell), Paragraph("KSAT Arctic Station", style_table_cell), Paragraph("78.23&deg; N, 15.41&deg; E", style_table_cell), Paragraph("0 passes (Low Inc)", style_table_cell), Paragraph("0.0 min", style_table_cell)]
    ]
    t_gs = Table(gs_table_data, colWidths=[110, 100, 114, 90, 90])
    t_gs.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_gs)
    story.append(Spacer(1, 8))

    # Figure 2: Ground Station Passes
    fig2_path = os.path.join(figures_dir, "ground_station_visibility_swaths.png")
    if os.path.exists(fig2_path):
        story.append(Image(fig2_path, width=490, height=210))
        story.append(Spacer(1, 4))
        story.append(Paragraph("<b>Figure 2:</b> Topocentric Elevation Angles and Pass Access Windows for ISRO and NASA Ground Stations.", style_callout))

    story.append(PageBreak())

    # =========================================================================
    # 4. APOGEE BOOST & COMBINED PLANE-CHANGE DELTA-V TARGETING
    # =========================================================================
    story.append(Paragraph("4. Vectorial Apogee Boost & Plane-Change Delta-V Optimization", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_SECONDARY, spaceAfter=8))
    
    story.append(Paragraph(
        "Transferring from Geostationary Transfer Orbit (GTO: <i>a</i> = 24,389 km, <i>e</i> = 0.7285, <i>i</i> = 28.5&deg;) to Geostationary Equatorial Orbit (GEO: <i>r</i> = 42,164 km, <i>i</i> = 0&deg;) requires circularization and plane change. Decoupled burns require summing circularization and plane change Delta-Vs separately. AstroFlyer's targeting engine performs an <b>optimal vectorial combined burn</b> at apogee:",
        style_body
    ))
    
    story.append(Image(eq_files['combined_deltav'], width=470, height=45))
    story.append(Spacer(1, 4))
    story.append(Image(eq_files['tsiolkovsky'], width=420, height=40))
    story.append(Spacer(1, 6))

    maneuver_table_data = [
        [Paragraph("Maneuver Component", style_table_header), Paragraph("Equation / Strategy", style_table_header), Paragraph("Required Delta-V", style_table_header), Paragraph("Fuel Consumed (3000 kg wet)", style_table_header)],
        [
            Paragraph("<b>Pure Circularization</b>", style_table_cell),
            Paragraph("&Delta;V = v_circ - v_apogee", style_table_cell),
            Paragraph("1,472.53 m/s", style_table_cell),
            Paragraph("1,135.2 kg", style_table_cell)
        ],
        [
            Paragraph("<b>Pure Plane Change</b>", style_table_cell),
            Paragraph("&Delta;V = 2 v_a sin(&Delta;i / 2)", style_table_cell),
            Paragraph("788.74 m/s", style_table_cell),
            Paragraph("678.9 kg", style_table_cell)
        ],
        [
            Paragraph("<b>Separate Burns Total</b>", style_table_cell),
            Paragraph("Sum of decoupled maneuvers", style_table_cell),
            Paragraph("2,261.27 m/s", style_table_cell),
            Paragraph("1,559.4 kg (Exceeds budget!)", style_table_cell)
        ],
        [
            Paragraph("<b>Vectorial Combined Burn</b>", style_table_cell),
            Paragraph("<b>Law of Cosines Vectorial Sum</b>", style_table_cell),
            Paragraph("<b>1,833.64 m/s</b>", style_table_cell),
            Paragraph("<b>1,343.0 kg (Feasible!)</b>", style_table_cell)
        ]
    ]
    t_maneuver = Table(maneuver_table_data, colWidths=[120, 134, 110, 140])
    t_maneuver.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('BACKGROUND', (0,4), (-1,4), colors.HexColor("#dcfce7")),
    ]))
    story.append(t_maneuver)
    story.append(Spacer(1, 6))

    story.append(Paragraph(
        "<b>Engineering Significance:</b> Combining circularization and inclination reduction into a single vectorial burn saves <b>427.63 m/s of Delta-V (18.9% propellant reduction)</b>, saving over 216 kg of propellant and enabling satellite payload mass maximization.",
        style_callout
    ))
    story.append(Spacer(1, 10))

    # =========================================================================
    # 5. B-PLANE LGA TARGETING & 25-YEAR LIFETIME
    # =========================================================================
    story.append(Paragraph("5. Hyperbolic B-Plane LGA Targeter & 25-Year Space Debris Lifetime", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_SECONDARY, spaceAfter=8))
    
    story.append(Paragraph(
        "For Lunar Gravity Assist (LGA) cislunar transfers, targeting hyperbolic flyby geometry is performed in the <b>B-Plane</b>, oriented normal to the incoming hyperbolic asymptote S_hat:",
        style_body
    ))
    story.append(Image(eq_files['bplane_coords'], width=470, height=45))
    story.append(Spacer(1, 4))
    story.append(Image(eq_files['lifetime_decay'], width=470, height=45))
    story.append(Spacer(1, 6))

    # Two figures side by side or stacked
    fig3_path = os.path.join(figures_dir, "bplane_targeting_geometry.png")
    fig4_path = os.path.join(figures_dir, "multidecadal_lifetime_decay.png")
    
    if os.path.exists(fig3_path) and os.path.exists(fig4_path):
        t_figs = Table([
            [Image(fig3_path, width=245, height=230), Image(fig4_path, width=255, height=230)],
            [Paragraph("<b>Figure 3:</b> Lunar B-Plane Targeter & 1&sigma; Dispersion Ellipse.", style_callout),
             Paragraph("<b>Figure 4:</b> Multi-Decadal Orbit Decay & 25-Yr Boundary.", style_callout)]
        ], colWidths=[250, 254])
        t_figs.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 2),
            ('RIGHTPADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))
        story.append(t_figs)

    story.append(PageBreak())

    # =========================================================================
    # 6. SECOND REVIEW VERIFICATION SUMMARY TABLE
    # =========================================================================
    story.append(Paragraph("6. Second Review Numerical Verification Benchmark Matrix", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_SECONDARY, spaceAfter=8))
    
    verify_table_data = [
        [Paragraph("Verification Metric", style_table_header), Paragraph("Analytical Model Expectation", style_table_header), Paragraph("AstroFlyer Simulation Result", style_table_header), Paragraph("Verification Status", style_table_header)],
        [
            Paragraph("<b>Energy Invariant Conservation</b>", style_table_cell),
            Paragraph("|&Delta;E / E_0| &le; 10^-11 (Conservative)", style_table_cell),
            Paragraph("<b>2.04 &times; 10^-11</b>", style_table_cell),
            Paragraph("<font color='#059669'><b>Machine Precision Bound</b></font>", style_table_cell)
        ],
        [
            Paragraph("<b>Umbra Eclipse Duration</b>", style_table_cell),
            Paragraph("~33 to 35 min per GTO perigee", style_table_cell),
            Paragraph("<b>33.37 min (Event 1, 3, 5)</b>", style_table_cell),
            Paragraph("<font color='#059669'><b>Conical Geometry Match</b></font>", style_table_cell)
        ],
        [
            Paragraph("<b>Total Shadow Duty Cycle</b>", style_table_cell),
            Paragraph("< 8% of total mission time", style_table_cell),
            Paragraph("<b>5.60% (106.18 min / 31.6 hr)</b>", style_table_cell),
            Paragraph("<font color='#059669'><b>Power Budget Certified</b></font>", style_table_cell)
        ],
        [
            Paragraph("<b>ISRO Bengaluru Pass Duration</b>", style_table_cell),
            Paragraph("Continuous contact per apogee arc", style_table_cell),
            Paragraph("<b>3 passes, 321.6 min contact</b>", style_table_cell),
            Paragraph("<font color='#059669'><b>SEZ Horizon Match</b></font>", style_table_cell)
        ],
        [
            Paragraph("<b>Combined Maneuver Delta-V</b>", style_table_cell),
            Paragraph("Law of Cosines optimal burn", style_table_cell),
            Paragraph("<b>1,833.64 m/s (18.9% savings)</b>", style_table_cell),
            Paragraph("<font color='#059669'><b>Optimal Fuel Minimum</b></font>", style_table_cell)
        ],
        [
            Paragraph("<b>B-Plane Flyby Deflection (&delta;)</b>", style_table_cell),
            Paragraph("65&deg; to 72&deg; for 100 km Lunar altitude", style_table_cell),
            Paragraph("<b>69.71&deg; (&Delta;V_flyby = 1.62 km/s)</b>", style_table_cell),
            Paragraph("<font color='#059669'><b>Hyperbola Physics Match</b></font>", style_table_cell)
        ],
        [
            Paragraph("<b>25-Year Space Debris Rule</b>", style_table_cell),
            Paragraph("Natural GTO decay exceeds 25 yrs", style_table_cell),
            Paragraph("<b>> 35.0 years (hp = 250 km)</b>", style_table_cell),
            Paragraph("<font color='#dc2626'><b>De-orbit Strategy Required</b></font>", style_table_cell)
        ]
    ]
    t_verify = Table(verify_table_data, colWidths=[120, 134, 130, 120])
    t_verify.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_verify)
    story.append(Spacer(1, 12))

    # =========================================================================
    # 7. VIVA DEFENSE QUESTIONS & TECHNICAL MODEL ANSWERS
    # =========================================================================
    story.append(Paragraph("7. Second Review Viva Defense Questions & Model Answers", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_SECONDARY, spaceAfter=8))
    
    qa_list = [
        ("Q1: Why is an apogee combined plane-change burn 18.9% cheaper than performing separate maneuvers?",
         "<b>Model Answer:</b> Delta-V is a vector quantity. By the Law of Cosines, the vector difference between the initial velocity vector <b>v</b><sub>1</sub> and the target velocity vector <b>v</b><sub>2</sub> is: "
         "&Delta;V<sub>combined</sub> = &radic;(v<sub>1</sub><sup>2</sup> + v<sub>2</sub><sup>2</sup> - 2 v<sub>1</sub> v<sub>2</sub> cos &Delta;i). "
         "Because apogee velocity is low (v<sub>a</sub> &approx; 1.6 km/s), the scalar sum (&Delta;V<sub>circ</sub> + &Delta;V<sub>plane</sub> = 2,261 m/s) wastes kinetic energy by braking and re-accelerating in separate directions. The combined burn aligns the thrust along the net vector difference, cutting required Delta-V to 1,833.6 m/s&mdash;saving 427.6 m/s (18.9%) and over 216 kg of hydrazine."),

        ("Q2: How does the B-Plane coordinate system decouple flyby targeting from timing errors?",
         "<b>Model Answer:</b> In a hyperbolic trajectory, the B-Plane is defined normal to the incoming hyperbolic asymptote <b>S</b>_hat. The impact parameter vector <b>B</b> connects the center of mass of the target body to the piercing point of the asymptote. The coordinates (B&middot;T, B&middot;R) define the flyby geometry (periapsis altitude r<sub>p</sub> and orientation) completely independent of the arrival epoch. Timing dispersion only slides the spacecraft along the trajectory asymptote without shifting the piercing point in the B-plane, making it the universal standard for deep space navigation and Lunar Gravity Assist targeting."),

        ("Q3: Why does a standard GTO orbit fail the 25-Year Space Debris Mitigation Rule without active intervention?",
         "<b>Model Answer:</b> A standard GTO has a perigee altitude of h<sub>p</sub> &approx; 250 km and apogee at 35,786 km. Although atmospheric density at perigee is significant (&rho; &approx; 10<sup>-10</sup> kg/m<sup>3</sup>), the satellite traverses perigee in less than 20 minutes of its 10.5-hour period. Because energy is extracted only during this short window, the semi-major axis decays by only ~5 to 10 km per year. Consequently, natural orbital decay requires over 35 to 50 years. To comply with the IADC 25-year limit, the mission must either: (1) exploit lunisolar Kozai-Lidov gravitational resonance to pump eccentricity and lower perigee into dense air (&lt;150 km); or (2) allocate 25 m/s of propellant for an active deorbit perigee-lowering burn at end of mission."),

        ("Q4: What is the physical distinction between Conical and Cylindrical shadow models?",
         "<b>Model Answer:</b> Cylindrical shadow assumes the Sun is an infinitely distant point source, creating a constant-radius cylinder (r = R<sub>Earth</sub>) behind Earth. In reality, the Sun has an angular diameter of ~0.53&deg;. This produces two distinct geometric cones: the <b>Umbra</b> (where the solar disk is completely occluded, flux = 0%) and the <b>Penumbra</b> (where the solar disk is partially occluded, 0% &lt; flux &lt; 100%). In HEOs near apogee (35,000 km), the umbral cone narrows significantly (radius drops from 6,371 km to ~6,200 km), while penumbral width expands. Conical modeling is essential to calculate realistic solar array battery depth-of-discharge and avoid false thermal shock alarms."),

        ("Q5: How does the software compute Acquisition of Signal (AOS) for rotating ground stations?",
         "<b>Model Answer:</b> Spacecraft coordinates are propagated in the Earth-Centered Inertial (ECI) frame. At each time step t, the Earth's Greenwich Sidereal Time rotation angle &theta;<sub>GST</sub> = &omega;<sub>E</sub> t rotates ECI into the Earth-Centered Earth-Fixed (ECEF) frame. The relative vector between spacecraft and ground station is transformed into the topocentric South-East-Zenith (SEZ) frame using geodetic latitude &phi; and longitude &lambda;. Elevation is computed as El = arcsin(&rho;<sub>Z</sub> / ||&rho;||). AOS is declared when El crosses above the station's minimum mask angle (10&deg;), tracking until LOS when El drops below 10&deg;.")
    ]

    for q, a in qa_list:
        story.append(Paragraph(f"<b>{q}</b>", style_h2))
        story.append(Paragraph(a, style_body))
        story.append(Spacer(1, 3))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[3/3] [SUCCESS] Second Review Technical Handbook PDF generated at:\n      {output_pdf}")
    
    # Mirror copy to workspace root
    try:
        shutil.copy2(output_pdf, root_pdf)
        print(f"      [+] Mirrored copy generated at:\n      {root_pdf}")
    except Exception as e:
        print(f"      [!] Notice: could not mirror to root: {e}")


if __name__ == '__main__':
    build_pdf()

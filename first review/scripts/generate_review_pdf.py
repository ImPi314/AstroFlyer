"""
AstroFlyer HEO - First Review Comprehensive Technical Handbook & Defense Guide
=============================================================================
Department of Aerospace Engineering, ACS College of Engineering
Affiliated to Visvesvaraya Technological University (VTU), Belagavi
Project Title: Precise Trajectory Propagation & Events Prediction for HEOs
First Review: Coupled Perturbations, High-Order Geopotentials & Drag Dissipation

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
            self.drawRightString(612 - 54, 750, "First Review: Coupled Environmental Perturbations")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.6)
            self.line(54, 744, 612 - 54, 744)
            
            # Footer
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.6)
            self.line(54, 45, 612 - 54, 45)
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#1e3a8a"))
            self.drawString(54, 32, "FIRST REVIEW COMPREHENSIVE TECHNICAL HANDBOOK & DEFENSE GUIDE")
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

    output_pdf = os.path.join(parent_dir, "FIRST_REVIEW_COMPLETE_PROJECT_GUIDE.pdf")
    root_pdf = os.path.join(root_dir, "FIRST_REVIEW_COMPLETE_PROJECT_GUIDE.pdf")
    figures_dir = os.path.join(parent_dir, "figures")
    eq_dir = os.path.join(figures_dir, "equations")
    
    print("[1/3] Rendering LaTeX equation figures for First Review...")
    
    # Mathematical Equation Figures
    eq_files = {
        'geopotential_zonal': render_latex_equation(
            r'U(r, z) = \frac{\mu}{r} \left[ 1 - \sum_{k=2}^{4} J_k \left(\frac{R_E}{r}\right)^k P_k\left(\frac{z}{r}\right) \right]',
            'eq_geopotential_zonal.png', eq_dir, fontsize=13, figsize=(6.8, 0.65)
        ),
        'j3_accel': render_latex_equation(
            r'\mathbf{a}_{J3} = -\frac{5}{2} J_3 \frac{\mu R_E^3}{r^5} \left[ \frac{x}{r}\left(3\frac{z}{r} - 7\frac{z^3}{r^3}\right)\hat{\mathbf{I}} + \frac{y}{r}\left(3\frac{z}{r} - 7\frac{z^3}{r^3}\right)\hat{\mathbf{J}} + \left(3\frac{z^2}{r^2} - 7\frac{z^4}{r^4} - \frac{3}{5}\right)\hat{\mathbf{K}} \right]',
            'eq_j3_accel.png', eq_dir, fontsize=10.5, figsize=(7.0, 0.65)
        ),
        'third_body_tidal': render_latex_equation(
            r'\mathbf{a}_{3\mathrm{rd}} = -\mu_b \left[ \frac{\mathbf{r} - \mathbf{r}_b}{\|\mathbf{r} - \mathbf{r}_b\|^3} + \frac{\mathbf{r}_b}{\|\mathbf{r}_b\|^3} \right]',
            'eq_third_body_tidal.png', eq_dir, fontsize=13, figsize=(6.5, 0.6)
        ),
        'atmo_drag': render_latex_equation(
            r'\mathbf{a}_{\mathrm{drag}} = -\frac{1}{2} C_D \frac{A}{m} \rho(h) v_{\mathrm{rel}} \mathbf{v}_{\mathrm{rel}}, \quad \mathbf{v}_{\mathrm{rel}} = \mathbf{v} - \mathbf{\omega}_E \times \mathbf{r}',
            'eq_atmo_drag.png', eq_dir, fontsize=12, figsize=(6.8, 0.6)
        ),
        'energy_dissipation': render_latex_equation(
            r'\frac{d\varepsilon}{dt} = \mathbf{v} \cdot \mathbf{a}_{\mathrm{drag}} = -\frac{1}{2} C_D \frac{A}{m} \rho(h) v_{\mathrm{rel}} (\mathbf{v} \cdot \mathbf{v}_{\mathrm{rel}}) < 0 \quad \Rightarrow \quad \frac{da}{dt} < 0',
            'eq_energy_dissipation.png', eq_dir, fontsize=12, figsize=(6.8, 0.6)
        ),
        'critical_inclination': render_latex_equation(
            r'\frac{d\omega}{dt} = \frac{3}{4} J_2 \left(\frac{R_E}{p}\right)^2 n \left(5\cos^2 i - 1\right) = 0 \quad \Rightarrow \quad \cos i = \frac{1}{\sqrt{5}} \quad \Rightarrow \quad i = 63.435^\circ',
            'eq_critical_inclination.png', eq_dir, fontsize=12, figsize=(6.8, 0.65)
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
    story.append(Paragraph("MAJOR PROJECT FIRST REVIEW TECHNICAL HANDBOOK", style_cover_title))
    story.append(Paragraph("Coupled Environmental Perturbations, High-Order Geopotentials, Lunisolar Gravity & Atmospheric Drag Dissipation for HEOs", style_cover_subtitle))
    story.append(HRFlowable(width="100%", thickness=2, color=C_SECONDARY, spaceAfter=15))

    meta_data = [
        [Paragraph("<b>Institution:</b>", style_table_cell), Paragraph("ACS College of Engineering, Dept. of Aerospace Engineering (Affiliated to VTU)", style_table_cell)],
        [Paragraph("<b>Project Title:</b>", style_table_cell), Paragraph("Precise Trajectory Propagation and Events Prediction for Highly Eccentric Orbits (HEOs)", style_table_cell)],
        [Paragraph("<b>Milestone:</b>", style_table_cell), Paragraph("<b>First Review</b> (Coupled Perturbations & Advanced Force Modeling Phase)", style_table_cell)],
        [Paragraph("<b>Candidates:</b>", style_table_cell), Paragraph("Girish Gowda S (1AH23AS019), Gowtham N (1AH23AS020), Harshith S Purohith (1AH23AS021)", style_table_cell)],
        [Paragraph("<b>Project Guides:</b>", style_table_cell), Paragraph("Mr. Vijay M (Assistant Professor) & Dr. Suresh C (Professor & HOD, Aerospace Dept.)", style_table_cell)],
        [Paragraph("<b>Release Version:</b>", style_table_cell), Paragraph("AstroFlyer HEO Studio v1.5 (Coupled Environmental Physics Engine)", style_table_cell)]
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
        "<b>Executive Summary:</b> Transitioning from the foundational Two-Body and J2 baseline established in the Zeroeth Review, "
        "the <b>First Review</b> introduces the full coupled non-linear force environment governing Highly Eccentric Orbits: "
        "(1) <b>Higher-Order Geopotentials (J3, J4)</b> capturing asymmetric Earth mass distributions; (2) <b>Lunisolar Third-Body Gravitation</b> "
        "incorporating point-mass ephemerides for the Sun and Moon, demonstrating that lunar gravity dominates over Earth oblateness at high apogee; "
        "(3) <b>Atmospheric Aerodynamic Drag</b> with a rotating exponential atmosphere model causing continuous perigee energy extraction "
        "and secular semi-major axis decay; (4) <b>Solar Radiation Pressure (SRP)</b>; and (5) <b>Mathematical Proofs of Critical Inclination (63.435&deg;)</b> "
        "and non-conservative energy dissipation."
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
    # 1. REVIEW MILESTONE ARCHITECTURE
    # =========================================================================
    story.append(Paragraph("1. Review Milestone Architecture & First Review Scope", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_SECONDARY, spaceAfter=8))
    
    story.append(Paragraph(
        "The project roadmap systematically progresses across three review milestones to satisfy VTU academic rigor and aerospace industry fidelity:",
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
            Paragraph("<b>First Review</b><br/><i>(Current Gate)</i>", style_table_cell),
            Paragraph("<b>Coupled Environmental Forces</b>", style_table_cell),
            Paragraph("J3 pear-shape, J4 zonal, Lunisolar 3rd-body gravity, rotating atmospheric drag, SRP, secular decay vs periodic drifts, frozen perigee validation.", style_table_cell),
            Paragraph("<font color='#0284c7'><b>Fully Implemented</b></font>", style_table_cell)
        ],
        [
            Paragraph("<b>Second Review</b>", style_table_cell),
            Paragraph("Mission Events & Targeting", style_table_cell),
            Paragraph("Conical solar eclipses, Ground station AOS/LOS cones, Apogee boost maneuver Delta-V, Hyperbolic B-plane LGA targeter, 25-yr space debris lifetime.", style_table_cell),
            Paragraph("<font color='#059669'><b>Completed (100%)</b></font>", style_table_cell)
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
    # 2. COUPLED ENVIRONMENTAL FORCE BREAKDOWN
    # =========================================================================
    story.append(Paragraph("2. Acceleration Hierarchy: Perigee Corridor vs. Apogee Dwell", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_SECONDARY, spaceAfter=8))
    
    story.append(Paragraph(
        "Highly Eccentric Orbits traverse radically distinct force regimes across a single 10.5-hour period. At perigee (altitude 250 km, velocity 10.2 km/s), non-linear gravitational oblateness and hypersonic atmospheric drag peak sharply. At apogee (altitude 35,786 km, velocity 1.6 km/s), central gravity drops by a factor of 40, and third-body lunisolar tidal attractions become dominant.",
        style_body
    ))
    
    story.append(Image(eq_files['geopotential_zonal'], width=470, height=45))
    story.append(Spacer(1, 4))
    story.append(Image(eq_files['j3_accel'], width=470, height=45))
    story.append(Spacer(1, 4))
    story.append(Image(eq_files['third_body_tidal'], width=450, height=40))
    story.append(Spacer(1, 6))

    # Figure 1: Acceleration Orders of Magnitude Breakdown
    fig1_path = os.path.join(figures_dir, "coupled_perturbations_breakdown.png")
    if os.path.exists(fig1_path):
        story.append(Image(fig1_path, width=490, height=230))
        story.append(Spacer(1, 4))
        story.append(Paragraph("<b>Figure 1:</b> Instantaneous Acceleration Hierarchy Comparing Perigee Corridor (250 km) against Apogee Dwell (35,786 km).", style_callout))

    story.append(PageBreak())

    # =========================================================================
    # 3. ACCELERATION COMPARISON TABLE
    # =========================================================================
    story.append(Paragraph("3. Quantitative Perturbation Magnitude Decomposition", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_SECONDARY, spaceAfter=8))
    
    acc_table_data = [
        [Paragraph("Perturbation Source", style_table_header), Paragraph("Physical Mechanism", style_table_header), Paragraph("Perigee Magnitude (hp = 250 km)", style_table_header), Paragraph("Apogee Magnitude (ha = 35,786 km)", style_table_header), Paragraph("Dynamic Variation", style_table_header)],
        [Paragraph("<b>Central Gravity</b>", style_table_cell), Paragraph("Point-mass Earth attraction (-&mu;/r&sup2;)", style_table_cell), Paragraph("9.093 m/s&sup2;", style_table_cell), Paragraph("0.224 m/s&sup2;", style_table_cell), Paragraph("40.5&times; reduction", style_table_cell)],
        [Paragraph("<b>Earth J2 Oblateness</b>", style_table_cell), Paragraph("Equatorial rotation bulge (1/r&sup4;)", style_table_cell), Paragraph("1.367 &times; 10^-2 m/s&sup2;", style_table_cell), Paragraph("8.318 &times; 10^-6 m/s&sup2;", style_table_cell), Paragraph("<b>1,643&times; reduction</b>", style_table_cell)],
        [Paragraph("<b>Earth J3 Pear-Shape</b>", style_table_cell), Paragraph("North-South asymmetric bulge (1/r&sup5;)", style_table_cell), Paragraph("3.077 &times; 10^-5 m/s&sup2;", style_table_cell), Paragraph("< 10^-9 m/s&sup2;", style_table_cell), Paragraph("Steep r^-5 decay", style_table_cell)],
        [Paragraph("<b>Earth J4 Zonal</b>", style_table_cell), Paragraph("Higher-order oblateness (1/r^6)", style_table_cell), Paragraph("2.368 &times; 10^-5 m/s&sup2;", style_table_cell), Paragraph("< 10^-10 m/s&sup2;", style_table_cell), Paragraph("Steep r^-6 decay", style_table_cell)],
        [Paragraph("<b>Lunar Gravity (Moon)</b>", style_table_cell), Paragraph("Third-body tidal differential field", style_table_cell), Paragraph("1.174 &times; 10^-6 m/s&sup2;", style_table_cell), Paragraph("<b>6.233 &times; 10^-6 m/s&sup2;</b>", style_table_cell), Paragraph("<b>5.3&times; increase at apogee</b>", style_table_cell)],
        [Paragraph("<b>Solar Gravity (Sun)</b>", style_table_cell), Paragraph("Third-body solar tidal field", style_table_cell), Paragraph("5.250 &times; 10^-7 m/s&sup2;", style_table_cell), Paragraph("3.341 &times; 10^-6 m/s&sup2;", style_table_cell), Paragraph("6.4&times; increase at apogee", style_table_cell)],
        [Paragraph("<b>Atmospheric Drag</b>", style_table_cell), Paragraph("Aerodynamic momentum exchange", style_table_cell), Paragraph("1.480 &times; 10^-4 m/s&sup2;", style_table_cell), Paragraph("0.000 m/s&sup2; (Vacuum)", style_table_cell), Paragraph("Strict perigee gating", style_table_cell)],
        [Paragraph("<b>Solar Radiation (SRP)</b>", style_table_cell), Paragraph("Photon radiation pressure", style_table_cell), Paragraph("9.120 &times; 10^-8 m/s&sup2;", style_table_cell), Paragraph("9.120 &times; 10^-8 m/s&sup2;", style_table_cell), Paragraph("Shadow gated", style_table_cell)]
    ]
    t_acc = Table(acc_table_data, colWidths=[110, 114, 100, 100, 80])
    t_acc.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), C_PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, C_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_acc)
    story.append(Spacer(1, 10))

    # =========================================================================
    # 4. NON-CONSERVATIVE ENERGY DISSIPATION & DRAG DECAY
    # =========================================================================
    story.append(Paragraph("4. Non-Conservative Energy Dissipation & Semi-Major Axis Drag Decay", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_SECONDARY, spaceAfter=8))
    
    story.append(Paragraph(
        "Under conservative gravitational fields (Two-body, J2, J3, J4, and Lunisolar point masses), total mechanical energy is strictly conserved. In Lagrange's Planetary Equations, conservative perturbations produce periodic fluctuations but <b>zero secular change</b> in semi-major axis (da/dt_sec = 0). Atmospheric drag breaks this conservation:",
        style_body
    ))
    
    story.append(Image(eq_files['atmo_drag'], width=470, height=45))
    story.append(Spacer(1, 4))
    story.append(Image(eq_files['energy_dissipation'], width=470, height=45))
    story.append(Spacer(1, 6))

    # Figure 2: Energy Dissipation
    fig2_path = os.path.join(figures_dir, "energy_dissipation_drag_decay.png")
    if os.path.exists(fig2_path):
        story.append(Image(fig2_path, width=490, height=220))
        story.append(Spacer(1, 4))
        story.append(Paragraph("<b>Figure 2:</b> Comparison of Conservative J2 Orbit vs. Coupled Atmospheric Drag Dissipation over 5 Orbits.", style_callout))

    story.append(PageBreak())

    # =========================================================================
    # 5. SECULAR PRECESSION & CRITICAL INCLINATION
    # =========================================================================
    story.append(Paragraph("5. Secular Precession Rates & Critical Inclination (63.435°) Stability", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_SECONDARY, spaceAfter=8))
    
    story.append(Paragraph(
        "First-order secular rates from Lagrange Planetary Equations govern the long-term nodal regression and apsidal rotation of inclined orbits. When inclination equals the <b>Critical Inclination (63.435&deg;)</b>, apsidal precession halts permanently:",
        style_body
    ))
    story.append(Image(eq_files['critical_inclination'], width=470, height=45))
    story.append(Spacer(1, 6))

    # Figures 3 and 4 side-by-side
    fig3_path = os.path.join(figures_dir, "secular_drift_comparison.png")
    fig4_path = os.path.join(figures_dir, "perigee_velocity_acceleration_profile.png")
    
    if os.path.exists(fig3_path) and os.path.exists(fig4_path):
        t_figs = Table([
            [Image(fig3_path, width=250, height=220), Image(fig4_path, width=250, height=220)],
            [Paragraph("<b>Figure 3:</b> Secular Precession (RAAN & Apsidal Drift).", style_callout),
             Paragraph("<b>Figure 4:</b> Hypersonic Perigee Corridor Velocity Surge.", style_callout)]
        ], colWidths=[252, 252])
        t_figs.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 2),
            ('RIGHTPADDING', (0,0), (-1,-1), 2),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))
        story.append(t_figs)

    story.append(Spacer(1, 10))

    # =========================================================================
    # 6. FIRST REVIEW VIVA DEFENSE QUESTIONS & MODEL ANSWERS
    # =========================================================================
    story.append(Paragraph("6. First Review Viva Defense Questions & Model Answers", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=C_SECONDARY, spaceAfter=8))
    
    qa_list = [
        ("Q1: Why does semi-major axis (a) remain constant under J2, but secularly decays under atmospheric drag?",
         "<b>Model Answer:</b> In orbital mechanics, semi-major axis a is directly proportional to specific orbital energy &epsilon; = -&mu; / (2a). "
         "The rate of change of energy is given by d&epsilon;/dt = <b>v</b> &middot; <b>a</b>_non-grav. Gravitational fields (Central gravity, J2, J3, J4, and Lunisolar point-masses) are <i>conservative</i>, derived from a scalar potential U such that <b>a</b> = &nabla;U. Over a complete orbit, the closed-line integral of conservative forces is zero (&oint; &nabla;U &middot; d<b>r</b> = 0), producing periodic fluctuations but zero secular drift (da/dt_sec = 0). Atmospheric drag is a dissipative, <i>non-conservative</i> force whose acceleration vector always opposes the velocity vector (<b>v</b> &middot; <b>a</b>_drag &lt; 0). Consequently, d&epsilon;/dt is strictly negative at every perigee pass, permanently lowering total energy and causing irreversible secular decay in semi-major axis (&Delta;a = -62.64 km over 5 orbits)."),

        ("Q2: What is the physical origin of the J3 zonal harmonic, and how does it affect perigee altitude?",
         "<b>Model Answer:</b> While J2 represents equatorial oblateness (symmetric across the equator), J3 = -2.532 &times; 10^-6 represents the Earth's <i>pear-shaped asymmetry</i>, where the southern polar radius is slightly larger than the northern polar radius. According to Gauss's perturbation equations, J3 causes a long-period oscillation in orbital eccentricity and argument of perigee: de/dt_J3 &prop; -J3 sin i cos &omega;. This long-period resonance causes the perigee altitude to oscillate by several kilometers over periods of hundreds of days, which is critical for HEOs because a downward perigee fluctuation can plunge the satellite into denser atmospheric layers, accelerating orbital decay."),

        ("Q3: Why does third-body lunar gravitation surpass Earth J2 acceleration at high apogee?",
         "<b>Model Answer:</b> Earth geopotential perturbations decay very steeply with distance: J2 acceleration scales as 1/r^4, J3 scales as 1/r^5, and J4 scales as 1/r^6. At perigee (r &approx; 6,621 km), J2 acceleration is 1.37 &times; 10^-2 m/s&sup2;. But at GTO apogee (r &approx; 42,164 km), the distance r has increased by 6.4x, causing J2 acceleration to collapse by (6.4)^4 &approx; 1,643x down to 8.3 &times; 10^-6 m/s&sup2;. Conversely, third-body lunar tidal acceleration scales linearly with spacecraft distance from Earth center: a_tidal &approx; 2 &mu;_Moon r / d_Moon^3. Because r is large at apogee, lunar tidal acceleration increases from 1.17 &times; 10^-6 m/s&sup2; at perigee up to 6.23 &times; 10^-6 m/s&sup2; at apogee&mdash;becoming comparable to and eventually surpassing J2."),

        ("Q4: What is the Critical Inclination (63.435°) and why is it essential for Molniya communications orbits?",
         "<b>Model Answer:</b> The secular apsidal precession rate caused by Earth's J2 oblateness is given by: "
         "d&omega;/dt = (3/4) J2 (R_E / p)&sup2; n (5 cos&sup2; i - 1). "
         "For an arbitrary orbit, perigee rotates in the orbital plane (e.g. +0.591&deg;/day for GTO). If perigee rotates, apogee also rotates into the southern hemisphere, defeating the purpose of high-latitude communications. Setting d&omega;/dt = 0 requires: "
         "5 cos&sup2; i - 1 = 0  =>  cos i = 1 / &radic;5  =>  <b>i = 63.435&deg;</b> (or retrograde 116.565&deg;). "
         "At this critical inclination, apsidal precession is frozen (d&omega;/dt = 0), permanently locking the satellite's apogee dwell over high northern latitudes (Russia, Canada, Arctic), which enables continuous 8-hour communications per satellite."),

        ("Q5: How does a co-rotating atmosphere affect aerodynamic drag calculations?",
         "<b>Model Answer:</b> The Earth rotates at an angular velocity &omega;_E &approx; 7.2921 &times; 10^-5 rad/s. Due to molecular friction and turbulent viscosity, the lower atmosphere co-rotates with the solid Earth. Therefore, the drag deceleration is not proportional to inertial velocity <b>v</b>, but to the relative airspeed: <b>v</b>_rel = <b>v</b> - <b>&omega;</b>_E &times; <b>r</b>. For prograde orbits (inclination &lt; 90&deg;), atmospheric co-rotation reduces the relative velocity by up to ~465 m/s at the equator, significantly reducing drag compared to a stationary atmosphere model. For retrograde orbits, relative velocity increases, amplifying aerodynamic braking.")
    ]

    for q, a in qa_list:
        story.append(Paragraph(f"<b>{q}</b>", style_h2))
        story.append(Paragraph(a, style_body))
        story.append(Spacer(1, 3))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[3/3] [SUCCESS] First Review Technical Handbook PDF generated at:\n      {output_pdf}")
    
    # Mirror copy to workspace root
    try:
        shutil.copy2(output_pdf, root_pdf)
        print(f"      [+] Mirrored copy generated at:\n      {root_pdf}")
    except Exception as e:
        print(f"      [!] Notice: could not mirror to root: {e}")


if __name__ == '__main__':
    build_pdf()

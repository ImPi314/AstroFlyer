"""
AstroFlyer HEO Studio — Flight Dynamics Simulation Window
High-Fidelity Aerospace Mission Analysis & Trajectory Simulation Suite
"""

import sys
import os
import numpy as np
from PyQt6.QtWidgets import (
    QMainWindow, QDockWidget, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QLabel, QComboBox, QTextEdit, QStatusBar, QMessageBox, QSlider, QFrame
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QTimer

from core.astro_engine import (
    MU_EARTH, R_EARTH, keplerian_to_cartesian, TrajectoryEngine
)
from .theme import ASTROFLYER_STYLESHEET
from .viewport_3d import Viewport3D
from .viewport_2d import Viewport2D
from .telemetry_panel import TelemetryPanel
from .mission_tree import MissionTree
from .data_table_view import DataTableViewer


class AstroFlyerApp(QMainWindow):
    """
    Main AstroFlyer Desktop Application Window.
    Hardware-accelerated 3D OpenGL viewport, real-time 2D NASA world map ground track video playback,
    comprehensive aerospace watch window (Keplerian, Flight, ECI, and Camera controls), and raw numerical dataset inspector.
    """
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("AstroFlyer HEO - Astrodynamics Simulation Studio")
        self.resize(1380, 820)
        self.setMinimumSize(1024, 620)
        self.setStyleSheet(ASTROFLYER_STYLESHEET)
        
        # State Data
        self.simulation_results = None
        self.nominal_a_km = 24389.0
        self.nominal_e = 0.728525
        self.anim_index = 0
        self.anim_speed = 10
        self.is_playing = False
        
        # High-FPS Animation Timer (60 FPS ~ 16ms)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance_animation_step)
        
        # Setup UI Structure
        self.init_central_viewports()
        self.init_docks()
        self.init_toolbar()
        self.init_menu_bar()
        self.init_status_bar()
        
        # Log welcome message
        self.log_event("AstroFlyer Astrodynamics Kernel initialized with Hardware-Accelerated 3D OpenGL.")
        self.log_event("2D World Map Ground Track Engine & Telemetry Inspector Ready.")
        
        # Run default GTO propagation on startup
        self.run_propagation({
            'hp_km': 250.0,
            'ha_km': 35786.0,
            'inc_deg': 28.5,
            'raan_deg': 45.0,
            'argp_deg': 30.0,
            'nu_deg': 0.0,
            'use_j2': True,
            'solver': 'Radau',
            'num_orbits': 5,
            'tol': 1e-11
        })

    def init_menu_bar(self):
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu("&File")
        act_export = QAction("Export Telemetry to CSV", self)
        act_export.triggered.connect(self.data_table_view.export_to_csv)
        file_menu.addAction(act_export)
        
        act_export_plan = QAction("Export Mission Plan (.MissionPlan)", self)
        act_export_plan.triggered.connect(self.export_mission_plan)
        file_menu.addAction(act_export_plan)

        act_import_plan = QAction("Import Mission Plan (.MissionPlan)", self)
        act_import_plan.triggered.connect(self.import_mission_plan)
        file_menu.addAction(act_import_plan)

        file_menu.addSeparator()
        act_exit = QAction("Exit", self)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)
        
        # Mission Menu
        mission_menu = menubar.addMenu("&Mission")
        act_run = QAction("Run Propagation", self)
        act_run.triggered.connect(self.dock_mission.on_run_clicked)
        mission_menu.addAction(act_run)
        
        # View Menu
        view_menu = menubar.addMenu("&View")
        act_iso = QAction("Isometric 3D View", self)
        act_iso.triggered.connect(self.viewport_3d.set_isometric_view)
        view_menu.addAction(act_iso)
        
        act_polar = QAction("Polar (Top) 3D View", self)
        act_polar.triggered.connect(self.viewport_3d.set_polar_view)
        view_menu.addAction(act_polar)
        
        act_equator = QAction("Equatorial 3D View", self)
        act_equator.triggered.connect(self.viewport_3d.set_equatorial_view)
        view_menu.addAction(act_equator)
        
        # Theme Profile Selector
        view_menu.addSeparator()
        menu_theme = view_menu.addMenu("Theme Profile")
        act_dark = QAction("Dark Theme (OKLCH Default)", self)
        act_dark.triggered.connect(lambda: self.set_theme("dark"))
        menu_theme.addAction(act_dark)
        
        act_light = QAction("Light Theme (OKLCH)", self)
        act_light.triggered.connect(lambda: self.set_theme("light"))
        menu_theme.addAction(act_light)
        
        # Help Menu
        help_menu = menubar.addMenu("&Help")
        act_about = QAction("About AstroFlyer", self)
        act_about.triggered.connect(self.show_about_dialog)
        help_menu.addAction(act_about)

    def init_toolbar(self):
        toolbar = QToolBar("Mission Controls", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Play / Pause / Step Controls (No Emojis, Pure Professional Typography)
        self.act_play = QAction("Play", self)
        self.act_play.triggered.connect(self.toggle_playback)
        toolbar.addAction(self.act_play)
        
        self.act_step_back = QAction("-10s", self)
        self.act_step_back.triggered.connect(self.step_backward)
        toolbar.addAction(self.act_step_back)
        
        self.act_step_fwd = QAction("+10s", self)
        self.act_step_fwd.triggered.connect(self.step_forward)
        toolbar.addAction(self.act_step_fwd)
        
        self.act_reset = QAction("Reset", self)
        self.act_reset.triggered.connect(self.reset_playback)
        toolbar.addAction(self.act_reset)
        
        toolbar.addSeparator()
        
        # Event Stepping Controls (Apsides & Node Crossings)
        lbl_events = QLabel(" Events: ")
        lbl_events.setStyleSheet("color: #94a3b8; font-weight: 600; font-size: 9.5pt;")
        toolbar.addWidget(lbl_events)
        
        self.act_peri = QAction("Perigee", self)
        self.act_peri.setToolTip("Step simulation forward to the next Perigee passage")
        self.act_peri.triggered.connect(lambda: self.step_to_event("perigee"))
        toolbar.addAction(self.act_peri)
        
        self.act_apo = QAction("Apogee", self)
        self.act_apo.setToolTip("Step simulation forward to the next Apogee dwell")
        self.act_apo.triggered.connect(lambda: self.step_to_event("apogee"))
        toolbar.addAction(self.act_apo)
        
        self.act_node = QAction("Node", self)
        self.act_node.setToolTip("Step simulation forward to the next Equatorial Crossing")
        self.act_node.triggered.connect(lambda: self.step_to_event("node"))
        toolbar.addAction(self.act_node)
        
        toolbar.addSeparator()
        
        # Timeline Seek Scrub Slider (Pure Single Track with Smooth Indicator Ball)
        lbl_scrub = QLabel(" Timeline: ")
        lbl_scrub.setStyleSheet("color: #94a3b8; font-weight: 600; font-size: 10pt;")
        toolbar.addWidget(lbl_scrub)
        
        self.slider_time = QSlider(Qt.Orientation.Horizontal)
        self.slider_time.setFixedWidth(200)
        self.slider_time.sliderMoved.connect(self.on_slider_scrub)
        toolbar.addWidget(self.slider_time)
        
        toolbar.addSeparator()
        
        # Playback Speed Dropdown
        lbl_speed = QLabel(" Speed: ")
        lbl_speed.setStyleSheet("color: #94a3b8; font-weight: 600; font-size: 10pt;")
        toolbar.addWidget(lbl_speed)
        
        self.combo_speed = QComboBox()
        self.combo_speed.addItems(["1x", "5x", "10x", "25x", "50x", "100x", "500x", "1000x"])
        self.combo_speed.setCurrentText("10x")
        self.combo_speed.currentTextChanged.connect(self.on_speed_changed)
        toolbar.addWidget(self.combo_speed)
        
        toolbar.addSeparator()
        
        # Export Mission Plan Action in Toolbar
        self.act_plan_export = QAction("Export Mission Plan", self)
        self.act_plan_export.setToolTip("Export active orbit to Mission Plan (.MissionPlan)")
        self.act_plan_export.triggered.connect(self.export_mission_plan)
        toolbar.addAction(self.act_plan_export)
        
        toolbar.addSeparator()
        
        # Clock HUD
        self.lbl_clock = QLabel("  MISSION TIME: 00:00:00.000 (0.00 hrs)  ")
        self.lbl_clock.setStyleSheet(
            "background-color: #141d2e; color: #38bdf8; font-family: 'Geist Mono', 'Consolas', monospace; "
            "font-size: 11pt; font-weight: bold; padding: 4px 12px; border: 1px solid #1e293b; border-radius: 6px;"
        )
        toolbar.addWidget(self.lbl_clock)

    def init_central_viewports(self):
        self.tab_viewports = QTabWidget()
        
        # Tab 1: Hardware-Accelerated 3D Celestial Viewport (OpenGL)
        self.viewport_3d = Viewport3D(self)
        self.tab_viewports.addTab(self.viewport_3d, "3D INERTIAL ORBIT VIEW (OPENGL)")
        
        # Tab 2: 2D Parametric Ground Track Viewport (NASA Blue Marble Projection & Video Trail)
        self.viewport_2d = Viewport2D(self)
        self.tab_viewports.addTab(self.viewport_2d, "2D WORLD MAP GROUND TRACK (VIDEO)")
        
        # Tab 3: Raw Numbers Simulation Telemetry Table View (Read-Only)
        self.data_table_view = DataTableViewer(self)
        self.tab_viewports.addTab(self.data_table_view, "RAW NUMERICAL TELEMETRY DATA (FULL DATASET)")
        
        self.setCentralWidget(self.tab_viewports)

    def init_docks(self):
        # Left Dock: Parametric Mission Setup
        self.dock_mission = MissionTree(self)
        self.dock_mission.propagation_requested.connect(self.run_propagation)
        
        dock_left = QDockWidget("MISSION EXPLORER (PARAMETRIC SETUP)", self)
        dock_left.setWidget(self.dock_mission)
        dock_left.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        dock_left.setFixedWidth(290)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock_left)
        
        # Right Dock: Comprehensive Aerospace Watch Window
        self.dock_telemetry = TelemetryPanel(self)
        self.dock_telemetry.camera_view_requested.connect(self.on_camera_view_requested)
        
        dock_right = QDockWidget("WATCH WINDOW (TELEMETRY INSPECTOR)", self)
        dock_right.setWidget(self.dock_telemetry)
        dock_right.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        dock_right.setFixedWidth(315)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock_right)
        
        # Bottom Dock: Mission Event Log
        self.txt_console = QTextEdit()
        self.txt_console.setReadOnly(True)
        self.txt_console.setStyleSheet(
            "background-color: #0b0f19; color: #cbd5e1; font-family: 'Geist Mono', 'Consolas', monospace; font-size: 9.5pt; padding: 6px; border: 1px solid #1e293b; border-radius: 4px;"
        )
        
        dock_bottom = QDockWidget("MISSION EVENT LOG & STATUS CONSOLE", self)
        dock_bottom.setWidget(self.txt_console)
        dock_bottom.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        dock_bottom.setFixedHeight(125)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock_bottom)

    def on_camera_view_requested(self, view_name):
        if view_name == "iso":
            self.viewport_3d.set_isometric_view()
        elif view_name == "polar":
            self.viewport_3d.set_polar_view()
        elif view_name == "equator":
            self.viewport_3d.set_equatorial_view()

    def init_status_bar(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("AstroFlyer Engine Ready. Hardware OpenGL & NASA World Map Active.")

    def log_event(self, msg):
        self.txt_console.append(f"[EVENT] {msg}")
        self.txt_console.ensureCursorVisible()

    def run_propagation(self, params):
        """
        Executes trajectory propagation based on user-supplied parametric inputs.
        """
        self.timer.stop()
        self.is_playing = False
        self.act_play.setText("Play")
        
        r_p = R_EARTH + params['hp_km'] * 1000.0
        r_a = R_EARTH + params['ha_km'] * 1000.0
        a = (r_p + r_a) / 2.0
        e = (r_a - r_p) / (r_a + r_p)
        self.nominal_a_km = a / 1000.0
        self.nominal_e = e
        inc = np.radians(params['inc_deg'])
        Omega = np.radians(params['raan_deg'])
        omega = np.radians(params['argp_deg'])
        nu = np.radians(params['nu_deg'])
        
        r0, v0 = keplerian_to_cartesian(a, e, inc, Omega, omega, nu)
        initial_state = np.concatenate((r0, v0))
        
        T = 2.0 * np.pi * np.sqrt(a**3 / MU_EARTH)
        num_orbits = params['num_orbits']
        t_span = (0.0, num_orbits * T)
        
        model_type = 'j2' if params['use_j2'] else 'two_body'
        solver_type = params['solver']
        tol = params['tol']
        
        self.log_event(
            f"Starting propagation: hp={params['hp_km']:.1f}km, ha={params['ha_km']:.1f}km, "
            f"inc={params['inc_deg']:.2f}°, model={model_type.upper()}, solver={solver_type}, orbits={num_orbits}..."
        )
        self.status.showMessage("Integrating trajectory equations of motion...")
        
        engine = TrajectoryEngine(initial_state)
        res = engine.propagate(t_span, num_points=3500, model=model_type, method=solver_type, rtol=tol, atol=tol)
        self.simulation_results = res
        self.anim_index = 0
        
        # Configure Scrubber Slider Range
        n_points = len(res['times'])
        self.slider_time.setRange(0, n_points - 1)
        self.slider_time.setValue(0)
        
        # Update 3D Viewport (OpenGL)
        pos_km = res['position_m'] / 1000.0
        self.viewport_3d.plot_trajectory(pos_km, label=f"Parametric Orbit ({model_type.upper()})", color="#38bdf8", is_perturbed=params['use_j2'])
        
        # Update 2D Ground Track Viewport with World Map
        self.viewport_2d.plot_ground_track(res['latitude_deg'], res['longitude_deg'], label="Ground Track", color="#38bdf8")
        
        # Load Complete Dataset into Raw Data Table (Read-Only)
        self.data_table_view.load_simulation_data(res)
        
        # Update Telemetry Readout
        self.render_frame_at_index(0)
        
        max_energy_err = np.max(res['energy_fractional_error'])
        period_exact_sec = 2.0 * np.pi * np.sqrt(a**3 / MU_EARTH)
        self.log_event(
            f"Propagation complete! Points: {n_points:,} | Exact Period T: {period_exact_sec/3600.0:.3f} hrs ({period_exact_sec:,.1f} s) | "
            f"Energy Conservation: {100.0 * (1.0 - max_energy_err):.6f}%"
        )
        self.status.showMessage(f"Propagation Complete. Period T: {period_exact_sec/3600.0:.3f} hrs | Energy Conservation: {100.0 * (1.0 - max_energy_err):.6f}%")

    def render_frame_at_index(self, idx):
        if self.simulation_results is None or idx >= len(self.simulation_results['times']):
            return
            
        res = self.simulation_results
        pos_km_point = res['position_m'][idx] / 1000.0
        lat = res['latitude_deg'][idx]
        lon = res['longitude_deg'][idx]
        t_sec = res['times'][idx]
        t_hrs = res['time_hours'][idx]
        
        # Exact Keplerian Period (constant for conservative gravity fields without drag)
        a_m = getattr(self, 'nominal_a_km', 24389.0) * 1000.0
        e_val = getattr(self, 'nominal_e', 0.728525)
        period_sec = 2.0 * np.pi * np.sqrt(a_m**3 / MU_EARTH) if a_m > 0 else 0.0
        period_hr = period_sec / 3600.0
        
        # Format clock strings
        hrs = int(t_sec // 3600)
        mins = int((t_sec % 3600) // 60)
        secs = t_sec % 60
        met_str = f"{hrs:02d}:{mins:02d}:{secs:06.3f}"
        self.lbl_clock.setText(f"  MISSION TIME: {met_str} ({t_hrs:.2f} hrs)  ")
        
        # Update timeline seek slider
        self.slider_time.blockSignals(True)
        self.slider_time.setValue(idx)
        self.slider_time.blockSignals(False)
        
        # Update 3D Viewport
        self.viewport_3d.update_spacecraft_position(pos_km_point, current_index=idx)
        
        # Update 2D Ground Track Viewport
        self.viewport_2d.update_subsatellite_position(lat, lon, current_index=idx)
        
        # Full Watch Window Telemetry Data (Right Dock)
        telemetry_data = {
            'a_km': getattr(self, 'nominal_a_km', 24389.0),
            'e': e_val,
            'inc_deg': res['inclination_deg'][idx],
            'raan_deg': res['raan_deg'][idx],
            'argp_deg': res['arg_perigee_deg'][idx],
            'nu_deg': res['true_anomaly_deg'][idx],
            'met_str': f"{met_str} ({t_hrs:.2f} hrs)",
            'period_str': f"{period_hr:.3f} hrs ({period_sec:,.1f} s)",
            'alt_km': res['altitude_km'][idx],
            'vel_kms': res['velocity_kms'][idx],
            'ra_km': (getattr(self, 'nominal_a_km', 24389.0) * (1.0 + e_val)) - (R_EARTH / 1000.0),
            'rp_km': (getattr(self, 'nominal_a_km', 24389.0) * (1.0 - e_val)) - (R_EARTH / 1000.0),
            'energy_mj_kg': res['energy_joules_kg'][idx] / 1e6,
            'energy_err': res['energy_fractional_error'][idx],
            'x_km': res['position_m'][idx, 0] / 1000.0,
            'y_km': res['position_m'][idx, 1] / 1000.0,
            'z_km': res['position_m'][idx, 2] / 1000.0,
            'vx_kms': res['velocity_ms'][idx, 0] / 1000.0,
            'vy_kms': res['velocity_ms'][idx, 1] / 1000.0,
            'vz_kms': res['velocity_ms'][idx, 2] / 1000.0
        }
        self.dock_telemetry.update_telemetry(telemetry_data)
        
        # Highlight active row in table if user is inspecting raw numbers
        self.data_table_view.highlight_current_step(idx)

    def advance_animation_step(self):
        if self.simulation_results is None:
            return
            
        n_points = len(self.simulation_results['times'])
        self.anim_index = (self.anim_index + self.anim_speed) % n_points
        self.render_frame_at_index(self.anim_index)

    def on_slider_scrub(self, value):
        self.anim_index = value
        self.render_frame_at_index(value)

    def toggle_playback(self):
        if self.is_playing:
            self.timer.stop()
            self.is_playing = False
            self.act_play.setText("Play")
            self.status.showMessage("Simulation Paused.")
        else:
            self.timer.start(16)  # 60 FPS
            self.is_playing = True
            self.act_play.setText("Pause")
            self.status.showMessage(f"Simulation Playing ({self.anim_speed}x rate)...")

    def step_forward(self):
        if self.simulation_results is not None:
            n_points = len(self.simulation_results['times'])
            self.anim_index = (self.anim_index + 15) % n_points
            self.render_frame_at_index(self.anim_index)

    def step_backward(self):
        if self.simulation_results is not None:
            n_points = len(self.simulation_results['times'])
            self.anim_index = (self.anim_index - 15) % n_points
            self.render_frame_at_index(self.anim_index)

    def reset_playback(self):
        self.anim_index = 0
        self.render_frame_at_index(0)

    def on_speed_changed(self, text):
        speed_map = {"1x": 1, "5x": 5, "10x": 10, "25x": 25, "50x": 50, "100x": 100, "500x": 250, "1000x": 500}
        self.anim_speed = speed_map.get(text, 10)

    def show_about_dialog(self):
        QMessageBox.about(
            self,
            "About AstroFlyer HEO",
            "<b>AstroFlyer HEO - Astrodynamics Simulation Studio</b><br><br>"
            "Part of Major Project: <i>Precise Trajectory Propagation and Events Prediction for Highly Eccentric Orbits</i><br><br>"
            "<b>Candidates:</b> Girish Gowda S, Gowtham N, Harshith S Purohith<br>"
            "<b>Supervisors:</b> Mr. Vijay M, Dr. Suresh C<br>"
            "<b>Institution:</b> ACS College of Engineering (Aerospace Engineering)<br><br>"
            "Open-source hardware-accelerated 3D OpenGL trajectory simulation & events prediction software."
        )

    def set_theme(self, mode):
        from .theme import THEME_DARK, THEME_LIGHT
        if mode == "light":
            self.setStyleSheet(THEME_LIGHT)
            self.lbl_clock.setStyleSheet(
                "background-color: #ffffff; color: #0f172a; font-family: 'Geist Mono', 'Consolas', monospace; "
                "font-size: 11pt; font-weight: bold; padding: 4px 12px; border: 1px solid #e2e8f0; border-radius: 6px;"
            )
            self.txt_console.setStyleSheet(
                "background-color: #ffffff; color: #0f172a; font-family: 'Geist Mono', 'Consolas', monospace; font-size: 10pt; padding: 6px; border: 1px solid #e2e8f0;"
            )
            self.viewport_2d.set_theme_mode("light")
            self.viewport_3d.set_theme_mode("light")
            self.log_event("UI switched to Light Theme (Modern Aerospace Profile).")
        else:
            self.setStyleSheet(THEME_DARK)
            self.lbl_clock.setStyleSheet(
                "background-color: #141d2e; color: #38bdf8; font-family: 'Geist Mono', 'Consolas', monospace; "
                "font-size: 11pt; font-weight: bold; padding: 4px 12px; border: 1px solid #1e293b; border-radius: 6px;"
            )
            self.txt_console.setStyleSheet(
                "background-color: #0b0f19; color: #cbd5e1; font-family: 'Geist Mono', 'Consolas', monospace; font-size: 9.5pt; padding: 6px; border: 1px solid #1e293b; border-radius: 4px;"
            )
            self.viewport_2d.set_theme_mode("dark")
            self.viewport_3d.set_theme_mode("dark")
            self.log_event("UI switched to Dark Theme (Modern Aerospace Default).")

    def step_to_event(self, event_type):
        """
        Event Stepping (Apsidal and Nodal crossings).
        Advances the animation directly to the next critical orbital milestone.
        """
        if not self.simulation_results:
            return
            
        alt = self.simulation_results.get('altitude_km')
        lat = self.simulation_results.get('latitude_deg')
        if alt is None or len(alt) == 0:
            return
            
        n = len(alt)
        curr = self.anim_index

        if event_type == "perigee":
            # Search forward for next local minimum in altitude
            for i in range(curr + 5, n - 1):
                if alt[i] <= alt[i - 1] and alt[i] <= alt[i + 1]:
                    self.anim_index = i
                    self.render_frame_at_index(self.anim_index)
                    t_hr = self.simulation_results['time_hours'][i]
                    self.log_event(f"Event Jump: Perigee at MET {t_hr:.2f} hrs (Altitude: {alt[i]:,.1f} km, Hypersonic Transit)")
                    return
            # Wrap around search from beginning if not found ahead
            for i in range(1, curr):
                if alt[i] <= alt[i - 1] and alt[i] <= alt[i + 1]:
                    self.anim_index = i
                    self.render_frame_at_index(self.anim_index)
                    t_hr = self.simulation_results['time_hours'][i]
                    self.log_event(f"Event Jump: Perigee at MET {t_hr:.2f} hrs (Altitude: {alt[i]:,.1f} km, Hypersonic Transit)")
                    return

        elif event_type == "apogee":
            # Search forward for next local maximum in altitude
            for i in range(curr + 5, n - 1):
                if alt[i] >= alt[i - 1] and alt[i] >= alt[i + 1]:
                    self.anim_index = i
                    self.render_frame_at_index(self.anim_index)
                    t_hr = self.simulation_results['time_hours'][i]
                    self.log_event(f"Event Jump: Apogee at MET {t_hr:.2f} hrs (Altitude: {alt[i]:,.1f} km, Apogee Dwell)")
                    return
            for i in range(1, curr):
                if alt[i] >= alt[i - 1] and alt[i] >= alt[i + 1]:
                    self.anim_index = i
                    self.render_frame_at_index(self.anim_index)
                    t_hr = self.simulation_results['time_hours'][i]
                    self.log_event(f"Event Jump: Apogee at MET {t_hr:.2f} hrs (Altitude: {alt[i]:,.1f} km, Apogee Dwell)")
                    return

        elif event_type == "node":
            if lat is None:
                return
            for i in range(curr + 3, n - 1):
                if (lat[i] >= 0 and lat[i - 1] < 0) or (lat[i] <= 0 and lat[i - 1] > 0):
                    self.anim_index = i
                    self.render_frame_at_index(self.anim_index)
                    node_str = "Ascending Node" if lat[i] >= 0 else "Descending Node"
                    t_hr = self.simulation_results['time_hours'][i]
                    self.log_event(f"Event Jump: {node_str} Crossing at MET {t_hr:.2f} hrs")
                    return

    def export_mission_plan(self):
        """Exports the active orbit to a standard .MissionPlan XML."""
        from PyQt6.QtWidgets import QFileDialog
        default_name = f"AstroFlyer_HEO_Export.MissionPlan"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Mission Plan", default_name,
            "Mission Plans (*.MissionPlan);;All Files (*)"
        )
        if file_path:
            try:
                from core.mission_plan_io import export_to_mission_plan
                orbit_cfg = {
                    'a': self.nominal_a_km,
                    'e': self.nominal_e,
                    'inc': getattr(self, 'current_inc_deg', 63.435),
                    'raan': getattr(self, 'current_raan_deg', 45.0),
                    'arg_perigee': getattr(self, 'current_argp_deg', 270.0),
                    'true_anomaly': 0.0
                }
                export_to_mission_plan(orbit_cfg, file_path)
                self.log_event(f"Exported Mission Plan: {os.path.basename(file_path)}")
                QMessageBox.information(
                    self, "Mission Plan Export",
                    f"Mission Plan successfully exported to:\n{file_path}\n\n"
                    "This file is schema-compliant and ready for analysis."
                )
            except Exception as e:
                QMessageBox.warning(self, "Export Failed", f"Could not export Mission Plan:\n{e}")

    def import_mission_plan(self):
        """Imports an orbit from an existing .MissionPlan XML."""
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Mission Plan", "",
            "Mission Plans (*.MissionPlan);;All Files (*)"
        )
        if file_path:
            try:
                from core.mission_plan_io import import_from_mission_plan
                imported = import_from_mission_plan(file_path)
                a = imported['a']
                e = imported['e']
                ra = a * (1 + e) - R_EARTH / 1000.0
                rp = a * (1 - e) - R_EARTH / 1000.0

                self.run_propagation({
                    'hp_km': rp,
                    'ha_km': ra,
                    'inc_deg': imported['inc'],
                    'raan_deg': imported['raan'],
                    'argp_deg': imported['arg_perigee'],
                    'nu_deg': imported['true_anomaly'],
                    'use_j2': True,
                    'solver': 'Radau',
                    'num_orbits': 5,
                    'tol': 1e-11
                })
                self.log_event(f"Imported Mission Plan: {os.path.basename(file_path)} ({imported['name']})")
                QMessageBox.information(
                    self, "Mission Plan Import",
                    f"Successfully loaded '{imported['name']}' mission configuration!\n"
                    f"Semi-Major Axis: {a:,.2f} km\nEccentricity: {e:.6f}\nInclination: {imported['inc']:.3f}°\n"
                    f"Propagated using AstroFlyer C++17 Radau-IIA Engine."
                )
            except Exception as e:
                QMessageBox.warning(self, "Import Failed", f"Could not import Mission Plan:\n{e}")


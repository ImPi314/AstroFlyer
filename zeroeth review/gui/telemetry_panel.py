"""
AstroCore GUI - Aerospace Telemetry & Watch Window Panel
Real-Time Classical Keplerian Elements, Flight State, ECI Coordinates & Camera View Controls
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout, QLabel, QPushButton, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal


class TelemetryPanel(QWidget):
    """
    Comprehensive Telemetry Watch Window Panel.
    Includes Classical Keplerian Elements, Flight Telemetry, ECI Cartesian Vectors, and 3D Camera Controls.
    """
    camera_view_requested = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(2, 2, 2, 2)
        main_layout.setSpacing(0)
        
        # Scroll area to comfortably fit all telemetry sections on any screen resolution
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")
        
        container = QWidget()
        self.layout = QVBoxLayout(container)
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.setSpacing(8)
        
        self.labels = {}
        
        self.init_watch_regime_badge()
        self.init_keplerian_group()
        self.init_flight_data_group()
        self.init_state_vector_group()
        self.init_camera_controls_group()
        self.layout.addStretch()
        
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def init_watch_regime_badge(self):
        """Real-Time Flight Regime & Shadow Indicator Badge."""
        self.regime_frame = QFrame()
        self.regime_frame.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-left: 3px solid #38bdf8;
                border-radius: 4px;
                padding: 4px 6px;
            }
        """)
        layout = QVBoxLayout(self.regime_frame)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        header = QLabel("WATCH WINDOW: HEO REGIME STATUS")
        header.setStyleSheet("color: #64748b; font-size: 7.5pt; font-weight: bold; letter-spacing: 0.5px;")
        layout.addWidget(header)

        self.lbl_regime = QLabel("NOMINAL COAST PHASE")
        self.lbl_regime.setStyleSheet("color: #38bdf8; font-family: 'Geist Mono', 'Consolas', monospace; font-size: 8.5pt; font-weight: bold;")
        layout.addWidget(self.lbl_regime)

        self.lbl_illumination = QLabel("LIGHTING: SUNLIT (100% FLUX)")
        self.lbl_illumination.setStyleSheet("color: #fbbf24; font-family: 'Geist Mono', 'Consolas', monospace; font-size: 8pt; font-weight: bold;")
        layout.addWidget(self.lbl_illumination)

        self.layout.addWidget(self.regime_frame)

    def _create_row(self, layout, row, label_text, default_val="--", is_highlight=False):
        lbl_name = QLabel(label_text)
        lbl_name.setStyleSheet("color: #94a3b8; font-size: 9pt;")
        
        lbl_val = QLabel(default_val)
        color = "#38bdf8" if is_highlight else "#f8fafc"
        lbl_val.setStyleSheet(f"color: {color}; font-family: 'Geist Mono', 'Consolas', monospace; font-size: 9pt; font-weight: bold;")
        lbl_val.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        layout.addWidget(lbl_name, row, 0)
        layout.addWidget(lbl_val, row, 1)
        return lbl_val

    def init_keplerian_group(self):
        grp = QGroupBox("CLASSICAL KEPLERIAN ELEMENTS")
        grid = QGridLayout(grp)
        grid.setContentsMargins(8, 12, 8, 8)
        grid.setVerticalSpacing(3)
        
        self.labels['a'] = self._create_row(grid, 0, "Semi-Major Axis (a):", "24,389.00 km")
        self.labels['e'] = self._create_row(grid, 1, "Eccentricity (e):", "0.728525")
        self.labels['inc'] = self._create_row(grid, 2, "Inclination (i):", "28.500°")
        self.labels['raan'] = self._create_row(grid, 3, "RAAN (Ω):", "45.000°")
        self.labels['argp'] = self._create_row(grid, 4, "Arg of Perigee (ω):", "30.000°")
        self.labels['nu'] = self._create_row(grid, 5, "True Anomaly (ν):", "0.000°", is_highlight=True)
        
        self.layout.addWidget(grp)

    def init_flight_data_group(self):
        grp = QGroupBox("DYNAMIC FLIGHT DATA (WATCH WINDOW)")
        grid = QGridLayout(grp)
        grid.setContentsMargins(8, 12, 8, 8)
        grid.setVerticalSpacing(3)
        
        self.labels['met'] = self._create_row(grid, 0, "Mission Time (MET):", "00:00:00.000")
        self.labels['alt'] = self._create_row(grid, 1, "Altitude (h):", "250.00 km", is_highlight=True)
        self.labels['vel'] = self._create_row(grid, 2, "Velocity (v):", "10.201 km/s", is_highlight=True)
        self.labels['ra'] = self._create_row(grid, 3, "Apogee Height:", "35,786.00 km")
        self.labels['rp'] = self._create_row(grid, 4, "Perigee Height:", "250.00 km")
        self.labels['period'] = self._create_row(grid, 5, "Orbital Period (T):", "10.529 hrs")
        self.labels['energy'] = self._create_row(grid, 6, "Specific Energy (ε):", "-8.1776 MJ/kg")
        self.labels['energy_err'] = self._create_row(grid, 7, "Energy Conserved:", "100.0000%")
        
        self.layout.addWidget(grp)

    def init_state_vector_group(self):
        grp = QGroupBox("ECI STATE VECTOR (J2000)")
        grid = QGridLayout(grp)
        grid.setContentsMargins(8, 12, 8, 8)
        grid.setVerticalSpacing(3)
        
        self.labels['x'] = self._create_row(grid, 0, "X (km):", "6,621.00")
        self.labels['y'] = self._create_row(grid, 1, "Y (km):", "0.00")
        self.labels['z'] = self._create_row(grid, 2, "Z (km):", "0.00")
        self.labels['vx'] = self._create_row(grid, 3, "Vx (km/s):", "0.0000")
        self.labels['vy'] = self._create_row(grid, 4, "Vy (km/s):", "8.9660")
        self.labels['vz'] = self._create_row(grid, 5, "Vz (km/s):", "4.8690")
        
        self.layout.addWidget(grp)

    def init_camera_controls_group(self):
        grp = QGroupBox("3D CELESTIAL CAMERA VIEWS")
        layout = QVBoxLayout(grp)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(6)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)
        
        btn_iso = QPushButton("Isometric")
        btn_iso.clicked.connect(lambda: self.camera_view_requested.emit("isometric"))
        btn_layout.addWidget(btn_iso)
        
        btn_top = QPushButton("Polar")
        btn_top.clicked.connect(lambda: self.camera_view_requested.emit("polar"))
        btn_layout.addWidget(btn_top)
        
        btn_side = QPushButton("Equatorial")
        btn_side.clicked.connect(lambda: self.camera_view_requested.emit("equator"))
        btn_layout.addWidget(btn_side)
        
        layout.addLayout(btn_layout)
        
        lbl_hint = QLabel("Left-Drag: Rotate • Right/Scroll: Zoom • Mid: Pan")
        lbl_hint.setStyleSheet("color: #64748b; font-size: 8pt;")
        lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_hint)
        
        self.layout.addWidget(grp)

    def update_telemetry(self, data):
        """
        Updates the telemetry labels with the latest simulation state and applies
        dynamic threshold alerts (Lime = Perigee Corridor, Red = Apogee Dwell).
        """
        if 'a_km' in data: self.labels['a'].setText(f"{data['a_km']:,.2f} km")
        if 'e' in data: self.labels['e'].setText(f"{data['e']:.6f}")
        if 'inc_deg' in data: self.labels['inc'].setText(f"{data['inc_deg']:.3f}°")
        if 'raan_deg' in data: self.labels['raan'].setText(f"{data['raan_deg']:.3f}°")
        if 'argp_deg' in data: self.labels['argp'].setText(f"{data['argp_deg']:.3f}°")
        if 'nu_deg' in data: self.labels['nu'].setText(f"{data['nu_deg']:.3f}°")
        
        if 'met_str' in data: self.labels['met'].setText(data['met_str'])
        
        # Dynamic Watch Window Threshold Alert Logic
        alt_km = data.get('alt_km', 250.0)
        vel_kms = data.get('vel_kms', 10.2)
        
        self.labels['alt'].setText(f"{alt_km:,.2f} km")
        self.labels['vel'].setText(f"{vel_kms:.4f} km/s")

        if alt_km < 1000.0 or vel_kms > 9.5:
            # Perigee Corridor Alert (Lime Green)
            self.regime_frame.setStyleSheet("""
                QFrame {
                    background-color: #052e16;
                    border: 1px solid #166534;
                    border-left: 4px solid #22c55e;
                    border-radius: 4px;
                    padding: 4px 6px;
                }
            """)
            self.lbl_regime.setText("PERIGEE TRANSIT (HYPERSONIC)")
            self.lbl_regime.setStyleSheet("color: #4ade80; font-family: 'Geist Mono', 'Consolas', monospace; font-size: 8.5pt; font-weight: bold;")
            self.labels['alt'].setStyleSheet("color: #4ade80; font-family: 'Geist Mono', monospace; font-size: 9pt; font-weight: bold;")
            self.labels['vel'].setStyleSheet("color: #4ade80; font-family: 'Geist Mono', monospace; font-size: 9pt; font-weight: bold;")
        elif alt_km > 35000.0:
            # Apogee Dwell Alert (Coral Red)
            self.regime_frame.setStyleSheet("""
                QFrame {
                    background-color: #450a0a;
                    border: 1px solid #991b1b;
                    border-left: 4px solid #ef4444;
                    border-radius: 4px;
                    padding: 4px 6px;
                }
            """)
            self.lbl_regime.setText("APOGEE DWELL (STATIONARY)")
            self.lbl_regime.setStyleSheet("color: #f87171; font-family: 'Geist Mono', 'Consolas', monospace; font-size: 8.5pt; font-weight: bold;")
            self.labels['alt'].setStyleSheet("color: #f87171; font-family: 'Geist Mono', monospace; font-size: 9pt; font-weight: bold;")
            self.labels['vel'].setStyleSheet("color: #f87171; font-family: 'Geist Mono', monospace; font-size: 9pt; font-weight: bold;")
        else:
            # Nominal Coasting Orbit
            self.regime_frame.setStyleSheet("""
                QFrame {
                    background-color: #0f172a;
                    border: 1px solid #1e293b;
                    border-left: 3px solid #38bdf8;
                    border-radius: 4px;
                    padding: 4px 6px;
                }
            """)
            self.lbl_regime.setText("NOMINAL COAST PHASE")
            self.lbl_regime.setStyleSheet("color: #38bdf8; font-family: 'Geist Mono', 'Consolas', monospace; font-size: 8.5pt; font-weight: bold;")
            self.labels['alt'].setStyleSheet("color: #38bdf8; font-family: 'Geist Mono', monospace; font-size: 9pt; font-weight: bold;")
            self.labels['vel'].setStyleSheet("color: #38bdf8; font-family: 'Geist Mono', monospace; font-size: 9pt; font-weight: bold;")

        # Illumination / Eclipse Calculation
        x_km = data.get('x_km', 6621.0)
        y_km = data.get('y_km', 0.0)
        z_km = data.get('z_km', 0.0)
        r_earth_km = 6378.137
        # Simplified cylindrical shadow (Sun assumed along +X)
        if x_km < 0 and (y_km**2 + z_km**2) < r_earth_km**2:
            self.lbl_illumination.setText("LIGHTING: ECLIPSE (UMBRA 0% FLUX)")
            self.lbl_illumination.setStyleSheet("color: #818cf8; font-family: 'Geist Mono', monospace; font-size: 8pt; font-weight: bold;")
        else:
            self.lbl_illumination.setText("LIGHTING: SUNLIT (100% FLUX)")
            self.lbl_illumination.setStyleSheet("color: #fbbf24; font-family: 'Geist Mono', monospace; font-size: 8pt; font-weight: bold;")

        if 'ra_km' in data: self.labels['ra'].setText(f"{data['ra_km']:,.2f} km")
        if 'rp_km' in data: self.labels['rp'].setText(f"{data['rp_km']:,.2f} km")
        if 'period_str' in data:
            self.labels['period'].setText(data['period_str'])
        elif 'period_hr' in data:
            self.labels['period'].setText(f"{data['period_hr']:.3f} hrs")
            
        if 'energy_mj_kg' in data: self.labels['energy'].setText(f"{data['energy_mj_kg']:.4f} MJ/kg")
        if 'energy_err' in data:
            err = data['energy_err']
            conservation = max(0.0, 100.0 * (1.0 - err))
            self.labels['energy_err'].setText(f"{conservation:.6f}%")
        
        if 'x_km' in data: self.labels['x'].setText(f"{data['x_km']:,.2f}")
        if 'y_km' in data: self.labels['y'].setText(f"{data['y_km']:,.2f}")
        if 'z_km' in data: self.labels['z'].setText(f"{data['z_km']:,.2f}")
        if 'vx_kms' in data: self.labels['vx'].setText(f"{data['vx_kms']:.4f}")
        if 'vy_kms' in data: self.labels['vy'].setText(f"{data['vy_kms']:.4f}")
        if 'vz_kms' in data: self.labels['vz'].setText(f"{data['vz_kms']:.4f}")

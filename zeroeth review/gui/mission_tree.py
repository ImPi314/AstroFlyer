"""
AstroCore GUI - Mission Explorer & Parametric Configuration Panel
Purely Parametric Orbit & Force Model Setup
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QGridLayout, QLabel,
    QComboBox, QDoubleSpinBox, QSpinBox, QCheckBox, QPushButton, QAbstractSpinBox
)
from PyQt6.QtCore import pyqtSignal


class MissionTree(QWidget):
    """
    Left Dock Configuration Panel.
    Enables purely parametric definition of initial orbital states, force models, and integrators.
    """
    propagation_requested = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.setSpacing(8)
        
        self.init_orbit_params_group()
        self.init_force_models_group()
        self.init_propagator_group()
        
        # Run Button
        self.btn_run = QPushButton("RUN PROPAGATION")
        self.btn_run.setObjectName("btn_run")
        self.btn_run.setFixedHeight(34)
        self.btn_run.clicked.connect(self.on_run_clicked)
        self.layout.addWidget(self.btn_run)
        
        self.layout.addStretch()
        
    def init_orbit_params_group(self):
        grp = QGroupBox("PARAMETRIC ORBIT DEFINITION")
        grid = QGridLayout(grp)
        grid.setContentsMargins(8, 12, 8, 8)
        grid.setVerticalSpacing(5)
        
        # Preset Selector
        grid.addWidget(QLabel("Orbit Preset:"), 0, 0)
        self.combo_preset = QComboBox()
        self.combo_preset.addItems([
            "GTO (Geostationary Transfer)",
            "Molniya (12-hr HEO, 63.4°)",
            "Tundra (24-hr HEO, 63.4°)",
            "LEO (Low Earth Orbit)",
            "GEO (Geostationary Orbit)",
            "Custom Parametric Orbit"
        ])
        self.combo_preset.currentIndexChanged.connect(self.on_preset_changed)
        grid.addWidget(self.combo_preset, 0, 1)
        
        # Perigee Altitude (km)
        grid.addWidget(QLabel("Perigee Alt (hp):"), 1, 0)
        self.spin_hp = QDoubleSpinBox()
        self.spin_hp.setRange(100.0, 500000.0)
        self.spin_hp.setSingleStep(50.0)
        self.spin_hp.setValue(250.0)
        self.spin_hp.setSuffix(" km")
        self.spin_hp.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        grid.addWidget(self.spin_hp, 1, 1)
        
        # Apogee Altitude (km)
        grid.addWidget(QLabel("Apogee Alt (ha):"), 2, 0)
        self.spin_ha = QDoubleSpinBox()
        self.spin_ha.setRange(100.0, 500000.0)
        self.spin_ha.setSingleStep(500.0)
        self.spin_ha.setValue(35786.0)
        self.spin_ha.setSuffix(" km")
        self.spin_ha.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        grid.addWidget(self.spin_ha, 2, 1)
        
        # Inclination (deg)
        grid.addWidget(QLabel("Inclination (i):"), 3, 0)
        self.spin_inc = QDoubleSpinBox()
        self.spin_inc.setRange(0.0, 180.0)
        self.spin_inc.setSingleStep(1.0)
        self.spin_inc.setValue(28.5)
        self.spin_inc.setSuffix(" °")
        self.spin_inc.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        grid.addWidget(self.spin_inc, 3, 1)
        
        # RAAN (deg)
        grid.addWidget(QLabel("RAAN (Ω):"), 4, 0)
        self.spin_raan = QDoubleSpinBox()
        self.spin_raan.setRange(0.0, 360.0)
        self.spin_raan.setSingleStep(5.0)
        self.spin_raan.setValue(45.0)
        self.spin_raan.setSuffix(" °")
        self.spin_raan.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        grid.addWidget(self.spin_raan, 4, 1)
        
        # Argument of Perigee (deg)
        grid.addWidget(QLabel("Arg of Perigee (ω):"), 5, 0)
        self.spin_argp = QDoubleSpinBox()
        self.spin_argp.setRange(0.0, 360.0)
        self.spin_argp.setSingleStep(5.0)
        self.spin_argp.setValue(30.0)
        self.spin_argp.setSuffix(" °")
        self.spin_argp.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        grid.addWidget(self.spin_argp, 5, 1)
        
        # True Anomaly (deg)
        grid.addWidget(QLabel("True Anomaly (ν):"), 6, 0)
        self.spin_nu = QDoubleSpinBox()
        self.spin_nu.setRange(0.0, 360.0)
        self.spin_nu.setSingleStep(5.0)
        self.spin_nu.setValue(0.0)
        self.spin_nu.setSuffix(" °")
        self.spin_nu.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        grid.addWidget(self.spin_nu, 6, 1)
        
        self.layout.addWidget(grp)
        
    def init_force_models_group(self):
        grp = QGroupBox("FORCE MODELS MATRIX")
        grid = QGridLayout(grp)
        grid.setContentsMargins(8, 12, 8, 8)
        grid.setVerticalSpacing(4)
        
        self.chk_central = QCheckBox("Central Point-Mass Gravity (μ)")
        self.chk_central.setChecked(True)
        self.chk_central.setEnabled(False)  # Fundamental
        grid.addWidget(self.chk_central, 0, 0, 1, 2)
        
        self.chk_j2 = QCheckBox("Earth J2 Zonal Harmonics")
        self.chk_j2.setChecked(True)
        grid.addWidget(self.chk_j2, 1, 0, 1, 2)
        
        self.layout.addWidget(grp)
        
    def init_propagator_group(self):
        grp = QGroupBox("NUMERICAL INTEGRATOR SETTINGS")
        grid = QGridLayout(grp)
        grid.setContentsMargins(8, 12, 8, 8)
        grid.setVerticalSpacing(5)
        
        # Solver Algorithm
        grid.addWidget(QLabel("Solver:"), 0, 0)
        self.combo_solver = QComboBox()
        self.combo_solver.addItems(["Radau-IIA (Stiff Implicit)", "RK45 (Dormand-Prince Adaptive)"])
        grid.addWidget(self.combo_solver, 0, 1)
        
        # Number of Orbits
        grid.addWidget(QLabel("Duration:"), 1, 0)
        self.spin_orbits = QSpinBox()
        self.spin_orbits.setRange(1, 100)
        self.spin_orbits.setSingleStep(1)
        self.spin_orbits.setValue(5)
        self.spin_orbits.setSuffix(" orbits")
        self.spin_orbits.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        self.spin_orbits.setKeyboardTracking(True)
        grid.addWidget(self.spin_orbits, 1, 1)
        
        # Tolerance
        grid.addWidget(QLabel("Tolerance:"), 2, 0)
        self.combo_tol = QComboBox()
        self.combo_tol.addItems(["1e-11 (High Precision)", "1e-9 (Standard)", "1e-7 (Fast)"])
        grid.addWidget(self.combo_tol, 2, 1)
        
        self.layout.addWidget(grp)
        
    def on_preset_changed(self, idx):
        presets = [
            (250.0, 35786.0, 28.5, 45.0, 30.0, 0.0),    # GTO
            (600.0, 39860.0, 63.4, 60.0, 270.0, 0.0),   # Molniya
            (24000.0, 46300.0, 63.4, 120.0, 270.0, 0.0),# Tundra
            (400.0, 400.0, 51.6, 0.0, 0.0, 0.0),        # LEO
            (35786.0, 35786.0, 0.0, 0.0, 0.0, 0.0),     # GEO
        ]
        if idx < len(presets):
            hp, ha, inc, raan, argp, nu = presets[idx]
            self.spin_hp.setValue(hp)
            self.spin_ha.setValue(ha)
            self.spin_inc.setValue(inc)
            self.spin_raan.setValue(raan)
            self.spin_argp.setValue(argp)
            self.spin_nu.setValue(nu)
            
    def on_run_clicked(self):
        tol_map = {"1e-11 (High Precision)": 1e-11, "1e-9 (Standard)": 1e-9, "1e-7 (Fast)": 1e-7}
        solver_map = {"Radau-IIA (Stiff Implicit)": "Radau", "RK45 (Dormand-Prince Adaptive)": "RK45"}
        
        params = {
            'hp_km': self.spin_hp.value(),
            'ha_km': self.spin_ha.value(),
            'inc_deg': self.spin_inc.value(),
            'raan_deg': self.spin_raan.value(),
            'argp_deg': self.spin_argp.value(),
            'nu_deg': self.spin_nu.value(),
            'use_j2': self.chk_j2.isChecked(),
            'solver': solver_map[self.combo_solver.currentText()],
            'num_orbits': self.spin_orbits.value(),
            'tol': tol_map[self.combo_tol.currentText()]
        }
        self.propagation_requested.emit(params)

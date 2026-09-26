"""
AstroCore GUI - Raw Simulation Telemetry Data Table View
High-Density Tabular Telemetry Inspector with Full Timeseries Numerical Readout (Read-Only)
"""

import numpy as np
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QPushButton, QLineEdit, QFileDialog, QHeaderView, QFrame, QAbstractItemView
)
from PyQt6.QtCore import Qt

from core.astro_engine import R_EARTH, MU_EARTH


class DataTableViewer(QWidget):
    """
    High-density tabular inspector for inspecting the raw numerical state vector
    and classical orbital elements across the entire simulation duration.
    Strictly read-only with full selection, search, and CSV export capabilities.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(2)
        
        self.simulation_results = None
        
        # Toolbar Header
        self.init_toolbar()
        
        # Data Table (Strictly Read-Only)
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #0b0f19;
                alternate-background-color: #101726;
                gridline-color: #1e293b;
                color: #f8fafc;
                font-family: 'Geist Mono', 'Consolas', monospace;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #141d2e;
                color: #94a3b8;
                font-weight: bold;
                padding: 6px;
                border: 1px solid #1e293b;
            }
            QTableWidget::item:selected {
                background-color: #2563eb;
                color: #ffffff;
            }
        """)
        
        self.headers = [
            "Step", "Time (s)", "Time (hrs)",
            "Semi-Major a (km)", "Eccentricity e", "Inc i (deg)", "RAAN Ω (deg)", "ArgP ω (deg)", "True Anom ν (deg)",
            "Altitude (km)", "Velocity (km/s)", "Latitude (deg)", "Longitude (deg)",
            "ECI X (km)", "ECI Y (km)", "ECI Z (km)",
            "ECI Vx (km/s)", "ECI Vy (km/s)", "ECI Vz (km/s)",
            "Specific Energy (MJ/kg)", "Energy Invariant Error (|ΔE/E0|)"
        ]
        
        self.table.setColumnCount(len(self.headers))
        self.table.setHorizontalHeaderLabels(self.headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        self.layout.addWidget(self.table)

    def init_toolbar(self):
        bar = QFrame()
        bar.setStyleSheet("background-color: #101726; border-bottom: 1px solid #1e293b; padding: 4px 8px;")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(6, 2, 6, 2)
        bar_layout.setSpacing(10)
        
        self.lbl_count = QLabel("Total Simulation Records: 0 (Read-Only Inspection)")
        self.lbl_count.setStyleSheet("color: #e2e8f0; font-weight: bold; font-size: 11px;")
        bar_layout.addWidget(self.lbl_count)
        
        bar_layout.addStretch()
        
        btn_export = QPushButton("Export Full Dataset to CSV")
        btn_export.setFixedHeight(24)
        btn_export.clicked.connect(self.export_to_csv)
        bar_layout.addWidget(btn_export)
        
        self.layout.addWidget(bar)

    def load_simulation_data(self, res):
        """
        Populates the table with the complete raw simulation dataset with non-editable cells.
        """
        self.simulation_results = res
        n_points = len(res['times'])
        self.lbl_count.setText(f"Total Simulation Records: {n_points:,} time steps (Strictly Read-Only)")
        
        self.table.setRowCount(n_points)
        self.table.setSortingEnabled(False)
        
        for i in range(n_points):
            row_values = [
                f"{i}",
                f"{res['times'][i]:.2f}",
                f"{res['time_hours'][i]:.4f}",
                f"{res['semi_major_axis_km'][i]:,.2f}",
                f"{res['eccentricity'][i]:.6f}",
                f"{res['inclination_deg'][i]:.3f}",
                f"{res['raan_deg'][i]:.3f}",
                f"{res['arg_perigee_deg'][i]:.3f}",
                f"{res['true_anomaly_deg'][i]:.3f}",
                f"{res['altitude_km'][i]:,.2f}",
                f"{res['velocity_kms'][i]:.4f}",
                f"{res['latitude_deg'][i]:.3f}",
                f"{res['longitude_deg'][i]:.3f}",
                f"{res['position_m'][i, 0] / 1000.0:,.2f}",
                f"{res['position_m'][i, 1] / 1000.0:,.2f}",
                f"{res['position_m'][i, 2] / 1000.0:,.2f}",
                f"{res['velocity_ms'][i, 0] / 1000.0:.4f}",
                f"{res['velocity_ms'][i, 1] / 1000.0:.4f}",
                f"{res['velocity_ms'][i, 2] / 1000.0:.4f}",
                f"{res['energy_joules_kg'][i] / 1e6:.4f}",
                f"{res['energy_fractional_error'][i]:.2e}"
            ]
            
            for col, val in enumerate(row_values):
                item = QTableWidgetItem(val)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(i, col, item)

    def highlight_current_step(self, step_idx):
        """
        Scrolls to and highlights the active time step in synchronization with video playback.
        """
        if self.table.rowCount() > step_idx:
            self.table.selectRow(step_idx)

    def export_to_csv(self):
        if self.simulation_results is None:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Simulation Telemetry CSV", "telemetry_dataset.csv", "CSV Files (*.csv)"
        )
        if file_path:
            import pandas as pd
            res = self.simulation_results
            df = pd.DataFrame({
                'step': np.arange(len(res['times'])),
                'time_s': res['times'],
                'time_hours': res['time_hours'],
                'semi_major_axis_km': res['semi_major_axis_km'],
                'eccentricity': res['eccentricity'],
                'inclination_deg': res['inclination_deg'],
                'raan_deg': res['raan_deg'],
                'arg_perigee_deg': res['arg_perigee_deg'],
                'true_anomaly_deg': res['true_anomaly_deg'],
                'altitude_km': res['altitude_km'],
                'velocity_kms': res['velocity_kms'],
                'latitude_deg': res['latitude_deg'],
                'longitude_deg': res['longitude_deg'],
                'pos_x_km': res['position_m'][:, 0] / 1000.0,
                'pos_y_km': res['position_m'][:, 1] / 1000.0,
                'pos_z_km': res['position_m'][:, 2] / 1000.0,
                'vel_x_kms': res['velocity_ms'][:, 0] / 1000.0,
                'vel_y_kms': res['velocity_ms'][:, 1] / 1000.0,
                'vel_z_kms': res['velocity_ms'][:, 2] / 1000.0,
                'energy_joules_kg': res['energy_joules_kg'],
                'energy_fractional_error': res['energy_fractional_error']
            })
            df.to_csv(file_path, index=False)

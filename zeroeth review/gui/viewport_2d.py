"""
AstroCore GUI - 2D Earth Ground Track Viewport
High-Performance Dynamic Time-Evolution Video Ground Track Projected on NASA World Map
"""

import os
import numpy as np
from PIL import Image
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt, QRectF
import pyqtgraph as pg


class Viewport2D(QWidget):
    """
    High-Performance 2D Parametric Ground Track Viewport with full NASA Earth World Map projection.
    Provides 100% vertical space utilization with floating corner telemetry badge.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Container widget
        self.container = QWidget(self)
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)
        
        # PyQtGraph Plot Widget (Fills 100% of viewport)
        self.plot_widget = pg.PlotWidget(self.container)
        self.plot_widget.setBackground('#0b0f19')
        
        vb = self.plot_widget.getViewBox()
        if vb is not None:
            vb.setRange(xRange=(-180, 180), yRange=(-90, 90), padding=0.0)
            vb.setLimits(xMin=-180, xMax=180, yMin=-90, yMax=90)
        
        self.plot_widget.setLabel('bottom', "Geodetic Longitude", units="deg", color='#94a3b8')
        self.plot_widget.setLabel('left', "Geodetic Latitude", units="deg", color='#94a3b8')
        self.container_layout.addWidget(self.plot_widget)
        
        self.layout.addWidget(self.container)
        
        # Floating Sub-Satellite Point Badge (Sleek Corner Overlay)
        self.badge = self.create_floating_badge()
        self.badge.setParent(self.plot_widget)
        self.badge.move(14, 14)
        
        # Data storage
        self.lats = None
        self.lons = None
        
        # Image Item for World Map
        self.map_item = None
        self.load_world_map_texture()
        
        # Plot Curves
        self.full_track_curves = []
        self.active_trail_curves = []
        self.subsat_marker = None
        self.subsat_halo = None
        
        # Ground Station Network (NASA DSN, ISRO ISTRAC, Svalbard)
        self.ground_stations = [
            {"name": "Goldstone", "lat": 35.43, "lon": -116.89, "rad": 18.0},
            {"name": "Madrid", "lat": 40.43, "lon": -4.25, "rad": 18.0},
            {"name": "Canberra", "lat": -35.40, "lon": 148.98, "rad": 18.0},
            {"name": "Bengaluru", "lat": 13.03, "lon": 77.51, "rad": 15.0},
            {"name": "Hassan", "lat": 13.07, "lon": 76.10, "rad": 15.0},
            {"name": "Svalbard", "lat": 78.23, "lon": 15.41, "rad": 22.0}
        ]
        self.station_markers = []
        self.station_cones = []
        self.plot_ground_stations()

    def create_floating_badge(self):
        badge = QFrame()
        badge.setStyleSheet("""
            QFrame {
                background-color: rgba(16, 23, 38, 0.92);
                border: 1px solid #1e293b;
                border-left: 3px solid #38bdf8;
                border-radius: 6px;
                padding: 4px 8px;
            }
            QLabel {
                font-family: 'Geist Mono', 'Consolas', monospace;
                font-size: 9pt;
            }
        """)
        layout = QVBoxLayout(badge)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(2)
        
        lbl_title = QLabel("2D EQUIRECTANGULAR GROUND TRACK (NASA BLUE MARBLE)")
        lbl_title.setStyleSheet("color: #e2e8f0; font-weight: bold; font-size: 9pt; letter-spacing: 0.5px;")
        layout.addWidget(lbl_title)
        
        self.lbl_coords = QLabel("Sub-Satellite Point: Lat: +0.00° | Lon: +0.00°")
        self.lbl_coords.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 9pt;")
        layout.addWidget(self.lbl_coords)
        
        return badge

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'badge') and self.badge is not None:
            self.badge.move(14, 14)

    def load_world_map_texture(self):
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        map_path = os.path.join(cur_dir, '..', 'data', 'world_map_dark.png')
        
        if os.path.exists(map_path):
            img = Image.open(map_path).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            img_arr = np.array(img)
            # Transpose to (width, height, channels) for pyqtgraph ImageItem
            img_arr = np.transpose(img_arr, (1, 0, 2))
            
            self.map_item = pg.ImageItem(img_arr)
            self.map_item.setRect(QRectF(-180, -90, 360, 180))
            self.map_item.setZValue(-100)
            self.plot_widget.addItem(self.map_item)

    def plot_ground_track(self, lats, lons, label="Ground Track", color="#38bdf8"):
        """
        Plots the continuous parametric ground track across ±180° boundaries on the World Map.
        """
        self.lats = np.array(lats)
        self.lons = np.array(lons)
        
        for c in self.full_track_curves:
            self.plot_widget.removeItem(c)
        for c in self.active_trail_curves:
            self.plot_widget.removeItem(c)
        if self.subsat_marker is not None:
            self.plot_widget.removeItem(self.subsat_marker)
        if self.subsat_halo is not None:
            self.plot_widget.removeItem(self.subsat_halo)
            
        self.full_track_curves = []
        self.active_trail_curves = []
        
        # Split trajectory whenever longitude crosses ±180° wrap-around
        lon_diffs = np.abs(np.diff(self.lons))
        split_indices = np.where(lon_diffs > 180.0)[0] + 1
        
        lon_segments = np.split(self.lons, split_indices)
        lat_segments = np.split(self.lats, split_indices)
        
        # Background Full Orbital Ground Track (Subtle Deep Navy)
        faint_pen = pg.mkPen(color=(37, 99, 235, 110), width=1.5)
        for lon_seg, lat_seg in zip(lon_segments, lat_segments):
            curve = self.plot_widget.plot(lon_seg, lat_seg, pen=faint_pen)
            self.full_track_curves.append(curve)
            
        # Active Video-Playback Trajectory Trail (Glowing Sky Blue)
        trail_pen = pg.mkPen(color=(56, 189, 248, 255), width=2.6)
        for _ in range(len(lon_segments)):
            trail_curve = self.plot_widget.plot([], [], pen=trail_pen)
            self.active_trail_curves.append(trail_curve)
            
        # Animated Sub-Satellite Point Marker (Pure White Center with Sky Blue Halo)
        self.subsat_halo = self.plot_widget.plot(
            [self.lons[0]], [self.lats[0]],
            pen=None, symbol='o', symbolSize=16,
            symbolPen=pg.mkPen('#38bdf8', width=2),
            symbolBrush=pg.mkBrush(56, 189, 248, 80)
        )
        self.subsat_marker = self.plot_widget.plot(
            [self.lons[0]], [self.lats[0]],
            pen=None, symbol='+', symbolSize=10,
            symbolPen=pg.mkPen('#ffffff', width=2),
            symbolBrush=pg.mkBrush('#ffffff')
        )
        self.update_subsatellite_position(self.lats[0], self.lons[0], 0)

    def plot_ground_stations(self):
        """Plots NASA DSN, ISTRAC, and polar ground stations with visibility cones."""
        for st in self.ground_stations:
            marker = self.plot_widget.plot(
                [st['lon']], [st['lat']],
                pen=None, symbol='d', symbolSize=9,
                symbolPen=pg.mkPen('#fbbf24', width=1.5),
                symbolBrush=pg.mkBrush(251, 191, 36, 180)
            )
            self.station_markers.append(marker)

            theta = np.linspace(0, 2*np.pi, 36)
            c_lons = st['lon'] + st['rad'] * np.cos(theta)
            c_lats = np.clip(st['lat'] + (st['rad'] * 0.75) * np.sin(theta), -89.0, 89.0)
            cone = self.plot_widget.plot(
                c_lons, c_lats,
                pen=pg.mkPen(color=(251, 191, 36, 80), width=1.0, style=Qt.PenStyle.DashLine)
            )
            self.station_cones.append(cone)

    def update_subsatellite_position(self, lat, lon, current_index=0):
        """
        Updates the 2D sub-satellite position marker, dynamic video trail, and AOS/LOS contact.
        """
        if self.subsat_marker is not None:
            self.subsat_marker.setData([lon], [lat])
        if self.subsat_halo is not None:
            self.subsat_halo.setData([lon], [lat])
            
        # Ground Station Contact Pass Detection (AOS / LOS logic)
        active_station = None
        for st in self.ground_stations:
            dist = np.sqrt((lat - st['lat'])**2 + (lon - st['lon'])**2)
            if dist <= st['rad']:
                active_station = st['name']
                break

        if active_station:
            self.lbl_coords.setText(f"Sub-Satellite Point: Lat: {lat:+.2f}° | Lon: {lon:+.2f}°  •  AOS: {active_station.upper()} (IN CONTACT)")
            self.lbl_coords.setStyleSheet("color: #4ade80; font-weight: bold; font-size: 9pt;")
        else:
            self.lbl_coords.setText(f"Sub-Satellite Point: Lat: {lat:+.2f}° | Lon: {lon:+.2f}°  •  LOS: NO GROUND STATION PASS")
            self.lbl_coords.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 9pt;")
        
        if self.lons is not None and len(self.active_trail_curves) > 0:
            cur_lons = self.lons[:current_index + 1]
            cur_lats = self.lats[:current_index + 1]
            
            lon_diffs = np.abs(np.diff(cur_lons))
            split_indices = np.where(lon_diffs > 180.0)[0] + 1
            
            cur_lon_segments = np.split(cur_lons, split_indices)
            cur_lat_segments = np.split(cur_lats, split_indices)
            
            for i, curve in enumerate(self.active_trail_curves):
                if i < len(cur_lon_segments):
                    curve.setData(cur_lon_segments[i], cur_lat_segments[i])
                else:
                    curve.setData([], [])

    def set_theme_mode(self, mode):
        if mode == "light":
            self.plot_widget.setBackground('#ffffff')
            self.badge.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 255, 255, 0.95);
                    border: 1px solid #e2e8f0;
                    border-left: 3px solid #2563eb;
                    border-radius: 6px;
                    padding: 4px 8px;
                }
                QLabel {
                    font-family: 'Geist Mono', 'Consolas', monospace;
                    font-size: 9pt;
                }
            """)
        else:
            self.plot_widget.setBackground('#0b0f19')
            self.badge.setStyleSheet("""
                QFrame {
                    background-color: rgba(16, 23, 38, 0.92);
                    border: 1px solid #1e293b;
                    border-left: 3px solid #38bdf8;
                    border-radius: 6px;
                    padding: 4px 8px;
                }
                QLabel {
                    font-family: 'Geist Mono', 'Consolas', monospace;
                    font-size: 9pt;
                }
            """)

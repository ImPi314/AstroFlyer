"""
AstroCore GUI - Hardware-Accelerated 3D Celestial Orbit Viewport
High-Performance 3D OpenGL Viewport with 100% Space Utilization & Harmonized Aerospace Palette
"""

import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
import pyqtgraph.opengl as gl

from core.astro_engine import R_EARTH


class Viewport3D(QWidget):
    """
    Hardware-Accelerated 3D Viewport using OpenGL.
    100% space utilization with smooth mouse rotation (Left Drag), pan (Middle Drag), zoom (Right Drag / Scroll).
    Harmonized with the modern aerospace theme.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # OpenGL View Widget (Fills 100% of viewport from edge to edge)
        self.view = gl.GLViewWidget(self)
        self.view.setBackgroundColor('#0b0f19')
        self.layout.addWidget(self.view)
        
        # State Data
        self.pos_data = None
        self.earth_radius_km = R_EARTH / 1000.0
        
        # OpenGL Scene Items
        self.earth_mesh = None
        self.orbit_line = None
        self.trail_line = None
        self.sat_marker = None
        self.equator_ring = None
        self.axis_x = None
        self.axis_y = None
        self.axis_z = None
        
        self.init_scene()

    def init_scene(self):
        # 1. Earth Sphere (Radius = 6,371 km) with smooth lighting & oceanic shading
        md = gl.MeshData.sphere(rows=40, cols=80, radius=self.earth_radius_km)
        self.earth_mesh = gl.GLMeshItem(
            meshdata=md, smooth=True,
            color=(0.12, 0.38, 0.68, 0.95),
            shader='shaded', glOptions='translucent'
        )
        self.view.addItem(self.earth_mesh)
        
        # 2. Equatorial Reference Ring (Subtle Translucent Sky Blue)
        theta = np.linspace(0, 2 * np.pi, 160)
        ring_r = self.earth_radius_km * 1.03
        eq_pts = np.column_stack((ring_r * np.cos(theta), ring_r * np.sin(theta), np.zeros_like(theta)))
        self.equator_ring = gl.GLLinePlotItem(pos=eq_pts, color=(0.22, 0.74, 0.97, 0.35), width=1.5, antialias=True)
        self.view.addItem(self.equator_ring)
        
        # 3. ECI Coordinate Axes (Silver-White +X Vernal Equinox, Sky-Blue +Y, Royal Cobalt +Z Polar Axis)
        axis_len = self.earth_radius_km * 2.2
        x_pts = np.array([[0, 0, 0], [axis_len, 0, 0]])
        y_pts = np.array([[0, 0, 0], [0, axis_len, 0]])
        z_pts = np.array([[0, 0, 0], [0, 0, axis_len]])
        
        self.axis_x = gl.GLLinePlotItem(pos=x_pts, color=(0.92, 0.95, 0.98, 0.85), width=2.2, antialias=True)
        self.axis_y = gl.GLLinePlotItem(pos=y_pts, color=(0.22, 0.74, 0.97, 0.85), width=2.0, antialias=True)
        self.axis_z = gl.GLLinePlotItem(pos=z_pts, color=(0.15, 0.39, 0.92, 0.85), width=2.0, antialias=True)
        
        self.view.addItem(self.axis_x)
        self.view.addItem(self.axis_y)
        self.view.addItem(self.axis_z)
        
        self.set_isometric_view()

    def set_isometric_view(self):
        self.view.setCameraPosition(elevation=32, azimuth=45, distance=self.earth_radius_km * 8.0)

    def set_polar_view(self):
        self.view.setCameraPosition(elevation=90, azimuth=0, distance=self.earth_radius_km * 8.0)

    def set_equatorial_view(self):
        self.view.setCameraPosition(elevation=0, azimuth=0, distance=self.earth_radius_km * 8.0)

    def plot_trajectory(self, pos_km, label="Orbit Path", color="#38bdf8", is_perturbed=False):
        """
        Renders the full 3D orbital trajectory and initializes dynamic video trail.
        """
        self.pos_data = pos_km
        
        if self.orbit_line is not None:
            self.view.removeItem(self.orbit_line)
        if self.trail_line is not None:
            self.view.removeItem(self.trail_line)
        if self.sat_marker is not None:
            self.view.removeItem(self.sat_marker)
            
        # Full Orbital Trajectory Background Ribbon (Subtle Deep Cobalt Blue)
        self.orbit_line = gl.GLLinePlotItem(
            pos=pos_km,
            color=(0.15, 0.39, 0.92, 0.40),
            width=1.5,
            antialias=True
        )
        self.view.addItem(self.orbit_line)
        
        # Dynamic Video Trail (Radiant Sky Blue Trail)
        init_trail = pos_km[:2]
        self.trail_line = gl.GLLinePlotItem(
            pos=init_trail,
            color=(0.22, 0.74, 0.97, 1.0),
            width=2.8,
            antialias=True
        )
        self.view.addItem(self.trail_line)
        
        # Dynamic Spacecraft Marker (Glowing Pure White Beacon)
        init_pos = pos_km[0:1]
        self.sat_marker = gl.GLScatterPlotItem(
            pos=init_pos,
            color=(1.0, 1.0, 1.0, 1.0),
            size=12.0,
            pxMode=True
        )
        self.view.addItem(self.sat_marker)
        
        max_dist = np.max(np.linalg.norm(pos_km, axis=1))
        self.view.setCameraPosition(distance=max_dist * 2.3)

    def update_spacecraft_position(self, pos_km_point, current_index=0):
        """
        Updates the 3D spacecraft position and dynamic video trail.
        """
        if self.sat_marker is not None:
            self.sat_marker.setData(pos=pos_km_point.reshape(1, 3))
            
        if self.trail_line is not None and self.pos_data is not None:
            trail_pts = self.pos_data[:max(current_index + 1, 2)]
            self.trail_line.setData(pos=trail_pts)

    def set_theme_mode(self, mode):
        if mode == "light":
            self.view.setBackgroundColor('#ffffff')
        else:
            self.view.setBackgroundColor('#0b0f19')

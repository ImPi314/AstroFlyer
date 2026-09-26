"""
AstroCore - Automated High-Resolution GUI Application Screenshot Capturer
Launches AstroFlyerApp and captures authentic screenshots of all application viewports.
"""

import sys
import os
import time

# Native platform for authentic Windows DirectWrite typography
if 'QT_QPA_PLATFORM' in os.environ:
    del os.environ['QT_QPA_PLATFORM']

cur_dir = os.path.dirname(os.path.abspath(__file__))
zeroeth_dir = os.path.abspath(os.path.join(cur_dir, '..'))
sys.path.insert(0, zeroeth_dir)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtCore import QSize
from gui.app_window import AstroFlyerApp


def capture_all_views():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    
    figures_dir = os.path.join(zeroeth_dir, 'figures')
    os.makedirs(figures_dir, exist_ok=True)
    
    win = AstroFlyerApp()
    win.resize(1400, 850)
    win.show()
    
    # Process events to allow full layout rendering
    app.processEvents()
    
    # 1. Capture 3D Inertial Orbit View Tab
    win.tab_viewports.setCurrentIndex(0)
    win.render_frame_at_index(800) # advance along orbit
    app.processEvents()
    
    pix_3d = win.grab()
    path_3d = os.path.join(figures_dir, 'app_screenshot_3d_orbit_view.png')
    pix_3d.save(path_3d)
    print(f"[Captured]: {path_3d}")
    
    # 2. Capture 2D World Map Ground Track Tab
    win.tab_viewports.setCurrentIndex(1)
    win.render_frame_at_index(800)
    app.processEvents()
    
    pix_2d = win.grab()
    path_2d = os.path.join(figures_dir, 'app_screenshot_2d_ground_track.png')
    pix_2d.save(path_2d)
    print(f"[Captured]: {path_2d}")
    
    # 3. Capture Raw Numerical Telemetry Data Table Tab
    win.tab_viewports.setCurrentIndex(2)
    app.processEvents()
    
    pix_table = win.grab()
    path_table = os.path.join(figures_dir, 'app_screenshot_raw_telemetry_table.png')
    pix_table.save(path_table)
    print(f"[Captured]: {path_table}")
    
    app.quit()
    print("[SUCCESS] All authentic application screenshots captured successfully!")


if __name__ == '__main__':
    capture_all_views()

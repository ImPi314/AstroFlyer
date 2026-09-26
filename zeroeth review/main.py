"""
AstroFlyer HEO - Offline Standalone Desktop Flight Dynamics Studio
Part of Major Project: Precise Trajectory Propagation and Events Prediction for Highly Eccentric Orbits
ACS College of Engineering - Aerospace Engineering Department
"""

import os
import sys
import argparse

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from gui.app_window import AstroFlyerApp


def main():
    parser = argparse.ArgumentParser(description="AstroFlyer HEO Desktop Simulation Studio")
    parser.add_argument('--pdf', action='store_true', help="Re-generate Technical Handbook PDF")
    args = parser.parse_args()

    if args.pdf:
        from scripts.generate_review_pdf import build_pdf
        build_pdf()
        return

    # Initialize native Qt Desktop Application
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    font = QFont("Segoe UI", 9)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    # Launch native AstroFlyer desktop application window
    window = AstroFlyerApp()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

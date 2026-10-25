#!/usr/bin/env python3
"""
AstroFlyer HEO - Offline Desktop Flight Dynamics Studio Launcher
ACS College of Engineering | Aerospace Engineering Major Project
"""

import os
import sys

# Ensure astroflyer package is in sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
astroflyer_dir = os.path.join(root_dir, "astroflyer")
if astroflyer_dir not in sys.path:
    sys.path.insert(0, astroflyer_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from astroflyer.main import main

if __name__ == "__main__":
    main()

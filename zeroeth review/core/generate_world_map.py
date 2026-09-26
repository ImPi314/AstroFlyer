"""
High-Resolution Equirectangular Dark World Map Generator for AstroFlyer
Generates an authentic aerospace dark-mode Earth world map (2048x1024) with continent coastlines,
latitude/longitude grid lines, and equator/tropic reference lines.
"""

import os
import numpy as np
from PIL import Image, ImageDraw


def generate_equirectangular_world_map(out_path, width=2048, height=1024):
    # Ocean base: Deep navy aerospace dark (#0b131e)
    img = Image.new('RGB', (width, height), (11, 19, 30))
    draw = ImageDraw.Draw(img)
    
    # Coordinate converter: lon [-180, 180] -> x [0, width], lat [-90, 90] -> y [height, 0]
    def to_xy(lon, lat):
        x = int(((lon + 180.0) / 360.0) * width)
        y = int(((90.0 - lat) / 180.0) * height)
        return x, y
    
    def to_poly(coords):
        return [to_xy(lon, lat) for lon, lat in coords]

    # Continent Polygons (High-fidelity simplified landmass boundaries)
    # North America
    na = [
        (-168, 66), (-165, 60), (-160, 56), (-150, 60), (-140, 60), (-130, 55),
        (-125, 50), (-124, 48), (-123, 38), (-117, 32), (-110, 23), (-105, 20),
        (-97, 18), (-90, 15), (-83, 9), (-77, 8), (-80, 9), (-88, 16),
        (-97, 26), (-90, 30), (-82, 25), (-80, 26), (-81, 31), (-75, 35),
        (-70, 42), (-65, 45), (-60, 47), (-64, 50), (-55, 52), (-60, 60),
        (-65, 65), (-75, 70), (-85, 70), (-95, 72), (-110, 72), (-120, 70),
        (-135, 70), (-150, 71), (-165, 71), (-168, 66)
    ]
    
    # South America
    sa = [
        (-77, 8), (-72, 11), (-60, 10), (-50, 0), (-35, -5), (-35, -10),
        (-38, -13), (-40, -22), (-50, -30), (-58, -35), (-65, -45), (-68, -54),
        (-75, -50), (-74, -42), (-72, -30), (-70, -18), (-80, -5), (-81, 0),
        (-77, 8)
    ]
    
    # Eurasia (Europe & Asia)
    eurasia = [
        (-9, 36), (-9, 43), (-5, 48), (2, 51), (8, 55), (10, 58), (20, 60),
        (25, 71), (40, 68), (60, 70), (80, 73), (105, 77), (130, 73), (160, 70),
        (170, 65), (180, 65), (180, 60), (160, 55), (145, 45), (130, 42),
        (122, 38), (120, 32), (118, 25), (108, 20), (105, 10), (100, 5),
        (98, 10), (90, 22), (80, 15), (77, 8), (73, 18), (68, 25), (60, 25),
        (55, 25), (50, 28), (45, 13), (43, 12), (35, 30), (28, 41), (23, 38),
        (15, 40), (0, 40), (-6, 36), (-9, 36)
    ]
    
    # Africa
    africa = [
        (-6, 36), (10, 37), (25, 32), (32, 31), (35, 28), (43, 12), (51, 12),
        (45, 0), (40, -10), (35, -25), (28, -33), (18, -34), (12, -20), (9, 0),
        (3, 6), (-15, 12), (-17, 15), (-13, 28), (-6, 36)
    ]
    
    # Australia
    aus = [
        (114, -22), (120, -15), (135, -12), (142, -11), (147, -18), (153, -28),
        (150, -37), (140, -38), (130, -32), (115, -34), (113, -26), (114, -22)
    ]
    
    # Greenland
    greenland = [
        (-50, 60), (-40, 65), (-20, 75), (-20, 83), (-40, 83), (-60, 80),
        (-60, 75), (-50, 60)
    ]
    
    # Antarctica
    antarctica = [
        (-180, -65), (180, -65), (180, -90), (-180, -90), (-180, -65)
    ]
    
    # Indian Subcontinent Detail Enhancement
    india = [
        (68, 25), (73, 18), (77, 8), (80, 15), (88, 22), (90, 22), (80, 28), (68, 25)
    ]
    
    # Japan & UK & Madagascar & Indonesia Islands
    uk = [(-5, 50), (2, 51), (0, 58), (-5, 58), (-5, 50)]
    japan = [(130, 32), (140, 36), (142, 44), (138, 40), (130, 32)]
    madagascar = [(43, -12), (50, -13), (48, -25), (44, -25), (43, -12)]
    indonesia = [(95, 5), (105, -5), (115, -8), (125, -8), (130, -2), (105, 0), (95, 5)]

    # Draw Landmasses in sleek dark aerospace slate (#1c2a38) with bright cyan boundary (#2e4a66)
    land_color = (24, 38, 52)
    coast_color = (48, 76, 104)
    
    for poly in [na, sa, eurasia, africa, aus, greenland, antarctica, india, uk, japan, madagascar, indonesia]:
        pts = to_poly(poly)
        draw.polygon(pts, fill=land_color, outline=coast_color)

    # Draw Equirectangular Grid Lines (Latitudes & Longitudes)
    grid_color = (20, 32, 46)
    for lon in range(-180, 181, 30):
        x, _ = to_xy(lon, 0)
        draw.line([(x, 0), (x, height)], fill=grid_color, width=1)
        
    for lat in range(-90, 91, 30):
        _, y = to_xy(0, lat)
        draw.line([(0, y), (width, y)], fill=grid_color, width=1)
        
    # Highlight Equator (0° Lat) in subtle blue
    _, eq_y = to_xy(0, 0)
    draw.line([(0, eq_y), (width, eq_y)], fill=(38, 80, 130), width=2)
    
    # Highlight Tropics (±23.44°) in subtle gold
    _, tc_y = to_xy(0, 23.44)
    _, cap_y = to_xy(0, -23.44)
    draw.line([(0, tc_y), (width, tc_y)], fill=(120, 90, 20), width=1)
    draw.line([(0, cap_y), (width, cap_y)], fill=(120, 90, 20), width=1)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path, format='PNG')
    print(f"[World Map Generated]: {out_path} ({width}x{height})")


if __name__ == '__main__':
    cur = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(cur, '..', 'data', 'world_map_dark.png')
    generate_equirectangular_world_map(out)

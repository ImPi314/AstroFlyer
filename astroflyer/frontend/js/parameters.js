// Numeric parameters the engine reports at every output point, shared by Watch and Plot.
// A parameter may be missing from a run (for example forces the engine did not compute).

import { num, sci } from './format.js';

export const PARAMETERS = [
    { group: 'Orbit', key: 'altitude_km', label: 'Altitude', unit: 'km', digits: 1 },
    { group: 'Orbit', key: 'speed_kms', label: 'Speed', unit: 'km/s', digits: 3 },
    { group: 'Orbit', key: 'sma_km', label: 'Semi-major axis', unit: 'km', digits: 1 },
    { group: 'Orbit', key: 'eccentricity', label: 'Eccentricity', unit: '', digits: 5 },
    { group: 'Orbit', key: 'inclination_deg', label: 'Inclination', unit: 'deg', digits: 3 },
    { group: 'Orbit', key: 'raan_deg', label: 'RAAN', unit: 'deg', digits: 3 },
    { group: 'Orbit', key: 'aop_deg', label: 'Argument of perigee', unit: 'deg', digits: 3 },
    { group: 'Orbit', key: 'true_anomaly_deg', label: 'True anomaly', unit: 'deg', digits: 2 },
    { group: 'Orbit', key: 'latitude_deg', label: 'Latitude', unit: 'deg', digits: 3 },
    { group: 'Orbit', key: 'longitude_deg', label: 'Longitude', unit: 'deg', digits: 3 },
    { group: 'Orbit', key: 'energy_error', label: 'Energy change', unit: 'relative', scientific: true },

    { group: 'Forces', key: 'a_central', label: 'Central gravity', unit: 'm/s²', scientific: true, log: true },
    { group: 'Forces', key: 'a_j2', label: 'J2', unit: 'm/s²', scientific: true, log: true },
    { group: 'Forces', key: 'a_j3', label: 'J3', unit: 'm/s²', scientific: true, log: true },
    { group: 'Forces', key: 'a_j4', label: 'J4', unit: 'm/s²', scientific: true, log: true },
    { group: 'Forces', key: 'a_tesseral', label: 'Tesseral harmonics', unit: 'm/s²', scientific: true, log: true },
    { group: 'Forces', key: 'a_sun', label: 'Sun gravity', unit: 'm/s²', scientific: true, log: true },
    { group: 'Forces', key: 'a_moon', label: 'Moon gravity', unit: 'm/s²', scientific: true, log: true },
    { group: 'Forces', key: 'a_drag', label: 'Atmospheric drag', unit: 'm/s²', scientific: true, log: true },
    { group: 'Forces', key: 'a_srp', label: 'Solar radiation pressure', unit: 'm/s²', scientific: true, log: true },

    { group: 'Radiation', key: 'l_shell', label: 'L-shell', unit: 'Earth radii', digits: 3 },
    { group: 'Radiation', key: 'b_field_ut', label: 'Magnetic field', unit: 'µT', digits: 2 },

    { group: 'Covariance', key: 'sigma_radial_m', label: 'Radial 1-sigma', unit: 'm', digits: 1 },
    { group: 'Covariance', key: 'sigma_intrack_m', label: 'In-track 1-sigma', unit: 'm', digits: 1 },
    { group: 'Covariance', key: 'sigma_crosstrack_m', label: 'Cross-track 1-sigma', unit: 'm', digits: 1 },
];

export const GROUPS = [...new Set(PARAMETERS.map((p) => p.group))];

// Vertical axis label that fits along a plot `room` px tall: name and unit, then the unit alone,
// then none (the pane's own selector names the parameter). width(text) measures text in px.
export function axisLabel(p, room, width) {
    const full = p.unit ? `${p.label} (${p.unit})` : p.label;
    if (width(full) <= room) return full;
    return p.unit && width(p.unit) <= room ? p.unit : '';
}

export function parameter(key) {
    return PARAMETERS.find((p) => p.key === key);
}

export function formatValue(p, value) {
    return p.scientific ? sci(value) : num(value, p.digits);
}

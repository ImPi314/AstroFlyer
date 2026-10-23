// Numeric parameters the engine reports at every output point, shared by Watch and Plot.

import { num, sci } from './format.js';

export const PARAMETERS = [
    { key: 'altitude_km', label: 'Altitude', unit: 'km', digits: 1 },
    { key: 'speed_kms', label: 'Speed', unit: 'km/s', digits: 3 },
    { key: 'sma_km', label: 'Semi-major axis', unit: 'km', digits: 1 },
    { key: 'eccentricity', label: 'Eccentricity', unit: '', digits: 5 },
    { key: 'inclination_deg', label: 'Inclination', unit: 'deg', digits: 3 },
    { key: 'raan_deg', label: 'RAAN', unit: 'deg', digits: 3 },
    { key: 'aop_deg', label: 'Argument of perigee', unit: 'deg', digits: 3 },
    { key: 'true_anomaly_deg', label: 'True anomaly', unit: 'deg', digits: 2 },
    { key: 'latitude_deg', label: 'Latitude', unit: 'deg', digits: 3 },
    { key: 'longitude_deg', label: 'Longitude', unit: 'deg', digits: 3 },
    { key: 'energy_error', label: 'Energy error', unit: 'relative', scientific: true },
];

export function parameter(key) {
    return PARAMETERS.find((p) => p.key === key);
}

export function formatValue(p, value) {
    return p.scientific ? sci(value) : num(value, p.digits);
}

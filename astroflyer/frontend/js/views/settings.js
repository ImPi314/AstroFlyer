// Display settings for each view. They change what is drawn, never the mission,
// so the inspector applies them immediately instead of through Apply.

import { PARAMETERS } from '../parameters.js';
import { WATCH_ROWS } from './watch.js';

export const VIEWS = [
    { id: 'orbit3d', label: '3D orbit view', icon: 'orbit' },
    { id: 'groundtrack', label: 'Ground track', icon: 'map' },
    { id: 'plot', label: 'Plot', icon: 'chart-spline' },
    { id: 'watch', label: 'Watch', icon: 'list' },
];

export const defaultViewSettings = {
    orbit3d: {
        frame: 'inertial',
        center: 'earth',
        tail_h: 0,
        ra: 30,
        dec: 25,
        distance: 120000,
        fov: 35,
    },
    groundtrack: {
        center: 'greenwich',
        night: true,
        stations: true,
        footprint: true,
    },
    plot: {
        y: 'altitude_km',
        reveal: false,
    },
    watch: Object.fromEntries(WATCH_ROWS.map((row) => [row.key, true])),
};

export const viewSchemas = {
    orbit3d: {
        title: '3D orbit view',
        groups: [
            {
                title: 'Scene',
                fields: [
                    { key: 'frame', label: 'Reference frame', type: 'select', options: [['inertial', 'Inertial (Earth-centred, fixed stars)'], ['fixed', 'Earth-fixed (rotates with the Earth)']] },
                    { key: 'center', label: 'Camera centre', type: 'select', options: [['earth', 'Earth'], ['spacecraft', 'Spacecraft']] },
                    { key: 'tail_h', label: 'Trail length', unit: 'h', type: 'number', min: 0, max: 10000, step: 1, hint: 'How much of the past path is drawn bright. 0 draws the whole run.' },
                ],
            },
            {
                title: 'Viewpoint',
                fields: [
                    { key: 'ra', label: 'Right ascension', unit: 'deg', type: 'number', min: 0, max: 360, step: 1, hint: 'Direction the camera looks from, measured in the frame above. Drag in the view to change it.' },
                    { key: 'dec', label: 'Declination', unit: 'deg', type: 'number', min: -89, max: 89, step: 1 },
                    { key: 'distance', label: 'Distance', unit: 'km', type: 'number', min: 8000, max: 2000000, step: 1000, hint: 'Scroll in the view to zoom.' },
                    { key: 'fov', label: 'Field of view', unit: 'deg', type: 'number', min: 5, max: 90, step: 1 },
                ],
            },
        ],
    },
    groundtrack: {
        title: 'Ground track',
        groups: [
            {
                title: 'Map',
                fields: [
                    { key: 'center', label: 'Centre map on', type: 'select', options: [['greenwich', 'Greenwich meridian'], ['spacecraft', 'Spacecraft longitude']] },
                    { key: 'night', label: 'Night side', type: 'checkbox' },
                    { key: 'stations', label: 'Ground stations', type: 'checkbox' },
                    { key: 'footprint', label: 'Spacecraft footprint', type: 'checkbox' },
                ],
            },
        ],
    },
    plot: {
        title: 'Plot',
        groups: [
            {
                title: 'Data',
                fields: [
                    { key: 'y', label: 'Parameter', type: 'select', options: PARAMETERS.map((p) => [p.key, p.unit ? `${p.label} (${p.unit})` : p.label]) },
                    { key: 'reveal', label: 'Draw only up to the current time', type: 'checkbox' },
                ],
            },
        ],
    },
    watch: {
        title: 'Watch',
        groups: [
            {
                title: 'Rows',
                fields: WATCH_ROWS.map((row) => ({ key: row.key, label: row.label, type: 'checkbox' })),
            },
        ],
    },
};

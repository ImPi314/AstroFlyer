// Every kind of view a pane can show, its default settings and the inspector form for them.
// Settings change only what is drawn, never the mission, so the inspector applies them at once.

import { PARAMETERS, GROUPS, parameter } from '../parameters.js';
import { createOrbit3d, orbit3dDefaults } from './orbit3d.js';
import { createGroundtrack, groundtrackDefaults } from './groundtrack.js';
import { createPlot, plotDefaults } from './plot.js';
import { createWatch, watchDefaults, WATCH_ROWS } from './watch.js';

export const VIEW_TYPES = {
    orbit3d: {
        label: '3D orbit view',
        icon: 'orbit',
        create: createOrbit3d,
        defaults: orbit3dDefaults,
        schema: {
            groups: [
                {
                    title: 'Scene',
                    fields: [
                        { key: 'frame', label: 'Reference frame', type: 'select', options: [['inertial', 'Inertial (Earth-centred, fixed stars)'], ['fixed', 'Earth-fixed (rotates with the Earth)']] },
                        { key: 'center', label: 'Camera centre', type: 'select', options: [['earth', 'Earth'], ['spacecraft', 'Spacecraft']] },
                        { key: 'tail_h', label: 'Trail length', unit: 'h', type: 'number', min: 0, max: 10000, step: 1, hint: 'How much of the past path is drawn bright. 0 draws the whole run.' },
                        { key: 'hud', label: 'Show time and camera readout', type: 'checkbox' },
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
        title: () => '3D orbit view',
    },
    groundtrack: {
        label: 'Ground track',
        icon: 'map',
        create: createGroundtrack,
        defaults: groundtrackDefaults,
        schema: {
            groups: [
                {
                    title: 'Map',
                    fields: [
                        { key: 'center', label: 'Centre map on', type: 'select', options: [['track', 'The whole track'], ['greenwich', 'Greenwich meridian'], ['longitude', 'A longitude'], ['spacecraft', 'Spacecraft longitude']] },
                        { key: 'center_lon', label: 'Centre longitude', unit: 'deg', type: 'number', min: -180, max: 180, step: 1, when: (v) => v.center === 'longitude' },
                        { key: 'night', label: 'Night side', type: 'checkbox' },
                        { key: 'stations', label: 'Ground stations', type: 'checkbox' },
                        { key: 'masks', label: 'Station visibility limits', type: 'checkbox' },
                        { key: 'footprint', label: 'Spacecraft footprint', type: 'checkbox' },
                    ],
                },
            ],
        },
        title: () => 'Ground track',
    },
    plot: {
        label: 'Plot',
        icon: 'chart-spline',
        create: createPlot,
        defaults: plotDefaults,
        schema: {
            groups: [
                {
                    title: 'Data',
                    fields: [
                        { key: 'y', label: 'Parameter', type: 'select', options: PARAMETERS.map((p) => [p.key, `${p.group}: ${p.label}`]) },
                        { key: 'reveal', label: 'Draw only up to the current time', type: 'checkbox' },
                    ],
                },
            ],
        },
        title: (settings) => `Plot: ${parameter(settings.y)?.label ?? settings.y}`,
    },
    watch: {
        label: 'Watch',
        icon: 'list',
        create: createWatch,
        defaults: watchDefaults,
        schema: {
            groups: GROUPS.map((group) => ({
                title: group,
                fields: WATCH_ROWS.filter((row) => row.group === group).map((row) => ({ key: row.key, label: row.label, type: 'checkbox' })),
            })),
        },
        title: () => 'Watch',
    },
};

// The HEO layout puts the 3D view over the ground track on the left, three stacked plots on
// the right and the watch along the bottom. The four-pane layout uses the first, second,
// third and last of the same panes.
export const LAYOUTS = {
    heo: { label: 'HEO layout: 3D, ground track, three plots and watch', icon: 'layout-grid', slots: ['p1', 'p2', 'p3', 'p4', 'p5', 'p6'] },
    quad: { label: 'Four panes', icon: 'columns-2', slots: ['p1', 'p2', 'p3', 'p6'] },
};

export function defaultPanes() {
    const pane = (type, settings = VIEW_TYPES[type].defaults()) => ({ type, settings });
    return {
        p1: pane('orbit3d'),
        p2: pane('groundtrack'),
        p3: pane('plot', plotDefaults('altitude_km')),
        p4: pane('plot', plotDefaults('true_anomaly_deg')),
        p5: pane('plot', plotDefaults('energy_error')),
        p6: pane('watch'),
    };
}

export function paneTitle(pane) {
    return VIEW_TYPES[pane.type].title(pane.settings);
}

// A plot's vertical axis label never runs past the plot: on a short plot it shortens to the unit,
// then goes (the pane's own selector already names the parameter).
// Run with: node --test astroflyer/tests/frontend/plot.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';

import { axisLabel, parameter } from '../../frontend/js/parameters.js';

const width = (text) => text.length * 7;   // 7 px per character
const altitude = parameter('altitude_km');   // "Altitude (km)" is 13 characters, 91 px; "km" is 14 px

test('a tall plot shows the parameter and its unit', () => {
    assert.equal(axisLabel(altitude, 200, width), 'Altitude (km)');
    assert.equal(axisLabel(altitude, 91, width), 'Altitude (km)');
});

test('a short plot shows only the unit', () => {
    assert.equal(axisLabel(altitude, 90, width), 'km');
    assert.equal(axisLabel(altitude, 14, width), 'km');
});

test('a plot too short for the unit shows no label', () => {
    assert.equal(axisLabel(altitude, 13, width), '');
});

test('a parameter without a unit shows its name or nothing', () => {
    const ecc = parameter('eccentricity');   // "Eccentricity", 84 px
    assert.equal(axisLabel(ecc, 100, width), 'Eccentricity');
    assert.equal(axisLabel(ecc, 60, width), '');
});

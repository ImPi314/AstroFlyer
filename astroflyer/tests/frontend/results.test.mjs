// A run must not be shown as if the engine used inputs it ignored.
// Run with: node --test astroflyer/tests/frontend/results.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';

import { ignoredInputs } from '../../frontend/js/results.js';

const vectors = { position_km: [7378, 0, 0], velocity_kms: [0, 4.32, 8.63] };

test('an engine that reports a Cartesian start and the run length used has ignored nothing', () => {
    assert.deepEqual(ignoredInputs({ ...vectors, duration_s: 3600 }, { initialState: 'cartesian', durationS: 3600 }), []);
    assert.deepEqual(ignoredInputs({ hp: 1000, ha: 39350, num_orbits: 3 }, { initialState: null, durationS: null }), []);
});

test('an older engine that answers without them is caught', () => {
    assert.deepEqual(ignoredInputs({ ...vectors }, { initialState: null, durationS: null }), ['position and velocity']);
    assert.deepEqual(ignoredInputs({ hp: 1000, ha: 39350, duration_s: 86400 }, { initialState: null, durationS: null }), ['run length in hours or days']);
    assert.deepEqual(ignoredInputs({ ...vectors, duration_s: 60 }, { initialState: 'keplerian', durationS: 30000 }), ['position and velocity', 'run length in hours or days']);
});

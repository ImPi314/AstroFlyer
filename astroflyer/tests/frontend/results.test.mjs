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

// ---------- Escape trajectories (e >= 1), PR #13 ----------

import { readFileSync } from 'node:fs';
import { fromPayload, closedOrbitTools } from '../../frontend/js/results.js';

// A real /api/propagate answer for a 7,000 km start at 11.5 km/s, cut to two samples.
const escape = JSON.parse(readFileSync(new URL('./fixtures/escape_payload.json', import.meta.url)));

test('an escape run reads without the closed-orbit sections and says it is not closed', () => {
    const result = fromPayload(escape);
    assert.equal(result.summary.closedOrbit, false);
    assert.equal(result.summary.apogee_alt_km, null);
    assert.equal(result.summary.period_h, null);
    assert.ok(result.summary.eccentricity > 1);
    assert.deepEqual(result.notes, escape.notes);
    assert.equal(result.times.length, 2);
    assert.equal(result.script, '');
    assert.equal(result.tle, '');
    assert.equal(result.lifetime.years, null);
});

test('a closed run, and an older engine that does not say, count as closed', () => {
    assert.equal(fromPayload({ ...escape, closed_orbit: true }).summary.closedOrbit, true);
    const { closed_orbit, ...older } = escape;
    assert.equal(fromPayload(older).summary.closedOrbit, true);
});

test('lifetime and apsis targeting are listed as closed-orbit tools', () => {
    assert.deepEqual([...closedOrbitTools].sort(), ['lifetime', 'targeting']);
});

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
});

test('a closed run, and an older engine that does not say, count as closed', () => {
    assert.equal(fromPayload({ ...escape, closed_orbit: true }).summary.closedOrbit, true);
    const { closed_orbit, ...older } = escape;
    assert.equal(fromPayload(older).summary.closedOrbit, true);
});

test('apsis targeting is listed as a closed-orbit tool', () => {
    assert.deepEqual([...closedOrbitTools], ['targeting']);
});

// The engine reports the relative change in two-body orbital energy. Only a two-body run should
// keep it constant, so only there is it an integration error; with other forces it is real change.
import { energySummary } from '../../frontend/js/results.js';

test('a two-body run reports its energy drift as an error', () => {
    assert.deepEqual(energySummary({ model: 'two_body', max_energy_error: 2e-12 }), ['Largest energy error', 2e-12]);
});

test('a run with other forces reports energy change, not error', () => {
    assert.deepEqual(energySummary({ model: 'coupled', max_energy_error: 9.31e-3 }), ['Largest energy change', 9.31e-3]);
    assert.deepEqual(energySummary({ model: 'j2', max_energy_error: 1e-4 }), ['Largest energy change', 1e-4]);
});

// ---------- Targeting starts where the run did ----------

import { targetingRequest } from '../../frontend/js/results.js';

test('the targeting request is the run request with the run initial state and epoch as the orbit', () => {
    const result = {
        ...fromPayload(escape),
        request: { hp: 250, ha: 35786, inc: 28.5, model: 'coupled', mass: 1200, enable_drag: true, epoch: '2030-01-01T00:00:00Z' },
    };
    const req = targetingRequest(result);
    for (const field of ['hp', 'ha', 'inc']) assert.equal(req[field], undefined);
    assert.equal(req.model, 'coupled');
    assert.equal(req.mass, 1200);
    assert.equal(req.enable_drag, true);
    assert.deepEqual(req.position_km, escape.position_m[0].map((v) => v / 1000));
    assert.deepEqual(req.velocity_kms, escape.velocity_ms[0].map((v) => v / 1000));
    assert.equal(req.epoch, escape.epoch.utc);
});

// ---------- Surface impact ----------
// The engine stops a run that reaches the Earth's surface and says where and when.

const impact = { t_s: 512.25, utc: '2026-03-15T00:08:32.250000Z', latitude_deg: 0.0, longitude_deg: 31.37 };

test('a run that reached the surface reads with its impact time and place', () => {
    const result = fromPayload({ ...escape, status: 'impact', impact, notes: ['The spacecraft reached the Earth\'s surface.'] });
    assert.deepEqual(result.impact, { t: 512.25, utc: impact.utc, latitude_deg: 0.0, longitude_deg: 31.37 });
    assert.deepEqual(result.notes, ['The spacecraft reached the Earth\'s surface.']);
});

test('a run that stayed clear of the surface, or an older engine, has no impact', () => {
    assert.equal(fromPayload(escape).impact, null);
    assert.equal(fromPayload({ ...escape, status: 'ok', impact: null }).impact, null);
});

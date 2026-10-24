// Building /api/analysis/access requests from the last run and reading its answer.
// Run with: node --test astroflyer/tests/frontend/access.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';

import { toAccessRequest, fromAccess } from '../../frontend/js/access.js';

const MISSION = {
    spacecraft: { name: 'Molniya', orbitInput: 'apsides', hp: 1000, ha: 39350, inc: 63.4, raan: 45, aop: 270, ta: 0 },
    propagator: { method: 'DOP853', model: 'j2' },
};
const RESULT = {
    times: [0, 60, 120],
    duration: 129600,
    epoch: { utc: '2000-01-01T11:58:55.816000Z' },
    summary: { sma_km: 26553.137, eccentricity: 0.722 },
    stations: [
        { name: 'Svalbard KSAT', lat_deg: 78.23, lon_deg: 15.39, alt_m: 500, min_elevation_deg: 5 },
        { name: 'Madrid DSN', lat_deg: 40.43, lon_deg: -4.25, alt_m: 834, min_elevation_deg: 10 },
    ],
};

test('the request repeats the last run: its epoch, orbit, length, force model and stations', () => {
    const body = toAccessRequest(MISSION, RESULT);
    assert.equal(body.epoch, '2000-01-01T11:58:55.816000Z');
    // The engine's own reading of the orbit, not one recomputed here from perigee and apogee.
    assert.equal(body.sma_km, 26553.137);
    assert.equal(body.ecc, 0.722);
    assert.deepEqual([body.inc_deg, body.raan_deg, body.aop_deg, body.ta_deg], [63.4, 45, 270, 0]);
    assert.equal(body.duration_s, 129600);
    assert.equal(body.model, 'j2');
    assert.equal(body.method, 'DOP853');
    assert.ok(body.step_s >= 10 && body.step_s <= 60);
    assert.deepEqual(body.stations[1], { name: 'Madrid DSN', lat_deg: 40.43, lon_deg: -4.25, height_m: 834, min_elevation_deg: 10 });
    assert.ok(body.parameters.includes('BetaAngle'));
    assert.ok(body.parameters.includes('Elevation.Svalbard KSAT'));
});

test('a run without an epoch sends none, so the engine uses its default', () => {
    assert.equal(toAccessRequest(MISSION, { ...RESULT, epoch: null }).epoch, null);
});

const ANSWER = {
    passes: {
        'Svalbard KSAT': [{ aos_utc: '2000-01-01T14:00:00.000000Z', tca_utc: '2000-01-01T18:00:00.000000Z', los_utc: '2000-01-01T22:00:00.000000Z', duration_s: 28800, max_elevation_deg: 61.2, aos_azimuth_deg: 10, los_azimuth_deg: 300, partial: false }],
        'Madrid DSN': [{ aos_utc: '2000-01-01T12:30:00.000000Z', tca_utc: '2000-01-01T13:00:00.000000Z', los_utc: '2000-01-01T13:30:00.000000Z', duration_s: 3600, max_elevation_deg: 40, aos_azimuth_deg: 90, los_azimuth_deg: 200, partial: true }],
    },
    eclipses: [
        { body: 'MOON', kind: 'penumbra', start_utc: '2000-01-02T01:00:00.000000Z', end_utc: '2000-01-02T01:10:00.000000Z', duration_s: 600, partial: false },
        { body: 'EARTH', kind: 'umbra', start_utc: '2000-01-01T12:10:00.000000Z', end_utc: '2000-01-01T12:40:00.000000Z', duration_s: 1800, partial: false },
    ],
    beta_angle_deg: [-12.5, -12.4, -12.6],
    report: { Epoch: ['a', 'b'], ElapsedSecs: [0, 60], BetaAngle: [-12.5, -12.4] },
    error: null,
};

test('passes from every station and eclipses come back as single lists in time order', () => {
    const access = fromAccess(ANSWER);
    assert.equal(access.error, null);
    assert.deepEqual(access.passes.map((p) => p.station), ['Madrid DSN', 'Svalbard KSAT']);
    assert.deepEqual(access.passes[0], {
        station: 'Madrid DSN', aos: '2000-01-01T12:30:00.000000Z', tca: '2000-01-01T13:00:00.000000Z', los: '2000-01-01T13:30:00.000000Z',
        duration_s: 3600, max_elevation_deg: 40, aos_azimuth_deg: 90, los_azimuth_deg: 200, partial: true,
    });
    assert.deepEqual(access.eclipses.map((e) => [e.body, e.kind]), [['Earth', 'umbra'], ['Moon', 'penumbra']]);
});

test('the beta angle range and the report table come from the engine columns', () => {
    const access = fromAccess(ANSWER);
    assert.deepEqual([access.beta.min, access.beta.max], [-12.6, -12.4]);
    assert.deepEqual(access.report, { columns: ['Epoch', 'ElapsedSecs', 'BetaAngle'], rows: [['a', 0, -12.5], ['b', 60, -12.4]] });
});

test('an engine error is kept and the lists are empty', () => {
    const access = fromAccess({ error: 'Unknown parameter Foo', passes: {}, eclipses: [], beta_angle_deg: [], report: {} });
    assert.equal(access.error, 'Unknown parameter Foo');
    assert.deepEqual([access.passes, access.eclipses, access.report.rows], [[], [], []]);
    assert.deepEqual([access.beta.min, access.beta.max], [null, null]);
});

// Mission burns, mission files and continuing a run from its end: what the console keeps in a
// mission, what it sends to the engine, and the mission a continued run starts from.
// Run with: node --test astroflyer/tests/frontend/burns.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';

import { continueFromEnd, defaultMission, newBurn, readMissionFile, schemas, toPropagateRequest, validate, withDefaults } from '../../frontend/js/mission.js';
import { fromPayload } from '../../frontend/js/results.js';

const mission = (burns) => ({ ...structuredClone(defaultMission), burns });

test('a new mission has no burns, and a new burn is a valid along-track burn at the next perigee', () => {
    assert.deepEqual(defaultMission.burns, []);
    const burn = newBurn(2);
    assert.equal(burn.name, 'Burn 3');
    assert.equal(burn.timing, 'perigee');
    assert.deepEqual(validate(schemas.burn, burn), {});
});

test('a burn is sent with its time in seconds, its VNC velocity change and its specific impulse', () => {
    const body = toPropagateRequest(mission([
        { ...newBurn(0), timing: 'elapsed', elapsed_h: 1.5, dv_v: 12.5, dv_n: -1, dv_c: 0.25, isp: 320 },
        { ...newBurn(1), timing: 'apogee', dv_v: 3 },
    ]));
    assert.deepEqual(body.burns, [
        { name: 'Burn 1', timing: 'elapsed', t_s: 5400, dv_ms: [12.5, -1, 0.25], frame: 'VNC', isp_s: 320 },
        { name: 'Burn 2', timing: 'apogee', dv_ms: [3, 0, 0], frame: 'VNC', isp_s: 300 },
    ]);
    assert.deepEqual(toPropagateRequest(mission([])).burns, []);
});

test('the time field belongs to timed burns only, and bad burn values are refused', () => {
    const timed = { ...newBurn(0), timing: 'elapsed', elapsed_h: -1 };
    assert.ok(validate(schemas.burn, timed).elapsed_h);
    assert.equal(validate(schemas.burn, { ...timed, timing: 'apogee' }).elapsed_h, undefined);
    assert.ok(validate(schemas.burn, { ...newBurn(0), isp: 0 }).isp);
    assert.ok(validate(schemas.burn, { ...newBurn(0), dv_v: 'fast' }).dv_v);
});

test('a mission saved before burns existed opens with none, and saved burns take new fields from the defaults', () => {
    const old = withDefaults({ spacecraft: defaultMission.spacecraft, propagator: defaultMission.propagator });
    assert.deepEqual(old.burns, []);
    const saved = withDefaults({ ...defaultMission, burns: [{ name: 'Kick', timing: 'elapsed', elapsed_h: 2, dv_v: 5, stray: 1 }] });
    assert.deepEqual(saved.burns, [{ ...newBurn(0), name: 'Kick', timing: 'elapsed', elapsed_h: 2, dv_v: 5 }]);
});

test('a mission file opens, and one with a bad value or of another kind is refused with the reason', () => {
    const file = (m) => JSON.stringify({ format: 'astroflyer-mission', version: 1, mission: m });
    const opened = readMissionFile(file(mission([newBurn(0)])));
    assert.equal(opened.burns.length, 1);
    assert.throws(() => readMissionFile(file(mission([{ ...newBurn(0), isp: -5 }]))), /burn 1 isp/);
    assert.throws(() => readMissionFile('{"format": "something-else"}'), /not an AstroFlyer mission file/);
    assert.throws(() => readMissionFile('not json'), /not an AstroFlyer mission file/);
});

const finalState = {
    utc: '2026-01-01T11:59:35.108282Z', t_s: 43175.108282,
    position_km: [-1234.5678901234, 6543.21, 1500.125], velocity_kms: [-7.123456789012, -2.5, 3.75], mass_kg: 1432.75,
};

test('continuing from the end of a run starts the mission at the run\'s final state, with no burns', () => {
    const before = mission([newBurn(0)]);
    const next = continueFromEnd(before, { finalState, request: toPropagateRequest(before), burns: [{ applied: true }] });
    assert.equal(next.spacecraft.orbitInput, 'cartesian');
    assert.equal(next.spacecraft.epoch, '2026-01-01 11:59:35.108282');
    assert.deepEqual([next.spacecraft.x, next.spacecraft.y, next.spacecraft.z], finalState.position_km);
    assert.deepEqual([next.spacecraft.vx, next.spacecraft.vy, next.spacecraft.vz], finalState.velocity_kms);
    assert.equal(next.spacecraft.mass, 1432.75);
    assert.deepEqual(next.burns, []);
    assert.deepEqual(next.propagator, before.propagator);       // the settings stay for the user to change
    assert.deepEqual(validate(schemas.spacecraft, next.spacecraft), {});
    // The epoch survives the round trip to the engine to the microsecond
    assert.equal(toPropagateRequest(next).epoch, '2026-01-01T11:59:35.108282Z');
});

test('each continued leg is kept in the mission history, so a saved mission says where it came from', () => {
    const first = mission([newBurn(0)]);
    const next = continueFromEnd(first, { finalState, request: toPropagateRequest(first), burns: [{ applied: true }] });
    assert.deepEqual(next.history, [{
        start_epoch: '2026-01-01 00:00:00', end_epoch: '2026-01-01 11:59:35.108282', duration_s: 43175.108282,
        method: 'DOP853', model: 'coupled', burns: 1,
    }]);
    const third = continueFromEnd(next, { finalState: { ...finalState, utc: '2026-01-02T00:00:00.000000Z' }, request: toPropagateRequest(next), burns: [] });
    assert.equal(third.history.length, 2);
    assert.deepEqual(withDefaults(JSON.parse(JSON.stringify(third))).history, third.history);
});

test('the run result keeps the engine\'s final state and burn report', () => {
    const payload = {
        times: [0, 10], position_m: [[7e6, 0, 0], [7e6, 1e4, 0]], velocity_ms: [[0, 7500, 0], [0, 7500, 0]],
        position_itrf_m: [[7e6, 0, 0], [7e6, 1e4, 0]], longitude_deg: [0, 0], altitude_km: [622, 622],
        velocity_kms: [7.5, 7.5], energy_error: [0, 0], active_orbit_config: {},
        final_state: finalState, burns: [{ name: 'Burn 1', applied: true, t_s: 5 }],
        events: [{ type: 'burn', t_s: 5, utc: 'x', name: 'Burn 1' }],
    };
    const result = fromPayload(payload);
    assert.deepEqual(result.finalState, finalState);
    assert.deepEqual(result.burns, payload.burns);
    assert.deepEqual(fromPayload({ ...payload, final_state: undefined, burns: undefined }).burns, []);
});

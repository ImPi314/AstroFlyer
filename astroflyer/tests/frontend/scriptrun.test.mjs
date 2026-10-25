// Reading /api/script/run results into what the Data workspace shows. Run with: node --test astroflyer/tests/frontend
import { test } from 'node:test';
import assert from 'node:assert/strict';

import { fromScriptRun } from '../../frontend/js/scriptrun.js';

const OK = {
    log: ['start', 'sum ok'],
    reports: { Rpt: { columns: ['Sat.ElapsedSecs', 'Sat.SMA'], rows: [[100, 7000], [200, 7000.1]] } },
    spacecraft: {
        Sat: { epoch_utc: '2026-10-23T00:05:00.000Z', position_m: [7e6, 0, 0], velocity_ms: [0, 7546, 0], sma_km: 7000, ecc: 0.001, inc_deg: 28.5, raan_deg: 0, aop_deg: 10, ta_deg: 20, altitude_km: 621.9, mass_kg: 1790, fuel_mass_kg: 790 },
    },
    ephemeris: { Sat: { epochs_utc: ['a', 'b', 'c'], t_s: [0, 150, 300], position_m: [[1, 2, 3], [1, 2, 3], [1, 2, 3]], velocity_ms: [[0, 0, 0], [0, 0, 0], [0, 0, 0]] } },
    targets: [{
        name: 'RaiseApogee', line: 41, converged: true, message: 'Converged', iterations: 4,
        variables: { 'Burn.Element1': 2.45 },
        goals: { 'Sat.RMAG': { target: 42164, achieved: 42164.0004, tolerance: 0.1 } },
    }],
    error: null,
};

test('a finished run keeps its log, reports, final states and targets in order', () => {
    const run = fromScriptRun(OK);
    assert.equal(run.error, null);
    assert.deepEqual(run.log, ['start', 'sum ok']);
    assert.deepEqual(run.reports, [{ name: 'Rpt', columns: ['Sat.ElapsedSecs', 'Sat.SMA'], rows: [[100, 7000], [200, 7000.1]] }]);
    assert.equal(run.spacecraft.length, 1);
    assert.equal(run.spacecraft[0].name, 'Sat');
    assert.equal(run.spacecraft[0].sma_km, 7000);
    assert.equal(run.spacecraft[0].fuel_mass_kg, 790);
    assert.equal(run.spacecraft[0].points, 3);
    assert.deepEqual(run.targets, [{
        name: 'RaiseApogee', line: 41, converged: true, message: 'Converged', iterations: 4,
        variables: [['Burn.Element1', 2.45]],
        goals: [{ param: 'Sat.RMAG', target: 42164, achieved: 42164.0004, tolerance: 0.1 }],
    }]);
});

test('a script error keeps its message and line, and whatever ran before it', () => {
    const run = fromScriptRun({ log: ['start'], reports: {}, spacecraft: {}, ephemeris: {}, targets: [], error: { message: 'Unknown object Sat2', line: 12 } });
    assert.deepEqual(run.error, { message: 'Unknown object Sat2', line: 12 });
    assert.deepEqual(run.log, ['start']);
    assert.deepEqual(run.spacecraft, []);
});

test('missing sections read as empty, and an error without a line keeps the line unknown', () => {
    const run = fromScriptRun({ error: { message: 'Parse failed' } });
    assert.deepEqual(run.error, { message: 'Parse failed', line: null });
    assert.deepEqual([run.log, run.reports, run.spacecraft, run.targets], [[], [], [], []]);
});

test('a spacecraft with no ephemeris has an unknown point count, not zero', () => {
    const run = fromScriptRun({ ...OK, ephemeris: {} });
    assert.equal(run.spacecraft[0].points, null);
});

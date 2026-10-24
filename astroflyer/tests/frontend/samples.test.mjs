// Home-screen HEO samples: each one must open as a valid mission.
// Run with: node --test astroflyer/tests/frontend/samples.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';

import { SAMPLES, sampleMission } from '../../frontend/js/samples.js';
import { schemas, validate } from '../../frontend/js/mission.js';

test('the common HEO families are all there', () => {
    const names = SAMPLES.map((s) => s.name);
    for (const name of ['Molniya', 'Tundra', 'Sirius (Tundra)', 'QZS-1', 'GTO (Cape Canaveral)', 'GTO (Kourou)', 'Supersynchronous GTO', 'MMS phase 1', 'XMM-Newton', 'INTEGRAL', 'Chandra', 'Lunar transfer']) {
        assert.ok(names.includes(name), `missing ${name}`);
    }
    assert.equal(new Set(names).size, names.length, 'sample names must be unique');
});

test('every sample opens as a mission the inspector accepts', () => {
    for (const sample of SAMPLES) {
        const mission = sampleMission(sample);
        assert.equal(mission.spacecraft.name, sample.name);
        assert.deepEqual(validate(schemas.spacecraft, mission.spacecraft), {}, `${sample.name} spacecraft`);
        assert.deepEqual(validate(schemas.propagator, mission.propagator), {}, `${sample.name} propagator`);
    }
});

test('every sample says where its numbers come from', () => {
    for (const sample of SAMPLES) {
        assert.ok(sample.source && sample.source.length > 10, `${sample.name} needs a source`);
        assert.ok(sample.lead && !/[\u{1F300}-\u{1FAFF}]/u.test(sample.lead), `${sample.name} needs a plain lead`);
    }
});

test('opening a sample does not change the default mission', () => {
    const before = JSON.stringify(sampleMission(SAMPLES[0]));
    sampleMission(SAMPLES[1]).spacecraft.inc = 1;
    assert.equal(JSON.stringify(sampleMission(SAMPLES[0])), before);
});

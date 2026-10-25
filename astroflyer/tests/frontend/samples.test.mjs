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

// Mission samples match the sources they cite (checked 2026-10-25):
// Sirius: Gunter's Space Page, 23,975 x 46,983 km at 63.4 deg.
// Ariane 5 V192 (ESA): 250 x 35,786 km at 6 deg.
// XMM-Newton (ESA fact sheet): 7,000 x 114,000 km at 40 deg, apogee in the south.
// INTEGRAL (ESA orbit page): 9,000 x 153,000 km at 51.6 deg.
// Chandra initial operational orbit (Weisskopf et al. 2000): 10,000 x 140,000 km at 28.5 deg.
test('cited mission samples match their sources', () => {
    const orbit = (name) => SAMPLES.find((s) => s.name === name).spacecraft;
    assert.deepEqual(pick(orbit('Sirius (Tundra)')), { orbitInput: 'apsides', hp: 23975, ha: 46983, inc: 63.4 });
    assert.deepEqual(pick(orbit('GTO (Kourou)')), { orbitInput: 'apsides', hp: 250, ha: 35786, inc: 6 });
    assert.deepEqual(pick(orbit('XMM-Newton')), { orbitInput: 'apsides', hp: 7000, ha: 114000, inc: 40 });
    assert.ok(Math.sin(orbit('XMM-Newton').aop * Math.PI / 180) > 0.9, 'perigee north, so apogee south');
    assert.deepEqual(pick(orbit('INTEGRAL')), { orbitInput: 'apsides', hp: 9000, ha: 153000, inc: 51.6 });
    assert.deepEqual(pick(orbit('Chandra')), { orbitInput: 'apsides', hp: 10000, ha: 140000, inc: 28.5 });
});

function pick({ orbitInput, hp, ha, inc }) {
    return { orbitInput, hp, ha, inc };
}

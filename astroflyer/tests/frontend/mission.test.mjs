// Mission inputs: the start epoch field and what it sends to the engine.
// Run with: node --test astroflyer/tests/frontend/mission.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';

import { defaultMission, schemas, toPropagateRequest, validate } from '../../frontend/js/mission.js';

const withEpoch = (epoch) => ({ ...defaultMission.spacecraft, epoch });

test('the default mission has a start epoch inside the bundled ephemeris years', () => {
    assert.match(defaultMission.spacecraft.epoch, /^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$/);
    assert.deepEqual(validate(schemas.spacecraft, defaultMission.spacecraft), {});
});

test('the epoch is sent to the engine as ISO 8601 UTC', () => {
    const body = toPropagateRequest({ ...defaultMission, spacecraft: withEpoch('2026-10-24 06:30:00') });
    assert.equal(body.epoch, '2026-10-24T06:30:00Z');
    assert.equal(toPropagateRequest({ ...defaultMission, spacecraft: withEpoch('2026-10-24 06:30') }).epoch, '2026-10-24T06:30:00Z');
    assert.equal(toPropagateRequest({ ...defaultMission, spacecraft: withEpoch('2026-10-24 06:30:00.250') }).epoch, '2026-10-24T06:30:00.250Z');
});

test('dates and times that do not exist, or other formats, are rejected', () => {
    for (const bad of ['', 'tomorrow', '24/10/2026 06:30', '2026-02-30 00:00:00', '2026-10-24 25:00:00', '2026-10-24T06:30:00Z']) {
        assert.ok(validate(schemas.spacecraft, withEpoch(bad)).epoch, `${bad} should be rejected`);
    }
});

test('epochs outside the bundled 1990 to 2060 ephemeris are rejected', () => {
    assert.ok(validate(schemas.spacecraft, withEpoch('1989-12-31 23:59:59')).epoch);
    assert.ok(validate(schemas.spacecraft, withEpoch('2060-01-02 00:00:00')).epoch);
    assert.equal(validate(schemas.spacecraft, withEpoch('1990-01-01 00:00:00')).epoch, undefined);
});

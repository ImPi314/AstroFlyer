// Mission inputs: the start epoch field and what it sends to the engine.
// Run with: node --test astroflyer/tests/frontend/mission.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';

import { defaultMission, schemas, toPropagateRequest, validate, visibleFields } from '../../frontend/js/mission.js';

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

// ---------- Cartesian initial state and run length as a time ----------

const cartesian = {
    ...defaultMission.spacecraft, orbitInput: 'cartesian',
    x: 7000, y: 0, z: 0, vx: 0, vy: 7.5, vz: 1.2,
};

test('a position and velocity state is sent as GCRF vectors instead of elements', () => {
    const body = toPropagateRequest({ ...defaultMission, spacecraft: cartesian });
    assert.deepEqual(body.position_km, [7000, 0, 0]);
    assert.deepEqual(body.velocity_kms, [0, 7.5, 1.2]);
    for (const key of ['hp', 'ha', 'a', 'e', 'inc', 'raan', 'aop', 'ta']) assert.equal(body[key], undefined, key);
    assert.deepEqual(validate(schemas.spacecraft, cartesian), {});
});

test('a position at or inside the Earth is refused', () => {
    assert.ok(validate(schemas.spacecraft, { ...cartesian, x: 0 }).x);
    assert.ok(validate(schemas.spacecraft, { ...cartesian, x: 6000 }).x);
});

test('element inputs still send elements and no vectors', () => {
    const body = toPropagateRequest(defaultMission);
    assert.equal(body.position_km, undefined);
    assert.equal(body.hp, defaultMission.spacecraft.hp);
});

const span = (durationUnit, duration) => ({ ...defaultMission, propagator: { ...defaultMission.propagator, durationUnit, duration } });

test('a run length in hours or days is sent as seconds, and orbits stay orbits', () => {
    assert.equal(toPropagateRequest(span('hours', 36)).duration_s, 129600);
    assert.equal(toPropagateRequest(span('days', 2.5)).duration_s, 216000);
    const orbits = toPropagateRequest(defaultMission);
    assert.equal(orbits.duration_s, undefined);
    assert.equal(orbits.num_orbits, defaultMission.propagator.num_orbits);
    assert.equal(defaultMission.propagator.durationUnit, 'orbits');
});

test('run lengths beyond the engine limit of 30 days are refused', () => {
    assert.ok(validate(schemas.propagator, span('days', 31).propagator).duration);
    assert.ok(validate(schemas.propagator, span('hours', 721).propagator).duration);
    assert.deepEqual(validate(schemas.propagator, span('days', 30).propagator), {});
});

test('a new mission propagates with DOP853, and Radau is still offered', () => {
    assert.equal(defaultMission.propagator.method, 'DOP853');
    const method = schemas.propagator.groups.flatMap((g) => g.fields).find((f) => f.key === 'method');
    assert.ok(method.options.some(([value]) => value === 'Radau'));
    assert.equal(method.options[0][0], 'DOP853');
});

// ---------- Step control and gravity fidelity ----------

const prop = (changes) => ({ ...defaultMission, propagator: { ...defaultMission.propagator, ...changes } });
const shown = (values) => visibleFields(schemas.propagator, values).flatMap((g) => g.fields.map((f) => f.key));

test('a new mission uses error control only, the 8 x 8 field and a fixed gravity degree', () => {
    const body = toPropagateRequest(defaultMission);
    assert.equal(body.steering, undefined);
    assert.equal(body.fidelity, 'full');
    assert.equal(body.gravity_degree, 8);
    assert.deepEqual(validate(schemas.propagator, defaultMission.propagator), {});
});

test('covariance steering is offered for RKF7(8) and Bulirsch-Stoer only, and sent only for them', () => {
    for (const method of ['RKF78', 'BS']) {
        assert.ok(shown({ ...defaultMission.propagator, method }).includes('steering'), method);
        assert.equal(toPropagateRequest(prop({ method, steering: 'covariance' })).steering, 'covariance', method);
    }
    for (const method of ['DOP853', 'Radau', 'RK4']) {
        assert.ok(!shown({ ...defaultMission.propagator, method }).includes('steering'), method);
        assert.equal(toPropagateRequest(prop({ method, steering: 'covariance' })).steering, undefined, method);
    }
});

test('the gravity degree and ECR-MF belong to the full force model', () => {
    assert.ok(shown(defaultMission.propagator).includes('fidelity'));
    assert.ok(shown(defaultMission.propagator).includes('gravity_degree'));
    for (const model of ['two_body', 'j2', 'j2_j3_j4']) {
        const fields = shown({ ...defaultMission.propagator, model });
        assert.ok(!fields.includes('fidelity') && !fields.includes('gravity_degree'), model);
        const body = toPropagateRequest(prop({ model, fidelity: 'ecr_mf', gravity_degree: 70 }));
        assert.equal(body.fidelity, 'full', model);
        assert.equal(body.gravity_degree, undefined, model);
    }
    const body = toPropagateRequest(prop({ fidelity: 'ecr_mf', gravity_degree: 70 }));
    assert.equal(body.fidelity, 'ecr_mf');
    assert.equal(body.gravity_degree, 70);
});

test('gravity degrees outside 2 to 70 or not whole are refused', () => {
    for (const bad of [1, 71, 8.5]) assert.ok(validate(schemas.propagator, { ...defaultMission.propagator, gravity_degree: bad }).gravity_degree, String(bad));
    for (const good of [2, 8, 70]) assert.equal(validate(schemas.propagator, { ...defaultMission.propagator, gravity_degree: good }).gravity_degree, undefined, String(good));
});

test('a mission saved before a field existed takes that field from the defaults', async () => {
    const { withDefaults } = await import('../../frontend/js/mission.js');
    const old = { spacecraft: { ...defaultMission.spacecraft, name: 'Old' }, propagator: { method: 'RKF78', tolerance: 1e-11, model: 'coupled', enable_drag: false, enable_third_body: true, enable_srp: true, durationUnit: 'orbits', num_orbits: 2, duration: 1, points_per_orbit: 300, unknown: 1 } };
    const mission = withDefaults(old);
    assert.equal(mission.spacecraft.name, 'Old');
    assert.equal(mission.propagator.method, 'RKF78');
    assert.equal(mission.propagator.enable_drag, false);
    assert.equal(mission.propagator.steering, 'none');
    assert.equal(mission.propagator.fidelity, 'full');
    assert.equal(mission.propagator.gravity_degree, 8);
    assert.equal(mission.propagator.unknown, undefined);
    assert.deepEqual(validate(schemas.propagator, mission.propagator), {});
});

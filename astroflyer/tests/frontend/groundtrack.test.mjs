// The ground track is drawn whole: segments that cross the map's edge reach both edges,
// and the map puts its edge where the track crosses it least, so loops (Tundra, quasi-zenith,
// Molniya and GTO apogee loops) are drawn whole for any orbit.
// Run with: node --test astroflyer/tests/frontend/groundtrack.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';

import { splitAtEdge, trackCenter } from '../../frontend/js/views/groundtrack.js';

// Pieces are [lon0, lat0, lon1, lat1] in degrees from the map centre, -180 (left edge) to 180 (right edge).

test('a segment inside the map is one piece', () => {
    assert.deepEqual(splitAtEdge(10, 5, 20, 8, 0), [[10, 5, 20, 8]]);
    assert.deepEqual(splitAtEdge(170, 5, 175, 8, 150), [[20, 5, 25, 8]]);
});

test('a segment crossing the right edge reaches it and carries on from the left edge', () => {
    // 170 E to 170 W is 20 deg eastward; the edge at 180 is halfway, so at latitude 15
    assert.deepEqual(splitAtEdge(170, 10, -170, 20, 0), [[170, 10, 180, 15], [-180, 15, -170, 20]]);
});

test('a westward segment crossing the left edge does the same the other way', () => {
    // 175 W to 165 E is 20 deg westward; the edge is a quarter of the way, at latitude -10 + 0.25 * 20
    assert.deepEqual(splitAtEdge(-175, -10, 165, 10, 0), [[-175, -10, -180, -5], [180, -5, 165, 10]]);
});

test('the edge moves with the map centre', () => {
    // Centred on 90 W the edge is at 90 E: 80 E to 100 E crosses it halfway
    assert.deepEqual(splitAtEdge(80, 0, 100, 40, -90), [[170, 0, 180, 20], [-180, 20, -170, 40]]);
});

const range = (from, to, step) => Array.from({ length: Math.floor((to - from) / step) + 1 }, (_, k) => from + k * step);

test('a loop across the date line is centred on it, not cut in two', () => {
    // A Tundra figure eight from 140 E across 180 to 140 W: its middle is 180
    assert.equal(trackCenter([...range(140, 180, 2), ...range(-180, -140, 2)]), 180);
});

test('a loop elsewhere is centred on its own middle', () => {
    // A quasi-zenith figure eight over Japan, 120 E to 160 E
    assert.equal(trackCenter(range(120, 160, 2)), 140);
});

test('a track over every longitude keeps the map on Greenwich', () => {
    assert.equal(trackCenter(range(-180, 178, 3)), 0);
});

// Two-body ground tracks (spherical Earth, rotation only), enough to give each kind of orbit its shape.
const MU = 398600.4418;               // km^3/s^2
const EARTH_RATE = 7.2921150e-5;      // rad/s
function keplerTrack({ a, e, inc, raan, aop, orbits, gmst0 = 0, points = 400 }) {
    const rad = Math.PI / 180;
    const n = Math.sqrt(MU / a ** 3);
    const total = Math.round(points * orbits);
    const lon = [];
    for (let k = 0; k <= total; k++) {
        const t = ((k / points) * 2 * Math.PI) / n;
        const M = n * t;
        let E = M;
        for (let it = 0; it < 30; it++) E -= (E - e * Math.sin(E) - M) / (1 - e * Math.cos(E));
        const nu = 2 * Math.atan2(Math.sqrt(1 + e) * Math.sin(E / 2), Math.sqrt(1 - e) * Math.cos(E / 2));
        const u = aop * rad + nu;
        const [O, i] = [raan * rad, inc * rad];
        const x = Math.cos(O) * Math.cos(u) - Math.sin(O) * Math.sin(u) * Math.cos(i);
        const y = Math.sin(O) * Math.cos(u) + Math.cos(O) * Math.sin(u) * Math.cos(i);
        const lonDeg = (Math.atan2(y, x) - EARTH_RATE * t) / rad - gmst0;
        lon.push(((lonDeg + 540) % 360 + 360) % 360 - 180);
    }
    return lon;
}

// Times the track jumps from one edge of a map centred on `center` to the other.
function edgeCrossings(lon, center) {
    let count = 0;
    for (let k = 1; k < lon.length; k++) {
        const r0 = ((lon[k - 1] - center + 540) % 360 + 360) % 360 - 180;
        const r1 = ((lon[k] - center + 540) % 360 + 360) % 360 - 180;
        if (Math.abs(r1 - r0) > 180) count++;
    }
    return count;
}

const fewestCrossings = (lon) => Math.min(...Array.from({ length: 360 }, (_, c) => edgeCrossings(lon, c - 179)));

const ORBITS = {
    'LEO, 400 km at 51.6 deg': { a: 6778, e: 0.0005, inc: 51.6, raan: 30, aop: 0, orbits: 5 },
    'Sun-synchronous LEO (retrograde)': { a: 7078, e: 0.001, inc: 98.2, raan: 100, aop: 90, orbits: 4 },
    Molniya: { a: 26554, e: 0.722, inc: 63.4, raan: 45, aop: 270, orbits: 3 },
    'Molniya over 20 orbits': { a: 26554, e: 0.722, inc: 63.4, raan: 45, aop: 270, orbits: 20 },
    'Tundra across the date line': { a: 42164, e: 0.25, inc: 63.4, raan: 260, aop: 270, orbits: 2 },
    'QZS figure eight across the date line': { a: 42164, e: 0.075, inc: 41, raan: 270, aop: 270, orbits: 2 },
    'QZS figure eight over Japan': { a: 42164, e: 0.075, inc: 41, raan: 235, aop: 270, orbits: 2 },
    'GEO drifting east across the date line': { a: 42100, e: 0.0002, inc: 0.1, raan: 0, aop: 0, orbits: 3, gmst0: -178 },
    'GTO from Cape Canaveral': { a: 24396, e: 0.728, inc: 28.5, raan: 0, aop: 180, orbits: 3 },
    'Supersynchronous GTO': { a: 39028, e: 0.829, inc: 27, raan: 0, aop: 180, orbits: 2 },
    'Retrograde high-e orbit': { a: 30000, e: 0.75, inc: 120, raan: 70, aop: 250, orbits: 3 },
    'High-e science orbit (e = 0.88)': { a: 67000, e: 0.88, inc: 51.6, raan: 10, aop: 0, orbits: 1 },
};

for (const [name, orbit] of Object.entries(ORBITS)) {
    test(`${name}: the map edge goes where the track crosses it least, wherever the orbit lies`, () => {
        for (let turn = 0; turn < 360; turn += 30) {
            const lon = keplerTrack({ ...orbit, raan: orbit.raan + turn });
            assert.equal(edgeCrossings(lon, trackCenter(lon)), fewestCrossings(lon), `RAAN ${orbit.raan + turn} deg`);
        }
    });
}

test('a regional loop is never split, whichever longitude it sits at', () => {
    for (let raan = 0; raan < 360; raan += 15) {
        const lon = keplerTrack({ a: 42164, e: 0.075, inc: 41, raan, aop: 270, orbits: 2 });
        assert.equal(edgeCrossings(lon, trackCenter(lon)), 0, `QZS loop with RAAN ${raan} deg`);
    }
});

// The ground track is drawn whole: segments that cross the map's edge reach both edges,
// and the map centres itself so a loop such as a Tundra figure eight isn't split.
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

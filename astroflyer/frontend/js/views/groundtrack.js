// Ground track on an equirectangular map. Latitude and longitude come from the engine;
// the night side uses the same Sun direction as the engine's shadow events.
// One instance per pane; ctx gives this pane's settings and tracks subscriptions.

import * as store from '../store.js';
import { stateAt } from '../results.js';
import { altitudeColor, css, rgb, token } from './colors.js';

const DEG = Math.PI / 180;
const NIGHT_W = 180;
const NIGHT_H = 90;
const COLOR_STEPS = 12;

let seam = 0;   // a segment longer than this crosses the map's edge (set before each draw)

export const groundtrackDefaults = () => ({
    center: 'track',
    center_lon: 0,
    night: true,
    stations: true,
    masks: false,
    footprint: true,
});

export function createGroundtrack(ctx) {
    const canvas = document.createElement('canvas');
    canvas.className = 'view-canvas';
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', 'Ground track of the spacecraft on a world map');
    ctx.body.append(canvas);

    const night = document.createElement('canvas');
    night.width = NIGHT_W;
    night.height = NIGHT_H;

    let map = null;
    let pending = false;
    const image = new Image();
    image.onload = () => { map = image; requestDraw(); };
    image.src = 'textures/earth.png';

    const requestDraw = () => {
        if (pending) return;
        pending = true;
        requestAnimationFrame(() => {
            pending = false;
            draw(canvas, night, map, ctx.settings());
        });
    };

    const observer = new ResizeObserver(requestDraw);
    observer.observe(ctx.body);
    ctx.on(['result', 'time'], requestDraw);
    ctx.onSettings(requestDraw);
    return { destroy: () => observer.disconnect() };
}

function draw(canvas, night, map, settings) {
    const body = canvas.parentElement;
    const dpr = window.devicePixelRatio || 1;
    const bw = body.clientWidth;
    const bh = body.clientHeight;
    if (!bw || !bh) return;
    canvas.width = Math.round(bw * dpr);
    canvas.height = Math.round(bh * dpr);
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, bw, bh);

    // Largest 2:1 rectangle that fits, centred.
    const w = Math.min(bw, bh * 2);
    const h = w / 2;
    const ox = (bw - w) / 2;
    seam = w / 2;
    const oy = (bh - h) / 2;

    const result = store.get('result');
    const now = result ? stateAt(result, store.get('time')) : null;
    const centerLon = settings.center === 'spacecraft' && now ? now.lonDeg
        : settings.center === 'longitude' ? settings.center_lon
        : settings.center === 'track' && result ? centerOf(result) : 0;
    const x = (lon) => ox + (((lon - centerLon + 540) % 360) / 360) * w;
    const y = (lat) => oy + ((90 - lat) / 180) * h;

    ctx.save();
    ctx.beginPath();
    ctx.rect(ox, oy, w, h);
    ctx.clip();

    if (map) {
        const shift = (((-centerLon % 360) + 360) % 360) / 360 * w;
        ctx.globalAlpha = 0.85;
        ctx.drawImage(map, ox + shift, oy, w, h);
        ctx.drawImage(map, ox + shift - w, oy, w, h);
        ctx.globalAlpha = 1;
    }

    drawGrid(ctx, x, y, ox, oy, w, h);
    if (result && settings.night) drawNight(ctx, night, now, centerLon, ox, oy, w, h);
    if (result) drawTrack(ctx, result, now, (rel) => ox + ((rel + 180) / 360) * w, y, centerLon);
    if (result && settings.masks) drawMasks(ctx, result, now, x, y);
    if (result && settings.footprint) drawFootprint(ctx, result, now, x, y);
    if (result && settings.stations) drawStations(ctx, result, x, y);
    if (now) drawCraft(ctx, x(now.lonDeg), y(now.latDeg));
    ctx.restore();

    ctx.strokeStyle = token('--line');
    ctx.strokeRect(ox + 0.5, oy + 0.5, w - 1, h - 1);
}

function drawGrid(ctx, x, y, ox, oy, w, h) {
    ctx.strokeStyle = css(rgb('--text'), 0.12);
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let lat = -60; lat <= 60; lat += 30) {
        ctx.moveTo(ox, Math.round(y(lat)) + 0.5);
        ctx.lineTo(ox + w, Math.round(y(lat)) + 0.5);
    }
    for (let lon = -180; lon < 180; lon += 30) {
        const px = Math.round(x(lon)) + 0.5;
        ctx.moveTo(px, oy);
        ctx.lineTo(px, oy + h);
    }
    ctx.stroke();
}

// Night side shaded on a coarse grid and scaled up, which softens the terminator.
function drawNight(ctx, night, now, centerLon, ox, oy, w, h) {
    const [sx, sy, sz] = now.sun;
    const c = Math.cos(now.theta);
    const s = Math.sin(now.theta);
    const sun = [c * sx + s * sy, -s * sx + c * sy, sz];   // Sun in the Earth-fixed frame
    const n = night.getContext('2d');
    const image = n.createImageData(NIGHT_W, NIGHT_H);
    const [r, g, b] = rgb('--sky').map((v) => Math.round(v * 255));
    for (let j = 0; j < NIGHT_H; j++) {
        const lat = (90 - (j + 0.5) * (180 / NIGHT_H)) * DEG;
        for (let i = 0; i < NIGHT_W; i++) {
            const lon = (centerLon - 180 + (i + 0.5) * (360 / NIGHT_W)) * DEG;
            const dot = Math.cos(lat) * Math.cos(lon) * sun[0] + Math.cos(lat) * Math.sin(lon) * sun[1] + Math.sin(lat) * sun[2];
            const k = (j * NIGHT_W + i) * 4;
            image.data[k] = r;
            image.data[k + 1] = g;
            image.data[k + 2] = b;
            image.data[k + 3] = Math.round(150 * Math.min(Math.max(0.5 - dot * 6, 0), 1));
        }
    }
    n.putImageData(image, 0, 0);
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(night, ox, oy, w, h);
}

const wrap180 = (deg) => ((deg + 540) % 360) - 180;

// Map centre for a track, so as little of it as possible is cut at the map's edge. The edge goes on
// the meridian the track crosses the fewest times: none for a loop over one region (a Tundra or
// quasi-zenith figure eight, a drifting GEO), and for a track that goes round the world (LEO,
// Molniya, GTO) a quick low pass rather than through an apogee loop, which it would cut several
// times. Of those meridians, the one farthest from the track; then the centre is rounded to 10 deg
// (or 5 deg) when that cuts no more and stays nearly as clear, and ties go to Greenwich.
export function trackCenter(lon) {
    const at = Array.from(lon, (l) => ((l % 360) + 360) % 360).filter(Number.isFinite);
    if (!at.length) return 0;
    const crossings = new Array(360).fill(0);   // by edge meridian, whole degrees east
    for (let k = 1; k < at.length; k++) {
        let d = at[k] - at[k - 1];
        d -= 360 * Math.round(d / 360);   // the short way round
        // Meridians the segment reaches, counting its end but not its start, so a pass counts once.
        const [from, to] = d >= 0 ? [Math.floor(at[k - 1]) + 1, Math.floor(at[k - 1] + d)] : [Math.ceil(at[k - 1] + d), Math.ceil(at[k - 1]) - 1];
        for (let m = from; m <= to; m++) crossings[((m % 360) + 360) % 360]++;
    }
    const sorted = [...at].sort((p, q) => p - q);
    const clearance = (edge) => {
        let lo = 0;
        let hi = sorted.length;
        while (lo < hi) {
            const mid = (lo + hi) >> 1;
            if (sorted[mid] < edge) lo = mid + 1; else hi = mid;
        }
        const after = lo < sorted.length ? sorted[lo] - edge : sorted[0] + 360 - edge;
        const before = lo > 0 ? edge - sorted[lo - 1] : edge - sorted[sorted.length - 1] + 360;
        return Math.min(after, before);
    };
    const edgeOf = (center) => ((center + 180) % 360 + 360) % 360;
    const offGreenwich = (center) => Math.abs(wrap180(center));

    let best = 0;   // centre, whole degrees
    for (let center = -179; center <= 180; center++) {
        const [e, b] = [edgeOf(center), edgeOf(best)];
        const fewer = crossings[e] - crossings[b];
        const clearer = clearance(e) - clearance(b);
        if (fewer < 0 || (fewer === 0 && (clearer > 1e-9 || (Math.abs(clearer) <= 1e-9 && offGreenwich(center) < offGreenwich(best))))) best = center;
    }
    const bestEdge = edgeOf(best);
    for (const step of [10, 5]) {
        const round = Math.round(best / step) * step;
        const e = edgeOf(round);
        if (crossings[e] === crossings[bestEdge] && clearance(e) >= Math.min(clearance(bestEdge) / 2, clearance(bestEdge) - 5)) {
            return round === -180 ? 180 : round + 0;   // + 0 turns -0 into 0
        }
    }
    return best === -180 ? 180 : best;
}

const centers = new WeakMap();   // run result -> its track centre
function centerOf(result) {
    if (!centers.has(result)) centers.set(result, trackCenter(result.samples.longitude_deg));
    return centers.get(result);
}

// One track segment as pieces [lon0, lat0, lon1, lat1], longitudes in degrees from the map centre
// (-180 is the left edge, 180 the right). A segment that crosses the edge is cut where it meets it,
// latitude interpolated, and carries on from the other edge, so the track has no gaps there.
export function splitAtEdge(lon0, lat0, lon1, lat1, centerLon) {
    const r0 = wrap180(lon0 - centerLon);
    let d = lon1 - lon0;
    d -= 360 * Math.round(d / 360);   // the short way round
    const r1 = r0 + d;
    if (r1 >= -180 && r1 <= 180) return [[r0, lat0, r1, lat1]];
    const edge = r1 > 180 ? 180 : -180;
    const latEdge = lat0 + ((edge - r0) / d) * (lat1 - lat0);
    return [[r0, lat0, edge, latEdge], [-edge, latEdge, r1 - 2 * edge, lat1]];
}

// xr maps a longitude from the map centre (see splitAtEdge) to the canvas.
function drawTrack(ctx, result, now, xr, y, centerLon) {
    const { latitude_deg: lat, longitude_deg: lon, altitude_km: alt } = result.samples;
    const min = Math.min(...alt);
    const max = Math.max(...alt);
    const paths = Array.from({ length: COLOR_STEPS }, () => [new Path2D(), new Path2D()]);
    for (let i = 1; i < lat.length; i++) {
        const step = Math.min(Math.floor(((alt[i] - min) / (max - min || 1)) * COLOR_STEPS), COLOR_STEPS - 1);
        const path = paths[step][i <= now.index ? 0 : 1];
        for (const [a0, b0, a1, b1] of splitAtEdge(lon[i - 1], lat[i - 1], lon[i], lat[i], centerLon)) {
            path.moveTo(xr(a0), y(b0));
            path.lineTo(xr(a1), y(b1));
        }
    }
    ctx.lineWidth = 1.5;
    paths.forEach(([past, future], step) => {
        const color = altitudeColor(min + ((step + 0.5) / COLOR_STEPS) * (max - min), min, max);
        ctx.strokeStyle = css(color, 0.35);
        ctx.stroke(future);
        ctx.strokeStyle = css(color, 1);
        ctx.stroke(past);
    });
}

// Ground that can see the spacecraft above the horizon.
function drawFootprint(ctx, result, now, x, y) {
    const lambda = Math.acos(Math.min(result.earthRadiusKm / now.radiusKm, 1));
    ctx.strokeStyle = css(rgb('--amber'), 0.55);
    drawCircle(ctx, now.latDeg, now.lonDeg, lambda, x, y);
}

// Around each station, where the spacecraft (at its current distance) clears the station's
// minimum elevation: the station mask projected onto the ground.
function drawMasks(ctx, result, now, x, y) {
    ctx.strokeStyle = css(rgb('--contact'), 0.5);
    for (const st of result.stations) {
        const el = st.min_elevation_deg * DEG;
        const lambda = Math.acos(Math.min((result.earthRadiusKm / now.radiusKm) * Math.cos(el), 1)) - el;
        if (lambda > 0) drawCircle(ctx, st.lat_deg, st.lon_deg, lambda, x, y);
    }
}

// Small circle of angular radius lambda (rad) around a point, split where it crosses the map edge.
function drawCircle(ctx, latDeg, lonDeg, lambda, x, y) {
    const lat0 = latDeg * DEG;
    const lon0 = lonDeg * DEG;
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 3]);
    ctx.beginPath();
    let prev = null;
    for (let k = 0; k <= 180; k++) {
        const az = (k / 180) * 2 * Math.PI;
        const lat = Math.asin(Math.sin(lat0) * Math.cos(lambda) + Math.cos(lat0) * Math.sin(lambda) * Math.cos(az));
        const lon = lon0 + Math.atan2(Math.sin(az) * Math.sin(lambda) * Math.cos(lat0), Math.cos(lambda) - Math.sin(lat0) * Math.sin(lat));
        const px = x(lon / DEG);
        const py = y(lat / DEG);
        if (prev !== null && Math.abs(px - prev) < seam) ctx.lineTo(px, py); else ctx.moveTo(px, py);
        prev = px;
    }
    ctx.stroke();
    ctx.setLineDash([]);
}

function drawStations(ctx, result, x, y) {
    const t = store.get('time');
    ctx.font = `500 11px ${token('--font')}`;
    ctx.textBaseline = 'middle';
    const placed = [];   // label boxes already drawn; a label that would overlap one is skipped
    for (const st of result.stations) {
        const inView = st.passes.some((p) => t >= p.t0 && t <= p.t1);
        const px = Math.round(x(st.lon_deg));
        const py = Math.round(y(st.lat_deg));
        ctx.fillStyle = inView ? token('--contact') : token('--muted');
        ctx.fillRect(px - 2.5, py - 2.5, 5, 5);
        if (inView) {
            const label = st.name.replace(/\s*\(.*\)$/, '');
            const box = [px + 6, py - 7, ctx.measureText(label).width, 14];
            const clear = placed.every(([bx, by, bw, bh]) => box[0] > bx + bw || box[0] + box[2] < bx || box[1] > by + bh || box[1] + box[3] < by);
            if (clear) {
                placed.push(box);
                ctx.fillStyle = token('--text');
                ctx.fillText(label, box[0], py);
            }
        }
    }
}

function drawCraft(ctx, px, py) {
    ctx.beginPath();
    ctx.arc(px, py, 4.5, 0, 2 * Math.PI);
    ctx.fillStyle = token('--amber');
    ctx.fill();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = token('--sky');
    ctx.stroke();
}

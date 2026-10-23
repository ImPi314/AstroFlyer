// Ground track on an equirectangular map. Latitude and longitude come from the engine;
// the night side uses the same Sun direction as the engine's shadow events.

import * as store from '../store.js';
import { stateAt } from '../results.js';
import { altitudeColor, css, rgb, token } from './colors.js';

const DEG = Math.PI / 180;
const NIGHT_W = 180;
const NIGHT_H = 90;
const COLOR_STEPS = 12;

let canvas;
let map = null;
let night;
let pending = false;
let seam = 0;   // a segment longer than this crosses the map's edge

export function mountGroundtrack(body) {
    canvas = document.createElement('canvas');
    canvas.className = 'view-canvas';
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', 'Ground track of the spacecraft on a world map');
    body.append(canvas);

    night = document.createElement('canvas');
    night.width = NIGHT_W;
    night.height = NIGHT_H;

    const image = new Image();
    image.onload = () => { map = image; requestDraw(); };
    image.src = 'textures/earth.png';

    new ResizeObserver(requestDraw).observe(body);
    store.on(['result', 'time', 'views'], requestDraw);
}

function requestDraw() {
    if (pending) return;
    pending = true;
    requestAnimationFrame(draw);
}

function draw() {
    pending = false;
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

    const settings = store.get('views').groundtrack;
    const result = store.get('result');
    const now = result ? stateAt(result, store.get('time')) : null;
    const centerLon = settings.center === 'spacecraft' && now ? now.lonDeg : 0;
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
    if (result && settings.night) drawNight(ctx, result, now, centerLon, ox, oy, w, h);
    if (result) drawTrack(ctx, result, now, x, y);
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
function drawNight(ctx, result, now, centerLon, ox, oy, w, h) {
    const [sx, sy, sz] = result.sunDirection;
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

function drawTrack(ctx, result, now, x, y) {
    const { latitude_deg: lat, longitude_deg: lon, altitude_km: alt } = result.samples;
    const min = Math.min(...alt);
    const max = Math.max(...alt);
    const paths = Array.from({ length: COLOR_STEPS }, () => [new Path2D(), new Path2D()]);
    for (let i = 1; i < lat.length; i++) {
        const x0 = x(lon[i - 1]);
        const x1 = x(lon[i]);
        if (Math.abs(x1 - x0) > seam) continue;
        const step = Math.min(Math.floor(((alt[i] - min) / (max - min || 1)) * COLOR_STEPS), COLOR_STEPS - 1);
        const path = paths[step][i <= now.index ? 0 : 1];
        path.moveTo(x0, y(lat[i - 1]));
        path.lineTo(x1, y(lat[i]));
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

// Area that can see the spacecraft above the horizon.
function drawFootprint(ctx, result, now, x, y) {
    const lambda = Math.acos(Math.min(result.earthRadiusKm / now.radiusKm, 1));
    const lat0 = now.latDeg * DEG;
    const lon0 = now.lonDeg * DEG;
    ctx.strokeStyle = css(rgb('--amber'), 0.55);
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

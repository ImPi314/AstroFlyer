// Timeline: run controls, the elapsed clock, playback, and the event track you can scrub.

import * as store from './store.js';
import { sampleIndex, eventTimes } from './results.js';
import { elapsed, icon } from './format.js';
import { startRun, stopRun, isRunning } from './run.js';
import { applyAll } from './inspector.js';
import { log } from './messages.js';

const SPEEDS = [60, 300, 600, 1800, 3600];
let root;
let track;
let canvas;
let lastFrame = null;
let loop = 0;   // id of the active playback loop, so only one advances time

export function mountTimeline(element) {
    root = element;
    root.innerHTML = `
        <div class="transport">
            <button class="button button-primary" type="button" data-action="run" title="Run (F5)">${icon('play')}<span>Run</span></button>
            <button class="icon-button" type="button" data-action="play" title="Play or pause (Space)">${icon('play')}</button>
            <button class="icon-button" type="button" data-action="stop" aria-label="Stop" title="Stop">${icon('square')}</button>
            <button class="icon-button" type="button" data-action="step" aria-label="Step one point" title="Step one point">${icon('step-forward')}</button>
        </div>
        <div class="clock">
            <span class="clock-now" aria-live="off"></span>
            <span class="clock-total"></span>
        </div>
        <div class="track-wrap">
            <div class="track" role="slider" tabindex="0" aria-label="Time in run">
                <canvas></canvas>
            </div>
            <ul class="legend">
                <li><i class="key key-perigee"></i>Perigee</li>
                <li><i class="key key-apogee"></i>Apogee</li>
                <li><i class="key key-shadow"></i>Shadow</li>
                <li><i class="key key-contact"></i>Station contact</li>
            </ul>
        </div>
        <div class="transport">
            <button class="icon-button" type="button" data-action="prev" aria-label="Previous event" title="Previous event">${icon('skip-back')}</button>
            <button class="icon-button" type="button" data-action="next" aria-label="Next event" title="Next event">${icon('skip-forward')}</button>
            <label class="speed">
                <span class="visually-hidden">Playback speed</span>
                <select data-action="speed">${SPEEDS.map((s) => `<option value="${s}" ${s === store.get('speed') ? 'selected' : ''}>${s}x</option>`).join('')}</select>
            </label>
        </div>`;

    track = root.querySelector('.track');
    canvas = track.querySelector('canvas');

    root.addEventListener('click', onClick);
    root.querySelector('[data-action="speed"]').addEventListener('change', (e) => store.set({ speed: Number(e.target.value) }));
    track.addEventListener('pointerdown', onPointer);
    track.addEventListener('keydown', onTrackKey);
    document.addEventListener('keydown', onGlobalKey);
    new ResizeObserver(draw).observe(track);

    store.on(['result', 'time'], draw);
    store.on(['result', 'time', 'run', 'playing'], renderControls);
    store.on('playing', (playing) => {
        if (!playing) return;
        const id = ++loop;
        lastFrame = null;
        requestAnimationFrame((now) => tick(now, id));
    });
    renderControls();
}

export function run() {
    if (isRunning()) return;
    if (!applyAll()) {
        log('error', 'Fix the highlighted fields before running.');
        return;
    }
    startRun();
}

function renderControls() {
    const result = store.get('result');
    const running = store.get('run').status === 'running';
    const playing = store.get('playing');
    const t = store.get('time');
    const runBtn = root.querySelector('[data-action="run"]');
    runBtn.disabled = running;
    runBtn.querySelector('span').textContent = running ? 'Running' : 'Run';
    const playBtn = root.querySelector('[data-action="play"]');
    playBtn.disabled = !result;
    playBtn.setAttribute('aria-label', playing ? 'Pause' : 'Play');
    playBtn.innerHTML = icon(playing ? 'pause' : 'play');
    root.querySelector('[data-action="stop"]').disabled = !running && !playing && (!result || t === result.times[0]);
    for (const action of ['step', 'prev', 'next']) root.querySelector(`[data-action="${action}"]`).disabled = !result;

    root.querySelector('.clock-now').textContent = result ? elapsed(t - result.times[0]) : 'T+ 00:00:00';
    root.querySelector('.clock-total').textContent = result ? `of ${elapsed(result.duration).slice(3)}` : 'No run yet';
    track.setAttribute('aria-valuemin', '0');
    track.setAttribute('aria-valuemax', String(Math.round(result?.duration ?? 0)));
    track.setAttribute('aria-valuenow', String(Math.round(result ? t - result.times[0] : 0)));
    track.setAttribute('aria-valuetext', result ? elapsed(t - result.times[0]) : 'No run yet');
}

function tick(now, id) {
    if (!store.get('playing') || id !== loop) return;
    const result = store.get('result');
    if (lastFrame !== null) {
        const t = store.get('time') + ((now - lastFrame) / 1000) * store.get('speed');
        const end = result.times.at(-1);
        store.set(t >= end ? { time: end, playing: false } : { time: t });
    }
    lastFrame = now;
    requestAnimationFrame((next) => tick(next, id));
}

function step(direction) {
    const result = store.get('result');
    const i = sampleIndex(result, store.get('time'));
    const next = Math.min(Math.max(i + direction, 0), result.times.length - 1);
    store.set({ playing: false, time: result.times[next] });
}

function jump(direction) {
    const result = store.get('result');
    const t = store.get('time');
    const points = eventTimes(result);
    const target = direction > 0 ? points.find((p) => p > t + 1e-6) : points.findLast((p) => p < t - 1e-6);
    if (target !== undefined) store.set({ playing: false, time: target });
}

function onClick(event) {
    const action = event.target.closest('button[data-action]')?.dataset.action;
    const result = store.get('result');
    switch (action) {
        case 'run': run(); break;
        case 'play':
            if (result && store.get('time') >= result.times.at(-1)) store.set({ time: result.times[0] });
            store.set({ playing: !store.get('playing') });
            break;
        case 'stop':
            if (isRunning()) stopRun();
            store.set({ playing: false, time: result ? result.times[0] : 0 });
            break;
        case 'step': step(1); break;
        case 'prev': jump(-1); break;
        case 'next': jump(1); break;
        default: break;
    }
}

function timeAtPointer(event) {
    const result = store.get('result');
    const rect = track.getBoundingClientRect();
    const frac = Math.min(Math.max((event.clientX - rect.left) / rect.width, 0), 1);
    return result.times[0] + frac * result.duration;
}

function onPointer(event) {
    if (!store.get('result')) return;
    track.setPointerCapture(event.pointerId);
    store.set({ playing: false, time: timeAtPointer(event) });
    const move = (e) => store.set({ time: timeAtPointer(e) });
    const up = () => { track.removeEventListener('pointermove', move); track.removeEventListener('pointerup', up); };
    track.addEventListener('pointermove', move);
    track.addEventListener('pointerup', up);
}

function onTrackKey(event) {
    const result = store.get('result');
    if (!result) return;
    switch (event.key) {
        case 'ArrowRight': step(1); break;
        case 'ArrowLeft': step(-1); break;
        case 'PageUp': jump(1); break;
        case 'PageDown': jump(-1); break;
        case 'Home': store.set({ playing: false, time: result.times[0] }); break;
        case 'End': store.set({ playing: false, time: result.times.at(-1) }); break;
        default: return;
    }
    event.preventDefault();
}

function onGlobalKey(event) {
    if (event.key === 'F5') {
        event.preventDefault();
        run();
        return;
    }
    const typing = event.target.closest('input, select, textarea, button, [role="slider"], [role="treeitem"]');
    if (event.key === ' ' && !typing && store.get('result')) {
        event.preventDefault();
        store.set({ playing: !store.get('playing') });
    }
}

function draw() {
    const dpr = window.devicePixelRatio || 1;
    const width = track.clientWidth;
    const height = track.clientHeight;
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);

    const css = getComputedStyle(document.documentElement);
    const color = (name) => css.getPropertyValue(name).trim();
    const mid = Math.round(height / 2) + 0.5;

    ctx.strokeStyle = color('--line');
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, mid);
    ctx.lineTo(width, mid);
    ctx.stroke();

    const result = store.get('result');
    if (!result) return;
    const x = (t) => ((t - result.times[0]) / result.duration) * width;

    ctx.fillStyle = color('--eclipse');
    for (const s of result.shadows) ctx.fillRect(x(s.t0), mid - 14, Math.max(2, x(s.t1) - x(s.t0)), 4);

    ctx.fillStyle = color('--contact');
    ctx.globalAlpha = 0.6;
    for (const st of result.stations) {
        for (const p of st.passes) ctx.fillRect(x(p.t0), mid + 10, Math.max(2, x(p.t1) - x(p.t0)), 4);
    }
    ctx.globalAlpha = 1;

    for (const a of result.apsides) {
        const px = Math.round(x(a.t)) + 0.5;
        ctx.strokeStyle = a.kind === 'perigee' ? color('--text') : color('--muted');
        ctx.beginPath();
        ctx.moveTo(px, a.kind === 'perigee' ? mid - 8 : mid - 5);
        ctx.lineTo(px, a.kind === 'perigee' ? mid + 8 : mid + 5);
        ctx.stroke();
    }

    const cx = Math.round(x(store.get('time'))) + 0.5;
    ctx.strokeStyle = color('--amber');
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(cx, 2);
    ctx.lineTo(cx, height - 2);
    ctx.stroke();
}

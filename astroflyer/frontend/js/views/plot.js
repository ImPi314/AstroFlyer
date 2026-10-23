// Plot: one engine parameter against elapsed time, with the timeline's time as a cursor line.
// uPlot comes from vendor/uPlot.iife.min.js, loaded as a classic script before the modules.

import * as store from '../store.js';
import { sampleIndex } from '../results.js';
import { PARAMETERS, GROUPS, parameter } from '../parameters.js';
import { icon, num, sci } from '../format.js';
import { token } from './colors.js';

const uPlot = window.uPlot;

let body;
let chart = null;
let builtFor = null;   // [result, parameter key] the chart was built from
let hours = [];        // x values: elapsed hours of each output point
let values = [];       // y values as drawn (non-positive values dropped on a log scale)
let shownIndex = -1;   // last point drawn

export function mountPlot(element, tools) {
    body = element;
    tools.innerHTML = `
        <label class="compact-select">
            <span class="visually-hidden">Parameter</span>
            <select data-plot="y">${GROUPS.map((group) => `<optgroup label="${group}">${PARAMETERS.filter((p) => p.group === group).map((p) => `<option value="${p.key}">${p.label}</option>`).join('')}</optgroup>`).join('')}</select>
        </label>
        <button class="icon-button" type="button" data-plot="png" aria-label="Save as PNG" title="Save as PNG">${icon('download')}</button>`;
    tools.querySelector('[data-plot="y"]').addEventListener('change', (event) => setY(event.target.value));
    tools.querySelector('[data-plot="png"]').addEventListener('click', savePng);

    new ResizeObserver(() => chart?.setSize(size())).observe(body);
    store.on(['result', 'views'], () => {
        tools.querySelector('[data-plot="y"]').value = settings().y;
        tools.querySelector('[data-plot="png"]').disabled = !store.get('result');
        build();
    });
    store.on('time', update);
    tools.querySelector('[data-plot="png"]').disabled = true;
    build();
}

function settings() {
    return store.get('views').plot;
}

function setY(y) {
    const views = store.get('views');
    store.set({ views: { ...views, plot: { ...views.plot, y } } });
}

function size() {
    return { width: Math.max(body.clientWidth, 1), height: Math.max(body.clientHeight, 1) };
}

function build() {
    const result = store.get('result');
    if (!result) {
        body.innerHTML = `<div class="empty"><p class="empty-title">No run yet</p><p>Plots appear after the first run.</p></div>`;
        return;
    }
    const key = settings().y;
    if (builtFor && builtFor[0] === result && builtFor[1] === key) {
        update();
        return;
    }
    builtFor = [result, key];
    shownIndex = -1;
    chart?.destroy();
    chart = null;
    body.innerHTML = '';

    const p = parameter(key);
    hours = result.times.map((t) => (t - result.times[0]) / 3600);
    const raw = result.samples[key];
    if (!raw) {
        body.innerHTML = `<div class="empty"><p class="empty-title">${p.label} is not in this run</p><p>The engine did not report it. Pick another parameter.</p></div>`;
        return;
    }
    values = p.log ? raw.map((v) => (v > 0 ? v : null)) : raw;
    const ys = values.filter((v) => v !== null);
    const axis = {
        stroke: token('--muted'),
        grid: { stroke: token('--line'), width: 1 },
        ticks: { stroke: token('--line'), width: 1 },
        font: `12px ${token('--font')}`,
        labelFont: `12px ${token('--font')}`,
    };
    chart = new uPlot({
        ...size(),
        legend: { show: false },
        cursor: { y: false, points: { show: false }, drag: { x: false, y: false } },
        scales: { x: { time: false, range: [hours[0], hours.at(-1)] }, y: p.log ? { distr: 3 } : { range: () => padRange(Math.min(...ys), Math.max(...ys)) } },
        axes: [
            { ...axis, label: 'Elapsed (h)', size: 44 },
            { ...axis, label: p.unit ? `${p.label} (${p.unit})` : p.label, size: 72, values: (u, splits) => tickLabels(p, splits) },
        ],
        series: [{}, { stroke: token('--track-low'), width: 1.5, points: { show: false } }],
        hooks: { draw: [drawCursor] },
    }, [hours, values], body);

    chart.over.addEventListener('pointerdown', (event) => {
        const seek = (e) => {
            const rect = chart.over.getBoundingClientRect();
            const h = chart.posToVal(e.clientX - rect.left, 'x');
            store.set({ playing: false, time: result.times[0] + Math.min(Math.max(h, 0), hours.at(-1)) * 3600 });
        };
        seek(event);
        chart.over.setPointerCapture(event.pointerId);
        chart.over.addEventListener('pointermove', seek);
        chart.over.addEventListener('pointerup', () => chart.over.removeEventListener('pointermove', seek), { once: true });
    });
    update();
}

// Tick labels with only as many decimals as the tick spacing needs.
function tickLabels(p, splits) {
    if (p.scientific) return splits.map((v) => sci(v, 1));
    const step = Math.abs(splits[1] - splits[0]) || 1;
    const digits = Math.min(Math.max(0, -Math.floor(Math.log10(step))), 6);
    return splits.map((v) => num(v, digits));
}

function padRange(min, max) {
    const pad = (max - min) * 0.05 || Math.abs(max) * 0.05 || 1;
    return [min - pad, max + pad];
}

// Moves the cursor line; with "draw only up to the current time" on, also trims the data.
function update() {
    const result = store.get('result');
    if (!chart || !result) return;
    const last = settings().reveal ? sampleIndex(result, store.get('time')) : hours.length - 1;
    if (last !== shownIndex) {
        shownIndex = last;
        chart.setData([hours.slice(0, last + 1), values.slice(0, last + 1)], false);   // redraws, cursor included
    } else {
        chart.redraw(false, false);
    }
}

function drawCursor(u) {
    const result = store.get('result');
    if (!result) return;
    const x = Math.round(u.valToPos((store.get('time') - result.times[0]) / 3600, 'x', true)) + 0.5;
    const { ctx } = u;
    ctx.save();
    ctx.strokeStyle = token('--amber');
    ctx.lineWidth = 2 * devicePixelRatio;
    ctx.beginPath();
    ctx.moveTo(x, u.bbox.top);
    ctx.lineTo(x, u.bbox.top + u.bbox.height);
    ctx.stroke();
    ctx.restore();
}

// Saves the plot on the app's background, so it reads the same outside the app.
function savePng() {
    if (!chart) return;
    const source = chart.ctx.canvas;
    const out = document.createElement('canvas');
    out.width = source.width;
    out.height = source.height;
    const ctx = out.getContext('2d');
    ctx.fillStyle = token('--panel');
    ctx.fillRect(0, 0, out.width, out.height);
    ctx.drawImage(source, 0, 0);
    const link = document.createElement('a');
    link.download = `${store.get('mission').spacecraft.name}-${settings().y}.png`.replace(/[^\w.-]+/g, '_');
    link.href = out.toDataURL('image/png');
    link.click();
}

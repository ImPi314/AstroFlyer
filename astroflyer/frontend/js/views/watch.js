// Watch: the spacecraft's state at the timeline's current time, plus a summary of the run.
// Values are the engine's output point at or before that time; which rows show is a view setting.

import * as store from '../store.js';
import { sampleIndex } from '../results.js';
import { PARAMETERS, formatValue } from '../parameters.js';
import { elapsed, num, sci } from '../format.js';

const LIGHTING = { SUNLIGHT: 'Sunlight', PENUMBRA: 'Penumbra', UMBRA: 'Umbra' };
const DASH = '–';

// Every row the watch can show: the shared numeric parameters plus two states.
const ROWS = [
    ...PARAMETERS.map((p) => ({ group: p.group, key: p.key, label: p.label, unit: p.unit, value: (r, i) => formatValue(p, r.samples[p.key]?.[i]) })),
    { group: 'Orbit', key: 'lighting', label: 'Lighting', unit: '', value: (r, i) => LIGHTING[r.samples.lighting?.[i]] ?? DASH },
    { group: 'Orbit', key: 'stations', label: 'Stations in view', unit: '', value: (r, i) => stationsInView(r, r.times[i]) || 'None' },
    { group: 'Radiation', key: 'radiation_zone', label: 'Radiation zone', unit: '', value: (r, i) => r.samples.radiation_zone?.[i] ?? DASH },
];

export const WATCH_ROWS = ROWS.map(({ group, key, label }) => ({ group, key, label }));

let root;
let held = false;
let shown = [];
let renderedSettings = null;

export function mountWatch(body, tools) {
    root = body;
    tools.innerHTML = '<label class="toggle"><input type="checkbox" name="hold"> Hold values</label>';
    tools.querySelector('input').addEventListener('change', (event) => {
        held = event.target.checked;
        if (!held) renderValues();
    });
    store.on('result', render);
    store.on('views', (views) => { if (views.watch !== renderedSettings) render(); });
    store.on('time', () => { if (!held) renderValues(); });
    render();
}

function stationsInView(result, t) {
    return result.stations
        .filter((st) => st.passes.some((p) => t >= p.t0 && t <= p.t1))
        .map((st) => st.name)
        .join(', ');
}

function render() {
    const result = store.get('result');
    if (!result) {
        root.innerHTML = `
            <div class="empty">
                <p class="empty-title">No run yet</p>
                <p>Check the spacecraft and propagator in the inspector, then press Run or F5.</p>
            </div>`;
        return;
    }
    const settings = store.get('views').watch;
    renderedSettings = settings;
    shown = ROWS.filter((row) => settings[row.key]);
    const s = result.summary;
    const facts = [
        ['Perigee altitude', `${num(s.perigee_alt_km)} km`],
        ['Apogee altitude', `${num(s.apogee_alt_km)} km`],
        ['Period', `${num(s.period_h, 3)} h`],
        ['Time in shadow', s.shadow_pct == null ? '–' : `${num(s.shadow_pct, 1)} %`],
        ['Largest energy error', sci(s.max_energy_error)],
        ['Solve time', `${num(s.solve_s, 2)} s`],
    ];
    root.innerHTML = `
        <dl class="summary">${facts.map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join('')}</dl>
        <table class="watch-table">
            <thead><tr><th scope="col">Parameter</th><th scope="col" class="num">Value</th><th scope="col">Unit</th></tr></thead>
            <tbody>
                <tr><th scope="row">Elapsed</th><td class="num" data-elapsed></td><td class="unit"></td></tr>
                ${shown.map((row) => `<tr><th scope="row">${row.label}</th><td class="num" data-row="${row.key}"></td><td class="unit">${row.unit}</td></tr>`).join('')}
            </tbody>
        </table>`;
    renderValues();
}

function renderValues() {
    const result = store.get('result');
    if (!result || !root.querySelector('.watch-table')) return;
    const i = sampleIndex(result, store.get('time'));
    root.querySelector('[data-elapsed]').textContent = elapsed(store.get('time') - result.times[0]).slice(3);
    for (const row of shown) root.querySelector(`[data-row="${row.key}"]`).textContent = row.value(result, i);
}

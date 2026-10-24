// Watch: the spacecraft's state at the timeline's current time, plus a summary of the run.
// Values are the engine's output point at or before that time; which rows show is a view setting.
// One instance per pane; ctx gives this pane's settings and tracks subscriptions.

import * as store from '../store.js';
import { sampleIndex, clockText, energySummary } from '../results.js';
import { PARAMETERS, formatValue } from '../parameters.js';
import { num, sci } from '../format.js';

const LIGHTING = { SUNLIGHT: 'Sunlight', PENUMBRA: 'Penumbra', UMBRA: 'Umbra' };
const DASH = '–';

// Every row the watch can show: the shared numeric parameters plus three states.
const ROWS = [
    ...PARAMETERS.map((p) => ({ group: p.group, key: p.key, label: p.label, unit: p.unit, value: (r, i) => formatValue(p, r.samples[p.key]?.[i]) })),
    { group: 'Orbit', key: 'lighting', label: 'Lighting', unit: '', value: (r, i) => LIGHTING[r.samples.lighting?.[i]] ?? DASH },
    { group: 'Orbit', key: 'stations', label: 'Stations in view', unit: '', value: (r, i) => stationsInView(r, r.times[i]) || 'None' },
    { group: 'Radiation', key: 'radiation_zone', label: 'Radiation zone', unit: '', value: (r, i) => r.samples.radiation_zone?.[i] ?? DASH },
];

export const WATCH_ROWS = ROWS.map(({ group, key, label }) => ({ group, key, label }));

export const watchDefaults = () => Object.fromEntries(WATCH_ROWS.map((row) => [row.key, row.group === 'Orbit']));

function stationsInView(result, t) {
    return result.stations
        .filter((st) => st.passes.some((p) => t >= p.t0 && t <= p.t1))
        .map((st) => st.name.replace(/\s*\(.*\)$/, ''))
        .join(', ');
}

export function createWatch(ctx) {
    const root = ctx.body;
    let held = false;
    let shown = [];

    ctx.tools.innerHTML = '<label class="toggle"><input type="checkbox" name="hold"> Hold values</label>';
    ctx.tools.querySelector('input').addEventListener('change', (event) => {
        held = event.target.checked;
        if (!held) renderValues();
    });

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
        const settings = ctx.settings();
        shown = ROWS.filter((row) => settings[row.key]);
        const s = result.summary;
        const facts = [
            ['Perigee altitude', `${num(s.perigee_alt_km)} km`],
            ['Apogee altitude', `${num(s.apogee_alt_km)} km`],
            ['Period', `${num(s.period_h, 3)} h`],
            ['Time in shadow', s.shadow_pct == null ? DASH : `${num(s.shadow_pct, 1)} %`],
            [energySummary(s)[0], sci(s.max_energy_error)],
            ['Solve time', `${num(s.solve_s, 2)} s`],
        ];
        root.innerHTML = `
            <div class="watch">
                <dl class="summary">${facts.map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join('')}</dl>
                <dl class="watch-grid">
                    <div class="watch-row"><dt>Time</dt><dd data-clock></dd></div>
                    ${shown.map((row) => `<div class="watch-row"><dt>${row.label}</dt><dd><span data-row="${row.key}"></span>${row.unit ? ` <span class="unit">${row.unit}</span>` : ''}</dd></div>`).join('')}
                </dl>
            </div>`;
        renderValues();
    }

    function renderValues() {
        const result = store.get('result');
        if (!result || !root.querySelector('.watch-grid')) return;
        const t = store.get('time');
        const i = sampleIndex(result, t);
        root.querySelector('[data-clock]').textContent = clockText(result, t, store.get('timeScale'));
        for (const row of shown) root.querySelector(`[data-row="${row.key}"]`).textContent = row.value(result, i);
    }

    ctx.on('result', render);
    ctx.onSettings(render);
    ctx.on(['time', 'timeScale'], () => { if (!held) renderValues(); });
    render();
    return { destroy() {} };
}

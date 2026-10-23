// Watch: the spacecraft's state at the timeline's current time, plus a summary of the run.

import * as store from '../store.js';
import { sampleIndex } from '../results.js';
import { elapsed, num, sci } from '../format.js';

const LIGHTING = { SUNLIGHT: 'Sunlight', PENUMBRA: 'Penumbra', UMBRA: 'Umbra' };

const ROWS = [
    ['Elapsed', '', (r, i) => elapsed(r.times[i] - r.times[0]).slice(3)],
    ['Altitude', 'km', (r, i) => num(r.samples.altitude_km[i], 1)],
    ['Speed', 'km/s', (r, i) => num(r.samples.speed_kms[i], 3)],
    ['Semi-major axis', 'km', (r, i) => num(r.samples.sma_km[i], 1)],
    ['Eccentricity', '', (r, i) => num(r.samples.eccentricity[i], 5)],
    ['Inclination', 'deg', (r, i) => num(r.samples.inclination_deg[i], 3)],
    ['RAAN', 'deg', (r, i) => num(r.samples.raan_deg[i], 3)],
    ['Argument of perigee', 'deg', (r, i) => num(r.samples.aop_deg[i], 3)],
    ['True anomaly', 'deg', (r, i) => num(r.samples.true_anomaly_deg[i], 2)],
    ['Latitude', 'deg', (r, i) => num(r.samples.latitude_deg[i], 3)],
    ['Longitude', 'deg', (r, i) => num(r.samples.longitude_deg[i], 3)],
    ['Lighting', '', (r, i) => LIGHTING[r.samples.lighting?.[i]] ?? '–'],
    ['Stations in view', '', (r, i) => stationsInView(r, r.times[i]) || 'None'],
    ['Energy error', 'relative', (r, i) => sci(r.samples.energy_error[i])],
];

let root;
let held = false;

export function mountWatch(element) {
    root = element;
    root.addEventListener('change', (event) => {
        if (event.target.name !== 'hold') return;
        held = event.target.checked;
        if (!held) renderValues();
    });
    store.on('result', render);
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
        <header class="view-head">
            <h2 class="view-title">Watch</h2>
            <label class="toggle"><input type="checkbox" name="hold" ${held ? 'checked' : ''}> Hold values</label>
        </header>
        <dl class="summary">${facts.map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join('')}</dl>
        <table class="watch-table">
            <thead><tr><th scope="col">Parameter</th><th scope="col" class="num">Value</th><th scope="col">Unit</th></tr></thead>
            <tbody>${ROWS.map(([label, unit]) => `<tr><th scope="row">${label}</th><td class="num"></td><td class="unit">${unit}</td></tr>`).join('')}</tbody>
        </table>`;
    renderValues();
}

function renderValues() {
    const result = store.get('result');
    if (!result || !root.querySelector('.watch-table')) return;
    const i = sampleIndex(result, store.get('time'));
    const cells = root.querySelectorAll('.watch-table td.num');
    ROWS.forEach(([, , value], row) => { cells[row].textContent = value(result, i); });
}

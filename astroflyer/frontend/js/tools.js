// Analysis and Data workspaces: tools that read the last run or ask the engine for one result.
// The mission tree, inspector and timeline stay as they are while a tool is open.

import * as store from './store.js';
import { solveApogeeRaise, simulateFiniteBurn, runScript, analyzeAccess, EngineError } from './api.js';
import { sampleIndex, closedOrbitTools, targetingRequest } from './results.js';
import { fromScriptRun } from './scriptrun.js';
import { toAccessRequest, fromAccess } from './access.js';
import { startScriptRun } from './run.js';
import { log } from './messages.js';
import { elapsed, escapeHtml, icon, num, saveFile } from './format.js';
import { token } from './views/colors.js';

const TOOLS = {
    analysis: [
        ['events', 'Events'],
        ['access', 'Access'],
        ['targeting', 'Targeting'],
        ['radiation', 'Radiation'],
        ['covariance', 'Covariance'],
    ],
    data: [
        ['script', 'Mission script'],
        ['export', 'Export'],
    ],
};
const PAGES = { events, access, targeting, radiation, covariance, script, export: exportPage };

let root;
let page;
const openTool = { analysis: 'events', data: 'script' };
let eventFilter = 'all';
let targetingState = { apogee: null, burn: null, busy: false, inputs: {} };   // inputs survive re-rendering
let scriptDraft = null;   // the user's edits; null means "show the last run's script"
let scriptRun = { busy: false, run: null, failure: null };   // last full script run, see scriptrun.js
let accessState = { busy: false, access: null, failure: null, forResult: null };   // see access.js

export function mountTools(element) {
    root = element;
    root.innerHTML = '<div class="tool-tabs" role="tablist"></div><div class="tool-page" role="tabpanel"></div>';
    page = root.querySelector('.tool-page');
    root.querySelector('.tool-tabs').addEventListener('click', (event) => {
        const id = event.target.closest('[data-tool]')?.dataset.tool;
        if (!id) return;
        openTool[store.get('workspace')] = id;
        render();
    });
    page.addEventListener('click', onPageClick);
    page.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' && event.target.matches('tr[data-t]')) seek(Number(event.target.dataset.t));
    });
    page.addEventListener('change', (event) => {
        if (event.target.name === 'event-filter') {
            eventFilter = event.target.value;
            render();
        }
    });
    page.addEventListener('input', (event) => {
        if (event.target.name === 'script') scriptDraft = event.target.value;
        if (event.target.closest('.tool-form')) targetingState.inputs[event.target.name] = event.target.value;
    });
    page.addEventListener('submit', (event) => {
        event.preventDefault();
        submitTargeting(event.target);
    });
    store.on(['workspace', 'result'], render);
    store.on('run', (run) => {
        const button = page.querySelector('[data-action="script-views"]');
        if (button) button.disabled = run.status === 'running';
    });
    render();
}

function render() {
    const workspace = store.get('workspace');
    if (workspace === 'mission') return;
    const current = openTool[workspace];
    root.querySelector('.tool-tabs').innerHTML = TOOLS[workspace].map(([id, label]) =>
        `<button type="button" role="tab" data-tool="${id}" aria-selected="${id === current}" class="tool-tab">${label}</button>`).join('');
    const result = store.get('result');
    const needsRun = current !== 'script';
    if (needsRun && !result) {
        page.innerHTML = '<div class="empty"><p class="empty-title">No run yet</p><p>Press Run or F5. This tool works from the last run.</p></div>';
    } else if (result && !result.summary.closedOrbit && closedOrbitTools.has(current)) {
        page.innerHTML = '<div class="empty"><p class="empty-title">Closed orbits only</p><p>The last run is an escape trajectory, so it has no apogee to target.</p></div>';
    } else {
        page.innerHTML = PAGES[current](result);
    }
}

function seek(t) {
    store.set({ playing: false, time: t });
}

function at(result, t) {
    return elapsed(t - result.times[0]);
}

function facts(rows) {
    return `<dl class="facts">${rows.map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join('')}</dl>`;
}

// ---------- Events ----------

function events(result) {
    const rows = [
        ...result.apsides.map((a) => ({ kind: 'apsides', t: a.t, name: a.kind === 'perigee' ? 'Perigee' : 'Apogee', detail: `${num(a.altitude_km)} km altitude` })),
        ...result.nodes.map((n) => ({ kind: 'nodes', t: n.t, name: n.kind === 'ascending' ? 'Ascending node' : 'Descending node', detail: `Longitude ${num(n.longitude_deg, 1)} deg` })),
        ...result.shadows.flatMap((s) => [
            { kind: 'shadow', t: s.t0, name: 'Enters shadow', detail: `${num((s.t1 - s.t0) / 60, 1)} min in umbra` },
            { kind: 'shadow', t: s.t1, name: 'Leaves shadow', detail: '' },
        ]),
        ...result.stations.flatMap((st) => st.passes.flatMap((p) => [
            { kind: 'stations', t: p.t0, name: `Contact with ${st.name}`, detail: `${num((p.t1 - p.t0) / 60, 1)} min, peak elevation ${num(p.max_elevation_deg, 1)} deg` },
            { kind: 'stations', t: p.t1, name: `Contact ends with ${st.name}`, detail: '' },
        ])),
    ].filter((row) => eventFilter === 'all' || row.kind === eventFilter).sort((a, b) => a.t - b.t);

    const filters = [['all', 'All events'], ['apsides', 'Perigee and apogee'], ['nodes', 'Node crossings'], ['shadow', 'Shadow'], ['stations', 'Station contact']];
    return `
        <header class="tool-head">
            <div>
                <h2 class="tool-title">Events</h2>
                <p class="tool-lead">Select an event to move the timeline to it.</p>
            </div>
            <label class="compact-select"><span class="visually-hidden">Show</span>
                <select name="event-filter">${filters.map(([v, l]) => `<option value="${v}" ${v === eventFilter ? 'selected' : ''}>${l}</option>`).join('')}</select>
            </label>
        </header>
        ${rows.length ? `<table class="data-table">
            <thead><tr><th scope="col">Time</th><th scope="col">Event</th><th scope="col">Detail</th></tr></thead>
            <tbody>${rows.map((row) => `<tr data-t="${row.t}" tabindex="0"><td class="num">${at(result, row.t)}</td><td>${escapeHtml(row.name)}</td><td class="muted">${row.detail}</td></tr>`).join('')}</tbody>
        </table>` : '<p class="tool-lead">No events of this kind in this run.</p>'}`;
}

// ---------- Access: station passes with masks, Earth and Moon eclipses, beta angle ----------

// "2000-01-01T12:30:00.000000Z" as "2000-01-01 12:30:00".
const utc = (iso) => (iso ? iso.replace('T', ' ').slice(0, 19) : '–');
const minutes = (s) => `${num(s / 60, 1)} min`;

function access(result) {
    const { busy, failure } = accessState;
    const current = accessState.forResult === result ? accessState.access : null;
    const stale = accessState.access && !current;
    const head = `
        <header class="tool-head">
            <div>
                <h2 class="tool-title">Access</h2>
                <p class="tool-lead">The engine propagates this run's orbit again from the same epoch, with the same force model and stations, and finds each station pass above its elevation limit, shadow from the Earth and the Moon, and the beta angle.</p>
            </div>
            <div class="tool-actions">
                ${current ? `<button class="button" type="button" data-action="access-report">${icon('download')}Save report</button>` : ''}
                <button class="button button-primary" type="button" data-action="access-run" ${busy ? 'disabled' : ''}>${icon('play')}${current ? 'Analyse again' : 'Analyse'}</button>
            </div>
        </header>`;
    if (busy) return `${head}<p class="tool-lead section-pad">Analysing access.</p>`;
    if (failure) return `${head}<p class="tool-lead section-pad script-error">${escapeHtml(failure)}</p>`;
    if (!current) return `${head}<p class="tool-lead section-pad">${stale ? 'The mission was run again since the last analysis. ' : ''}Press Analyse to work out access for this run.</p>`;
    if (current.error) return `${head}<p class="tool-lead section-pad script-error">${escapeHtml(current.error)}</p>`;
    const contact = current.passes.reduce((sum, p) => sum + p.duration_s, 0);
    const shadow = current.eclipses.filter((e) => e.kind === 'umbra').reduce((sum, e) => sum + e.duration_s, 0);
    const flag = (partial) => (partial ? ' <span class="muted">(cut by the run start or end)</span>' : '');
    return `
        ${head}
        ${facts([
            ['Station passes', num(current.passes.length)],
            ['Total contact', minutes(contact)],
            ['Shadow periods', num(current.eclipses.length)],
            ['Time in umbra', minutes(shadow)],
            ['Beta angle', current.beta.min == null ? '–' : `${num(current.beta.min, 1)} to ${num(current.beta.max, 1)} deg`],
        ])}
        <section class="tool-section">
            <h3 class="section-title">Station passes</h3>
            ${current.passes.length ? `<table class="data-table compact">
                <thead><tr><th scope="col">Station</th><th scope="col">AOS (UTC)</th><th scope="col">Closest (UTC)</th><th scope="col">LOS (UTC)</th><th scope="col" class="num">Length</th><th scope="col" class="num">Peak elevation</th><th scope="col" class="num">AOS / LOS azimuth</th></tr></thead>
                <tbody>${current.passes.map((p) => `<tr>
                    <td>${escapeHtml(p.station)}${flag(p.partial)}</td><td>${utc(p.aos)}</td><td>${utc(p.tca)}</td><td>${utc(p.los)}</td>
                    <td class="num">${minutes(p.duration_s)}</td><td class="num">${num(p.max_elevation_deg, 1)} deg</td>
                    <td class="num">${num(p.aos_azimuth_deg)} / ${num(p.los_azimuth_deg)} deg</td></tr>`).join('')}</tbody>
            </table>` : `<p class="tool-lead section-pad">${result.stations.length ? 'No station sees the spacecraft in this run.' : 'The engine listed no ground stations for this run, so no passes were worked out.'}</p>`}
        </section>
        <section class="tool-section">
            <h3 class="section-title">Shadow</h3>
            ${current.eclipses.length ? `<table class="data-table compact">
                <thead><tr><th scope="col">Shadow of</th><th scope="col">Kind</th><th scope="col">Start (UTC)</th><th scope="col">End (UTC)</th><th scope="col" class="num">Length</th></tr></thead>
                <tbody>${current.eclipses.map((e) => `<tr>
                    <td>${escapeHtml(e.body)}</td><td>${e.kind === 'umbra' ? 'Umbra' : 'Penumbra'}${flag(e.partial)}</td><td>${utc(e.start)}</td><td>${utc(e.end)}</td>
                    <td class="num">${minutes(e.duration_s)}</td></tr>`).join('')}</tbody>
            </table>` : '<p class="tool-lead section-pad">The spacecraft stays in sunlight for the whole run.</p>'}
        </section>`;
}

async function startAccess(result) {
    accessState = { busy: true, access: null, failure: null, forResult: null };
    render();
    try {
        const analysed = fromAccess(await analyzeAccess(toAccessRequest(store.get('mission'), result)));
        accessState = { busy: false, access: analysed, failure: null, forResult: result };
        if (analysed.error) log('error', `Access analysis failed: ${analysed.error}`);
        else log('info', `Access analysis found ${analysed.passes.length} station passes and ${analysed.eclipses.length} shadow periods.`);
    } catch (err) {
        const message = err instanceof EngineError ? err.message : `Unexpected error: ${err.message}`;
        accessState = { busy: false, access: null, failure: message, forResult: null };
        log('error', message);
    }
    render();
}

// ---------- Targeting ----------

function perigeeState(result) {
    const first = result.apsides.find((a) => a.kind === 'perigee');
    const i = first ? sampleIndex(result, first.t) : 0;
    return {
        perigeeRadiusKm: result.earthRadiusKm + (first?.altitude_km ?? result.summary.perigee_alt_km),
        perigeeSpeedKms: result.samples.speed_kms[i],
    };
}

function targeting(result) {
    const { perigeeRadiusKm, perigeeSpeedKms } = perigeeState(result);
    const { apogee, burn, busy } = targetingState;
    const mass = result.request?.mass ?? store.get('mission').spacecraft.mass;
    const model = result.request?.model ?? store.get('mission').propagator.model;
    const dvDefault = apogee ? Math.abs(apogee.optimal_delta_v_ms) : 1000;
    return `
        <header class="tool-head">
            <div>
                <h2 class="tool-title">Targeting</h2>
                <p class="tool-lead">Both solvers start from this run's first perigee (radius about ${num(perigeeRadiusKm, 1)} km, speed ${num(perigeeSpeedKms, 3)} km/s) and propagate with the run's force model (${escapeHtml(model)}) and spacecraft.</p>
            </div>
        </header>
        <section class="tool-section">
            <h3 class="section-title">Raise apogee with one perigee burn</h3>
            <form class="tool-form" data-form="apogee" novalidate>
                ${inputField('target', 'Target apogee radius', 'km', 42164, 'GEO radius is 42,164 km.')}
                <button class="button button-primary" type="submit" ${busy ? 'disabled' : ''}>Solve</button>
            </form>
            ${apogee ? `
                ${facts([
                    ['Result', apogee.converged ? 'Converged' : 'Did not converge'],
                    ['Burn at perigee', `${num(apogee.optimal_delta_v_ms, 3)} m/s`],
                    ['Two-body (vis-viva) answer', `${num(apogee.two_body_delta_v_ms, 3)} m/s`],
                    ['Perigee (burn) epoch', `${escapeHtml(apogee.perigee_epoch_utc)} UTC`],
                    ['Apogee radius reached', `${num(apogee.achieved_apogee_km, 3)} km`],
                    ['Iterations', num(apogee.total_iterations)],
                ])}
                <table class="data-table compact">
                    <thead><tr><th scope="col">Iteration</th><th scope="col" class="num">Burn (m/s)</th><th scope="col" class="num">Apogee radius (km)</th><th scope="col" class="num">Miss (km)</th></tr></thead>
                    <tbody>${apogee.iteration_history.map((h) => `<tr><td>${h.iteration}</td><td class="num">${num(h.delta_v_ms, 3)}</td><td class="num">${num(h.achieved_apogee_km, 1)}</td><td class="num">${num(h.residual_km, 4)}</td></tr>`).join('')}</tbody>
                </table>` : ''}
        </section>
        <section class="tool-section">
            <h3 class="section-title">Finite burn with mass loss</h3>
            <p class="tool-lead">The burn is centred on the perigee with thrust along the velocity. Its loss is the requested velocity change minus the impulsive burn at the perigee that reaches the same apogee.</p>
            <form class="tool-form" data-form="burn" novalidate>
                ${inputField('dv', 'Velocity change', 'm/s', Math.round(dvDefault * 100) / 100)}
                ${inputField('mass', 'Starting mass', 'kg', mass)}
                ${inputField('thrust', 'Thrust', 'N', 450)}
                ${inputField('isp', 'Specific impulse', 's', 315)}
                <button class="button button-primary" type="submit" ${busy ? 'disabled' : ''}>Simulate</button>
            </form>
            ${burn ? facts([
                ['Burn duration', `${num(burn.burn_duration_min, 1)} min`],
                ['Propellant used', `${num(burn.propellant_consumed_kg, 1)} kg`],
                ['Final mass', `${num(burn.final_mass_kg, 1)} kg`],
                ['Ideal velocity change', `${num(burn.ideal_delta_v_ms, 1)} m/s`],
                ['Apogee radius, finite burn', `${num(burn.apogee_after_finite_km, 1)} km`],
                ['Apogee radius, impulsive burn', `${num(burn.apogee_after_impulsive_km, 1)} km`],
                ['Finite-burn loss', `${num(burn.gravity_losses_ms, 2)} m/s`],
                ['Effective velocity change', `${num(burn.actual_effective_delta_v_ms, 2)} m/s`],
            ]) : ''}
        </section>`;
}

function inputField(name, label, unit, fallback, hint = '') {
    const value = escapeHtml(targetingState.inputs[name] ?? fallback);
    return `<div class="field">
        <label for="tool-${name}">${label}</label>
        <div class="field-control"><input id="tool-${name}" name="${name}" type="number" step="any" min="0" value="${value}"><span class="field-unit">${unit}</span></div>
        ${hint ? `<p class="field-hint">${hint}</p>` : ''}
    </div>`;
}

async function submitTargeting(form) {
    const values = Object.fromEntries([...form.querySelectorAll('input')].map((input) => [input.name, input.valueAsNumber]));
    if (Object.values(values).some((v) => !Number.isFinite(v) || v <= 0)) {
        log('error', 'Enter a positive number in every targeting field.');
        return;
    }
    const result = store.get('result');
    targetingState = { ...targetingState, busy: true };
    render();
    try {
        if (form.dataset.form === 'apogee') {
            const apogee = await solveApogeeRaise(targetingRequest(result), values.target);
            targetingState = { ...targetingState, apogee };
            log('info', `Apogee raise ${apogee.converged ? 'converged' : 'did not converge'}: ${num(apogee.optimal_delta_v_ms, 2)} m/s at perigee.`);
        } else {
            const burn = await simulateFiniteBurn(targetingRequest(result), { deltaVms: values.dv, massKg: values.mass, thrustN: values.thrust, ispS: values.isp });
            targetingState = { ...targetingState, burn };
            log('info', `Finite burn: ${num(burn.burn_duration_min, 1)} min, ${num(burn.propellant_consumed_kg, 1)} kg of propellant.`);
        }
    } catch (err) {
        log('error', err instanceof EngineError ? err.message : `Unexpected error: ${err.message}`);
    } finally {
        targetingState = { ...targetingState, busy: false };
        render();
    }
}

// ---------- Radiation and covariance ----------

function radiation(result) {
    const { crossings } = result.radiation;
    const time = (belt) => crossings.filter((c) => c.belt === belt).reduce((sum, c) => sum + (c.t1 - c.t0), 0) / 60;
    return `
        <header class="tool-head">
            <div>
                <h2 class="tool-title">Radiation</h2>
                <p class="tool-lead">Time spent in the Van Allen belts in this run, from a tilted-dipole L-shell. No dose is estimated: that needs a trapped-particle model this app does not have. L-shell and field strength over time are in Plot, under Radiation.</p>
            </div>
        </header>
        ${facts([
            ['Inner belt crossings', `${num(crossings.filter((c) => c.belt === 'Inner').length)}, ${num(time('Inner'), 1)} min`],
            ['Outer belt crossings', `${num(crossings.filter((c) => c.belt === 'Outer').length)}, ${num(time('Outer'), 1)} min`],
        ])}
        ${crossings.length ? `<table class="data-table">
            <thead><tr><th scope="col">Enters</th><th scope="col">Belt</th><th scope="col" class="num">Duration (min)</th></tr></thead>
            <tbody>${crossings.map((c) => `<tr data-t="${c.t0}" tabindex="0"><td class="num">${at(result, c.t0)}</td><td>${c.belt} belt</td><td class="num">${num((c.t1 - c.t0) / 60, 1)}</td></tr>`).join('')}</tbody>
        </table>` : ''}`;
}

function covariance(result) {
    const c = result.covariance;
    return `
        <header class="tool-head">
            <div>
                <h2 class="tool-title">Covariance</h2>
                <p class="tool-lead">Position uncertainty carried along the orbit by the state transition matrix. The radial, in-track and cross-track histories are in Plot, under Covariance.</p>
            </div>
        </header>
        ${facts([
            ['Starting 1-sigma position', `${num(c.initialSigmaM, 1)} m`],
            ['Final 1-sigma position', `${num(c.finalSigmaM, 1)} m`],
            ['Final radial', `${num(c.finalRadialM, 1)} m`],
            ['Final in-track', `${num(c.finalIntrackM, 1)} m`],
            ['Final cross-track', `${num(c.finalCrosstrackM, 1)} m`],
            ['Transition matrix determinant', num(c.stmDeterminant, 6)],
        ])}
        <p class="tool-lead">A determinant of exactly 1 means the uncertainty volume is preserved, as it should be with conservative forces only.</p>`;
}

// ---------- Data: mission script and export ----------

function script(result) {
    const text = scriptDraft ?? result?.script ?? '';
    const running = store.get('run').status === 'running';
    return `
        <header class="tool-head">
            <div>
                <h2 class="tool-title">Mission script</h2>
                <p class="tool-lead">Run script carries out the whole mission sequence and lists its reports, targets and final states below. Show orbit in views propagates only the orbit in the script, with the inspector's propagator settings, and opens it in the Mission views.</p>
            </div>
            <div class="tool-actions">
                <button class="button" type="button" data-action="script-reset" ${result ? '' : 'disabled'}>${icon('rotate-ccw')}Use last run's script</button>
                <button class="button" type="button" data-action="script-save" ${text ? '' : 'disabled'}>${icon('download')}Save</button>
                <button class="button" type="button" data-action="script-views" ${running ? 'disabled' : ''}>${icon('play')}Show orbit in views</button>
                <button class="button button-primary" type="button" data-action="script-run" ${scriptRun.busy ? 'disabled' : ''}>${icon('play')}Run script</button>
            </div>
        </header>
        <label class="visually-hidden" for="script-text">Mission script</label>
        <textarea class="code-editor" id="script-text" name="script" spellcheck="false" placeholder="Run the mission once to start from its script, or paste a script here.">${escapeHtml(text)}</textarea>
        ${scriptOutput()}`;
}

function scriptOutput() {
    const { busy, run, failure } = scriptRun;
    if (busy) return '<section class="tool-section"><p class="tool-lead section-pad">Running the script.</p></section>';
    if (failure) return `<section class="tool-section"><p class="tool-lead section-pad script-error">${escapeHtml(failure)}</p></section>`;
    if (!run) return '';
    const table = (head, rows) => `
        <table class="data-table compact">
            <thead><tr>${head.map(([label, cls]) => `<th scope="col" class="${cls ?? ''}">${escapeHtml(label)}</th>`).join('')}</tr></thead>
            <tbody>${rows.join('')}</tbody>
        </table>`;
    const value = (v) => (typeof v === 'number' ? num(v, Math.abs(v) >= 1000 ? 1 : 6) : escapeHtml(v ?? '–'));
    return `
        ${run.error ? `
            <section class="tool-section">
                <h3 class="section-title">Script stopped</h3>
                <p class="tool-lead section-pad script-error">${run.error.line != null ? `Line ${run.error.line}: ` : ''}${escapeHtml(run.error.message)}</p>
                ${run.error.line != null ? `<div class="section-pad"><button class="button" type="button" data-action="script-line" data-line="${run.error.line}">Go to line ${run.error.line}</button></div>` : ''}
            </section>` : ''}
        ${run.targets.length ? `
            <section class="tool-section">
                <h3 class="section-title">Targets</h3>
                ${table([['Target'], ['Result'], ['Iterations', 'num'], ['Variables'], ['Goals']], run.targets.map((t) => `<tr>
                    <td>${escapeHtml(t.name)} <span class="muted">line ${t.line}</span></td>
                    <td>${t.converged ? 'Converged' : `<span class="script-error">${escapeHtml(t.message || 'Did not converge')}</span>`}</td>
                    <td class="num">${num(t.iterations)}</td>
                    <td>${t.variables.map(([k, v]) => `${escapeHtml(k)} = ${value(v)}`).join('<br>')}</td>
                    <td>${t.goals.map((g) => `${escapeHtml(g.param)}: ${value(g.achieved)} for ${value(g.target)} (tolerance ${value(g.tolerance)})`).join('<br>')}</td>
                </tr>`))}
            </section>` : ''}
        ${run.spacecraft.length ? `
            <section class="tool-section">
                <h3 class="section-title">Final states</h3>
                ${table([['Spacecraft'], ['Epoch (UTC)'], ['SMA (km)', 'num'], ['ECC', 'num'], ['INC (deg)', 'num'], ['Altitude (km)', 'num'], ['Mass (kg)', 'num'], ['Fuel (kg)', 'num'], ['Points', 'num']],
                    run.spacecraft.map((s) => `<tr><td>${escapeHtml(s.name)}</td><td>${escapeHtml(s.epoch_utc ?? '–')}</td><td class="num">${num(s.sma_km, 1)}</td><td class="num">${num(s.ecc, 6)}</td><td class="num">${num(s.inc_deg, 3)}</td><td class="num">${num(s.altitude_km, 1)}</td><td class="num">${num(s.mass_kg, 2)}</td><td class="num">${num(s.fuel_mass_kg, 2)}</td><td class="num">${num(s.points)}</td></tr>`))}
            </section>` : ''}
        ${run.reports.map((r, i) => `
            <section class="tool-section">
                <header class="section-head">
                    <div><h3 class="section-title">Report ${escapeHtml(r.name)}</h3><p class="tool-lead">${num(r.rows.length)} rows</p></div>
                    <button class="button" type="button" data-action="script-report" data-index="${i}">${icon('download')}Save</button>
                </header>
                ${table(r.columns.map((c) => [c, 'num']), r.rows.slice(0, 200).map((row) => `<tr>${row.map((v) => `<td class="num">${value(v)}</td>`).join('')}</tr>`))}
                ${r.rows.length > 200 ? `<p class="tool-lead section-pad">Showing the first 200 rows. Save the report for all ${num(r.rows.length)}.</p>` : ''}
            </section>`).join('')}
        <section class="tool-section">
            <h3 class="section-title">Log</h3>
            ${run.log.length ? `<pre class="code-block">${escapeHtml(run.log.join('\n'))}</pre>` : '<p class="tool-lead section-pad">The script wrote nothing to the log.</p>'}
        </section>`;
}

async function startFullScriptRun(text) {
    scriptRun = { busy: true, run: null, failure: null };
    render();
    log('info', 'Running the mission script.');
    try {
        const run = fromScriptRun(await runScript(text));
        scriptRun = { busy: false, run, failure: null };
        if (run.error) log('error', `The script stopped${run.error.line != null ? ` at line ${run.error.line}` : ''}: ${run.error.message}`);
        else log('info', `Script finished: ${run.spacecraft.length} spacecraft, ${run.reports.length} reports, ${run.targets.length} targets.`);
    } catch (err) {
        const message = err instanceof EngineError ? err.message : `Unexpected error: ${err.message}`;
        scriptRun = { busy: false, run: null, failure: message };
        log('error', message);
    }
    render();
}

function reportCsv(report) {
    const cell = (v) => (/[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v));
    return `${[report.columns, ...report.rows].map((row) => row.map(cell).join(',')).join('\n')}\n`;
}

// Selects line n (counted from 1) of the script editor.
function selectLine(n) {
    const editor = page.querySelector('#script-text');
    const lines = editor.value.split('\n');
    const start = lines.slice(0, n - 1).reduce((sum, line) => sum + line.length + 1, 0);
    editor.focus();
    editor.setSelectionRange(start, start + (lines[n - 1]?.length ?? 0));
    const lineHeight = editor.scrollHeight / Math.max(lines.length, 1);
    editor.scrollTop = Math.max(0, (n - 3) * lineHeight);
}

function exportPage(result) {
    const name = store.get('mission').spacecraft.name.replace(/[^\w.-]+/g, '_');
    const block = (title, lead, text, action) => `
        <section class="tool-section">
            <header class="section-head">
                <div><h3 class="section-title">${title}</h3><p class="tool-lead">${lead}</p></div>
                <button class="button" type="button" data-action="${action}" ${text ? '' : 'disabled'}>${icon('download')}Save</button>
            </header>
            ${text ? `<pre class="code-block">${escapeHtml(text)}</pre>` : '<p class="tool-lead">The engine did not return this for the last run.</p>'}
        </section>`;
    return `
        <header class="tool-head">
            <div>
                <h2 class="tool-title">Export</h2>
                <p class="tool-lead">Files describe the last run of ${escapeHtml(store.get('mission').spacecraft.name)} and save as ${escapeHtml(name)}.tle, .opm and .csv.</p>
            </div>
        </header>
        ${block('Two-line element set', 'Mean elements in the NORAD TLE layout.', result.tle, 'save-tle')}
        ${block('CCSDS orbit parameter message', 'The starting state as a CCSDS OPM.', result.opm, 'save-opm')}
        <section class="tool-section">
            <header class="section-head">
                <div><h3 class="section-title">Ephemeris table</h3><p class="tool-lead">${num(result.times.length)} points of time, inertial position and velocity as CSV.</p></div>
                <button class="button" type="button" data-action="save-csv">${icon('download')}Save</button>
            </header>
        </section>`;
}

function ephemerisCsv(result) {
    const lines = ['time_s,x_km,y_km,z_km,vx_kms,vy_kms,vz_kms'];
    result.times.forEach((t, i) => {
        const p = result.inertialKm;
        const v = result.velocityKms;
        lines.push([t, p[i * 3], p[i * 3 + 1], p[i * 3 + 2], v[i * 3], v[i * 3 + 1], v[i * 3 + 2]].map((x) => Number(x).toPrecision(12)).join(','));
    });
    return `${lines.join('\n')}\n`;
}

function onPageClick(event) {
    const row = event.target.closest('tr[data-t]');
    if (row) {
        seek(Number(row.dataset.t));
        return;
    }
    const result = store.get('result');
    const name = store.get('mission').spacecraft.name.replace(/[^\w.-]+/g, '_');
    switch (event.target.closest('[data-action]')?.dataset.action) {
        case 'script-run':
        case 'script-views': {
            const text = page.querySelector('#script-text').value;
            if (!text.trim()) {
                log('error', 'The script is empty.');
                return;
            }
            if (event.target.closest('[data-action]').dataset.action === 'script-run') startFullScriptRun(text);
            else startScriptRun(text);
            break;
        }
        case 'access-run':
            startAccess(result);
            break;
        case 'access-report': {
            const { report } = accessState.access;
            saveFile(`${name}_access.csv`, reportCsv({ columns: report.columns, rows: report.rows }), 'text/csv');
            break;
        }
        case 'script-line':
            selectLine(Number(event.target.closest('[data-line]').dataset.line));
            break;
        case 'script-report': {
            const report = scriptRun.run.reports[Number(event.target.closest('[data-index]').dataset.index)];
            saveFile(`${report.name.replace(/[^\w.-]+/g, '_')}.csv`, reportCsv(report), 'text/csv');
            break;
        }
        case 'script-reset':
            scriptDraft = null;
            render();
            break;
        case 'script-save':
            saveFile(`${name}.script`, page.querySelector('#script-text').value);
            break;
        case 'save-tle': saveFile(`${name}.tle`, result.tle); break;
        case 'save-opm': saveFile(`${name}.opm`, result.opm); break;
        case 'save-csv': saveFile(`${name}.csv`, ephemerisCsv(result), 'text/csv'); break;
        default: break;
    }
}

// Inspector: edits the selected mission object as a draft, applied with Apply or on Run.

import * as store from './store.js';
import { schemas, validate, visibleFields } from './mission.js';
import { escapeHtml, icon, num } from './format.js';

const EDITABLE = ['spacecraft', 'propagator'];
const drafts = {};
let root;

export function mountInspector(element) {
    root = element;
    resetDrafts();
    root.addEventListener('input', onInput);
    root.addEventListener('change', onChange);
    root.addEventListener('click', onClick);
    store.on('selection', render);
    store.on('result', render);
    render();
}

// On narrow windows the inspector slides over the views; selecting an object opens it.
export function openInspector() {
    root.classList.add('is-open');
}

// Applies every valid draft. Returns false and shows the errors if any draft is invalid.
export function applyAll() {
    let ok = true;
    let mission = store.get('mission');
    for (const kind of EDITABLE) {
        if (Object.keys(validate(kind, drafts[kind])).length) {
            ok = false;
        } else if (isDirty(kind)) {
            mission = { ...mission, [kind]: { ...drafts[kind] } };
        }
    }
    store.set({ mission });
    if (!ok) {
        const bad = EDITABLE.find((kind) => Object.keys(validate(kind, drafts[kind])).length);
        store.set({ selection: bad });
        openInspector();
    }
    render();
    return ok;
}

function resetDrafts(kind) {
    const mission = store.get('mission');
    for (const k of kind ? [kind] : EDITABLE) drafts[k] = { ...mission[k] };
}

function isDirty(kind) {
    const applied = store.get('mission')[kind];
    return Object.keys(applied).some((key) => !Object.is(applied[key], drafts[kind][key]));
}

function render() {
    const selection = store.get('selection');
    const close = `<button class="icon-button inspector-close" type="button" data-action="close" aria-label="Close inspector">${icon('x')}</button>`;
    if (EDITABLE.includes(selection)) root.innerHTML = renderForm(selection, close);
    else if (selection.startsWith('station:')) root.innerHTML = renderStation(Number(selection.split(':')[1]), close);
    else root.innerHTML = renderWatchInfo(close);
}

function renderForm(kind, close) {
    const values = drafts[kind];
    const errors = validate(kind, values);
    const dirty = isDirty(kind);
    const groups = visibleFields(kind, values).map((group) => `
        <details class="field-group" open>
            <summary>${icon('chevron-down')}<span>${group.title}</span></summary>
            ${group.fields.map((field) => renderField(field, values[field.key], errors[field.key])).join('')}
        </details>`).join('');
    return `
        <header class="inspector-head">
            <div>
                <h2 class="inspector-title">${escapeHtml(kind === 'spacecraft' ? values.name || 'Spacecraft' : schemas[kind].title)}</h2>
                <p class="inspector-kind">${kind === 'spacecraft' ? 'Spacecraft' : 'Integrator and force model'}</p>
            </div>
            ${close}
        </header>
        <form class="inspector-body" data-kind="${kind}" novalidate>${groups}</form>
        <footer class="inspector-foot">
            <span class="inspector-state">${dirty ? 'Unapplied changes' : 'Applied'}</span>
            <button class="button" type="button" data-action="revert" ${dirty ? '' : 'disabled'}>${icon('rotate-ccw')}Revert</button>
            <button class="button button-primary" type="button" data-action="apply" ${dirty && !Object.keys(errors).length ? '' : 'disabled'}>${icon('check')}Apply</button>
        </footer>`;
}

function renderField(field, value, error) {
    const id = `field-${field.key}`;
    const describedBy = [field.hint ? `${id}-hint` : '', error ? `${id}-error` : ''].filter(Boolean).join(' ');
    const aria = `${describedBy ? `aria-describedby="${describedBy}"` : ''} ${error ? 'aria-invalid="true"' : ''}`;
    let control;
    if (field.type === 'select') {
        control = `<select id="${id}" data-key="${field.key}" ${aria}>${field.options.map(([v, label]) =>
            `<option value="${v}" ${v === value ? 'selected' : ''}>${label}</option>`).join('')}</select>`;
    } else if (field.type === 'checkbox') {
        return `<div class="field field-check">
            <input id="${id}" type="checkbox" data-key="${field.key}" ${value ? 'checked' : ''}>
            <label for="${id}">${field.label}</label>
        </div>`;
    } else if (field.type === 'number') {
        control = `<input id="${id}" type="number" data-key="${field.key}" value="${Number.isFinite(value) ? value : ''}" step="${field.step}" ${aria}>`;
    } else {
        control = `<input id="${id}" type="text" data-key="${field.key}" value="${escapeHtml(value)}" ${aria}>`;
    }
    return `<div class="field${error ? ' has-error' : ''}" data-field="${field.key}">
        <label for="${id}">${field.label}</label>
        <div class="field-control">${control}${field.unit ? `<span class="field-unit">${field.unit}</span>` : ''}</div>
        ${field.hint ? `<p class="field-hint" id="${id}-hint">${field.hint}</p>` : ''}
        <p class="field-error" id="${id}-error" ${error ? '' : 'hidden'}>${error ?? ''}</p>
    </div>`;
}

function renderStation(index, close) {
    const station = store.get('result')?.stations[index];
    if (!station) return renderWatchInfo(close);
    const rows = [
        ['Latitude', `${num(station.lat_deg, 3)} deg`],
        ['Longitude', `${num(station.lon_deg, 3)} deg`],
        ['Altitude', `${num(station.alt_m)} m`],
        ['Minimum elevation', `${num(station.min_elevation_deg, 1)} deg`],
        ['Passes in this run', num(station.passes.length)],
        ['Total contact', `${num(station.contact_min, 1)} min`],
    ];
    return `
        <header class="inspector-head">
            <div>
                <h2 class="inspector-title">${escapeHtml(station.name)}</h2>
                <p class="inspector-kind">${escapeHtml(station.network)}</p>
            </div>
            ${close}
        </header>
        <div class="inspector-body">
            <dl class="readout">${rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('')}</dl>
            <p class="inspector-note">Stations are fixed by the engine for now and can't be edited here.</p>
        </div>`;
}

function renderWatchInfo(close) {
    return `
        <header class="inspector-head">
            <div>
                <h2 class="inspector-title">Watch</h2>
                <p class="inspector-kind">Output</p>
            </div>
            ${close}
        </header>
        <div class="inspector-body">
            <p class="inspector-note">Watch lists the spacecraft's state at the time shown on the timeline. Use Hold values to freeze it while playback continues.</p>
        </div>`;
}

function readValue(input) {
    if (input.type === 'checkbox') return input.checked;
    if (input.type === 'number') return input.value === '' ? NaN : input.valueAsNumber;
    return input.value;
}

function onInput(event) {
    const input = event.target;
    const form = input.closest('form');
    if (!form || input.tagName === 'SELECT' || input.type === 'checkbox') return;
    const kind = form.dataset.kind;
    drafts[kind][input.dataset.key] = readValue(input);
    updateStatus(kind);
}

function onChange(event) {
    const input = event.target;
    const form = input.closest('form');
    if (!form) return;
    const kind = form.dataset.kind;
    drafts[kind][input.dataset.key] = readValue(input);
    if (input.tagName === 'SELECT' || input.type === 'checkbox') {
        render();
        root.querySelector(`[data-key="${input.dataset.key}"]`)?.focus();
    } else {
        updateStatus(kind);
    }
}

// Updates errors and the Apply state in place, so typing never loses focus.
function updateStatus(kind) {
    const errors = validate(kind, drafts[kind]);
    for (const fieldEl of root.querySelectorAll('[data-field]')) {
        const key = fieldEl.dataset.field;
        const error = errors[key];
        const errorEl = fieldEl.querySelector('.field-error');
        const control = fieldEl.querySelector('[data-key]');
        fieldEl.classList.toggle('has-error', Boolean(error));
        errorEl.hidden = !error;
        errorEl.textContent = error ?? '';
        if (error) control.setAttribute('aria-invalid', 'true'); else control.removeAttribute('aria-invalid');
        const ids = [fieldEl.querySelector('.field-hint')?.id, error ? errorEl.id : null].filter(Boolean);
        if (ids.length) control.setAttribute('aria-describedby', ids.join(' ')); else control.removeAttribute('aria-describedby');
    }
    const dirty = isDirty(kind);
    root.querySelector('.inspector-state').textContent = dirty ? 'Unapplied changes' : 'Applied';
    root.querySelector('[data-action="revert"]').disabled = !dirty;
    root.querySelector('[data-action="apply"]').disabled = !dirty || Object.keys(errors).length > 0;
    if (kind === 'spacecraft') root.querySelector('.inspector-title').textContent = drafts.spacecraft.name || 'Spacecraft';
}

function onClick(event) {
    const action = event.target.closest('[data-action]')?.dataset.action;
    if (action === 'close') root.classList.remove('is-open');
    if (action === 'revert') {
        resetDrafts(store.get('selection'));
        render();
    }
    if (action === 'apply') {
        const kind = store.get('selection');
        if (Object.keys(validate(kind, drafts[kind])).length) return;
        store.set({ mission: { ...store.get('mission'), [kind]: { ...drafts[kind] } } });
        render();
    }
}

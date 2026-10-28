// Inspector: edits the selected mission object (spacecraft, propagator or a burn) as a draft,
// applied with Apply or on Run.
// View settings change only what is drawn, so they apply as soon as they are valid.

import * as store from './store.js';
import { schemas, validate, visibleFields } from './mission.js';
import { escapeHtml, icon, num } from './format.js';
import { VIEW_TYPES, paneTitle } from './views/registry.js';

const EDITABLE = ['spacecraft', 'propagator'];
const drafts = {};      // by kind: 'spacecraft', 'propagator' or 'burn:<index>'

const isBurn = (kind) => /^burn:\d+$/.test(kind);
const burnAt = (kind) => Number(kind.slice(5));
const schemaOf = (kind) => (isBurn(kind) ? schemas.burn : schemas[kind]);
const appliedOf = (kind, mission = store.get('mission')) => (isBurn(kind) ? mission.burns[burnAt(kind)] : mission[kind]);
const isEditable = (kind) => EDITABLE.includes(kind) || (isBurn(kind) && Boolean(appliedOf(kind)));
const editableKinds = () => [...EDITABLE, ...store.get('mission').burns.map((_, i) => `burn:${i}`)];

function withApplied(mission, kind, values) {
    if (!isBurn(kind)) return { ...mission, [kind]: { ...values } };
    return { ...mission, burns: mission.burns.map((burn, i) => (i === burnAt(kind) ? { ...values } : burn)) };
}
let root;

export function mountInspector(element) {
    root = element;
    resetDrafts();
    root.addEventListener('input', onInput);
    root.addEventListener('change', onChange);
    root.addEventListener('click', onClick);
    store.on('selection', render);
    store.on('result', render);
    // Keep the viewpoint fields current while the camera is dragged, but never re-render under the user's cursor.
    store.on('panes', () => {
        if (paneId() && !root.contains(document.activeElement)) render();
    });
    render();
}

function paneId() {
    const selection = store.get('selection');
    const id = selection.startsWith('pane:') ? selection.slice(5) : null;
    return id && store.get('panes')[id] ? id : null;
}

function updatePane(id, patch) {
    const panes = store.get('panes');
    store.set({ panes: { ...panes, [id]: { ...panes[id], settings: { ...panes[id].settings, ...patch } } } });
}

// On narrow windows the inspector slides over the views; selecting an object opens it.
export function openInspector() {
    root.classList.add('is-open');
}

// Replaces the whole mission (a file, sample or new mission), discarding unapplied edits.
export function loadMission(mission) {
    store.set({ mission });
    resetDrafts();
    render();
}

// Applies every valid draft. Returns false and shows the errors if any draft is invalid.
export function applyAll() {
    let ok = true;
    let mission = store.get('mission');
    const kinds = editableKinds();
    kinds.forEach(draftOf);
    for (const kind of kinds) {
        if (Object.keys(validate(schemaOf(kind), drafts[kind])).length) {
            ok = false;
        } else if (isDirty(kind)) {
            mission = withApplied(mission, kind, drafts[kind]);
        }
    }
    store.set({ mission });
    if (!ok) {
        const bad = kinds.find((kind) => Object.keys(validate(schemaOf(kind), drafts[kind])).length);
        store.set({ selection: bad });
        openInspector();
    }
    render();
    return ok;
}

function resetDrafts(kind) {
    if (!kind) for (const k of Object.keys(drafts)) delete drafts[k];
    for (const k of kind ? [kind] : editableKinds()) drafts[k] = { ...appliedOf(k) };
}

// A burn added in the mission tree gets its draft when it is first shown.
function draftOf(kind) {
    if (!drafts[kind]) drafts[kind] = { ...appliedOf(kind) };
    return drafts[kind];
}

// Removes a burn; the burns after it move up, and so do their unapplied edits.
function deleteBurn(kind) {
    const index = burnAt(kind);
    const mission = store.get('mission');
    const kept = mission.burns.map((_, i) => drafts[`burn:${i}`]).filter((_, i) => i !== index);
    for (const k of Object.keys(drafts)) if (isBurn(k)) delete drafts[k];
    kept.forEach((draft, i) => { if (draft) drafts[`burn:${i}`] = draft; });
    store.set({ mission: { ...mission, burns: mission.burns.filter((_, i) => i !== index) }, selection: 'propagator' });
}

function isDirty(kind) {
    const applied = appliedOf(kind);
    return Object.keys(applied).some((key) => !Object.is(applied[key], drafts[kind][key]));
}

function render() {
    const selection = store.get('selection');
    const close = `<button class="icon-button inspector-close" type="button" data-action="close" aria-label="Close inspector">${icon('x')}</button>`;
    if (isEditable(selection)) root.innerHTML = renderForm(selection, close);
    else if (paneId()) root.innerHTML = renderViewForm(paneId(), close);
    else if (selection.startsWith('station:')) root.innerHTML = renderStation(Number(selection.split(':')[1]), close);
    else root.innerHTML = renderEmpty(close);
}

const KIND_LABELS = { spacecraft: 'Spacecraft', propagator: 'Integrator and force model' };

function titleOf(kind, values) {
    if (kind === 'spacecraft') return values.name || 'Spacecraft';
    if (isBurn(kind)) return values.name || 'Burn';
    return schemas[kind].title;
}

function renderForm(kind, close) {
    const values = draftOf(kind);
    const errors = validate(schemaOf(kind), values);
    const dirty = isDirty(kind);
    const groups = renderGroups(schemaOf(kind), values, errors);
    const remove = isBurn(kind) ? `<button class="button" type="button" data-action="delete-burn">${icon('x')}Delete</button>` : '';
    return `
        <header class="inspector-head">
            <div>
                <h2 class="inspector-title">${escapeHtml(titleOf(kind, values))}</h2>
                <p class="inspector-kind">${isBurn(kind) ? `Impulsive burn ${burnAt(kind) + 1}, applied by Run` : KIND_LABELS[kind]}</p>
            </div>
            ${close}
        </header>
        <form class="inspector-body" data-kind="${kind}" novalidate>${groups}</form>
        <footer class="inspector-foot">
            <span class="inspector-state">${dirty ? 'Unapplied changes' : 'Applied'}</span>
            ${remove}
            <button class="button" type="button" data-action="revert" ${dirty ? '' : 'disabled'}>${icon('rotate-ccw')}Revert</button>
            <button class="button button-primary" type="button" data-action="apply" ${dirty && !Object.keys(errors).length ? '' : 'disabled'}>${icon('check')}Apply</button>
        </footer>`;
}

function renderGroups(schema, values, errors) {
    return visibleFields(schema, values).map((group) => `
        <details class="field-group" open>
            <summary>${icon('chevron-down')}<span>${group.title}</span></summary>
            ${group.fields.map((field) => renderField(field, values[field.key], errors[field.key])).join('')}
        </details>`).join('');
}

function renderViewForm(id, close) {
    const pane = store.get('panes')[id];
    const values = pane.settings;
    const viewpoints = pane.type === 'orbit3d' ? `
        <details class="field-group" open>
            <summary>${icon('chevron-down')}<span>Saved viewpoints</span></summary>
            <ul class="viewpoints">${values.viewpoints.map((vp, i) => `
                <li>
                    <button class="viewpoint-go" type="button" data-action="viewpoint-go" data-index="${i}">${escapeHtml(vp.name)}</button>
                    <button class="icon-button" type="button" data-action="viewpoint-delete" data-index="${i}" aria-label="Delete ${escapeHtml(vp.name)}" title="Delete">${icon('x')}</button>
                </li>`).join('')}
            </ul>
            <div class="field"><button class="button" type="button" data-action="viewpoint-save">${icon('plus')}Save current viewpoint</button></div>
        </details>` : '';
    return `
        <header class="inspector-head">
            <div>
                <h2 class="inspector-title">${escapeHtml(paneTitle(pane))}</h2>
                <p class="inspector-kind">View settings, applied as you change them</p>
            </div>
            ${close}
        </header>
        <form class="inspector-body" data-pane="${id}" novalidate>${renderGroups(VIEW_TYPES[pane.type].schema, values, {})}${viewpoints}</form>`;
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
    if (!station) return renderEmpty(close);
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

function renderEmpty(close) {
    return `
        <header class="inspector-head">
            <div><h2 class="inspector-title">Nothing selected</h2></div>
            ${close}
        </header>
        <div class="inspector-body">
            <p class="inspector-note">Select an object in the mission tree to see its settings.</p>
        </div>`;
}

function readValue(input) {
    if (input.type === 'checkbox') return input.checked;
    if (input.type === 'number') return input.value === '' ? NaN : input.valueAsNumber;
    return input.value;
}

// A valid view setting goes straight to the store; an invalid one only shows its error.
function setViewValue(id, input) {
    const pane = store.get('panes')[id];
    const values = { ...pane.settings, [input.dataset.key]: readValue(input) };
    const errors = validate(VIEW_TYPES[pane.type].schema, values);
    showErrors(errors);
    if (!errors[input.dataset.key]) updatePane(id, { [input.dataset.key]: values[input.dataset.key] });
}

function onInput(event) {
    const input = event.target;
    const form = input.closest('form');
    if (!form || input.tagName === 'SELECT' || input.type === 'checkbox') return;
    if (form.dataset.pane) {
        setViewValue(form.dataset.pane, input);
        return;
    }
    const kind = form.dataset.kind;
    drafts[kind][input.dataset.key] = readValue(input);
    updateStatus(kind);
}

function onChange(event) {
    const input = event.target;
    const form = input.closest('form');
    if (!form) return;
    if (form.dataset.pane) {
        if (!input.dataset.key) return;
        setViewValue(form.dataset.pane, input);
        if (input.tagName === 'SELECT') {
            render();   // a choice can show or hide other fields
            root.querySelector(`[data-key="${input.dataset.key}"]`)?.focus();
        }
        return;
    }
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
    const errors = validate(schemaOf(kind), drafts[kind]);
    showErrors(errors);
    const dirty = isDirty(kind);
    root.querySelector('.inspector-state').textContent = dirty ? 'Unapplied changes' : 'Applied';
    root.querySelector('[data-action="revert"]').disabled = !dirty;
    root.querySelector('[data-action="apply"]').disabled = !dirty || Object.keys(errors).length > 0;
    if (kind === 'spacecraft' || isBurn(kind)) root.querySelector('.inspector-title').textContent = titleOf(kind, drafts[kind]);
}

function showErrors(errors) {
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
}

function onClick(event) {
    const action = event.target.closest('[data-action]')?.dataset.action;
    if (action === 'close') root.classList.remove('is-open');
    if (action?.startsWith('viewpoint-')) {
        const id = paneId();
        const settings = store.get('panes')[id].settings;
        const index = Number(event.target.closest('[data-index]')?.dataset.index);
        if (action === 'viewpoint-go') {
            const { name, ...view } = settings.viewpoints[index];
            updatePane(id, view);
        } else if (action === 'viewpoint-delete') {
            updatePane(id, { viewpoints: settings.viewpoints.filter((_, i) => i !== index) });
        } else {
            const { ra, dec, distance, fov, frame, center } = settings;
            updatePane(id, { viewpoints: [...settings.viewpoints, { name: `Viewpoint ${settings.viewpoints.length + 1}`, ra, dec, distance, fov, frame, center }] });
        }
        render();
    }
    if (action === 'revert') {
        resetDrafts(store.get('selection'));
        render();
    }
    if (action === 'apply') {
        const kind = store.get('selection');
        if (Object.keys(validate(schemaOf(kind), drafts[kind])).length) return;
        store.set({ mission: withApplied(store.get('mission'), kind, drafts[kind]) });
        render();
    }
    if (action === 'delete-burn') deleteBurn(store.get('selection'));
}

// Workspace: tiled panes. Each pane shows any kind of view, picked from its header, and can be
// maximized. The arrangement and every pane's settings are remembered between sessions.

import * as store from './store.js';
import { escapeHtml, icon } from './format.js';
import { openInspector } from './inspector.js';
import { VIEW_TYPES, LAYOUTS, defaultPanes, paneTitle } from './views/registry.js';

const SAVED_KEY = 'astroflyer.workspace.v1';
const mounted = new Map();   // pane id -> { type, ctx, view }
let root;

export function mountWorkspace(element, layoutControls) {
    root = element;
    restore();

    for (const id of Object.keys(store.get('panes'))) {
        const panel = document.createElement('section');
        panel.className = 'view';
        panel.dataset.pane = id;
        panel.style.gridArea = id;
        panel.innerHTML = `
            <header class="view-head">
                <label class="pane-type">
                    <span class="visually-hidden">Show in this pane</span>
                    <select>${Object.entries(VIEW_TYPES).map(([type, v]) => `<option value="${type}">${v.label}</option>`).join('')}</select>
                </label>
                <button class="view-title" type="button" title="Show settings"></button>
                <div class="view-tools"></div>
                <button class="icon-button pane-max" type="button"></button>
            </header>
            <div class="view-body"></div>`;
        panel.querySelector('select').addEventListener('change', (event) => setPaneType(id, event.target.value));
        panel.querySelector('.view-title').addEventListener('click', () => {
            store.set({ selection: `pane:${id}` });
            openInspector();
        });
        panel.querySelector('.pane-max').addEventListener('click', () => {
            store.set({ maximized: store.get('maximized') === id ? null : id });
        });
        root.append(panel);
    }

    layoutControls.innerHTML = `${Object.entries(LAYOUTS).map(([id, layout]) =>
        `<button class="icon-button" type="button" data-layout="${id}" aria-label="${layout.label}" title="${layout.label}">${icon(layout.icon)}</button>`).join('')}
        <button class="icon-button" type="button" data-layout="reset" aria-label="Reset panes to the HEO layout" title="Reset panes to the HEO layout">${icon('rotate-ccw')}</button>`;
    layoutControls.addEventListener('click', (event) => {
        const layout = event.target.closest('[data-layout]')?.dataset.layout;
        if (layout === 'reset') store.set({ panes: defaultPanes(), layout: 'heo', maximized: null });
        else if (layout) store.set({ layout, maximized: null });
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && store.get('maximized')) store.set({ maximized: null });
    });
    store.on('selection', (selection) => {
        if (selection.startsWith('pane:')) store.set({ workspace: 'mission' });
    });
    store.on('panes', () => { sync(); save(); });
    store.on(['layout', 'maximized'], () => { arrange(); save(); });
    sync();
    arrange();

    function arrange() {
        const layout = store.get('layout');
        const maximized = store.get('maximized');
        root.dataset.layout = maximized ? 'single' : layout;
        for (const panel of root.children) {
            const id = panel.dataset.pane;
            panel.hidden = maximized ? id !== maximized : !LAYOUTS[layout].slots.includes(id);
            const max = panel.querySelector('.pane-max');
            const label = maximized === id ? 'Restore pane' : 'Maximize pane';
            max.innerHTML = icon(maximized === id ? 'minimize-2' : 'maximize-2');
            max.setAttribute('aria-label', label);
            max.title = label;
        }
        for (const button of layoutControls.querySelectorAll('[data-layout]')) {
            button.setAttribute('aria-pressed', String(button.dataset.layout === layout));
        }
    }
}

// Panes shown in the current layout, in slot order.
export function visiblePanes() {
    const maximized = store.get('maximized');
    const ids = maximized ? [maximized] : LAYOUTS[store.get('layout')].slots;
    const panes = store.get('panes');
    return ids.map((id) => ({ id, ...panes[id] }));
}

function setPaneType(id, type) {
    const panes = store.get('panes');
    store.set({ panes: { ...panes, [id]: { type, settings: VIEW_TYPES[type].defaults() } } });
}

// Mounts each pane's view, replacing it when the pane's view type changes.
function sync() {
    const panes = store.get('panes');
    for (const panel of root.children) {
        const id = panel.dataset.pane;
        const pane = panes[id];
        const title = panel.querySelector('.view-title');
        title.innerHTML = `${icon(VIEW_TYPES[pane.type].icon)}<span>${escapeHtml(paneTitle(pane))}</span>`;
        panel.setAttribute('aria-label', paneTitle(pane));
        panel.querySelector('select').value = pane.type;
        panel.dataset.view = pane.type;
        const current = mounted.get(id);
        if (current?.type === pane.type) continue;
        if (current) {
            current.view.destroy();
            current.ctx.dispose();
        }
        const body = panel.querySelector('.view-body');
        const tools = panel.querySelector('.view-tools');
        body.innerHTML = '';
        tools.innerHTML = '';
        const ctx = paneContext(id, body, tools);
        mounted.set(id, { type: pane.type, ctx, view: VIEW_TYPES[pane.type].create(ctx) });
    }
}

// What a view needs from its pane: its body and header tools, its settings, and subscriptions
// that are removed with the view.
function paneContext(id, body, tools) {
    const offs = [];
    return {
        id,
        body,
        tools,
        settings: () => store.get('panes')[id].settings,
        update(patch) {
            const panes = store.get('panes');
            store.set({ panes: { ...panes, [id]: { ...panes[id], settings: { ...panes[id].settings, ...patch } } } });
        },
        on(keys, fn) {
            offs.push(store.on(keys, fn));
        },
        onSettings(fn) {
            let last = store.get('panes')[id].settings;
            offs.push(store.on('panes', (panes) => {
                const next = panes[id]?.settings;
                if (next && next !== last) {
                    last = next;
                    fn(next);
                }
            }));
        },
        dispose() {
            offs.forEach((off) => off());
        },
    };
}

function restore() {
    let saved = null;
    try { saved = JSON.parse(localStorage.getItem(SAVED_KEY)); } catch { /* storage unavailable or corrupt */ }
    const fresh = defaultPanes();
    const valid = saved && LAYOUTS[saved.layout] && Object.keys(fresh).every((id) => VIEW_TYPES[saved.panes?.[id]?.type]);
    if (!valid) {
        store.set({ panes: fresh, layout: 'heo' });
        return;
    }
    // Fill in settings added since the layout was saved.
    const panes = Object.fromEntries(Object.keys(fresh).map((id) => {
        const { type, settings } = saved.panes[id];
        return [id, { type, settings: { ...VIEW_TYPES[type].defaults(), ...settings } }];
    }));
    store.set({ panes, layout: saved.layout });
}

let saveTimer = null;
function save() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
        try {
            localStorage.setItem(SAVED_KEY, JSON.stringify({ layout: store.get('layout'), panes: store.get('panes') }));
        } catch { /* the layout just won't be remembered */ }
    }, 500);
}

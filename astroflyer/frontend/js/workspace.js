// Workspace: the view panels and how they are arranged (one, two side by side, or all).

import * as store from './store.js';
import { icon } from './format.js';
import { openInspector } from './inspector.js';
import { VIEWS } from './views/settings.js';
import { mountOrbit3d } from './views/orbit3d.js';
import { mountGroundtrack } from './views/groundtrack.js';
import { mountPlot } from './views/plot.js';
import { mountWatch } from './views/watch.js';

const MOUNT = { orbit3d: mountOrbit3d, groundtrack: mountGroundtrack, plot: mountPlot, watch: mountWatch };
const LAYOUTS = [
    ['single', 'rectangle-horizontal', 'One view'],
    ['split', 'columns-2', '3D and ground track side by side'],
    ['grid', 'layout-grid', 'All views'],
];
const LAYOUT_KEY = 'astroflyer.layout';

let root;
let focus = 'orbit3d';   // the view shown in the one-view layout

export function mountWorkspace(element, layoutControls) {
    root = element;
    for (const view of VIEWS) {
        const panel = document.createElement('section');
        panel.className = 'view';
        panel.dataset.view = view.id;
        panel.setAttribute('aria-label', view.label);
        panel.innerHTML = `
            <header class="view-head">
                <button class="view-title" type="button" title="Show settings">${icon(view.icon)}<span>${view.label}</span></button>
                <div class="view-tools"></div>
            </header>
            <div class="view-body"></div>`;
        panel.querySelector('.view-title').addEventListener('click', () => {
            store.set({ selection: `view:${view.id}` });
            openInspector();
        });
        root.append(panel);
        MOUNT[view.id](panel.querySelector('.view-body'), panel.querySelector('.view-tools'));
    }

    layoutControls.innerHTML = LAYOUTS.map(([id, name, label]) =>
        `<button class="icon-button" type="button" data-layout="${id}" aria-label="${label}" title="${label}">${icon(name)}</button>`).join('');
    layoutControls.addEventListener('click', (event) => {
        const layout = event.target.closest('[data-layout]')?.dataset.layout;
        if (!layout) return;
        store.set({ layout });
        try { localStorage.setItem(LAYOUT_KEY, layout); } catch { /* layout just won't be remembered */ }
    });

    try {
        const saved = localStorage.getItem(LAYOUT_KEY);
        if (LAYOUTS.some(([id]) => id === saved)) store.set({ layout: saved });
    } catch { /* storage unavailable */ }

    store.on('selection', (selection) => {
        if (!selection.startsWith('view:')) return;
        focus = selection.slice(5);
        store.set({ workspace: 'mission' });
        if (store.get('layout') === 'single') arrange();
    });
    store.on('layout', arrange);
    arrange();

    function arrange() {
        const layout = store.get('layout');
        root.dataset.layout = layout;
        for (const panel of root.children) {
            const id = panel.dataset.view;
            panel.hidden = layout === 'single' ? id !== focus : layout === 'split' ? !['orbit3d', 'groundtrack'].includes(id) : false;
        }
        for (const button of layoutControls.querySelectorAll('[data-layout]')) {
            button.setAttribute('aria-pressed', String(button.dataset.layout === layout));
        }
    }
}

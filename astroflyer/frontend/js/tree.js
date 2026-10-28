// Mission tree: the objects in the mission. Selecting one opens it in the inspector.

import * as store from './store.js';
import { newBurn } from './mission.js';
import { escapeHtml, icon } from './format.js';
import { openInspector } from './inspector.js';
import { VIEW_TYPES, paneTitle } from './views/registry.js';
import { visiblePanes } from './workspace.js';

let root;
const expanded = new Set(['burns', 'stations', 'outputs']);

export function mountTree(element) {
    root = element;
    root.addEventListener('click', (event) => {
        const item = event.target.closest('[role="treeitem"]');
        if (!item) return;
        if (event.target.closest('.tree-twisty')) toggle(item.dataset.id);
        else activate(item);
    });
    root.addEventListener('keydown', onKey);
    store.on(['mission', 'result', 'selection', 'panes', 'layout', 'maximized'], render);
    render();
}

function items() {
    const mission = store.get('mission');
    const result = store.get('result');
    const stations = result?.stations ?? [];
    return [
        { id: 'spacecraft', icon: 'satellite', label: mission.spacecraft.name },
        { id: 'propagator', icon: 'settings-2', label: 'Propagator' },
        {
            id: 'burns', icon: 'rocket', label: 'Burns', group: true,
            children: [
                ...mission.burns.map((burn, i) => ({ id: `burn:${i}`, label: burn.name })),
                { id: 'burn:add', icon: 'plus', label: 'Add burn' },
            ],
        },
        {
            id: 'stations', icon: 'radio-tower', label: 'Ground stations', group: true,
            empty: 'Listed after the first run',
            children: stations.map((st, i) => ({ id: `station:${i}`, label: st.name })),
        },
        {
            id: 'outputs', icon: 'file-output', label: 'Outputs', group: true,
            children: visiblePanes().map((pane) => ({ id: `pane:${pane.id}`, icon: VIEW_TYPES[pane.type].icon, label: paneTitle(pane) })),
        },
    ];
}

function render() {
    const selection = store.get('selection');
    const row = (item, level) => {
        const isOpen = expanded.has(item.id);
        const selectable = !item.group;
        const selected = item.id === selection;
        const attrs = [
            'role="treeitem"',
            `data-id="${item.id}"`,
            `aria-level="${level}"`,
            selectable ? `aria-selected="${selected}"` : '',
            item.group ? `aria-expanded="${isOpen}"` : '',
            `tabindex="${selected ? 0 : -1}"`,
        ].join(' ');
        const children = item.group && isOpen
            ? `<ul role="group">${item.children.length
                ? item.children.map((child) => row(child, level + 1)).join('')
                : `<li class="tree-empty">${item.empty}</li>`}</ul>`
            : '';
        return `<li ${attrs} class="tree-item${selected ? ' is-selected' : ''}">
            <span class="tree-row" style="--level:${level}">
                ${item.group ? `<span class="tree-twisty">${icon(isOpen ? 'chevron-down' : 'chevron-right')}</span>` : '<span class="tree-twisty"></span>'}
                ${item.icon ? icon(item.icon) : ''}
                <span class="tree-label">${escapeHtml(item.label)}</span>
            </span>${children}</li>`;
    };
    const hadFocus = root.contains(document.activeElement);
    root.innerHTML = items().map((item) => row(item, 1)).join('');
    if (!root.querySelector('[tabindex="0"]')) root.querySelector('[role="treeitem"]').tabIndex = 0;
    if (hadFocus) root.querySelector('[tabindex="0"]').focus();
}

function toggle(id) {
    if (expanded.has(id)) expanded.delete(id); else expanded.add(id);
    render();
    focusItem(id);
}

function activate(item) {
    if (item.hasAttribute('aria-expanded')) toggle(item.dataset.id);
    else if (item.dataset.id === 'burn:add') {
        const mission = store.get('mission');
        const burns = [...mission.burns, newBurn(mission.burns.length)];
        store.set({ mission: { ...mission, burns }, selection: `burn:${burns.length - 1}` });
        openInspector();
    } else {
        store.set({ selection: item.dataset.id });
        openInspector();
    }
}

function focusItem(id) {
    const all = [...root.querySelectorAll('[role="treeitem"]')];
    for (const el of all) el.tabIndex = el.dataset.id === id ? 0 : -1;
    all.find((el) => el.dataset.id === id)?.focus();
}

function onKey(event) {
    const current = event.target.closest('[role="treeitem"]');
    if (!current) return;
    const visible = [...root.querySelectorAll('[role="treeitem"]')];
    const index = visible.indexOf(current);
    const id = current.dataset.id;
    const isGroup = current.hasAttribute('aria-expanded');
    switch (event.key) {
        case 'ArrowDown': focusItem(visible[Math.min(index + 1, visible.length - 1)].dataset.id); break;
        case 'ArrowUp': focusItem(visible[Math.max(index - 1, 0)].dataset.id); break;
        case 'ArrowRight': if (isGroup && !expanded.has(id)) toggle(id); break;
        case 'ArrowLeft': if (isGroup && expanded.has(id)) toggle(id); break;
        case 'Enter':
        case ' ': activate(current); break;
        default: return;
    }
    event.preventDefault();
}

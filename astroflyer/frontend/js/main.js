import * as store from './store.js';
import { defaultMission } from './mission.js';
import { mountTree } from './tree.js';
import { mountInspector } from './inspector.js';
import { mountTimeline } from './timeline.js';
import { mountMessages, log } from './messages.js';
import { mountWorkspace } from './workspace.js';
import { mountTools } from './tools.js';
import { mountHome, saveMission } from './home.js';
import { mountStatus } from './status.js';

store.set({ mission: structuredClone(defaultMission) });

mountMessages(document.getElementById('messages'));
// Panes first: the tree lists them.
mountWorkspace(document.getElementById('workspace'), document.getElementById('layout-controls'));
mountTree(document.getElementById('tree'));
mountInspector(document.getElementById('inspector'));
mountTimeline(document.getElementById('timeline'));
mountTools(document.getElementById('tools'));
mountHome(document.getElementById('home'));
mountStatus(document.getElementById('status'));

document.querySelector('.topbar-actions').addEventListener('click', (event) => {
    const action = event.target.closest('[data-action]')?.dataset.action;
    if (action === 'home') store.set({ home: !store.get('home') });
    if (action === 'save') saveMission();
});

// The mission tree and inspector can be hidden to give the views the whole width.
const app = document.getElementById('app');
const PANELS_KEY = 'astroflyer.panels.v1';
const setPanel = (panel, shown) => {
    app.classList.toggle(`hide-${panel}`, !shown);
    const button = document.querySelector(`[data-panel="${panel}"]`);
    button.setAttribute('aria-pressed', String(shown));
    const label = `${shown ? 'Hide' : 'Show'} ${panel === 'tree' ? 'mission tree' : 'inspector'}`;
    button.setAttribute('aria-label', label);
    button.title = label;
};
let panels = { tree: true, inspector: true };
try { panels = { ...panels, ...JSON.parse(localStorage.getItem(PANELS_KEY)) }; } catch { /* use defaults */ }
for (const [panel, shown] of Object.entries(panels)) setPanel(panel, shown);
document.querySelector('.panel-toggles').addEventListener('click', (event) => {
    const panel = event.target.closest('[data-panel]')?.dataset.panel;
    if (!panel) return;
    panels[panel] = !panels[panel];
    setPanel(panel, panels[panel]);
    try { localStorage.setItem(PANELS_KEY, JSON.stringify(panels)); } catch { /* not remembered */ }
});

// Mission shows the views; Analysis and Data show tools in the same place.
const switcher = document.getElementById('workspace-switch');
switcher.addEventListener('click', (event) => {
    const workspace = event.target.closest('[data-workspace]')?.dataset.workspace;
    if (workspace) store.set({ workspace });
});
store.on('workspace', (workspace) => {
    for (const button of switcher.querySelectorAll('[data-workspace]')) {
        button.setAttribute('aria-selected', String(button.dataset.workspace === workspace));
    }
    document.getElementById('workspace').hidden = workspace !== 'mission';
    document.getElementById('layout-controls').hidden = workspace !== 'mission';
    document.getElementById('tools').hidden = workspace === 'mission';
    store.set({ home: false });
});

const missionName = document.getElementById('topbar-mission');
const showName = () => {
    const name = store.get('mission').spacecraft.name;
    missionName.textContent = name;
    document.title = `${name} - AstroFlyer`;
};
store.on('mission', showName);
showName();

store.set({ home: true });
log('info', 'Ready. Pick a sample or set up the spacecraft and propagator, then press Run.');

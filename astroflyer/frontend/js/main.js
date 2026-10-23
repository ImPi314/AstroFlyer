import * as store from './store.js';
import { defaultMission } from './mission.js';
import { defaultViewSettings } from './views/settings.js';
import { mountTree } from './tree.js';
import { mountInspector } from './inspector.js';
import { mountTimeline } from './timeline.js';
import { mountMessages, log } from './messages.js';
import { mountWorkspace } from './workspace.js';
import { mountTools } from './tools.js';

store.set({
    mission: structuredClone(defaultMission),
    views: structuredClone(defaultViewSettings),
});

mountMessages(document.getElementById('messages'));
mountTree(document.getElementById('tree'));
mountInspector(document.getElementById('inspector'));
mountTimeline(document.getElementById('timeline'));
mountWorkspace(document.getElementById('workspace'), document.getElementById('layout-controls'));
mountTools(document.getElementById('tools'));

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
});

const missionName = document.getElementById('topbar-mission');
const showName = () => {
    const name = store.get('mission').spacecraft.name;
    missionName.textContent = name;
    document.title = `${name} - AstroFlyer`;
};
store.on('mission', showName);
showName();

log('info', 'Ready. Set up the spacecraft and propagator, then press Run.');

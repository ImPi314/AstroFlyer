import * as store from './store.js';
import { defaultMission } from './mission.js';
import { defaultViewSettings } from './views/settings.js';
import { mountTree } from './tree.js';
import { mountInspector } from './inspector.js';
import { mountTimeline } from './timeline.js';
import { mountMessages, log } from './messages.js';
import { mountWorkspace } from './workspace.js';

store.set({
    mission: structuredClone(defaultMission),
    views: structuredClone(defaultViewSettings),
});

mountMessages(document.getElementById('messages'));
mountTree(document.getElementById('tree'));
mountInspector(document.getElementById('inspector'));
mountTimeline(document.getElementById('timeline'));
mountWorkspace(document.getElementById('workspace'), document.getElementById('layout-controls'));

const missionName = document.getElementById('topbar-mission');
const showName = () => {
    const name = store.get('mission').spacecraft.name;
    missionName.textContent = name;
    document.title = `${name} - AstroFlyer`;
};
store.on('mission', showName);
showName();

log('info', 'Ready. Set up the spacecraft and propagator, then press Run.');

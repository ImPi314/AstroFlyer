import * as store from './store.js';
import { defaultMission } from './mission.js';
import { mountTree } from './tree.js';
import { mountInspector } from './inspector.js';
import { mountTimeline } from './timeline.js';
import { mountMessages, log } from './messages.js';
import { mountWatch } from './views/watch.js';

store.set({ mission: structuredClone(defaultMission) });

mountMessages(document.getElementById('messages'));
mountTree(document.getElementById('tree'));
mountInspector(document.getElementById('inspector'));
mountTimeline(document.getElementById('timeline'));

const workspace = document.getElementById('workspace');
const watch = document.createElement('section');
watch.className = 'view';
watch.setAttribute('aria-label', 'Watch');
workspace.append(watch);
mountWatch(watch);

const missionName = document.getElementById('topbar-mission');
const showName = () => {
    const name = store.get('mission').spacecraft.name;
    missionName.textContent = name;
    document.title = `${name} - AstroFlyer`;
};
store.on('mission', showName);
showName();

log('info', 'Ready. Set up the spacecraft and propagator, then press Run.');

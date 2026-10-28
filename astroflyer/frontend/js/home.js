// Home screen and mission files: start a new mission, open or save one, reopen a recent one,
// or start from an HEO sample. Mission files are JSON holding the spacecraft, propagator, burns
// and the legs the mission was continued from (see mission.js).

import * as store from './store.js';
import { continueFromEnd, defaultMission, missionFileText, readMissionFile, withDefaults } from './mission.js';
import { loadMission } from './inspector.js';
import { log } from './messages.js';
import { escapeHtml, icon, num, saveFile } from './format.js';
import { SAMPLES, sampleMission } from './samples.js';

const RECENT_KEY = 'astroflyer.recent.v1';
const MAX_RECENT = 6;

let root;
let picker;

export function mountHome(element) {
    root = element;
    root.addEventListener('click', onClick);
    root.addEventListener('change', (event) => {
        if (event.target.name === 'open-file') openFile(event.target.files[0]);
    });
    // The top bar's Open button and Ctrl+O use one hidden file chooser.
    picker = document.createElement('input');
    Object.assign(picker, { type: 'file', accept: '.json,application/json', hidden: true });
    picker.addEventListener('change', () => { openFile(picker.files[0]); picker.value = ''; });
    document.body.append(picker);
    store.on('home', render);
    document.addEventListener('keydown', (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
            event.preventDefault();
            saveMission();
        }
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'o') {
            event.preventDefault();
            chooseMissionFile();
        }
        if (event.key === 'Escape' && store.get('home')) store.set({ home: false });
    });
    render();
}

export function chooseMissionFile() {
    picker.click();
}

export function saveMission() {
    const mission = store.get('mission');
    const name = `${mission.spacecraft.name.replace(/[^\w.-]+/g, '_')}.json`;
    saveFile(name, missionFileText(mission), 'application/json');
    store.set({ missionFile: name });
    remember(name, mission);
    log('info', `Saved ${name}.`);
}

function render() {
    root.hidden = !store.get('home');
    if (root.hidden) return;
    const recent = readRecent();
    root.innerHTML = `
        <div class="home-inner">
            <header class="home-head">
                <h2 class="tool-title">Start</h2>
                <button class="icon-button" type="button" data-action="close" aria-label="Close" title="Close (Esc)">${icon('x')}</button>
            </header>
            <div class="home-actions">
                <button class="button" type="button" data-action="new">${icon('plus')}New mission</button>
                <label class="button">${icon('folder-open')}Open mission file<input class="visually-hidden" type="file" name="open-file" accept=".json,application/json"></label>
            </div>
            ${recent.length ? `
                <h3 class="section-title">Recent</h3>
                <ul class="recent">${recent.map((r, i) => `
                    <li><button type="button" data-action="recent" data-index="${i}">
                        <span>${escapeHtml(r.file)}</span>
                        <span class="muted">${escapeHtml(r.mission.spacecraft.name)}, saved ${new Date(r.savedAt).toLocaleString('en-GB')}</span>
                    </button></li>`).join('')}
                </ul>` : ''}
            <h3 class="section-title">HEO samples</h3>
            <div class="samples">${SAMPLES.map((s, i) => `
                <button class="sample" type="button" data-action="sample" data-index="${i}">
                    <span class="sample-name">${s.name}</span>
                    <span class="sample-lead">${s.lead}</span>
                    <span class="sample-meta">${sampleMeta(s)}</span>
                    <span class="sample-meta">${escapeHtml(s.source)}</span>
                </button>`).join('')}
            </div>
        </div>`;
}

function sampleMeta(sample) {
    const sc = sample.spacecraft;
    const shape = sc.orbitInput === 'apsides' ? `${num(sc.hp)} by ${num(sc.ha)} km` : `a ${num(sc.a)} km, e ${sc.e}`;
    return `${shape}, ${num(sc.inc, 1)} deg, ${sample.orbits} orbits`;
}

function start(mission, file) {
    loadMission(mission);
    store.set({ missionFile: file, home: false, workspace: 'mission', selection: 'spacecraft' });
}

function onClick(event) {
    const target = event.target.closest('[data-action]');
    if (!target) return;
    const index = Number(target.dataset.index);
    switch (target.dataset.action) {
        case 'close': store.set({ home: false }); break;
        case 'new': start(structuredClone(defaultMission), null); break;
        case 'recent': {
            const r = readRecent()[index];
            start(withDefaults(r.mission), r.file);
            break;
        }
        case 'sample': {
            const sample = SAMPLES[index];
            start(sampleMission(sample), null);
            log('info', `Loaded the ${sample.name} sample. Press Run to propagate it.`);
            break;
        }
        default: break;
    }
}

async function openFile(file) {
    if (!file) return;
    try {
        const mission = readMissionFile(await file.text());
        start(mission, file.name);
        remember(file.name, mission);
        const legs = mission.history.length;
        log('info', `Opened ${file.name}${legs ? `, continued from ${legs} earlier leg${legs > 1 ? 's' : ''}` : ''}.`);
    } catch (err) {
        log('error', `Could not open ${file.name}: ${err.message}.`);
    }
}

// Carries the mission on from the end of the last run: the next Run starts at its final state,
// with whatever propagator settings the user picks. Saving then keeps that point as a checkpoint.
export function continueMission() {
    const result = store.get('result');
    if (!result?.finalState) {
        log('error', 'Run the mission first: Continue starts from the end of the last run.');
        return;
    }
    if (result.impact) {
        log('error', 'The last run ended on the Earth\'s surface, so there is nothing to continue.');
        return;
    }
    const mission = continueFromEnd(store.get('mission'), result);
    const cleared = store.get('mission').burns.length;
    loadMission(mission);
    store.set({ selection: 'propagator' });
    log('info', `Continuing from the end of the last run, ${mission.spacecraft.epoch} UTC, mass ${num(mission.spacecraft.mass, 1)} kg.`
        + `${cleared ? ' Its burns were cleared; add new ones for this leg.' : ''} Change the settings and press Run. Save keeps this point as a checkpoint.`);
}

function readRecent() {
    try {
        const list = JSON.parse(localStorage.getItem(RECENT_KEY));
        return Array.isArray(list) ? list.filter((r) => r?.mission?.spacecraft && r?.mission?.propagator) : [];
    } catch {
        return [];
    }
}

function remember(file, mission) {
    const list = [{ file, mission, savedAt: Date.now() }, ...readRecent().filter((r) => r.file !== file)].slice(0, MAX_RECENT);
    try { localStorage.setItem(RECENT_KEY, JSON.stringify(list)); } catch { /* recent list just isn't kept */ }
}

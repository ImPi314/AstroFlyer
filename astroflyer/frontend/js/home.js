// Home screen and mission files: start a new mission, open or save one, reopen a recent one,
// or start from an HEO sample. Mission files are JSON holding the spacecraft and propagator.

import * as store from './store.js';
import { defaultMission, schemas, validate } from './mission.js';
import { loadMission } from './inspector.js';
import { log } from './messages.js';
import { escapeHtml, icon, num, saveFile } from './format.js';

const FORMAT = 'astroflyer-mission';
const RECENT_KEY = 'astroflyer.recent.v1';
const MAX_RECENT = 6;

// Starting orbits for common highly elliptical and inclined missions. Only the orbit and
// duration differ from the default mission.
const SAMPLES = [
    {
        name: 'Molniya',
        lead: 'Twelve-hour orbit at 63.4 deg with apogee held over the northern hemisphere.',
        spacecraft: { orbitInput: 'apsides', hp: 1000, ha: 39350, inc: 63.4, raan: 45, aop: 270, ta: 0 },
        orbits: 3,
    },
    {
        name: 'Tundra',
        lead: 'Geosynchronous period with e = 0.25, so the spacecraft dwells over one region each day.',
        spacecraft: { orbitInput: 'keplerian', a: 42164, e: 0.25, inc: 63.4, raan: 0, aop: 270, ta: 0 },
        orbits: 2,
    },
    {
        name: 'GTO',
        lead: 'Geostationary transfer orbit from a 28.5 deg launch site, apogee at GEO altitude.',
        spacecraft: { orbitInput: 'apsides', hp: 250, ha: 35786, inc: 28.5, raan: 0, aop: 180, ta: 0 },
        orbits: 3,
    },
    {
        name: 'QZS-1',
        lead: 'Quasi-zenith orbit: geosynchronous, e = 0.075 and 41 deg, tracing a figure eight over Japan.',
        spacecraft: { orbitInput: 'keplerian', a: 42164, e: 0.075, inc: 41, raan: 0, aop: 270, ta: 0 },
        orbits: 2,
    },
];

let root;

export function mountHome(element) {
    root = element;
    root.addEventListener('click', onClick);
    root.addEventListener('change', (event) => {
        if (event.target.name === 'open-file') openFile(event.target.files[0]);
    });
    store.on('home', render);
    document.addEventListener('keydown', (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
            event.preventDefault();
            saveMission();
        }
        if (event.key === 'Escape' && store.get('home')) store.set({ home: false });
    });
    render();
}

export function saveMission() {
    const mission = store.get('mission');
    const name = `${mission.spacecraft.name.replace(/[^\w.-]+/g, '_')}.json`;
    saveFile(name, `${JSON.stringify({ format: FORMAT, version: 1, mission }, null, 2)}\n`, 'application/json');
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
            start(r.mission, r.file);
            break;
        }
        case 'sample': {
            const sample = SAMPLES[index];
            const mission = structuredClone(defaultMission);
            Object.assign(mission.spacecraft, sample.spacecraft, { name: sample.name });
            mission.propagator.num_orbits = sample.orbits;
            start(mission, null);
            log('info', `Loaded the ${sample.name} sample. Press Run to propagate it.`);
            break;
        }
        default: break;
    }
}

async function openFile(file) {
    if (!file) return;
    try {
        const data = JSON.parse(await file.text());
        if (data?.format !== FORMAT) throw new Error('it is not an AstroFlyer mission file');
        // Start from the defaults so files saved before a field existed still open, and keep
        // only the fields AstroFlyer knows.
        const pick = (kind) => Object.fromEntries(Object.entries(defaultMission[kind]).map(([key, fallback]) => [key, data.mission?.[kind]?.[key] ?? fallback]));
        const mission = { spacecraft: pick('spacecraft'), propagator: pick('propagator') };
        const problems = ['spacecraft', 'propagator'].flatMap((kind) => Object.keys(validate(schemas[kind], mission[kind])));
        if (problems.length) throw new Error(`these values are missing or out of range: ${problems.join(', ')}`);
        start(mission, file.name);
        remember(file.name, mission);
        log('info', `Opened ${file.name}.`);
    } catch (err) {
        log('error', `Could not open ${file.name}: ${err.message}.`);
    }
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

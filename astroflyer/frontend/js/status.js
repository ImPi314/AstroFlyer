// Status bar: the mission file, how many errors were logged, and the run state with a timer.

import * as store from './store.js';
import { onErrorCount } from './messages.js';
import { escapeHtml, num } from './format.js';

let root;
let timer = null;

export function mountStatus(element) {
    root = element;
    root.innerHTML = '<span data-status="file"></span><span data-status="errors"></span><span data-status="run"></span>';
    store.on(['missionFile', 'mission'], renderFile);
    store.on(['run', 'result'], renderRun);
    onErrorCount((count) => {
        const el = root.querySelector('[data-status="errors"]');
        el.textContent = count === 1 ? '1 error' : `${num(count)} errors`;
        el.dataset.level = count ? 'error' : '';
    });
    renderFile();
    renderRun();
}

function renderFile() {
    const file = store.get('missionFile');
    root.querySelector('[data-status="file"]').innerHTML = file ? escapeHtml(file) : '<span class="muted">Unsaved mission</span>';
}

function renderRun() {
    const run = store.get('run');
    const el = root.querySelector('[data-status="run"]');
    clearInterval(timer);
    timer = null;
    el.dataset.level = run.status !== 'running' && store.get('result')?.impact ? 'error' : '';
    if (run.status === 'running') {
        const tick = () => { el.textContent = `Running, ${num((performance.now() - run.startedAt) / 1000, 1)} s`; };
        tick();
        timer = setInterval(tick, 200);
    } else if (run.status === 'failed') {
        el.textContent = 'Run failed';
    } else if (store.get('result')?.impact) {
        el.textContent = `Ended at surface impact, last run ${num(store.get('result').summary.solve_s, 2)} s`;
    } else if (store.get('result')) {
        el.textContent = `Stopped, last run ${num(store.get('result').summary.solve_s, 2)} s`;
    } else {
        el.textContent = 'Stopped';
    }
}

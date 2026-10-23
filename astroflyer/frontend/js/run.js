// Owns the propagation request: starting it, cancelling it, and publishing the result.

import * as store from './store.js';
import { propagate, propagateScript, EngineError } from './api.js';
import { toPropagateRequest } from './mission.js';
import { fromPayload } from './results.js';
import { log } from './messages.js';
import { num } from './format.js';

// Request fields that describe the orbit; a script run takes these from the script instead.
const ORBIT_FIELDS = ['hp', 'ha', 'a', 'e', 'inc', 'raan', 'aop', 'ta'];

let controller = null;

export function isRunning() {
    return controller !== null;
}

export function startRun() {
    const mission = store.get('mission');
    return execute(
        `Propagating ${mission.spacecraft.name} for ${num(mission.propagator.num_orbits, 1)} orbits.`,
        (signal) => propagate(toPropagateRequest(mission), signal),
    );
}

export function startScriptRun(scriptText) {
    const body = toPropagateRequest(store.get('mission'));
    for (const field of ORBIT_FIELDS) delete body[field];
    return execute('Propagating the orbit in the mission script.', (signal) => propagateScript(scriptText, body, signal));
}

async function execute(startMessage, call) {
    if (controller) return;
    controller = new AbortController();
    const mine = controller;
    store.set({ run: { status: 'running', error: null }, playing: false });
    log('info', startMessage);

    try {
        const result = fromPayload(await call(mine.signal));
        store.set({ result, time: result.times[0], run: { status: 'done', error: null }, playing: true });
        log('info', `Finished in ${num(result.summary.solve_s, 2)} s with ${num(result.summary.points)} points. Perigee ${num(result.summary.perigee_alt_km)} km, apogee ${num(result.summary.apogee_alt_km)} km.`);
    } catch (err) {
        if (err.name === 'AbortError') {
            const hasResult = Boolean(store.get('result'));
            store.set({ run: { status: hasResult ? 'done' : 'idle', error: null } });
            log('info', hasResult ? 'Run stopped. The previous result is still shown.' : 'Run stopped.');
        } else {
            const message = err instanceof EngineError ? err.message : `Unexpected error: ${err.message}`;
            store.set({ run: { status: 'failed', error: message } });
            log('error', message);
        }
    } finally {
        if (controller === mine) controller = null;
    }
}

export function stopRun() {
    controller?.abort();
}

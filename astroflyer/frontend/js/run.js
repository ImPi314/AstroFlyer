// Owns the propagation request: starting it, cancelling it, and publishing the result.

import * as store from './store.js';
import { propagate, EngineError } from './api.js';
import { toPropagateRequest } from './mission.js';
import { fromPayload } from './results.js';
import { log } from './messages.js';
import { num } from './format.js';

let controller = null;

export function isRunning() {
    return controller !== null;
}

export async function startRun() {
    if (controller) return;
    const mission = store.get('mission');
    controller = new AbortController();
    const mine = controller;
    store.set({ run: { status: 'running', error: null }, playing: false });
    log('info', `Propagating ${mission.spacecraft.name} for ${num(mission.propagator.num_orbits, 1)} orbits.`);

    try {
        const payload = await propagate(toPropagateRequest(mission), mine.signal);
        const result = fromPayload(payload);
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

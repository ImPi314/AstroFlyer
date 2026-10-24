// Owns the propagation request: starting it, cancelling it, and publishing the result.

import * as store from './store.js';
import { propagate, propagateScript, EngineError } from './api.js';
import { toPropagateRequest } from './mission.js';
import { fromPayload, ignoredInputs } from './results.js';
import { log } from './messages.js';
import { num } from './format.js';

// Request fields that describe the orbit; a script run takes these from the script instead.
const ORBIT_FIELDS = ['hp', 'ha', 'a', 'e', 'inc', 'raan', 'aop', 'ta', 'position_km', 'velocity_kms'];

let controller = null;

export function isRunning() {
    return controller !== null;
}

export function startRun() {
    const mission = store.get('mission');
    const body = toPropagateRequest(mission);
    return execute(
        `Propagating ${mission.spacecraft.name} for ${spanText(mission.propagator)}.`,
        body,
        (signal) => propagate(body, signal),
    );
}

function spanText(prop) {
    if (prop.durationUnit === 'hours') return `${num(prop.duration, 1)} hours`;
    if (prop.durationUnit === 'days') return `${num(prop.duration, 2)} days`;
    return `${num(prop.num_orbits, 1)} orbits`;
}

export function startScriptRun(scriptText) {
    const body = toPropagateRequest(store.get('mission'));
    for (const field of ORBIT_FIELDS) delete body[field];
    return execute('Propagating the orbit in the mission script.', body, (signal) => propagateScript(scriptText, body, signal));
}

async function execute(startMessage, body, call) {
    if (controller) return;
    controller = new AbortController();
    const mine = controller;
    store.set({ run: { status: 'running', error: null, startedAt: performance.now() }, playing: false });
    log('info', startMessage);

    try {
        const result = fromPayload(await call(mine.signal));
        const ignored = ignoredInputs(body, result.summary);
        if (ignored.length) {
            throw new EngineError(`This engine does not support ${ignored.join(' or ')} and would have run a different orbit. Update AstroFlyer, or enter the orbit as elements and the run length in orbits.`);
        }
        store.set({ result, time: result.times[0], run: { status: 'done', error: null, startedAt: null }, playing: true });
        const shape = result.summary.closedOrbit
            ? `Perigee ${num(result.summary.perigee_alt_km)} km, apogee ${num(result.summary.apogee_alt_km)} km.`
            : `Escape trajectory, e = ${num(result.summary.eccentricity, 4)}, closest approach ${num(result.summary.perigee_alt_km)} km.`;
        log('info', `Finished in ${num(result.summary.solve_s, 2)} s with ${num(result.summary.points)} points. ${shape}`);
        for (const note of result.notes) log('info', note);
    } catch (err) {
        if (err.name === 'AbortError') {
            const hasResult = Boolean(store.get('result'));
            store.set({ run: { status: hasResult ? 'done' : 'idle', error: null, startedAt: null } });
            log('info', hasResult ? 'Run stopped. The previous result is still shown.' : 'Run stopped.');
        } else {
            const message = err instanceof EngineError ? err.message : `Unexpected error: ${err.message}`;
            store.set({ run: { status: 'failed', error: message, startedAt: null } });
            log('error', message);
        }
    } finally {
        if (controller === mine) controller = null;
    }
}

export function stopRun() {
    controller?.abort();
}

// Client for the local engine served by backend/app_server.py on the same origin.

export class EngineError extends Error {
    constructor(message, status = null) {
        super(message);
        this.status = status;   // HTTP status when the engine answered, otherwise null
    }
}

async function request(path, options) {
    let response;
    try {
        response = await fetch(path, options);
    } catch (err) {
        if (err.name === 'AbortError') throw err;
        throw new EngineError('The engine did not answer. It may have failed on these inputs; if it keeps happening, restart AstroFlyer.');
    }
    let data;
    try {
        data = await response.json();
    } catch {
        throw new EngineError(`The engine returned an unreadable answer (HTTP ${response.status}).`, response.status);
    }
    if (!response.ok) {
        throw new EngineError(data.message || `The engine reported an error (HTTP ${response.status}).`, response.status);
    }
    return data;
}

async function propagateAt(path, body, signal) {
    const data = await request(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal,
    });
    if (data.status !== 'ok') throw new EngineError(data.message || 'The engine could not propagate this mission.');
    return data;
}

export function propagate(body, signal) {
    return propagateAt('/api/propagate', body, signal);
}

// The engine reads the six orbit elements from the script; everything else comes from body.
export function propagateScript(scriptText, body, signal) {
    return propagateAt('/api/script/propagate', { ...body, script_text: scriptText }, signal);
}

// Runs the whole mission script (objects, Propagate, Maneuver, Target, Report) on the engine.
export async function runScript(scriptText, signal) {
    try {
        return await request('/api/script/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ script_text: scriptText }),
            signal,
        });
    } catch (err) {
        if (err instanceof EngineError && err.status === 404) {
            throw new EngineError('This engine cannot run full mission scripts yet. Use Show orbit in views to propagate the orbit in the script.', 404);
        }
        throw err;
    }
}

// Station passes, eclipses, beta angle and a report for one orbit, see access.js for the body.
export async function analyzeAccess(body, signal) {
    try {
        return await request('/api/analysis/access', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
            signal,
        });
    } catch (err) {
        if (err instanceof EngineError && err.status === 404) {
            throw new EngineError('This engine cannot run access analysis yet. Contact and shadow events from the run are in Events.', 404);
        }
        throw err;
    }
}

export function solveApogeeRaise({ perigeeRadiusKm, perigeeSpeedKms, targetApogeeKm }) {
    const query = new URLSearchParams({ r0: perigeeRadiusKm, v0: perigeeSpeedKms, target_ra: targetApogeeKm });
    return request(`/api/targeting/differential_corrector?${query}`);
}

export function simulateFiniteBurn({ deltaVms, massKg, thrustN, ispS }) {
    const query = new URLSearchParams({ deltav: deltaVms, mass: massKg, thrust: thrustN, isp: ispS });
    return request(`/api/targeting/finite_burn?${query}`);
}

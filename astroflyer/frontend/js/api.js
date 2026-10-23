// Client for the local engine served by backend/app_server.py on the same origin.

export class EngineError extends Error {}

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
        throw new EngineError(`The engine returned an unreadable answer (HTTP ${response.status}).`);
    }
    if (!response.ok) {
        throw new EngineError(data.message || `The engine reported an error (HTTP ${response.status}).`);
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

export function solveApogeeRaise({ perigeeRadiusKm, perigeeSpeedKms, targetApogeeKm }) {
    const query = new URLSearchParams({ r0: perigeeRadiusKm, v0: perigeeSpeedKms, target_ra: targetApogeeKm });
    return request(`/api/targeting/differential_corrector?${query}`);
}

export function simulateFiniteBurn({ deltaVms, massKg, thrustN, ispS }) {
    const query = new URLSearchParams({ deltav: deltaVms, mass: massKg, thrust: thrustN, isp: ispS });
    return request(`/api/targeting/finite_burn?${query}`);
}

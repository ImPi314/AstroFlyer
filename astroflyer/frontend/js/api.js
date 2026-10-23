// Client for the local engine served by backend/app_server.py on the same origin.

export class EngineError extends Error {}

export async function propagate(body, signal) {
    let response;
    try {
        response = await fetch('/api/propagate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
            signal,
        });
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
    if (!response.ok || data.status !== 'ok') {
        throw new EngineError(data.message || `The engine reported an error (HTTP ${response.status}).`);
    }
    return data;
}

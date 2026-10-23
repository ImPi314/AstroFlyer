// Single owner of UI state. Views read from here and subscribe to the keys they draw,
// so every view shows the same mission, run result and time.

const listeners = new Map();

const state = {
    mission: null,      // applied mission, see mission.js
    selection: 'spacecraft',
    run: { status: 'idle', error: null },   // idle | running | done | failed
    result: null,       // see results.js
    time: 0,            // seconds since the start of the run
    playing: false,
    speed: 600,         // simulated seconds per real second
    views: null,        // display settings per view, see views/settings.js
    layout: 'grid',     // single | split | grid
    workspace: 'mission',   // mission | analysis | data
};

export function get(key) {
    return state[key];
}

export function set(patch) {
    const changed = Object.keys(patch).filter((key) => state[key] !== patch[key]);
    Object.assign(state, patch);
    for (const key of changed) {
        for (const fn of listeners.get(key) ?? []) fn(state[key]);
    }
}

export function on(keys, fn) {
    for (const key of [].concat(keys)) {
        if (!listeners.has(key)) listeners.set(key, new Set());
        listeners.get(key).add(fn);
    }
}

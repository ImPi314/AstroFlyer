// Single owner of UI state. Views read from here and subscribe to the keys they draw,
// so every view shows the same mission, run result and time.

const listeners = new Map();

const state = {
    mission: null,      // applied mission, see mission.js
    missionFile: null,  // name of the mission file last opened or saved
    selection: 'spacecraft',
    run: { status: 'idle', error: null, startedAt: null },   // idle | running | done | failed
    result: null,       // see results.js
    time: 0,            // seconds since the start of the run
    playing: false,
    speed: 600,         // simulated seconds per real second
    timeScale: 'utc',   // time scale of the epoch readout, when the engine reports an epoch
    panes: null,        // { id: { type, settings } }, see views/registry.js
    layout: 'heo',      // heo | quad
    maximized: null,    // id of the pane filling the workspace, if any
    workspace: 'mission',   // mission | analysis | data
    home: false,        // home screen open
};

export function get(key) {
    return state[key];
}

export function set(patch) {
    const changed = Object.keys(patch).filter((key) => state[key] !== patch[key]);
    Object.assign(state, patch);
    for (const key of changed) {
        for (const fn of [...(listeners.get(key) ?? [])]) fn(state[key]);
    }
}

// Returns a function that removes the subscription.
export function on(keys, fn) {
    const list = [].concat(keys);
    for (const key of list) {
        if (!listeners.has(key)) listeners.set(key, new Set());
        listeners.get(key).add(fn);
    }
    return () => { for (const key of list) listeners.get(key).delete(fn); };
}

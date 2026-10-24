// Turns the engine's /api/script/run payload into what the mission script page shows.
// This is the only place that knows that payload's field names.

const entries = (object) => Object.entries(object ?? {});

export function fromScriptRun(payload) {
    const ephemeris = payload.ephemeris ?? {};
    return {
        error: payload.error ? { message: payload.error.message, line: payload.error.line ?? null } : null,
        log: payload.log ?? [],
        reports: entries(payload.reports).map(([name, report]) => ({ name, columns: report.columns, rows: report.rows })),
        spacecraft: entries(payload.spacecraft).map(([name, state]) => ({
            name,
            ...state,
            points: ephemeris[name]?.t_s?.length ?? null,
        })),
        targets: (payload.targets ?? []).map((target) => ({
            name: target.name,
            line: target.line,
            converged: target.converged,
            message: target.message,
            iterations: target.iterations,
            variables: entries(target.variables),
            goals: entries(target.goals).map(([param, goal]) => ({ param, target: goal.target, achieved: goal.achieved, tolerance: goal.tolerance })),
        })),
    };
}

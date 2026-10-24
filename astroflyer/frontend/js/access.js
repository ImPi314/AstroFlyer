// Builds /api/analysis/access requests from the last run and reads the engine's answer.
// This is the only place that knows that endpoint's field names.

const REPORT = ['Epoch', 'ElapsedSecs', 'Altitude', 'Latitude', 'Longitude', 'BetaAngle', 'ShadowFraction'];
const STATION_REPORT = ['Elevation', 'Azimuth', 'Range'];
const BODIES = { EARTH: 'Earth', MOON: 'Moon' };

// Repeats the last run: same epoch, the engine's own semi-major axis and eccentricity, same length,
// force model and stations. The engine propagates this again for the analysis.
export function toAccessRequest(mission, result) {
    const { spacecraft: sc, propagator: prop } = mission;
    return {
        epoch: result.epoch?.utc ?? null,
        sma_km: result.summary.sma_km,
        ecc: result.summary.eccentricity,
        inc_deg: sc.inc,
        raan_deg: sc.raan,
        aop_deg: sc.aop,
        ta_deg: sc.ta,
        duration_s: result.duration,
        // About 2,000 samples, but no coarser than a minute so short passes are not missed.
        step_s: Math.min(60, Math.max(10, result.duration / 2000)),
        model: prop.model,
        method: prop.method,
        stations: result.stations.map((st) => ({
            name: st.name, lat_deg: st.lat_deg, lon_deg: st.lon_deg, height_m: st.alt_m, min_elevation_deg: st.min_elevation_deg,
        })),
        parameters: [...REPORT, ...result.stations.flatMap((st) => STATION_REPORT.map((p) => `${p}.${st.name}`))],
    };
}

export function fromAccess(payload) {
    const beta = payload.beta_angle_deg ?? [];
    const columns = Object.keys(payload.report ?? {});
    const length = columns.length ? payload.report[columns[0]].length : 0;
    const byTime = (key) => (x, y) => (x[key] < y[key] ? -1 : x[key] > y[key] ? 1 : 0);
    return {
        error: payload.error ?? null,
        passes: Object.entries(payload.passes ?? {}).flatMap(([station, list]) => list.map((p) => ({
            station,
            aos: p.aos_utc,
            tca: p.tca_utc,
            los: p.los_utc,
            duration_s: p.duration_s,
            max_elevation_deg: p.max_elevation_deg,
            aos_azimuth_deg: p.aos_azimuth_deg,
            los_azimuth_deg: p.los_azimuth_deg,
            partial: p.partial,
        }))).sort(byTime('aos')),
        eclipses: (payload.eclipses ?? []).map((e) => ({
            body: BODIES[e.body] ?? e.body,
            kind: e.kind,
            start: e.start_utc,
            end: e.end_utc,
            duration_s: e.duration_s,
            partial: e.partial,
        })).sort(byTime('start')),
        beta: {
            min: beta.length ? Math.min(...beta) : null,
            max: beta.length ? Math.max(...beta) : null,
            series: beta,
        },
        report: {
            columns,
            rows: Array.from({ length }, (_, i) => columns.map((c) => payload.report[c][i])),
        },
    };
}

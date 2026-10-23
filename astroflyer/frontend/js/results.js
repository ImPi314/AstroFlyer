// Turns the engine's /api/propagate payload into the one shape every view reads.
// This is the only place that knows the payload's field names.

export function fromPayload(payload) {
    const times = payload.times_sec;
    const events = payload.events_suite ?? {};
    const eclipses = events.solar_eclipses ?? {};
    const stations = Object.values(events.ground_stations ?? {});

    return {
        times,
        duration: times.at(-1) - times[0],
        samples: {
            altitude_km: payload.altitude_km,
            speed_kms: payload.velocity_kms,
            sma_km: payload.semi_major_axis_km,
            eccentricity: payload.eccentricity,
            inclination_deg: payload.inclination_deg,
            raan_deg: payload.raan_deg,
            aop_deg: payload.arg_perigee_deg,
            true_anomaly_deg: payload.true_anomaly_deg,
            latitude_deg: payload.latitude_deg,
            longitude_deg: payload.longitude_deg,
            energy_error: payload.energy_error,
            lighting: eclipses.regimes ?? null,
        },
        position_m: payload.position_m,
        apsides: (events.exact_apsidal_events ?? []).map((ev) => ({
            kind: ev.event_type === 'APOAPSIS_PASSAGE' ? 'apogee' : 'perigee',
            t: ev.epoch_s,
            altitude_km: ev.altitude_km,
        })),
        // The engine lists each shadow twice (umbra and penumbra) with the same bounds; keep umbra.
        shadows: (eclipses.events ?? [])
            .filter((ev) => ev.event_type.startsWith('UMBRA'))
            .map((ev) => ({ t0: ev.entry_epoch_s, t1: ev.exit_epoch_s })),
        stations: stations.map((st) => ({
            name: st.metadata.name,
            lat_deg: st.metadata.lat_deg,
            lon_deg: st.metadata.lon_deg,
            alt_m: st.metadata.alt_m,
            min_elevation_deg: st.metadata.min_el_deg,
            network: st.metadata.network,
            contact_min: st.total_contact_min,
            passes: st.passes.map((p) => ({ t0: p.aos_epoch_s, t1: p.los_epoch_s, max_elevation_deg: p.max_elevation_deg })),
        })),
        summary: {
            perigee_alt_km: payload.active_orbit_config.perigee_alt_km,
            apogee_alt_km: payload.active_orbit_config.apogee_alt_km,
            sma_km: payload.active_orbit_config.semi_major_axis_km,
            eccentricity: payload.active_orbit_config.eccentricity,
            period_h: payload.active_orbit_config.orbital_period_hours,
            solve_s: payload.active_orbit_config.solve_time_sec,
            points: payload.total_points,
            max_energy_error: Math.max(...payload.energy_error.map(Math.abs)),
            shadow_pct: eclipses.mission_eclipse_fraction_pct ?? null,
        },
    };
}

// Index of the last sample at or before t.
export function sampleIndex(result, t) {
    const { times } = result;
    let lo = 0;
    let hi = times.length - 1;
    if (t <= times[0]) return 0;
    if (t >= times[hi]) return hi;
    while (hi - lo > 1) {
        const mid = (lo + hi) >> 1;
        if (times[mid] <= t) lo = mid; else hi = mid;
    }
    return lo;
}

// Every point the timeline can jump to, sorted by time.
export function eventTimes(result) {
    const points = [
        ...result.apsides.map((a) => a.t),
        ...result.shadows.flatMap((s) => [s.t0, s.t1]),
        ...result.stations.flatMap((st) => st.passes.flatMap((p) => [p.t0, p.t1])),
    ];
    return [...new Set(points)].sort((a, b) => a - b);
}

// Turns the engine's /api/propagate payload into the one shape every view reads.
// This is the only place that knows the payload's field names.

const DEG = Math.PI / 180;

// The engine rotates the Earth by its own angle and does not report it, so read it back
// from its outputs: inertial right ascension minus Earth-fixed longitude, unwrapped.
function earthRotation(positions, longitudesDeg) {
    const theta = new Float64Array(positions.length);
    let previous = 0;
    positions.forEach(([x, y], i) => {
        let angle = Math.atan2(y, x) - longitudesDeg[i] * DEG;
        if (i > 0) angle -= 2 * Math.PI * Math.round((angle - previous) / (2 * Math.PI));
        theta[i] = previous = angle;
    });
    return theta;
}

export function fromPayload(payload) {
    const times = payload.times_sec;
    const theta = earthRotation(payload.position_m, payload.longitude_deg);
    const inertialKm = new Float32Array(times.length * 3);
    const fixedKm = new Float32Array(times.length * 3);
    payload.position_m.forEach(([x, y, z], i) => {
        const c = Math.cos(theta[i]);
        const s = Math.sin(theta[i]);
        inertialKm.set([x / 1000, y / 1000, z / 1000], i * 3);
        fixedKm.set([(c * x + s * y) / 1000, (-s * x + c * y) / 1000, z / 1000], i * 3);
    });
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
        theta,
        // The radius the engine measures altitude from, so the drawn Earth matches its altitudes.
        earthRadiusKm: Math.hypot(...payload.position_m[0]) / 1000 - payload.altitude_km[0],
        inertialKm,
        fixedKm,
        // Sun direction in the inertial frame. The engine's shadow model uses a fixed Sun on +X
        // until it reports one, so the night side drawn here matches its shadow events.
        sunDirection: payload.sun_direction_eci ?? [1, 0, 0],
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

// Interpolated state at time t: inertial and Earth-fixed position in km and the Earth's rotation.
export function stateAt(result, t) {
    const i = sampleIndex(result, t);
    const j = Math.min(i + 1, result.times.length - 1);
    const f = j === i ? 0 : (t - result.times[i]) / (result.times[j] - result.times[i]);
    const mix = (array) => [0, 1, 2].map((k) => array[i * 3 + k] + f * (array[j * 3 + k] - array[i * 3 + k]));
    const { latitude_deg: lat, longitude_deg: lon } = result.samples;
    let dLon = lon[j] - lon[i];
    dLon -= 360 * Math.round(dLon / 360);
    const lonDeg = lon[i] + f * dLon;
    const fixed = mix(result.fixedKm);
    return {
        index: i,
        inertial: mix(result.inertialKm),
        fixed,
        theta: result.theta[i] + f * (result.theta[j] - result.theta[i]),
        latDeg: lat[i] + f * (lat[j] - lat[i]),
        lonDeg: lonDeg - 360 * Math.round(lonDeg / 360),
        radiusKm: Math.hypot(...fixed),
    };
}

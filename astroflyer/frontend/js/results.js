// Turns the engine's /api/propagate payload into the one shape every view reads.
// This is the only place that knows the payload's field names.

import { elapsed } from './format.js';

const DEG = Math.PI / 180;
const ZONES = { FREE_SPACE: 'Outside the belts', INNER_PROTON_BELT: 'Inner belt', OUTER_ELECTRON_BELT: 'Outer belt', RADIATION_SLOT_REGION: 'Slot region' };

// The engine does not report its Earth rotation angle, so read it back from its outputs:
// inertial right ascension minus Earth-fixed longitude (from its ITRF position when it
// sends one, otherwise from its longitudes), unwrapped.
function earthRotation(positions, fixedPositions, longitudesDeg) {
    const theta = new Float64Array(positions.length);
    let previous = 0;
    positions.forEach(([x, y], i) => {
        const lon = fixedPositions ? Math.atan2(fixedPositions[i][1], fixedPositions[i][0]) : longitudesDeg[i] * DEG;
        let angle = Math.atan2(y, x) - lon;
        if (i > 0) angle -= 2 * Math.PI * Math.round((angle - previous) / (2 * Math.PI));
        theta[i] = previous = angle;
    });
    return theta;
}

export function fromPayload(payload) {
    const times = payload.times_sec;
    const itrf = payload.position_itrf_m ?? null;
    const theta = earthRotation(payload.position_m, itrf, payload.longitude_deg);
    const inertialKm = new Float32Array(times.length * 3);
    const fixedKm = new Float32Array(times.length * 3);
    const velocityKms = new Float64Array(times.length * 3);
    payload.velocity_ms.forEach(([vx, vy, vz], i) => velocityKms.set([vx / 1000, vy / 1000, vz / 1000], i * 3));
    payload.position_m.forEach(([x, y, z], i) => {
        const c = Math.cos(theta[i]);
        const s = Math.sin(theta[i]);
        inertialKm.set([x / 1000, y / 1000, z / 1000], i * 3);
        fixedKm.set(itrf ? itrf[i].map((v) => v / 1000) : [(c * x + s * y) / 1000, (-s * x + c * y) / 1000, z / 1000], i * 3);
    });
    const listed = payload.events ?? null;   // newer engines list apsides and nodes together
    const events = payload.events_suite ?? {};
    const eclipses = events.solar_eclipses ?? {};
    const stations = Object.values(events.ground_stations ?? {});
    const forces = payload.force_diagnostics ?? {};
    const radiation = payload.radiation_belts ?? {};
    const covariance = payload.covariance_dispersion ?? {};
    const subsystems = payload.fsw_subsystems ?? {};
    const lifetime = events.multi_decadal_lifetime ?? {};

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
            a_central: forces.a_central_ms2,
            a_j2: forces.a_j2_ms2,
            a_j3: forces.a_j3_ms2,
            a_j4: forces.a_j4_ms2,
            a_tesseral: forces.a_tesseral_ms2,
            a_sun: forces.a_sun_ms2,
            a_moon: forces.a_moon_ms2,
            a_drag: forces.a_drag_ms2,
            a_srp: forces.a_srp_ms2,
            l_shell: radiation.l_shell_series,
            b_field_ut: radiation.b_field_series_ut,
            dose_rate: radiation.dose_rate_rad_hr,
            dose_total: radiation.cumulative_dose_rad,
            radiation_zone: radiation.regimes_series?.map((z) => ZONES[z] ?? z) ?? null,
            sigma_radial_m: covariance.sigma_radial_m,
            sigma_intrack_m: covariance.sigma_intrack_m,
            sigma_crosstrack_m: covariance.sigma_crosstrack_m,
            solar_power_w: subsystems.solar_power_w,
            battery_soc_pct: subsystems.battery_soc_pct,
            temperature_c: subsystems.temperature_c,
            wheel1_rpm: subsystems.rw1_rpm,
            wheel2_rpm: subsystems.rw2_rpm,
        },
        theta,
        // The radius the engine measures altitude from, so the drawn Earth matches its altitudes.
        earthRadiusKm: Math.hypot(...payload.position_m[0]) / 1000 - payload.altitude_km[0],
        inertialKm,
        fixedKm,
        velocityKms,
        // Sun direction in the inertial frame, per sample or for the whole run. Older engines use
        // a fixed Sun on +X, so the night side drawn here matches their shadow events.
        sun: sunDirections(payload.sun_direction_eci, times.length),
        // Start epoch in each time scale as ISO strings, when the engine reports one.
        epoch: payload.epoch ?? null,
        apsides: listed
            ? listed.filter((ev) => ev.type === 'perigee' || ev.type === 'apogee').map((ev) => ({
                kind: ev.type,
                t: ev.t_s,
                altitude_km: payload.altitude_km[nearest(times, ev.t_s)],
            }))
            : (events.exact_apsidal_events ?? []).map((ev) => ({
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
        nodes: listed
            ? listed.filter((ev) => ev.type.endsWith('_node')).map((ev) => ({
                kind: ev.type === 'ascending_node' ? 'ascending' : 'descending',
                t: ev.t_s,
                longitude_deg: payload.longitude_deg[nearest(times, ev.t_s)],
            }))
            : (events.exact_nodal_events ?? []).map((ev) => ({
                kind: ev.event_type === 'ASCENDING_NODE' ? 'ascending' : 'descending',
                t: ev.epoch_s,
                longitude_deg: ev.longitude_deg,
            })),
        radiation: {
            totalDoseRad: Number(radiation.summary?.total_ionizing_dose_rad ?? NaN),
            crossings: (radiation.crossing_events ?? []).map((ev) => ({
                belt: ev.belt?.startsWith('INNER') ? 'Inner' : 'Outer',
                t0: ev.ingress_s,
                t1: ev.egress_s,
            })),
        },
        covariance: {
            initialSigmaM: Number(covariance.summary?.initial_1sigma_pos_m ?? NaN),
            finalSigmaM: Number(covariance.summary?.final_1sigma_pos_m ?? NaN),
            finalRadialM: Number(covariance.summary?.final_radial_dispersion_m ?? NaN),
            finalIntrackM: Number(covariance.summary?.final_intrack_dispersion_m ?? NaN),
            finalCrosstrackM: Number(covariance.summary?.final_crosstrack_dispersion_m ?? NaN),
            stmDeterminant: Number(covariance.summary?.stm_determinant ?? NaN),
        },
        lifetime: {
            years: lifetime.lifetime_assessment?.orbital_lifetime_years ?? null,
            meetsIadc: lifetime.lifetime_assessment?.iadc_25_year_rule_compliant ?? null,
            series: lifetime.trajectory_decay_timeseries ?? null,
        },
        script: payload.script_workbench?.script_content ?? '',
        tle: payload.ccsds_interoperability?.tle_string ?? '',
        opm: payload.ccsds_interoperability?.opm_string ?? '',
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

function sunDirections(reported, count) {
    if (Array.isArray(reported?.[0]) && reported.length === count) return reported;
    const one = Array.isArray(reported) && reported.length === 3 ? reported : [1, 0, 0];
    return Array.from({ length: count }, () => one);
}

function nearest(times, t) {
    let best = 0;
    for (let i = 1; i < times.length; i++) if (Math.abs(times[i] - t) < Math.abs(times[best] - t)) best = i;
    return best;
}

export const TIME_SCALES = ['utc', 'tai', 'tt', 'tdb', 'ut1'];

// The clock at time t: a calendar epoch in the chosen scale when the engine reports one,
// otherwise elapsed time since the start of the run.
export function clockText(result, t, scale = 'utc') {
    // The engine writes "2000-01-01T11:59:27.816000 TAI" (or "...Z" for UTC). Read the calendar part
    // as the scale's own clock, not local time; Date keeps milliseconds only.
    const match = /^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(\.\d{1,3})?/.exec(result.epoch?.[scale] ?? '');
    const ms = match ? Date.parse(`${match[1]}${match[2] ?? ''}Z`) : NaN;
    if (Number.isNaN(ms)) return elapsed(t - result.times[0]);
    const iso = new Date(ms + (t - result.times[0]) * 1000).toISOString();
    return `${iso.slice(0, 10)} ${iso.slice(11, 19)} ${scale.toUpperCase()}`;
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
        ...result.nodes.map((n) => n.t),
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
    const sun = [0, 1, 2].map((k) => result.sun[i][k] + f * (result.sun[j][k] - result.sun[i][k]));
    return {
        sun,
        index: i,
        inertial: mix(result.inertialKm),
        fixed,
        theta: result.theta[i] + f * (result.theta[j] - result.theta[i]),
        latDeg: lat[i] + f * (lat[j] - lat[i]),
        lonDeg: lonDeg - 360 * Math.round(lonDeg / 360),
        radiusKm: Math.hypot(...fixed),
    };
}

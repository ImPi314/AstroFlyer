// Mission objects the user edits, their field definitions, validation,
// and the request body sent to the local engine's /api/propagate.

export const defaultMission = {
    spacecraft: {
        name: 'Molniya-1',
        epoch: '2026-01-01 00:00:00',
        orbitInput: 'apsides',
        hp: 1000,
        ha: 39350,
        a: 26554,
        e: 0.722,
        inc: 63.4,
        raan: 45,
        aop: 270,
        ta: 0,
        // Roughly the default Molniya at perigee (node line on X), a starting point when switching
        // to position and velocity.
        x: 7378, y: 0, z: 0, vx: 0, vy: 4.32, vz: 8.63,
        mass: 1500,
        cd: 2.2,
        drag_area: 15,
        cr: 1.2,
        srp_area: 15,
    },
    propagator: {
        method: 'DOP853',
        tolerance: 1e-10,
        steering: 'none',
        model: 'coupled',
        gravity_degree: 8,
        fidelity: 'full',
        enable_drag: true,
        enable_third_body: true,
        enable_srp: true,
        durationUnit: 'orbits',
        num_orbits: 3,
        duration: 1,
        points_per_orbit: 400,
    },
    // Impulsive burns, applied by Run in this order; see schemas.burn.
    burns: [],
    // Earlier legs this mission was continued from, oldest first; see continueFromEnd.
    history: [],
};

// A burn as the inspector edits it: velocity change in the local VNC frame, in m/s.
const defaultBurn = { name: 'Burn', timing: 'perigee', elapsed_h: 1, dv_v: 10, dv_n: 0, dv_c: 0, isp: 300 };

export function newBurn(index) {
    return { ...defaultBurn, name: `Burn ${index + 1}` };
}

const apsides = (values) => values.orbitInput === 'apsides';
const keplerian = (values) => values.orbitInput === 'keplerian';
const cartesian = (values) => values.orbitInput === 'cartesian';
const elements = (values) => !cartesian(values);
const fullModel = (values) => values.model === 'coupled';
const steerable = (values) => values.method === 'RKF78' || values.method === 'BS';
const spanIn = (unit) => (values) => values.durationUnit === unit;
const timed = (values) => values.timing === 'elapsed';
const dvField = (key, label, hint) => ({ key, label, unit: 'm/s', type: 'number', min: -10000, max: 10000, step: 'any', hint });

const R_EARTH_KM = 6378.137;
const SECONDS = { hours: 3600, days: 86400 };
const vectorField = (key, label, unit, limit) => ({ key, label, unit, type: 'number', min: -limit, max: limit, step: 'any', when: cartesian });

// Ranges follow what the engine accepts; it clamps anything outside them.
export const schemas = {
    spacecraft: {
        title: 'Spacecraft',
        groups: [
            {
                title: 'Identity',
                fields: [
                    { key: 'name', label: 'Name', type: 'text', hint: 'Shown in the mission tree and window title.' },
                ],
            },
            {
                title: 'Orbit state',
                fields: [
                    { key: 'epoch', label: 'Start epoch', unit: 'UTC', type: 'epoch', hint: 'Date and time of the state below, as YYYY-MM-DD HH:MM:SS. The bundled Sun and Moon ephemeris covers 1990 to 2060.' },
                    { key: 'orbitInput', label: 'Enter orbit as', type: 'select', options: [['apsides', 'Perigee and apogee altitude'], ['keplerian', 'Semi-major axis and eccentricity'], ['cartesian', 'Position and velocity (GCRF)']] },
                    { ...vectorField('x', 'Position X', 'km', 500000), hint: 'Earth-centred inertial (GCRF) position at the start epoch.' },
                    vectorField('y', 'Position Y', 'km', 500000),
                    vectorField('z', 'Position Z', 'km', 500000),
                    { ...vectorField('vx', 'Velocity X', 'km/s', 20), hint: 'GCRF velocity at the start epoch. The orbit must stay bound to the Earth.' },
                    vectorField('vy', 'Velocity Y', 'km/s', 20),
                    vectorField('vz', 'Velocity Z', 'km/s', 20),
                    { key: 'hp', label: 'Perigee altitude', unit: 'km', type: 'number', min: 100, max: 400000, step: 1, when: apsides, hint: 'Height of the lowest point above the Earth’s surface.' },
                    { key: 'ha', label: 'Apogee altitude', unit: 'km', type: 'number', min: 100, max: 400000, step: 1, when: apsides, hint: 'Height of the highest point. Must be above perigee.' },
                    { key: 'a', label: 'Semi-major axis', unit: 'km', type: 'number', min: 6500, max: 400000, step: 1, when: keplerian },
                    { key: 'e', label: 'Eccentricity', type: 'number', min: 0, max: 0.99, step: 0.001, when: keplerian, hint: 'From 0 (circular) to 0.99.' },
                    { key: 'inc', label: 'Inclination', unit: 'deg', type: 'number', min: 0, max: 180, step: 0.1, hint: '63.4 deg keeps a Molniya apogee from drifting.', when: elements },
                    { key: 'raan', label: 'Right ascension of ascending node', unit: 'deg', type: 'number', min: 0, max: 360, step: 0.1 , when: elements },
                    { key: 'aop', label: 'Argument of perigee', unit: 'deg', type: 'number', min: 0, max: 360, step: 0.1, hint: '270 deg puts apogee over the northern hemisphere.', when: elements },
                    { key: 'ta', label: 'True anomaly', unit: 'deg', type: 'number', min: 0, max: 360, step: 0.1, hint: 'Position along the orbit at the start. 0 is perigee.', when: elements },
                ],
            },
            {
                title: 'Physical properties',
                fields: [
                    { key: 'mass', label: 'Mass', unit: 'kg', type: 'number', min: 10, max: 100000, step: 1 },
                    { key: 'cd', label: 'Drag coefficient', type: 'number', min: 0, max: 5, step: 0.1 },
                    { key: 'drag_area', label: 'Drag area', unit: 'm²', type: 'number', min: 0, max: 1000, step: 0.1 },
                    { key: 'cr', label: 'Reflectivity coefficient', type: 'number', min: 0, max: 2, step: 0.05 },
                    { key: 'srp_area', label: 'Solar pressure area', unit: 'm²', type: 'number', min: 0, max: 1000, step: 0.1 },
                ],
            },
        ],
    },
    propagator: {
        title: 'Propagator',
        groups: [
            {
                title: 'Integrator',
                fields: [
                    { key: 'method', label: 'Method', type: 'select', options: [['DOP853', 'Dormand-Prince 8(5,3)'], ['Radau', 'Radau IIA, implicit'], ['RKF78', 'Runge-Kutta-Fehlberg 7(8)'], ['BS', 'Bulirsch-Stoer'], ['RK4', 'Runge-Kutta 4, fixed 10 s step']], hint: 'Dormand-Prince is the integrator checked against Orekit and the quickest for these orbits. Radau is implicit, for stiff problems; it is five to six times slower here.' },
                    { key: 'tolerance', label: 'Tolerance', type: 'number', min: 1e-13, max: 1e-6, step: 'any', hint: 'Relative and absolute error per step, for example 1e-10.' },
                    { key: 'steering', label: 'Step control', type: 'select', options: [['none', 'Error control only'], ['covariance', 'Covariance-steered']], when: steerable, hint: 'Covariance-steered also limits each step so that the propagated 1-sigma position uncertainty grows by at most 2 %. About three to five times slower; it bounds the uncertainty growth, it is not a general accuracy gain.' },
                ],
            },
            {
                title: 'Force model',
                fields: [
                    { key: 'model', label: 'Gravity and forces', type: 'select', options: [['two_body', 'Two-body'], ['j2', 'Two-body with J2'], ['j2_j3_j4', 'Zonals J2 to J4'], ['coupled', 'Full model']] },
                    { key: 'gravity_degree', label: 'Gravity field', unit: 'degree and order', type: 'number', min: 2, max: 70, step: 1, integer: true, when: fullModel, hint: 'EGM2008 up to 70 x 70. Every cross-check used 8 x 8.' },
                    { key: 'fidelity', label: 'Gravity fidelity', type: 'select', options: [['full', 'Same degree on the whole orbit'], ['ecr_mf', 'ECR-MF: degree by altitude, certified']], when: fullModel, hint: 'ECR-MF lowers the degree above 2,000 and 20,000 km altitude only as far as the omitted gravity stays below 1e-10 m/s^2. It matters for fields above 8 x 8.' },
                    { key: 'enable_drag', label: 'Atmospheric drag', type: 'checkbox', when: fullModel },
                    { key: 'enable_third_body', label: 'Sun and Moon gravity', type: 'checkbox', when: fullModel },
                    { key: 'enable_srp', label: 'Solar radiation pressure', type: 'checkbox', when: fullModel },
                ],
            },
            {
                title: 'Span',
                fields: [
                    { key: 'durationUnit', label: 'Run length in', type: 'select', options: [['orbits', 'Orbits'], ['hours', 'Hours'], ['days', 'Days']] },
                    { key: 'num_orbits', label: 'Duration', unit: 'orbits', type: 'number', min: 0.5, max: 20, step: 0.5, when: spanIn('orbits') },
                    { key: 'duration', label: 'Duration', unit: 'h', type: 'number', min: 0.1, max: 720, step: 'any', when: spanIn('hours'), hint: 'Up to 30 days.' },
                    { key: 'duration', label: 'Duration', unit: 'days', type: 'number', min: 0.01, max: 30, step: 'any', when: spanIn('days'), hint: 'Up to 30 days.' },
                    { key: 'points_per_orbit', label: 'Output points', unit: 'per orbit', type: 'number', min: 50, max: 1000, step: 10, hint: 'The engine keeps the total between 200 and 3,600 points.' },
                ],
            },
        ],
    },
    burn: {
        title: 'Impulsive burn',
        groups: [
            {
                title: 'Burn',
                fields: [
                    { key: 'name', label: 'Name', type: 'text' },
                    { key: 'timing', label: 'When', type: 'select', options: [['perigee', 'At the next perigee'], ['apogee', 'At the next apogee'], ['elapsed', 'At a time after the start']], hint: 'Burns happen in the order listed, each after the one before. The next perigee or apogee is the first one after the previous burn, or after the start.' },
                    { key: 'elapsed_h', label: 'Time after the start', unit: 'h', type: 'number', min: 0, max: 720, step: 'any', when: timed, hint: 'Must fall inside the run.' },
                ],
            },
            {
                title: 'Velocity change (VNC frame)',
                fields: [
                    dvField('dv_v', 'Along the velocity (V)', 'Positive speeds the spacecraft up: at perigee it raises the apogee.'),
                    dvField('dv_n', 'Along the orbit normal (N)', 'Turns the orbit plane.'),
                    dvField('dv_c', 'Co-normal (C = V x N)', 'In the orbit plane, at right angles to the velocity.'),
                    { key: 'isp', label: 'Specific impulse', unit: 's', type: 'number', min: 1, max: 10000, step: 'any', hint: 'Sets the propellant used, by the rocket equation. The lighter spacecraft then feels more drag and solar pressure per kilogram.' },
                ],
            },
        ],
    },
};

export function visibleFields(schema, values) {
    return schema.groups.map((group) => ({
        ...group,
        fields: group.fields.filter((field) => !field.when || field.when(values)),
    }));
}

// Years of the bundled DE440 Sun and Moon ephemeris; the engine has no Sun direction outside them.
const EPOCH_MIN = Date.UTC(1990, 0, 1);
const EPOCH_MAX = Date.UTC(2060, 0, 1);

// "YYYY-MM-DD HH:MM", with optional seconds and fraction, as a UTC calendar time.
// Returns { iso, ms } for a real date and time, otherwise null.
function parseEpoch(text) {
    const m = /^(\d{4})-(\d\d)-(\d\d) (\d\d):(\d\d)(?::(\d\d)(\.\d{1,6})?)?$/.exec(String(text ?? '').trim());
    if (!m) return null;
    const [, y, mo, d, h, mi, s = '00', frac = ''] = m;
    const ms = Date.UTC(+y, +mo - 1, +d, +h, +mi, +s);
    const back = new Date(ms);
    // Date rolls 30 February into March and 25:00 into the next day; refuse those.
    if (back.getUTCMonth() !== +mo - 1 || back.getUTCDate() !== +d || back.getUTCHours() !== +h || +mi > 59 || +s > 59) return null;
    return { iso: `${y}-${mo}-${d}T${h}:${mi}:${s}${frac}Z`, ms };
}

// Returns { key: message } for every visible field that is invalid.
export function validate(schema, values) {
    const errors = {};
    for (const group of visibleFields(schema, values)) {
        for (const field of group.fields) {
            const value = values[field.key];
            if (field.type === 'text' && !String(value ?? '').trim()) {
                errors[field.key] = 'Enter a name.';
            } else if (field.type === 'select' && !field.options.some(([option]) => option === value)) {
                errors[field.key] = 'Pick one of the options.';
            } else if (field.type === 'checkbox' && typeof value !== 'boolean') {
                errors[field.key] = 'Turn this on or off.';
            } else if (field.type === 'epoch') {
                const epoch = parseEpoch(value);
                if (!epoch) errors[field.key] = 'Enter a real date and time as YYYY-MM-DD HH:MM:SS.';
                else if (epoch.ms < EPOCH_MIN || epoch.ms >= EPOCH_MAX) errors[field.key] = 'Use a date from 1990 to 2059.';
            } else if (field.type === 'number') {
                if (typeof value !== 'number' || !Number.isFinite(value)) {
                    errors[field.key] = 'Enter a number.';
                } else if (value < field.min || value > field.max) {
                    errors[field.key] = `Use a value from ${field.min} to ${field.max}.`;
                } else if (field.integer && !Number.isInteger(value)) {
                    errors[field.key] = 'Enter a whole number.';
                }
            }
        }
    }
    if (schema === schemas.spacecraft && apsides(values) && !errors.hp && !errors.ha && values.ha <= values.hp) {
        errors.ha = 'Apogee must be higher than perigee.';
    }
    if (schema === schemas.spacecraft && cartesian(values) && !errors.x && !errors.y && !errors.z
        && Math.hypot(values.x, values.y, values.z) <= R_EARTH_KM) {
        errors.x = 'The position is inside the Earth. Its distance from the centre must exceed 6,378 km.';
    }
    return errors;
}

// A saved mission with every field AstroFlyer knows: fields saved before they existed take the
// default, and fields it no longer knows are dropped.
export function withDefaults(saved) {
    const fill = (defaults, values) => Object.fromEntries(Object.entries(defaults).map(([key, fallback]) => [key, values?.[key] ?? fallback]));
    const list = (value) => (Array.isArray(value) ? value : []);
    return {
        spacecraft: fill(defaultMission.spacecraft, saved?.spacecraft),
        propagator: fill(defaultMission.propagator, saved?.propagator),
        burns: list(saved?.burns).map((burn, i) => fill(newBurn(i), burn)),
        history: list(saved?.history).map((leg) => ({ ...leg })),
    };
}

const FILE_FORMAT = 'astroflyer-mission';

// The text of a mission file as JSON, the way Save writes it.
export function missionFileText(mission) {
    return `${JSON.stringify({ format: FILE_FORMAT, version: 1, mission }, null, 2)}\n`;
}

// The mission in a mission file's text. Throws an Error saying why when it is not one, or when
// a value is missing or out of range.
export function readMissionFile(text) {
    let data;
    try { data = JSON.parse(text); } catch { data = null; }
    if (data?.format !== FILE_FORMAT) throw new Error('it is not an AstroFlyer mission file');
    const mission = withDefaults(data.mission);
    const problems = [
        ...['spacecraft', 'propagator'].flatMap((kind) => Object.keys(validate(schemas[kind], mission[kind]))),
        ...mission.burns.flatMap((burn, i) => Object.keys(validate(schemas.burn, burn)).map((key) => `burn ${i + 1} ${key}`)),
    ];
    if (problems.length) throw new Error(`these values are missing or out of range: ${problems.join(', ')}`);
    return mission;
}

// "2026-01-01T11:59:35.108282Z" as the epoch field writes it.
const epochField = (utc) => utc.replace('T', ' ').replace(/Z$/, '');

// The mission that carries on from the end of a run (result.finalState, see results.js): the
// spacecraft starts at the run's final GCRF state, epoch and mass; the propagator settings stay,
// for the user to change; the burns, which belonged to the finished leg, are cleared; and the
// finished leg is added to the history.
export function continueFromEnd(mission, result) {
    const end = result.finalState;
    const [x, y, z] = end.position_km;
    const [vx, vy, vz] = end.velocity_kms;
    const request = result.request ?? {};
    const leg = {
        start_epoch: mission.spacecraft.epoch,
        end_epoch: epochField(end.utc),
        duration_s: end.t_s,
        method: request.method ?? mission.propagator.method,
        model: request.model ?? mission.propagator.model,
        burns: (result.burns ?? []).filter((burn) => burn.applied).length,
    };
    return {
        spacecraft: { ...mission.spacecraft, orbitInput: 'cartesian', epoch: leg.end_epoch, x, y, z, vx, vy, vz, mass: end.mass_kg },
        propagator: { ...mission.propagator },
        burns: [],
        history: [...(mission.history ?? []), leg],
    };
}

// The orbit part of the request: GCRF vectors, or elements with their angles.
function orbitRequest(sc) {
    if (cartesian(sc)) return { position_km: [sc.x, sc.y, sc.z], velocity_kms: [sc.vx, sc.vy, sc.vz] };
    const shape = apsides(sc) ? { hp: sc.hp, ha: sc.ha } : { a: sc.a, e: sc.e };
    return { ...shape, inc: sc.inc, raan: sc.raan, aop: sc.aop, ta: sc.ta };
}

export function toPropagateRequest(mission) {
    const { spacecraft: sc, propagator: prop } = mission;
    const span = prop.durationUnit in SECONDS ? { duration_s: prop.duration * SECONDS[prop.durationUnit] } : { num_orbits: prop.num_orbits };
    return {
        epoch: parseEpoch(sc.epoch)?.iso,
        ...orbitRequest(sc),
        mass: sc.mass,
        cd: sc.cd,
        drag_area: sc.drag_area,
        cr: sc.cr,
        srp_area: sc.srp_area,
        preset: sc.name,
        method: prop.method,
        tolerance: prop.tolerance,
        model: prop.model,
        ...(steerable(prop) && prop.steering === 'covariance' ? { steering: 'covariance' } : {}),
        ...(fullModel(prop) ? { gravity_degree: prop.gravity_degree, fidelity: prop.fidelity } : { fidelity: 'full' }),
        enable_drag: prop.enable_drag,
        enable_third_body: prop.enable_third_body,
        enable_srp: prop.enable_srp,
        ...span,
        points_per_orbit: prop.points_per_orbit,
        burns: (mission.burns ?? []).map((burn) => ({
            name: burn.name,
            timing: burn.timing,
            ...(timed(burn) ? { t_s: burn.elapsed_h * 3600 } : {}),
            dv_ms: [burn.dv_v, burn.dv_n, burn.dv_c],
            frame: 'VNC',
            isp_s: burn.isp,
        })),
    };
}

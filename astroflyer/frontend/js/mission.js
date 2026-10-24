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
        method: 'Radau',
        tolerance: 1e-10,
        model: 'coupled',
        enable_drag: true,
        enable_third_body: true,
        enable_srp: true,
        durationUnit: 'orbits',
        num_orbits: 3,
        duration: 1,
        points_per_orbit: 400,
    },
};

const apsides = (values) => values.orbitInput === 'apsides';
const keplerian = (values) => values.orbitInput === 'keplerian';
const cartesian = (values) => values.orbitInput === 'cartesian';
const elements = (values) => !cartesian(values);
const fullModel = (values) => values.model === 'coupled';
const spanIn = (unit) => (values) => values.durationUnit === unit;

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
                    { key: 'method', label: 'Method', type: 'select', options: [['Radau', 'Radau IIA, implicit'], ['DOP853', 'Dormand-Prince 8(5,3)'], ['RK45', 'Runge-Kutta 4(5)']], hint: 'Radau handles the fast perigee pass well. Dormand-Prince is quicker for smooth orbits.' },
                    { key: 'tolerance', label: 'Tolerance', type: 'number', min: 1e-13, max: 1e-6, step: 'any', hint: 'Relative and absolute error per step, for example 1e-10.' },
                ],
            },
            {
                title: 'Force model',
                fields: [
                    { key: 'model', label: 'Gravity and forces', type: 'select', options: [['two_body', 'Two-body'], ['j2', 'Two-body with J2'], ['j2_j3_j4', 'Zonals J2 to J4'], ['coupled', 'Full model']] },
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
        enable_drag: prop.enable_drag,
        enable_third_body: prop.enable_third_body,
        enable_srp: prop.enable_srp,
        ...span,
        points_per_orbit: prop.points_per_orbit,
    };
}

// Starting orbits for common highly elliptical missions, shown on the home screen.
// Only the orbit and run length differ from the default mission. Mission orbits are the
// published values at or shortly after launch, rounded; "typical" ones are representative shapes.

import { defaultMission } from './mission.js';

export const SAMPLES = [
    {
        name: 'Molniya',
        lead: 'Twelve-hour orbit at the critical 63.4 deg inclination, with apogee held over the northern hemisphere.',
        source: 'Typical Molniya communications orbit.',
        spacecraft: { orbitInput: 'apsides', hp: 1000, ha: 39350, inc: 63.4, raan: 45, aop: 270, ta: 0 },
        orbits: 3,
    },
    {
        name: 'Tundra',
        lead: 'Geosynchronous period with e = 0.25, so the spacecraft dwells over one region each day.',
        source: 'Typical Tundra orbit.',
        spacecraft: { orbitInput: 'keplerian', a: 42164, e: 0.25, inc: 63.4, raan: 0, aop: 270, ta: 0 },
        orbits: 2,
    },
    {
        name: 'Sirius (Tundra)',
        lead: 'The Tundra orbit flown by the first Sirius satellite radio spacecraft, apogee over North America.',
        source: 'Sirius FM-1 to FM-3: e about 0.268 at 63.4 deg, as published for the Sirius constellation.',
        spacecraft: { orbitInput: 'keplerian', a: 42164, e: 0.268, inc: 63.4, raan: 0, aop: 270, ta: 0 },
        orbits: 2,
    },
    {
        name: 'QZS-1',
        lead: 'Quasi-zenith orbit: geosynchronous, e = 0.075 and about 41 deg, tracing a figure eight over Japan.',
        source: 'QZS-1 (Michibiki), approximate published elements.',
        spacecraft: { orbitInput: 'keplerian', a: 42164, e: 0.075, inc: 41, raan: 0, aop: 270, ta: 0 },
        orbits: 2,
    },
    {
        name: 'GTO (Cape Canaveral)',
        lead: 'Geostationary transfer orbit from a 28.5 deg launch site, apogee at GEO altitude.',
        source: 'Typical GTO from Cape Canaveral.',
        spacecraft: { orbitInput: 'apsides', hp: 250, ha: 35786, inc: 28.5, raan: 0, aop: 180, ta: 0 },
        orbits: 3,
    },
    {
        name: 'GTO (Kourou)',
        lead: 'Near-equatorial transfer orbit from French Guiana, so less plane change is left for the spacecraft.',
        source: 'Ariane 5 standard GTO: 250 by 35,943 km at 6 deg, argument of perigee 178 deg.',
        spacecraft: { orbitInput: 'apsides', hp: 250, ha: 35943, inc: 6, raan: 0, aop: 178, ta: 0 },
        orbits: 3,
    },
    {
        name: 'Supersynchronous GTO',
        lead: 'Transfer orbit with apogee well above GEO, where the plane change costs less.',
        source: 'Typical supersynchronous transfer orbit.',
        spacecraft: { orbitInput: 'apsides', hp: 300, ha: 65000, inc: 27, raan: 0, aop: 180, ta: 0 },
        orbits: 2,
    },
    {
        name: 'MMS phase 1',
        lead: 'Magnetospheric science orbit from 1.2 to 12 Earth radii, through the dayside magnetopause.',
        source: 'NASA MMS phase 1 orbit: 1.2 by 12 Earth radii (geocentric) at 28 deg.',
        spacecraft: { orbitInput: 'apsides', hp: 1276, ha: 70164, inc: 28, raan: 0, aop: 0, ta: 0 },
        orbits: 2,
    },
    {
        name: 'XMM-Newton',
        lead: 'Two-day X-ray observatory orbit that spends most of its time above the radiation belts.',
        source: 'ESA XMM-Newton initial orbit: 7,000 by 114,000 km at 40 deg.',
        spacecraft: { orbitInput: 'apsides', hp: 7000, ha: 114000, inc: 40, raan: 0, aop: 0, ta: 0 },
        orbits: 2,
    },
    {
        name: 'INTEGRAL',
        lead: 'Three-day gamma-ray observatory orbit, also kept clear of the belts for long observations.',
        source: 'ESA INTEGRAL initial orbit: about 9,000 by 153,000 km at about 52 deg.',
        spacecraft: { orbitInput: 'apsides', hp: 9000, ha: 153000, inc: 52, raan: 0, aop: 0, ta: 0 },
        orbits: 1,
    },
    {
        name: 'Chandra',
        lead: 'X-ray observatory orbit of about 64 hours, reaching more than a third of the way to the Moon.',
        source: 'NASA Chandra mission facts: about 16,000 by 139,000 km; 28.5 deg launch inclination.',
        spacecraft: { orbitInput: 'apsides', hp: 16000, ha: 139000, inc: 28.5, raan: 0, aop: 0, ta: 0 },
        orbits: 1,
    },
    {
        name: 'Lunar transfer',
        lead: 'Translunar injection shape from a low parking orbit out to the Moon\'s distance.',
        source: 'Typical lunar transfer orbit; the Moon is only a perturbing body here.',
        spacecraft: { orbitInput: 'apsides', hp: 200, ha: 380000, inc: 28.5, raan: 0, aop: 0, ta: 0 },
        orbits: 0.5,
    },
];

export function sampleMission(sample) {
    const mission = structuredClone(defaultMission);
    Object.assign(mission.spacecraft, sample.spacecraft, { name: sample.name });
    mission.propagator.num_orbits = sample.orbits;
    return mission;
}

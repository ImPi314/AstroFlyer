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
        source: 'Sirius FM-1 to FM-3 constellation orbit: 23,975 by 46,983 km at 63.4 deg (Gunter\'s Space Page).',
        spacecraft: { orbitInput: 'apsides', hp: 23975, ha: 46983, inc: 63.4, raan: 0, aop: 270, ta: 0 },
        orbits: 2,
    },
    {
        name: 'QZS-1',
        lead: 'Quasi-zenith orbit: geosynchronous, e = 0.075 and about 41 deg, tracing a figure eight over Japan.',
        source: 'Quasi-zenith orbit design values for QZS-1 (Michibiki): a 42,164 km, e 0.075, 41 deg (JAXA IS-QZSS). QZS-1 has since been retired to a higher orbit.',
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
        source: 'Ariane 5 flight V192 target orbit: 250 by 35,786 km at 6 deg (ESA). Argument of perigee 178 deg is typical for Kourou, not from that source.',
        spacecraft: { orbitInput: 'apsides', hp: 250, ha: 35786, inc: 6, raan: 0, aop: 178, ta: 0 },
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
        source: 'ESA XMM-Newton orbit after launch: 7,000 by 114,000 km at 40 deg, apogee in the south (ESA fact sheet).',
        spacecraft: { orbitInput: 'apsides', hp: 7000, ha: 114000, inc: 40, raan: 0, aop: 90, ta: 0 },
        orbits: 2,
    },
    {
        name: 'INTEGRAL',
        lead: 'Three-day gamma-ray observatory orbit, also kept clear of the belts for long observations.',
        source: 'ESA INTEGRAL initial orbit: 9,000 by 153,000 km at 51.6 deg (ESA orbit page).',
        spacecraft: { orbitInput: 'apsides', hp: 9000, ha: 153000, inc: 51.6, raan: 0, aop: 0, ta: 0 },
        orbits: 1,
    },
    {
        name: 'Chandra',
        lead: 'X-ray observatory orbit of about 64 hours, reaching more than a third of the way to the Moon.',
        source: 'Chandra initial operational orbit: about 10,000 by 140,000 km at 28.5 deg (Weisskopf et al. 2000).',
        spacecraft: { orbitInput: 'apsides', hp: 10000, ha: 140000, inc: 28.5, raan: 0, aop: 0, ta: 0 },
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

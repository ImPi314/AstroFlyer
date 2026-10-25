// 3D orbit view. Scene units are kilometres; +Z is the Earth's north pole.
// THREE comes from vendor/three.min.js, loaded as a classic script before the modules.
// One instance per pane; ctx gives this pane's settings and tracks subscriptions.

import * as store from '../store.js';
import { stateAt, sampleIndex, clockText } from '../results.js';
import { num } from '../format.js';
import { altitudeColor, rgb, token } from './colors.js';

const THREE = window.THREE;
const DEG = Math.PI / 180;
const DISPLAY_EARTH_RADIUS_KM = 6378.137;   // only until a run reports the engine's radius

export const orbit3dDefaults = () => ({
    frame: 'inertial',
    center: 'earth',
    tail_h: 0,
    ra: 30,
    dec: 25,
    distance: 120000,
    fov: 35,
    hud: true,
    viewpoints: [
        { name: 'Overview', ra: 30, dec: 25 },
        { name: 'Above the north pole', ra: 0, dec: 89 },
        { name: 'From the equator', ra: 0, dec: 0 },
    ],
});

export function createOrbit3d(ctx) {
    const { body } = ctx;
    const canvas = document.createElement('canvas');
    canvas.className = 'view-canvas';
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', '3D view of the orbit around the Earth. Drag to turn, scroll to zoom.');
    const hud = document.createElement('div');
    hud.className = 'hud';
    hud.setAttribute('aria-hidden', 'true');
    body.append(canvas, hud);

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio || 1);
    renderer.setClearColor(new THREE.Color(token('--sky')));

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(35, 1, 100, 5e6);
    camera.up.set(0, 0, 1);

    scene.add(new THREE.AmbientLight(0xffffff, 0.2));
    const sunLight = new THREE.DirectionalLight(0xffffff, 1.0);
    scene.add(sunLight);

    const earth = new THREE.Group();
    const globe = new THREE.Mesh(new THREE.SphereGeometry(1, 96, 64), new THREE.MeshLambertMaterial({ color: 0xffffff }));
    globe.rotation.x = Math.PI / 2;    // sphere poles from +Y to +Z; longitude 0 lands on +X
    earth.add(globe);
    earth.scale.setScalar(DISPLAY_EARTH_RADIUS_KM);
    scene.add(earth);
    new THREE.TextureLoader().load('textures/earth.png', (texture) => {
        globe.material.map = texture;
        globe.material.needsUpdate = true;
        requestRender();
    });

    const dot = dotTexture();
    const fullPath = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.3 }));
    const trailPath = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ vertexColors: true }));
    const apsides = new THREE.Points(new THREE.BufferGeometry(), new THREE.PointsMaterial({ size: 7, sizeAttenuation: false, vertexColors: true, map: dot, transparent: true, alphaTest: 0.5 }));
    const craft = new THREE.Points(new THREE.BufferGeometry(), new THREE.PointsMaterial({ size: 11, sizeAttenuation: false, color: new THREE.Color(token('--amber')), map: dot, transparent: true, alphaTest: 0.5 }));
    craft.geometry.setAttribute('position', new THREE.Float32BufferAttribute([0, 0, 0], 3));
    for (const object of [fullPath, trailPath, apsides, craft]) {
        object.visible = false;
        object.frustumCulled = false;
        scene.add(object);
    }

    let pending = false;
    let builtFrame = null;   // frame the path geometry was built in

    function buildPaths() {
        const result = store.get('result');
        if (!result) return;
        builtFrame = ctx.settings().frame;
        const positions = builtFrame === 'fixed' ? result.fixedKm : result.inertialKm;
        const alt = result.samples.altitude_km;
        const min = Math.min(...alt);
        const max = Math.max(...alt);
        const colors = new Float32Array(alt.length * 3);
        alt.forEach((a, i) => colors.set(altitudeColor(a, min, max), i * 3));
        const position = new THREE.BufferAttribute(positions, 3);
        const color = new THREE.BufferAttribute(colors, 3);
        for (const line of [fullPath, trailPath]) {
            line.geometry.setAttribute('position', position);
            line.geometry.setAttribute('color', color);
            line.visible = true;
        }
        const marks = result.apsides.map((a) => sampleIndex(result, a.t));
        const perigee = rgb('--text');
        const apogee = rgb('--muted');
        apsides.geometry.setAttribute('position', new THREE.Float32BufferAttribute(marks.flatMap((i) => [...positions.slice(i * 3, i * 3 + 3)]), 3));
        apsides.geometry.setAttribute('color', new THREE.Float32BufferAttribute(result.apsides.flatMap((a) => (a.kind === 'perigee' ? perigee : apogee)), 3));
        apsides.visible = true;
        craft.visible = true;
        earth.scale.setScalar(result.earthRadiusKm);
        requestRender();
    }

    // After a new run, back the camera off until the whole orbit fits.
    function fitCamera() {
        const result = store.get('result');
        if (!result) return;
        let reach = 0;
        for (let i = 0; i < result.inertialKm.length; i += 3) {
            reach = Math.max(reach, Math.hypot(result.inertialKm[i], result.inertialKm[i + 1], result.inertialKm[i + 2]));
        }
        const view = ctx.settings();
        const half = (Math.min(view.fov, view.fov * camera.aspect) / 2) * DEG;
        ctx.update({ distance: Math.round(Math.min((reach * 1.15) / Math.sin(half), 2000000)) });
    }

    function requestRender() {
        if (pending) return;
        pending = true;
        requestAnimationFrame(render);
    }

    function render() {
        pending = false;
        const result = store.get('result');
        const view = ctx.settings();
        const fixed = view.frame === 'fixed';
        let target = [0, 0, 0];

        if (result) {
            const t = store.get('time');
            const now = stateAt(result, t);
            if (view.center === 'spacecraft') target = fixed ? now.fixed : now.inertial;
            craft.geometry.attributes.position.array.set(fixed ? now.fixed : now.inertial);
            craft.geometry.attributes.position.needsUpdate = true;
            earth.rotation.z = fixed ? 0 : now.theta;

            const end = now.index + 1;
            const start = view.tail_h > 0 ? sampleIndex(result, t - view.tail_h * 3600) : 0;
            trailPath.geometry.setDrawRange(start, Math.max(end - start, 0));

            const sun = new THREE.Vector3(...now.sun);
            if (fixed) sun.applyAxisAngle(new THREE.Vector3(0, 0, 1), -now.theta);
            sunLight.position.copy(sun.multiplyScalar(1e6));
        } else {
            sunLight.position.set(1e6, 0, 0);
        }

        const ra = view.ra * DEG;
        const dec = view.dec * DEG;
        camera.fov = view.fov;
        camera.position.set(
            target[0] + view.distance * Math.cos(dec) * Math.cos(ra),
            target[1] + view.distance * Math.cos(dec) * Math.sin(ra),
            target[2] + view.distance * Math.sin(dec),
        );
        camera.lookAt(...target);
        camera.updateProjectionMatrix();
        renderer.render(scene, camera);
        renderHud(result, view);
    }

    function renderHud(result, view) {
        hud.hidden = !view.hud;
        if (!view.hud) return;
        const name = store.get('mission').spacecraft.name;
        hud.textContent = [
            result ? clockText(result, store.get('time'), store.get('timeScale')) : 'No run yet',
            `${view.frame === 'fixed' ? 'Earth-fixed (ITRF)' : 'Inertial (GCRF)'} frame, looking at ${view.center === 'spacecraft' ? name : 'the Earth'}`,
            `RA ${num(view.ra, 1)} deg, Dec ${num(view.dec, 1)} deg, range ${num(view.distance)} km`,
            `Field of view ${num(view.fov)} deg`,
        ].join('\n');
    }

    function resize() {
        const { clientWidth: w, clientHeight: h } = body;
        if (!w || !h) return;
        renderer.setSize(w, h, false);
        camera.aspect = w / h;
        requestRender();
    }

    canvas.addEventListener('pointerdown', (event) => {
        canvas.setPointerCapture(event.pointerId);
        let last = [event.clientX, event.clientY];
        const move = (e) => {
            const view = ctx.settings();
            const ra = (view.ra - (e.clientX - last[0]) * 0.3 + 360) % 360;
            const dec = Math.min(Math.max(view.dec + (e.clientY - last[1]) * 0.3, -89), 89);
            last = [e.clientX, e.clientY];
            ctx.update({ ra: Math.round(ra * 10) / 10, dec: Math.round(dec * 10) / 10 });
        };
        const up = () => {
            canvas.removeEventListener('pointermove', move);
            canvas.removeEventListener('pointerup', up);
        };
        canvas.addEventListener('pointermove', move);
        canvas.addEventListener('pointerup', up);
    });
    canvas.addEventListener('wheel', (event) => {
        event.preventDefault();
        const distance = Math.min(Math.max(ctx.settings().distance * Math.exp(event.deltaY * 0.001), 8000), 2000000);
        ctx.update({ distance: Math.round(distance) });
    }, { passive: false });

    const observer = new ResizeObserver(resize);
    observer.observe(body);
    ctx.on('result', () => { buildPaths(); fitCamera(); });
    ctx.on(['time', 'mission', 'timeScale'], requestRender);
    ctx.onSettings((view) => {
        if (view.frame !== builtFrame) buildPaths();
        requestRender();
    });
    buildPaths();
    requestRender();

    return {
        destroy() {
            observer.disconnect();
            renderer.dispose();
            renderer.forceContextLoss();
        },
    };
}

// Round marker sprite; WebGL points are square otherwise.
function dotTexture() {
    const size = 32;
    const c = document.createElement('canvas');
    c.width = c.height = size;
    const ctx = c.getContext('2d');
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(size / 2, size / 2, size / 2 - 1, 0, 2 * Math.PI);
    ctx.fill();
    return new THREE.CanvasTexture(c);
}

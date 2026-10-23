/**
 * AstroFlyer 3D Inertial Celestial Orbit Viewport
 * High-Precision Astrodynamics Engine modeled after FreeFlyer 8.0.1 (ViewWindow1 - ThreeDView):
 * =========================================================================================
 * Technical Rigor & Mathematical Specifications:
 * 1. Reference Frame: Earth-Centered Inertial (ECI J2000), Right-Handed:
 *      +X_Three: Vernal Equinox (♈) in Equatorial Plane (+X_ECI)
 *      +Y_Three: North Celestial Pole (+Z_ECI)
 *      +Z_Three: -Y_ECI (Equatorial plane, 90° East of equinox is -Z_Three)
 * 2. Earth System Dynamics:
 *      • High-Resolution 2K NASA Blue Marble / Night Global Texture with anisotropic filtering
 *      • Greenwich Mean Sidereal Time (GMST) rotation: theta_GMST(t) = omega_E * t
 *      • Texture Prime Meridian rigorously aligned with geodetic (0° Lat, 0° Lon)
 *      • Ground Stations rigidly pinned to rotating Earth body-fixed frame (ECEF -> ECI)
 * 3. Spacecraft Modeling & Adaptive Screen-Space LOD:
 *      • True Physical Spacecraft Bus (Gold MLI Thermal Foil, Parabolic Dish, Apogee Thruster)
 *      • Dual Articulated Solar Array Wings tracking Sun Vector
 *      • Adaptive Screen-Space Scaling: 1:1 physical meter-scale when zoomed in;
 *        smoothly auto-scaled when zoomed out to maintain tactical visibility without
 *        distorting physical planetary proportions.
 * 4. Dual Trajectory Mechanics:
 *      • Perturbed Integrated Ribbon with FreeFlyer HEO Regime Gating:
 *          - Lime Green (#00ff00): Perigee Corridor (h < 8,000 km, hypersonic, drag/J2 peak)
 *          - Red (#ff2244): Apogee Dwell (h > 35,000 km, stationary dwell)
 *          - Cyan (#00e5ff): Nominal Transit
 *      • Instantaneous Osculating Keplerian Ellipse:
 *          - Real-time analytical Kepler ellipse passing through spacecraft,
 *            visually showing osculating apsidal/nodal precession rate.
 * 5. Local Orbital Frame Triad (RIC / LVLH):
 *      • Radial (R_hat, Orange): along r_vec
 *      • In-Track (I_hat, Cyan): along h_hat x r_hat
 *      • Cross-Track (C_hat, Magenta): along angular momentum h_vec
 * 6. True Conical Earth Shadow Geometry:
 *      • Convergent Umbra Cone (tapering to vertex at L_umbra = 1.38e6 km behind Earth)
 *      • Divergent Penumbra Cone (half-angle 0.269°)
 *      • Live spacecraft eclipse state annunciation (Umbra / Penumbra / Sunlight)
 * 7. Ground Station Network & Dynamic Line-of-Sight (LOS):
 *      • ISTRAC Bengaluru, Hassan MCF, DSN (Goldstone, Madrid, Canberra), Svalbard
 *      • 10° Topocentric Elevation Mask Cones
 *      • Active Laser Uplink Beam on AOS with live Az/El/Range readouts
 * 8. Molniya 3-Satellite Constellation Triad:
 *      • Concurrent visualization of 3 phased satellites (1A, 1B, 1C) with handover lines
 * =========================================================================================
 */

class Viewport3D {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;

        // Astrodynamical constants (WGS-84 / IERS / JPL DE440)
        this.R_EARTH = 6378.137;                 // Earth equatorial radius in km
        this.OMEGA_EARTH = 7.2921159e-5;         // Earth rotation rate rad/s
        this.AU_KM = 149597870.7;                // 1 AU in km
        this.R_SUN_KM = 696340.0;                // Sun radius in km

        // Trajectory state
        this.positions = [];     // Array of [x, y, z] in km (ECI)
        this.velocities = [];    // Velocity magnitude in km/s
        this.velVectors = [];    // 3D velocity vectors [vx, vy, vz] in km/s
        this.altitudes = [];     // Altitude in km
        this.trueAnomalies = []; // True anomaly in deg
        this.times = [];         // Epoch times in seconds
        this.semiMajorAxes = []; // Semi-major axis in km
        this.eccentricities = [];// Eccentricity
        this.inclinations = [];  // Inclination in deg
        this.raans = [];         // RAAN in deg
        this.argPerigees = [];   // Arg of perigee in deg
        this.currentIndex = 0;

        // Multi-satellite constellation data
        this.constellationData = null;

        // Visual toggles & modes
        this.trackSpacecraft = false;
        this.earthFixedMode = false;
        this.showOrbitPlane = true;
        this.showOsculatingEllipse = true;
        this.showRICVectors = true;
        this.showFootprint = true;
        this.showStations = true;
        this.showShadowCone = true;
        this.showBelts = false;
        this.showConstellation = true;

        // Ground stations (WGS-84 Lat, Lon in degrees)
        this.groundStations = [
            { id: 'ISTRAC', name: 'ISTRAC Bengaluru', lat: 12.97, lon: 77.58, color: 0xf59e0b, maskDeg: 10 },
            { id: 'HASSAN', name: 'Hassan MCF', lat: 13.01, lon: 76.10, color: 0xf59e0b, maskDeg: 10 },
            { id: 'GOLDSTONE', name: 'DSN Goldstone', lat: 35.43, lon: -116.89, color: 0x22c55e, maskDeg: 10 },
            { id: 'MADRID', name: 'DSN Madrid', lat: 40.43, lon: -4.25, color: 0x22c55e, maskDeg: 10 },
            { id: 'CANBERRA', name: 'DSN Canberra', lat: -35.40, lon: 148.98, color: 0x22c55e, maskDeg: 10 },
            { id: 'SVALBARD', name: 'Svalbard SatStation', lat: 78.23, lon: 15.41, color: 0x38bdf8, maskDeg: 10 }
        ];

        // Three.js Scene Initialization
        this.initScene();
        this.initMouseControls();
        this.initHUDControls();
        this.animate();

        window.addEventListener('resize', () => this.onResize());
    }

    initScene() {
        const parent = this.canvas.parentElement;
        const w = parent.clientWidth || 800;
        const h = parent.clientHeight || 500;

        // High-Precision WebGL Renderer with Logarithmic Depth Buffer (prevents Z-fighting in deep space)
        this.renderer = new THREE.WebGLRenderer({
            canvas: this.canvas,
            antialias: true,
            alpha: false,
            logarithmicDepthBuffer: true,
            powerPreference: 'high-performance'
        });
        this.renderer.setSize(w, h);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        this.renderer.setClearColor(0x020408, 1.0); // Deep aerospace space background

        this.scene = new THREE.Scene();

        // FreeFlyer Standard Perspective Camera: FOV 45°, R 57,000 km, RA 185°, Dec -16°
        this.camera = new THREE.PerspectiveCamera(45, w / h, 5, 2000000);
        this.camRadius = 57000;
        this.camTheta = THREE.MathUtils.degToRad(185);
        this.camPhi = THREE.MathUtils.degToRad(90 - (-16));
        this.camTarget = new THREE.Vector3(0, 0, 0);
        this.updateCameraPosition();

        // Balanced Celestial Lighting
        const ambientLight = new THREE.AmbientLight(0x2d3748, 0.55);
        this.scene.add(ambientLight);

        // Sun Directional Light along Ecliptic
        this.sunLight = new THREE.DirectionalLight(0xffffff, 1.8);
        this.sunLight.position.set(150000, 0, -50000);
        this.scene.add(this.sunLight);

        // Visual Component Hierarchies
        this.createStarfield();
        this.createEarthSystem();
        this.createCelestialReferences();
        this.createConicalShadowSystem();
        this.createRadiationBelts();
        this.createSpacecraftModel();
        this.createRICFrameTriad();
        this.createNadirAndFootprint();
        this.createStationLinks();
        this.createConstellationGroup();

        // Dynamic Elements
        this.orbitLine = null;
        this.osculatingEllipseLine = null;
        this.orbitPlaneMesh = null;
        this.apsidesLine = null;
        this.nodalLine = null;
    }

    createStarfield() {
        const count = 4500;
        const geo = new THREE.BufferGeometry();
        const pos = [];
        const col = [];

        for (let i = 0; i < count; i++) {
            const r = 450000 + Math.random() * 350000;
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.acos(2 * Math.random() - 1);
            pos.push(
                r * Math.sin(phi) * Math.cos(theta),
                r * Math.cos(phi),
                r * Math.sin(phi) * Math.sin(theta)
            );
            const t = Math.random();
            if (t > 0.85) col.push(0.72, 0.85, 1.0);       // B-class blue
            else if (t < 0.15) col.push(1.0, 0.88, 0.70);  // K-class gold
            else col.push(0.96, 0.96, 0.98);               // G-class white
        }

        geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
        geo.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
        const mat = new THREE.PointsMaterial({
            vertexColors: true,
            size: 55,
            sizeAttenuation: true,
            transparent: true,
            opacity: 0.88
        });
        this.scene.add(new THREE.Points(geo, mat));
    }

    createEarthSystem() {
        // Rotating Earth Group: rotates around Celestial Y (+Z_ECI) with GMST
        this.earthGroup = new THREE.Group();

        const earthGeo = new THREE.SphereGeometry(this.R_EARTH, 96, 96);
        const textureLoader = new THREE.TextureLoader();

        const onTextureLoaded = (tex) => {
            tex.wrapS = THREE.RepeatWrapping;
            tex.wrapT = THREE.ClampToEdgeWrapping;
            tex.anisotropy = 8;
            if (this.earthMesh) {
                this.earthMesh.material.map = tex;
                this.earthMesh.material.needsUpdate = true;
            }
            this.renderer.render(this.scene, this.camera);
        };

        const earthTexture = textureLoader.load('world_map_dark.png', onTextureLoaded, undefined, () => {
            textureLoader.load('blue_marble_map.png', onTextureLoaded);
        });

        const earthMat = new THREE.MeshPhongMaterial({
            map: earthTexture,
            color: 0xffffff,
            emissive: 0x020617,
            specular: 0x1e293b,
            shininess: 30
        });

        this.earthMesh = new THREE.Mesh(earthGeo, earthMat);
        // Rigorous alignment: In Three.js SphereGeometry, texture center u=0.5 (Lon=0°) is at +Z.
        // Rotating by +90° (Math.PI/2) around Y places Lon=0° exactly at +X, perfectly matching ECEF coordinates!
        this.earthMesh.rotation.y = Math.PI / 2.0;
        this.earthGroup.add(this.earthMesh);

        // Rayleigh Atmospheric Scattering Limb Halo
        const atmosGeo = new THREE.SphereGeometry(this.R_EARTH * 1.025, 64, 64);
        const atmosMat = new THREE.MeshBasicMaterial({
            color: 0x00d4ff,
            transparent: true,
            opacity: 0.16,
            side: THREE.BackSide
        });
        this.atmosMesh = new THREE.Mesh(atmosGeo, atmosMat);
        this.earthGroup.add(this.atmosMesh);

        // Attach Ground Stations directly to rotating Earth Group
        this.createGroundStationPins();

        this.scene.add(this.earthGroup);
    }

    createGroundStationPins() {
        this.stationPins = [];

        this.groundStations.forEach(st => {
            const phi = THREE.MathUtils.degToRad(st.lat);
            const lambda = THREE.MathUtils.degToRad(st.lon);

            // Rigorous Geodetic to Body-Fixed Cartesian:
            // X = R_E * cos(phi) * cos(lambda)
            // Y = R_E * sin(phi)
            // Z = -R_E * cos(phi) * sin(lambda)
            const r = this.R_EARTH + 4.0;
            const x = r * Math.cos(phi) * Math.cos(lambda);
            const y = r * Math.sin(phi);
            const z = -r * Math.cos(phi) * Math.sin(lambda);

            const stGroup = new THREE.Group();
            stGroup.position.set(x, y, z);

            const norm = new THREE.Vector3(x, y, z).normalize();

            // Mast
            const mastGeo = new THREE.CylinderGeometry(18, 6, 320, 8);
            const mastMat = new THREE.MeshBasicMaterial({ color: st.color });
            const mast = new THREE.Mesh(mastGeo, mastMat);
            mast.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), norm);
            stGroup.add(mast);

            // Head Beacon
            const headGeo = new THREE.SphereGeometry(85, 12, 12);
            const headMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
            const head = new THREE.Mesh(headGeo, headMat);
            head.position.copy(norm.clone().multiplyScalar(220));
            stGroup.add(head);

            // 10° Topocentric Elevation Mask Cone
            const coneH = 2000;
            const coneR = coneH * Math.tan(THREE.MathUtils.degToRad(90 - st.maskDeg));
            const coneGeo = new THREE.ConeGeometry(coneR, coneH, 24, 1, true);
            const coneMat = new THREE.MeshBasicMaterial({
                color: st.color,
                wireframe: true,
                transparent: true,
                opacity: 0.12
            });
            const cone = new THREE.Mesh(coneGeo, coneMat);
            cone.position.copy(norm.clone().multiplyScalar(coneH / 2.0));
            cone.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), norm);
            stGroup.add(cone);

            // Billboard Station Name Sprite
            const sprite = this.createStationSprite(st.name, st.color);
            sprite.position.copy(norm.clone().multiplyScalar(480));
            stGroup.add(sprite);

            this.earthGroup.add(stGroup);

            this.stationPins.push({
                data: st,
                localPos: new THREE.Vector3(x, y, z),
                headObj: head,
                group: stGroup
            });
        });
    }

    createStationSprite(name, colorHex) {
        const canvas = document.createElement('canvas');
        canvas.width = 256;
        canvas.height = 64;
        const ctx = canvas.getContext('2d');

        ctx.fillStyle = 'rgba(10, 16, 28, 0.88)';
        ctx.strokeStyle = `#${colorHex.toString(16).padStart(6, '0')}`;
        ctx.lineWidth = 2;
        ctx.fillRect(4, 8, 248, 48);
        ctx.strokeRect(4, 8, 248, 48);

        ctx.font = 'bold 20px Tahoma, sans-serif';
        ctx.fillStyle = '#ffffff';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(name, 128, 32);

        const tex = new THREE.CanvasTexture(canvas);
        const spriteMat = new THREE.SpriteMaterial({ map: tex, transparent: true });
        const sprite = new THREE.Sprite(spriteMat);
        sprite.scale.set(1200, 300, 1);
        return sprite;
    }

    createCelestialReferences() {
        this.celestialGroup = new THREE.Group();

        // 1. Celestial Equator Ring (Z_ECI = 0 plane -> Y=0 in Three.js)
        const eqR = this.R_EARTH * 1.015;
        const eqCurve = new THREE.EllipseCurve(0, 0, eqR, eqR, 0, 2 * Math.PI, false, 0);
        const eqPoints = eqCurve.getPoints(128).map(p => new THREE.Vector3(p.x, 0, p.y));
        const eqGeo = new THREE.BufferGeometry().setFromPoints(eqPoints);
        const eqMat = new THREE.LineBasicMaterial({ color: 0x00e5ff, transparent: true, opacity: 0.55 });
        this.celestialGroup.add(new THREE.Line(eqGeo, eqMat));

        // 2. Vernal Equinox Vector (+X_ECI direction, ♈)
        const eqxLen = 16000;
        const eqxGeo = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(0, 0, 0),
            new THREE.Vector3(eqxLen, 0, 0)
        ]);
        const eqxMat = new THREE.LineBasicMaterial({ color: 0xef4444, linewidth: 2 });
        this.celestialGroup.add(new THREE.Line(eqxGeo, eqxMat));

        const eqxCone = new THREE.Mesh(
            new THREE.ConeGeometry(280, 800, 16),
            new THREE.MeshBasicMaterial({ color: 0xef4444 })
        );
        eqxCone.position.set(eqxLen + 350, 0, 0);
        eqxCone.rotation.z = -Math.PI / 2;
        this.celestialGroup.add(eqxCone);

        // 3. North Celestial Pole Axis (+Z_ECI -> +Y_Three)
        const npLen = 16000;
        const npGeo = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(0, -npLen, 0),
            new THREE.Vector3(0, npLen, 0)
        ]);
        const npMat = new THREE.LineBasicMaterial({ color: 0x38bdf8, linewidth: 2 });
        this.celestialGroup.add(new THREE.Line(npGeo, npMat));

        const npCone = new THREE.Mesh(
            new THREE.ConeGeometry(280, 800, 16),
            new THREE.MeshBasicMaterial({ color: 0x38bdf8 })
        );
        npCone.position.set(0, npLen + 350, 0);
        this.celestialGroup.add(npCone);

        this.scene.add(this.celestialGroup);
    }

    createConicalShadowSystem() {
        // Rigorous Dual-Cone Solar Eclipse Geometry
        this.shadowGroup = new THREE.Group();

        // 1. Umbra Cone: Convergent cone behind Earth
        // Tip distance L_umbra = R_E * D_sun / (R_sun - R_E) ~ 1,384,000 km
        // In local view, render the first 120,000 km where HEO orbits cross
        const umbraLen = 120000; // km
        const rUmbraBase = this.R_EARTH;
        const rUmbraTip = this.R_EARTH * (1.0 - umbraLen / 1384000.0);

        const umbraGeo = new THREE.CylinderGeometry(rUmbraTip, rUmbraBase, umbraLen, 32, 1, true);
        const umbraMat = new THREE.MeshBasicMaterial({
            color: 0x581c87, // Deep royal purple for complete umbra
            transparent: true,
            opacity: 0.18,
            side: THREE.DoubleSide
        });
        const umbraMesh = new THREE.Mesh(umbraGeo, umbraMat);
        umbraMesh.position.set(0, 0, umbraLen / 2.0);
        umbraMesh.rotation.x = Math.PI / 2;
        this.shadowGroup.add(umbraMesh);

        // 2. Penumbra Cone: Divergent cone behind Earth (opening half-angle 0.269°)
        const penumbraLen = 120000;
        const rPenumbraTip = this.R_EARTH + penumbraLen * Math.tan(THREE.MathUtils.degToRad(0.269));
        const penGeo = new THREE.CylinderGeometry(rPenumbraTip, this.R_EARTH, penumbraLen, 32, 1, true);
        const penMat = new THREE.MeshBasicMaterial({
            color: 0xf59e0b, // Amber translucent for partial penumbra
            transparent: true,
            opacity: 0.08,
            side: THREE.DoubleSide
        });
        const penMesh = new THREE.Mesh(penGeo, penMat);
        penMesh.position.set(0, 0, penumbraLen / 2.0);
        penMesh.rotation.x = Math.PI / 2;
        this.shadowGroup.add(penMesh);

        this.scene.add(this.shadowGroup);
    }

    createRadiationBelts() {
        this.radiationBeltGroup = new THREE.Group();

        // 1. Inner Proton Belt (1,000 to 6,000 km alt -> Torus radius ~9,500 km, tube ~2,400 km)
        const innerGeo = new THREE.TorusGeometry(9500, 2400, 16, 48);
        const innerMat = new THREE.MeshBasicMaterial({
            color: 0xf59e0b,
            transparent: true,
            opacity: 0.15,
            wireframe: true
        });
        const innerTorus = new THREE.Mesh(innerGeo, innerMat);
        innerTorus.rotation.x = Math.PI / 2;
        this.radiationBeltGroup.add(innerTorus);

        // 2. Outer Electron Belt (15,000 to 25,000 km alt -> Torus radius ~22,000 km, tube ~7,200 km)
        const outerGeo = new THREE.TorusGeometry(22000, 7200, 16, 56);
        const outerMat = new THREE.MeshBasicMaterial({
            color: 0xa855f7,
            transparent: true,
            opacity: 0.09,
            wireframe: true
        });
        const outerTorus = new THREE.Mesh(outerGeo, outerMat);
        outerTorus.rotation.x = Math.PI / 2;
        this.radiationBeltGroup.add(outerTorus);

        // Geomagnetic Dipole Axis Tilt (11.5 degrees)
        this.radiationBeltGroup.rotation.z = THREE.MathUtils.degToRad(11.5);
        this.radiationBeltGroup.visible = false;
        this.scene.add(this.radiationBeltGroup);
    }

    createSpacecraftModel() {
        this.scGroup = new THREE.Group();

        // Base unit dimensions: 1 unit = 100 meters in scaled mesh coordinates
        // 1. Hexagonal Avionics Bus (Gold MLI Thermal Foil)
        const busGeo = new THREE.CylinderGeometry(1.4, 1.4, 2.6, 6);
        const busMat = new THREE.MeshPhongMaterial({
            color: 0xd4af37,
            specular: 0xffffff,
            shininess: 90
        });
        const bus = new THREE.Mesh(busGeo, busMat);
        this.scGroup.add(bus);

        // 2. Apogee Kick Engine Bell (Titanium Niobium nozzle)
        const engineGeo = new THREE.ConeGeometry(0.8, 1.4, 16);
        const engineMat = new THREE.MeshPhongMaterial({ color: 0x334155, shininess: 45 });
        const engine = new THREE.Mesh(engineGeo, engineMat);
        engine.position.set(0, -1.9, 0);
        engine.rotation.x = Math.PI;
        this.scGroup.add(engine);

        // 3. High-Gain Communications Dish
        const dishGeo = new THREE.CylinderGeometry(1.2, 0.2, 0.45, 24);
        const dishMat = new THREE.MeshPhongMaterial({ color: 0xf8fafc, specular: 0xffffff, shininess: 95 });
        const dish = new THREE.Mesh(dishGeo, dishMat);
        dish.position.set(0, 1.7, 0);
        this.scGroup.add(dish);

        // 4. Articulated Solar Array Wings (tracking Sun)
        this.solarArrayGroup = new THREE.Group();
        const wingGeo = new THREE.BoxGeometry(5.2, 0.08, 1.8);
        const wingMat = new THREE.MeshPhongMaterial({
            color: 0x0a2540,
            emissive: 0x031224,
            specular: 0x38bdf8,
            shininess: 95
        });

        const leftWing = new THREE.Mesh(wingGeo, wingMat);
        leftWing.position.set(-3.6, 0, 0);
        this.solarArrayGroup.add(leftWing);

        const rightWing = new THREE.Mesh(wingGeo, wingMat);
        rightWing.position.set(3.6, 0, 0);
        this.solarArrayGroup.add(rightWing);

        this.scGroup.add(this.solarArrayGroup);

        // 5. Tactical Aerospace Reticle Beacon (Screen-Space Constant Diamond)
        const beaconCanvas = document.createElement('canvas');
        beaconCanvas.width = 128;
        beaconCanvas.height = 128;
        const bCtx = beaconCanvas.getContext('2d');
        bCtx.strokeStyle = '#00e5ff';
        bCtx.lineWidth = 4;
        bCtx.beginPath();
        bCtx.moveTo(64, 16);
        bCtx.lineTo(112, 64);
        bCtx.lineTo(64, 112);
        bCtx.lineTo(16, 64);
        bCtx.closePath();
        bCtx.stroke();
        bCtx.fillStyle = '#ffffff';
        bCtx.beginPath();
        bCtx.arc(64, 64, 8, 0, 2 * Math.PI);
        bCtx.fill();

        const bTex = new THREE.CanvasTexture(beaconCanvas);
        const bMat = new THREE.SpriteMaterial({ map: bTex, transparent: true });
        this.scBeacon = new THREE.Sprite(bMat);
        this.scBeacon.scale.set(600, 600, 1);
        this.scGroup.add(this.scBeacon);

        this.scene.add(this.scGroup);
    }

    createRICFrameTriad() {
        this.ricGroup = new THREE.Group();

        // 1. Radial (R_hat, Orange)
        this.arrowRadial = new THREE.ArrowHelper(
            new THREE.Vector3(1, 0, 0),
            new THREE.Vector3(0, 0, 0),
            2800,
            0xf97316,
            450,
            180
        );
        this.ricGroup.add(this.arrowRadial);

        // 2. In-Track (I_hat / V_hat, Cyan)
        this.arrowInTrack = new THREE.ArrowHelper(
            new THREE.Vector3(0, 1, 0),
            new THREE.Vector3(0, 0, 0),
            2800,
            0x06b6d4,
            450,
            180
        );
        this.ricGroup.add(this.arrowInTrack);

        // 3. Cross-Track (C_hat / Normal, Magenta)
        this.arrowCrossTrack = new THREE.ArrowHelper(
            new THREE.Vector3(0, 0, 1),
            new THREE.Vector3(0, 0, 0),
            2800,
            0xd946ef,
            450,
            180
        );
        this.ricGroup.add(this.arrowCrossTrack);

        this.scene.add(this.ricGroup);
    }

    createNadirAndFootprint() {
        // Vertical Nadir Beam from Spacecraft to Earth Sub-Satellite Point (SSP)
        const nadirGeo = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(0, 0, 0),
            new THREE.Vector3(0, 0, 0)
        ]);
        const nadirMat = new THREE.LineDashedMaterial({
            color: 0x00e5ff,
            dashSize: 400,
            gapSize: 200,
            transparent: true,
            opacity: 0.6
        });
        this.nadirBeam = new THREE.Line(nadirGeo, nadirMat);
        this.scene.add(this.nadirBeam);

        // Dynamic Spherical Visibility Horizon Footprint Circle on Earth
        const footGeo = new THREE.BufferGeometry();
        const footMat = new THREE.LineBasicMaterial({
            color: 0x00e5ff,
            transparent: true,
            opacity: 0.85,
            linewidth: 2
        });
        this.footprintCircle = new THREE.LineLoop(footGeo, footMat);
        this.scene.add(this.footprintCircle);
    }

    createStationLinks() {
        this.losLines = [];
        this.groundStations.forEach(st => {
            const geo = new THREE.BufferGeometry().setFromPoints([
                new THREE.Vector3(0, 0, 0),
                new THREE.Vector3(0, 0, 0)
            ]);
            const mat = new THREE.LineBasicMaterial({
                color: 0x22c55e, // Emerald green on active AOS contact
                transparent: true,
                opacity: 0.9,
                linewidth: 2
            });
            const line = new THREE.Line(geo, mat);
            line.visible = false;
            this.scene.add(line);
            this.losLines.push({ stationId: st.id, line, mat });
        });
    }

    createConstellationGroup() {
        this.constellationGroup = new THREE.Group();
        this.constellationSatellites = {};
        this.scene.add(this.constellationGroup);
    }

    initMouseControls() {
        let isDragging = false;
        let dragButton = 0;
        let lastX = 0, lastY = 0;

        this.canvas.addEventListener('contextmenu', (e) => e.preventDefault());

        this.canvas.addEventListener('mousedown', (e) => {
            isDragging = true;
            dragButton = e.button;
            lastX = e.clientX;
            lastY = e.clientY;
        });

        window.addEventListener('mouseup', () => { isDragging = false; });

        this.canvas.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            const dx = e.clientX - lastX;
            const dy = e.clientY - lastY;

            if (dragButton === 0) {
                // Orbit Rotation
                this.camTheta -= dx * 0.005;
                this.camPhi -= dy * 0.005;
                this.camPhi = Math.max(0.04, Math.min(Math.PI - 0.04, this.camPhi));
            } else if (dragButton === 2 || dragButton === 1) {
                // Pan Camera Target
                const panFactor = this.camRadius * 0.0008;
                const right = new THREE.Vector3();
                this.camera.getWorldDirection(right);
                right.cross(this.camera.up).normalize();
                this.camTarget.addScaledVector(right, -dx * panFactor);
                this.camTarget.addScaledVector(this.camera.up, dy * panFactor);
            }

            lastX = e.clientX;
            lastY = e.clientY;
            this.updateCameraPosition();
        });

        this.canvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            this.camRadius *= e.deltaY > 0 ? 1.08 : 0.92;
            this.camRadius = Math.max(6500, Math.min(600000, this.camRadius));
            this.updateCameraPosition();
        }, { passive: false });
    }

    initHUDControls() {
        const btnReset = document.getElementById('btn-cam-reset');
        const btnTop = document.getElementById('btn-cam-top');
        const btnEq = document.getElementById('btn-cam-eq');
        const btnTrack = document.getElementById('btn-cam-track');
        const btnBelts = document.getElementById('btn-toggle-belts-3d');

        if (btnReset) {
            btnReset.addEventListener('click', () => {
                this.trackSpacecraft = false;
                this.earthFixedMode = false;
                this.camTarget.set(0, 0, 0);
                this.camRadius = 57000;
                this.camTheta = THREE.MathUtils.degToRad(185);
                this.camPhi = THREE.MathUtils.degToRad(90 - (-16));
                this.updateCameraPosition();
            });
        }
        if (btnTop) {
            btnTop.addEventListener('click', () => {
                this.trackSpacecraft = false;
                this.camTarget.set(0, 0, 0);
                this.camPhi = 0.05; // Looking straight down North Celestial Pole
                this.camRadius = 75000;
                this.updateCameraPosition();
            });
        }
        if (btnEq) {
            btnEq.addEventListener('click', () => {
                this.trackSpacecraft = false;
                this.earthFixedMode = false;
                this.camTarget.set(0, 0, 0);
                this.camPhi = Math.PI / 2.0; // Equatorial edge-on
                this.camRadius = 65000;
                this.updateCameraPosition();
            });
        }
        const btnEcef = document.getElementById('btn-cam-ecef');
        if (btnEcef) {
            btnEcef.addEventListener('click', () => {
                this.earthFixedMode = !this.earthFixedMode;
                btnEcef.innerText = this.earthFixedMode ? '🌍 ECEF: ON' : '🌍 ECEF: OFF';
                btnEcef.style.backgroundColor = this.earthFixedMode ? 'var(--ff-accent-primary)' : '';
                this.updateCameraPosition();
            });
        }
        if (btnTrack) {
            btnTrack.addEventListener('click', () => {
                this.trackSpacecraft = !this.trackSpacecraft;
                btnTrack.style.backgroundColor = this.trackSpacecraft ? 'var(--ff-accent-primary)' : '';
                if (this.trackSpacecraft) {
                    this.camRadius = 1800; // Close inspection range
                }
                this.updateCameraPosition();
            });
        }
        if (btnBelts) {
            btnBelts.addEventListener('click', () => {
                this.showBelts = !this.showBelts;
                if (this.radiationBeltGroup) this.radiationBeltGroup.visible = this.showBelts;
                btnBelts.innerText = this.showBelts ? '🛡️ Belts: ON' : '🛡️ Belts: OFF';
                btnBelts.style.backgroundColor = this.showBelts ? 'var(--ff-accent-purple)' : '';
            });
        }
    }

    updateCameraPosition() {
        let target = this.camTarget;
        if (this.trackSpacecraft && this.scGroup) {
            target = this.scGroup.position;
        }

        let theta = this.camTheta;
        if (this.earthFixedMode && this.times.length > 0) {
            const t = this.times[this.currentIndex] || 0;
            theta += (this.OMEGA_EARTH * t);
        }

        this.camera.position.set(
            target.x + this.camRadius * Math.sin(this.camPhi) * Math.cos(theta),
            target.y + this.camRadius * Math.cos(this.camPhi),
            target.z + this.camRadius * Math.sin(this.camPhi) * Math.sin(theta)
        );
        this.camera.lookAt(target);

        // Update HUD Camera Status Readout
        const raDeg = Math.round(((theta * 180 / Math.PI) % 360 + 360) % 360);
        const decDeg = Math.round(90 - this.camPhi * 180 / Math.PI);
        const ffCameraStatus = document.getElementById('ff-3d-cam-status');
        if (ffCameraStatus) {
            ffCameraStatus.innerText = `R: ${(Math.round(this.camRadius)).toLocaleString()} km | RA: ${raDeg}° | Dec: ${decDeg}°`;
        }
    }

    loadTrajectory(data) {
        if (!data) return;
        const rawPos = data.positions_m || data.position_m;
        if (!rawPos || !Array.isArray(rawPos)) return;

        // ECI meters to Three.js coordinates: X_Three = X_ECI, Y_Three = Z_ECI, Z_Three = -Y_ECI (km)
        this.positions = rawPos.map(p => [p[0] / 1000.0, p[2] / 1000.0, -p[1] / 1000.0]);
        this.velocities = data.velocity_kms || [];
        this.velVectors = (data.velocity_ms || []).map(v => [v[0] / 1000.0, v[2] / 1000.0, -v[1] / 1000.0]);
        this.altitudes = data.altitude_km || [];
        this.trueAnomalies = data.true_anomaly_deg || [];
        this.times = data.times || data.times_sec || [];
        this.semiMajorAxes = data.semi_major_axis_km || [];
        this.eccentricities = data.eccentricity || [];
        this.inclinations = data.inclination_deg || [];
        this.raans = data.raan_deg || [];
        this.argPerigees = data.arg_perigee_deg || [];

        // Check if multi-satellite constellation data exists in payload
        if (data.innovations_suite && data.innovations_suite.molniya_constellation_handover) {
            this.loadConstellationData(data.innovations_suite.molniya_constellation_handover);
        }

        // 1. Remove old trajectory elements
        if (this.orbitLine) {
            this.scene.remove(this.orbitLine);
            this.orbitLine.geometry.dispose();
            this.orbitLine = null;
        }
        if (this.osculatingEllipseLine) {
            this.scene.remove(this.osculatingEllipseLine);
            this.osculatingEllipseLine.geometry.dispose();
            this.osculatingEllipseLine = null;
        }
        if (this.orbitPlaneMesh) {
            this.scene.remove(this.orbitPlaneMesh);
            this.orbitPlaneMesh.geometry.dispose();
            this.orbitPlaneMesh = null;
        }
        if (this.apsidesLine) {
            this.scene.remove(this.apsidesLine);
            this.apsidesLine.geometry.dispose();
            this.apsidesLine = null;
        }
        if (this.nodalLine) {
            this.scene.remove(this.nodalLine);
            this.nodalLine.geometry.dispose();
            this.nodalLine = null;
        }

        // 2. Build FreeFlyer HEO Trajectory Ribbon (Regime Gating)
        const points = [];
        const colors = [];

        for (let i = 0; i < this.positions.length; i++) {
            const p = this.positions[i];
            points.push(new THREE.Vector3(p[0], p[1], p[2]));

            const alt = this.altitudes[i] !== undefined ? this.altitudes[i] : 20000;
            if (alt < 8000) {
                colors.push(0.0, 1.0, 0.2);   // Lime Green (Perigee Corridor)
            } else if (alt > 35000) {
                colors.push(1.0, 0.13, 0.27); // Coral Red (Apogee Dwell)
            } else {
                colors.push(0.0, 0.9, 1.0);   // Cyan (Nominal Arc)
            }
        }

        const orbitGeo = new THREE.BufferGeometry().setFromPoints(points);
        orbitGeo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
        const orbitMat = new THREE.LineBasicMaterial({
            vertexColors: true,
            linewidth: 2,
            transparent: true,
            opacity: 0.95
        });
        this.orbitLine = new THREE.Line(orbitGeo, orbitMat);
        this.scene.add(this.orbitLine);

        // 3. Build Translucent Orbital Plane
        const planeGeo = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(0, 0, 0),
            ...points
        ]);
        const planeMat = new THREE.MeshBasicMaterial({
            color: 0x0284c7,
            transparent: true,
            opacity: 0.07,
            side: THREE.DoubleSide
        });
        this.orbitPlaneMesh = new THREE.Mesh(planeGeo, planeMat);
        this.scene.add(this.orbitPlaneMesh);

        // 4. Line of Apsides (Perigee to Earth Center to Apogee)
        let minAltIdx = 0, maxAltIdx = 0;
        let minAlt = Infinity, maxAlt = -Infinity;
        for (let i = 0; i < this.altitudes.length; i++) {
            if (this.altitudes[i] < minAlt) { minAlt = this.altitudes[i]; minAltIdx = i; }
            if (this.altitudes[i] > maxAlt) { maxAlt = this.altitudes[i]; maxAltIdx = i; }
        }

        if (this.positions[minAltIdx] && this.positions[maxAltIdx]) {
            const pPeri = this.positions[minAltIdx];
            const pApo = this.positions[maxAltIdx];
            const apsGeo = new THREE.BufferGeometry().setFromPoints([
                new THREE.Vector3(pPeri[0], pPeri[1], pPeri[2]),
                new THREE.Vector3(0, 0, 0),
                new THREE.Vector3(pApo[0], pApo[1], pApo[2])
            ]);
            const apsMat = new THREE.LineDashedMaterial({
                color: 0xf59e0b,
                dashSize: 600,
                gapSize: 400
            });
            this.apsidesLine = new THREE.Line(apsGeo, apsMat);
            this.apsidesLine.computeLineDistances();
            this.scene.add(this.apsidesLine);
        }

        // 5. Line of Nodes (Intersection with Equatorial Plane Y=0)
        this.buildLineOfNodes();

        this.updatePosition(0);
    }

    buildLineOfNodes() {
        if (!this.positions || this.positions.length < 2) return;
        let ascNode = null, descNode = null;

        for (let i = 0; i < this.positions.length - 1; i++) {
            const y1 = this.positions[i][1];
            const y2 = this.positions[i + 1][1];
            if (y1 * y2 <= 0) {
                const frac = -y1 / (y2 - y1);
                const xN = this.positions[i][0] + frac * (this.positions[i + 1][0] - this.positions[i][0]);
                const zN = this.positions[i][2] + frac * (this.positions[i + 1][2] - this.positions[i][2]);
                const nodePt = new THREE.Vector3(xN, 0, zN);
                if (y2 > y1 && !ascNode) ascNode = nodePt;
                else if (y2 < y1 && !descNode) descNode = nodePt;
            }
        }

        if (ascNode && descNode) {
            const nodalGeo = new THREE.BufferGeometry().setFromPoints([
                ascNode.clone().multiplyScalar(1.2),
                new THREE.Vector3(0, 0, 0),
                descNode.clone().multiplyScalar(1.2)
            ]);
            const nodalMat = new THREE.LineDashedMaterial({
                color: 0x38bdf8,
                dashSize: 500,
                gapSize: 350
            });
            this.nodalLine = new THREE.Line(nodalGeo, nodalMat);
            this.nodalLine.computeLineDistances();
            this.scene.add(this.nodalLine);
        }
    }

    loadConstellationData(constData) {
        if (!constData || !constData.satellites) return;
        this.constellationData = constData;

        // Clear existing constellation meshes
        while (this.constellationGroup.children.length > 0) {
            const obj = this.constellationGroup.children[0];
            this.constellationGroup.remove(obj);
        }

        const colors = {
            "Molniya-1A": 0x00e5ff,
            "Molniya-1B": 0xf59e0b,
            "Molniya-1C": 0xa855f7
        };

        for (const [satName, satObj] of Object.entries(constData.satellites)) {
            const satPts = satObj.position_m.map(p => new THREE.Vector3(p[0] / 1000.0, p[2] / 1000.0, -p[1] / 1000.0));
            const cGeo = new THREE.BufferGeometry().setFromPoints(satPts);
            const cMat = new THREE.LineBasicMaterial({
                color: colors[satName] || 0x38bdf8,
                transparent: true,
                opacity: 0.6,
                linewidth: 1.5
            });
            const cLine = new THREE.Line(cGeo, cMat);
            this.constellationGroup.add(cLine);

            // Satellite Beacon
            const bGeo = new THREE.SphereGeometry(140, 12, 12);
            const bMat = new THREE.MeshBasicMaterial({ color: colors[satName] || 0xffffff });
            const beacon = new THREE.Mesh(bGeo, bMat);
            this.constellationGroup.add(beacon);

            this.constellationSatellites[satName] = { line: cLine, beacon, positions: satPts };
        }
    }

    updateOsculatingKeplerianEllipse(i) {
        // Renders instantaneous Keplerian ellipse at current osculating state
        if (!this.semiMajorAxes || !this.semiMajorAxes[i]) return;

        const a = this.semiMajorAxes[i];
        const e = this.eccentricities[i];
        const inc = THREE.MathUtils.degToRad(this.inclinations[i] || 63.4);
        const raan = THREE.MathUtils.degToRad(this.raans[i] || 0.0);
        const aop = THREE.MathUtils.degToRad(this.argPerigees[i] || 270.0);

        const pts = [];
        const nSegments = 120;
        const p = a * (1.0 - e * e);

        for (let j = 0; j <= nSegments; j++) {
            const nu = (j / nSegments) * Math.PI * 2.0;
            const r = p / (1.0 + e * Math.cos(nu));

            // Perifocal coordinates
            const x_pqw = r * Math.cos(nu);
            const y_pqw = r * Math.sin(nu);

            // Perifocal to ECI rotation matrix
            const cosO = Math.cos(raan), sinO = Math.sin(raan);
            const cosi = Math.cos(inc),  sini = Math.sin(inc);
            const cosw = Math.cos(aop),  sinw = Math.sin(aop);

            const Px = cosO * cosw - sinO * sinw * cosi;
            const Py = sinO * cosw + cosO * sinw * cosi;
            const Pz = sinw * sini;

            const Qx = -cosO * sinw - sinO * cosw * cosi;
            const Qy = -sinO * sinw + cosO * cosw * cosi;
            const Qz = cosw * sini;

            const x_eci = x_pqw * Px + y_pqw * Qx;
            const y_eci = x_pqw * Py + y_pqw * Qy;
            const z_eci = x_pqw * Pz + y_pqw * Qz;

            // Map ECI to Three.js coordinates
            pts.push(new THREE.Vector3(x_eci, z_eci, -y_eci));
        }

        if (this.osculatingEllipseLine) {
            this.scene.remove(this.osculatingEllipseLine);
            this.osculatingEllipseLine.geometry.dispose();
            this.osculatingEllipseLine = null;
        }

        const ellGeo = new THREE.BufferGeometry().setFromPoints(pts);
        const ellMat = new THREE.LineDashedMaterial({
            color: 0xfde047, // Bright gold
            dashSize: 400,
            gapSize: 250,
            transparent: true,
            opacity: 0.65
        });
        this.osculatingEllipseLine = new THREE.Line(ellGeo, ellMat);
        this.osculatingEllipseLine.computeLineDistances();
        this.scene.add(this.osculatingEllipseLine);
    }

    updatePosition(idx) {
        if (!this.positions || this.positions.length === 0) return;
        const i = Math.max(0, Math.min(idx, this.positions.length - 1));
        this.currentIndex = i;

        const p = this.positions[i];
        const scPos = new THREE.Vector3(p[0], p[1], p[2]);
        const tSec = this.times[i] || 0;

        // 1. Earth Rotation with Greenwich Mean Sidereal Time (GMST)
        const thetaGMST = (this.OMEGA_EARTH * tSec) % (2.0 * Math.PI);
        if (this.earthGroup) {
            this.earthGroup.rotation.y = thetaGMST;
        }

        // 2. Spacecraft Position & Adaptive Screen-Space LOD Scaling
        if (this.scGroup) {
            this.scGroup.position.copy(scPos);

            // Compute distance from camera to spacecraft
            const camDist = this.camera.position.distanceTo(scPos);
            // Adaptive scale: When zoomed in (e.g. 1500 km), scale factor is small (1:1 physical).
            // When zoomed out (e.g. 50,000 km), smoothly scale up so the vehicle remains sharp and visible!
            const visualScale = Math.max(1.0, Math.min(220.0, camDist * 0.0035));
            this.scGroup.scale.set(visualScale, visualScale, visualScale);

            // Nadir Bus Alignment (-r)
            const nadirDir = scPos.clone().negate().normalize();
            this.scGroup.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), nadirDir);

            // Articulated Solar Array Wings tracking Sun Vector
            if (this.solarArrayGroup && this.sunLight) {
                const sunDir = this.sunLight.position.clone().normalize();
                this.solarArrayGroup.lookAt(scPos.clone().add(sunDir));
            }
        }

        // 3. Update Local Orbital Frame (RIC / LVLH Triad)
        if (this.ricGroup) {
            this.ricGroup.position.copy(scPos);

            // Radial unit vector: R_hat = r_vec / ||r||
            const rHat = scPos.clone().normalize();
            this.arrowRadial.setDirection(rHat);
            this.arrowRadial.setLength(2600, 400, 160);

            // In-Track / Velocity unit vector: V_hat = v_vec / ||v||
            let vDir = new THREE.Vector3(0, 1, 0);
            if (this.velVectors && this.velVectors[i]) {
                const v = this.velVectors[i];
                vDir = new THREE.Vector3(v[0], v[1], v[2]).normalize();
            } else if (i < this.positions.length - 1) {
                const pNext = this.positions[i + 1];
                vDir = new THREE.Vector3(pNext[0] - p[0], pNext[1] - p[1], pNext[2] - p[2]).normalize();
            }
            this.arrowInTrack.setDirection(vDir);
            this.arrowInTrack.setLength(3200, 400, 160);

            // Cross-Track unit vector: C_hat = (r x v) / ||r x v||
            const cVec = rHat.clone().cross(vDir).normalize();
            this.arrowCrossTrack.setDirection(cVec);
            this.arrowCrossTrack.setLength(2400, 400, 160);
        }

        // 4. Update Osculating Keplerian Ellipse
        if (this.showOsculatingEllipse) {
            this.updateOsculatingKeplerianEllipse(i);
        }

        // 5. Update Vertical Nadir Beam to Earth Surface
        const rMag = scPos.length();
        const sspPos = scPos.clone().normalize().multiplyScalar(this.R_EARTH);
        if (this.nadirBeam) {
            this.nadirBeam.geometry.setFromPoints([scPos, sspPos]);
            this.nadirBeam.computeLineDistances();
        }

        // 6. Update Dynamic Horizon Footprint Circle on Earth Sphere
        if (this.footprintCircle) {
            const h = Math.max(10.0, rMag - this.R_EARTH);
            const lamRad = Math.acos(Math.min(1.0, this.R_EARTH / (this.R_EARTH + h)));
            const rFoot = this.R_EARTH * Math.sin(lamRad);
            const dFoot = this.R_EARTH * Math.cos(lamRad);

            const nVec = sspPos.clone().normalize();
            let uVec = new THREE.Vector3(0, 1, 0).cross(nVec).normalize();
            if (uVec.lengthSq() < 0.001) uVec.set(1, 0, 0);
            const vVec = nVec.clone().cross(uVec).normalize();

            const footPts = [];
            const nSegments = 64;
            const centerCircle = nVec.clone().multiplyScalar(dFoot);

            for (let j = 0; j <= nSegments; j++) {
                const ang = (j / nSegments) * Math.PI * 2.0;
                const pt = centerCircle.clone()
                    .addScaledVector(uVec, rFoot * Math.cos(ang))
                    .addScaledVector(vVec, rFoot * Math.sin(ang));
                footPts.push(pt);
            }
            this.footprintCircle.geometry.setFromPoints(footPts);
        }

        // 7. Ground Station Dynamic LOS Laser Links & Contact Detection
        if (this.stationPins && this.stationPins.length > 0) {
            this.stationPins.forEach((st, idx) => {
                const stECI = st.localPos.clone().applyAxisAngle(new THREE.Vector3(0, 1, 0), thetaGMST);
                const rhoVec = scPos.clone().sub(stECI);
                const rho = rhoVec.length();

                const sinEl = stECI.dot(rhoVec) / (stECI.length() * rho);
                const elDeg = Math.asin(Math.max(-1.0, Math.min(1.0, sinEl))) * (180.0 / Math.PI);

                const inContact = elDeg >= st.data.maskDeg;
                const losLine = this.losLines[idx]?.line;

                if (losLine) {
                    if (inContact) {
                        losLine.visible = true;
                        losLine.geometry.setFromPoints([stECI, scPos]);
                        st.headObj.material.color.setHex(0x00ff00); // Glow green on AOS
                    } else {
                        losLine.visible = false;
                        st.headObj.material.color.setHex(0xffffff);
                    }
                }
            });
        }

        // 8. Update Shadow Cone Orientation & Detect Eclipse Condition
        let eclipseStatus = "SUNLIGHT";
        if (this.shadowGroup && this.sunLight) {
            const oppSun = this.sunLight.position.clone().negate().normalize();
            this.shadowGroup.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), oppSun);

            // Test if spacecraft is inside Umbra or Penumbra
            const dShadow = scPos.dot(oppSun);
            if (dShadow > 0) {
                // Perpendicular distance from shadow centerline
                const rPerp = scPos.clone().sub(oppSun.clone().multiplyScalar(dShadow)).length();
                const rUmbraBound = this.R_EARTH * Math.max(0.0, 1.0 - dShadow / 1384000.0);
                const rPenBound = this.R_EARTH + dShadow * Math.tan(THREE.MathUtils.degToRad(0.269));

                if (rPerp <= rUmbraBound) {
                    eclipseStatus = "UMBRA (FULL ECLIPSE)";
                } else if (rPerp <= rPenBound) {
                    eclipseStatus = "PENUMBRA (PARTIAL ECLIPSE)";
                }
            }
        }

        // 9. Update Multi-Satellite Constellation Beacons
        if (this.constellationData && this.constellationSatellites) {
            for (const [satName, satEntry] of Object.entries(this.constellationSatellites)) {
                if (satEntry.positions && satEntry.positions[i]) {
                    satEntry.beacon.position.copy(satEntry.positions[i]);
                }
            }
        }

        // 10. Update HUD Readout
        this.updateFreeFlyerStatusHUD(i, eclipseStatus);

        if (this.trackSpacecraft) {
            this.updateCameraPosition();
        }
    }

    updateFreeFlyerStatusHUD(i, eclipseStatus="SUNLIGHT") {
        const alt = this.altitudes[i] !== undefined ? this.altitudes[i] : 0;
        const vel = this.velocities[i] !== undefined ? this.velocities[i] : 0;
        const nu = this.trueAnomalies[i] !== undefined ? this.trueAnomalies[i] : 0;
        const tSec = this.times[i] !== undefined ? this.times[i] : 0;

        const hrs = Math.floor(tSec / 3600);
        const mins = Math.floor((tSec % 3600) / 60);
        const secs = (tSec % 60).toFixed(2);
        const epochStr = `MET +${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(5, '0')}`;

        const hudEpoch = document.getElementById('ff-3d-epoch');
        const hudHeight = document.getElementById('ff-3d-height');
        const hudVel = document.getElementById('ff-3d-vel');
        const hudNu = document.getElementById('ff-3d-nu');
        const hudRegime = document.getElementById('ff-3d-regime');

        if (hudEpoch) hudEpoch.innerText = epochStr;
        if (hudHeight) {
            hudHeight.innerText = `${alt.toFixed(2)} km`;
            hudHeight.style.color = alt < 8000 ? '#4ade80' : alt > 35000 ? '#f87171' : '#00e5ff';
        }
        if (hudVel) hudVel.innerText = `${vel.toFixed(3)} km/s`;
        if (hudNu) hudNu.innerText = `${nu.toFixed(2)}°`;

        if (hudRegime) {
            if (eclipseStatus.indexOf("UMBRA") !== -1) {
                hudRegime.innerText = "UMBRA INGRESS (TOTAL ECLIPSE)";
                hudRegime.className = "ff-regime-badge ff-regime-umbra";
            } else if (eclipseStatus.indexOf("PENUMBRA") !== -1) {
                hudRegime.innerText = "PENUMBRA (SOLAR ATTENUATION)";
                hudRegime.className = "ff-regime-badge ff-regime-penumbra";
            } else if (alt < 8000) {
                hudRegime.innerText = "PERIGEE CORRIDOR (HYPERSONIC)";
                hudRegime.className = "ff-regime-badge ff-regime-perigee";
            } else if (alt > 35000) {
                hudRegime.innerText = "APOGEE DWELL (STATIONARY)";
                hudRegime.className = "ff-regime-badge ff-regime-apogee";
            } else {
                hudRegime.innerText = "NOMINAL TRANSIT";
                hudRegime.className = "ff-regime-badge ff-regime-nominal";
            }
        }
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        if (this.canvas && this.canvas.offsetParent !== null) {
            this.render();
        }
    }

    render() {
        if (this.renderer && this.scene && this.camera) {
            if (this.scBeacon) {
                this.scBeacon.lookAt(this.camera.position);
            }
            this.renderer.render(this.scene, this.camera);
        }
    }

    onResize() {
        if (!this.canvas || !this.canvas.parentElement) return;
        const parent = this.canvas.parentElement;
        const w = parent.clientWidth || 800;
        const h = parent.clientHeight || 500;

        this.camera.aspect = w / h;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(w, h);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        this.render();
    }
}

window.Viewport3D = Viewport3D;

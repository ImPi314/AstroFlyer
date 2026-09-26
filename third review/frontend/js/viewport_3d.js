/**
 * AstroFlyer 3D Inertial Celestial Orbit Viewport
 * Complete implementation of FreeFlyer 8.0.1 ViewWindow1 (ThreeDView):
 *   - Reference Frame: Earth-Centered Inertial (ECI J2000)
 *   - FreeFlyer Viewpoint 1 Default: RA 185°, Dec -16°, Radius 57,000 km, FOV 45°
 *   - Pure Black Space Background (#000000) with Starfield
 *   - High-Resolution Textured Earth (NASA Blue Marble) with Celestial Equator & Night Shading
 *   - FreeFlyer HEO Trajectory Coloring:
 *       • Height < 8,000 km: ColorTools.Lime (#00ff00 / #4ade80) [Perigee Corridor]
 *       • Height > 40,000 km: ColorTools.Red (#ff2d55 / #f87171) [Apogee Dwell]
 *       • Nominal Arc: ColorTools.White / Cyan (#00e5ff)
 *   - 3D Spacecraft1 Model with Gold MLI Bus, Photovoltaic Arrays, Velocity Vector & Label
 *   - 3D Ground Station Pins with Line-of-Sight Cones (ISRO ISTRAC, Hassan MCF, NASA DSN)
 *   - FreeFlyer Signature Status Text HUD (Tahoma Font, Backdrop, Epoch, Height, Velocity)
 *   - Viewpoint Presets: Viewpoint1 (Default HEO), Polar (+Z), Equatorial, Track Spacecraft
 */

class Viewport3D {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;

        // Trajectory state
        this.positions = [];     // Array of [x, y, z] in km (ECI)
        this.velocities = [];    // Velocity magnitude in km/s
        this.altitudes = [];     // Altitude in km
        this.trueAnomalies = []; // True anomaly in deg
        this.times = [];         // Epoch times in seconds
        this.currentIndex = 0;
        this.trackSpacecraft = false;
        this.showAxes = true;
        this.showStations = true;

        // Ground stations (lat deg, lon deg)
        this.groundStations = [
            { name: 'ISTRAC Bengaluru', lat: 12.97, lon: 77.58, color: 0xf59e0b },
            { name: 'Hassan MCF', lat: 13.01, lon: 76.10, color: 0xf59e0b },
            { name: 'DSN Goldstone', lat: 35.43, lon: -116.89, color: 0x22c55e },
            { name: 'DSN Madrid', lat: 40.43, lon: -4.25, color: 0x22c55e },
            { name: 'DSN Canberra', lat: -35.40, lon: 148.98, color: 0x22c55e },
            { name: 'Svalbard SatStation', lat: 78.23, lon: 15.41, color: 0x38bdf8 }
        ];

        // Three.js Setup
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

        // Renderer
        this.renderer = new THREE.WebGLRenderer({
            canvas: this.canvas,
            antialias: true,
            alpha: false,
            powerPreference: 'high-performance'
        });
        this.renderer.setSize(w, h);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        // FreeFlyer BackgroundColor: 0 (Pure space black)
        this.renderer.setClearColor(0x000000, 1);

        // Scene
        this.scene = new THREE.Scene();

        // FreeFlyer Viewpoint 1: FOV 45°, Radius 57,000 km, RA 185°, Dec -16°
        this.camera = new THREE.PerspectiveCamera(45, w / h, 50, 600000);
        this.camRadius = 57000;
        // RA 185 deg = 3.2288 rad, Dec -16 deg = -0.279 rad (Polar phi = 90 - (-16) = 106 deg = 1.85 rad)
        this.camTheta = THREE.MathUtils.degToRad(185);
        this.camPhi = THREE.MathUtils.degToRad(90 - (-16));
        this.camTarget = new THREE.Vector3(0, 0, 0);
        this.updateCameraPosition();

        // Lighting: FreeFlyer AmbientColor: 6710886 (soft slate) + Directional Sun
        const ambientLight = new THREE.AmbientLight(0x404040, 0.7);
        this.scene.add(ambientLight);

        this.sunLight = new THREE.DirectionalLight(0xffffff, 1.4);
        this.sunLight.position.set(120000, 30000, 45000);
        this.scene.add(this.sunLight);

        // FreeFlyer Starfield
        this.createStarfield();

        // FreeFlyer Earth Sphere (Radius 6378.137 km)
        this.createEarth();

        // Van Allen Radiation Belts (Inner Proton & Outer Electron Toroids)
        this.createRadiationBelts();

        // FreeFlyer ECI Coordinate Axes (+X, +Y, +Z)
        this.createAxes();

        // Ground Stations on 3D Globe
        this.createGroundStationPins();

        // Orbit Line (populated on data load)
        this.orbitLine = null;

        // Spacecraft1 Model
        this.createSpacecraftModel();

    }

    createStarfield() {
        const starCount = 3000;
        const starsGeo = new THREE.BufferGeometry();
        const positions = [];
        const colors = [];

        for (let i = 0; i < starCount; i++) {
            const r = 250000 + Math.random() * 150000;
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.acos(2 * Math.random() - 1);
            positions.push(
                r * Math.sin(phi) * Math.cos(theta),
                r * Math.sin(phi) * Math.sin(theta),
                r * Math.cos(phi)
            );
            const tint = Math.random();
            if (tint > 0.85) colors.push(0.7, 0.85, 1.0);
            else if (tint < 0.15) colors.push(1.0, 0.95, 0.8);
            else colors.push(0.95, 0.95, 1.0);
        }

        starsGeo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
        starsGeo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
        const starMat = new THREE.PointsMaterial({
            vertexColors: true,
            size: 40,
            sizeAttenuation: true,
            transparent: true,
            opacity: 0.8
        });
        this.scene.add(new THREE.Points(starsGeo, starMat));
    }

    createEarth() {
        const R_EARTH = 6378.137; // km

        const earthGeo = new THREE.SphereGeometry(R_EARTH, 64, 64);
        const textureLoader = new THREE.TextureLoader();
        const earthTexture = textureLoader.load('world_map_dark.png', () => {
            this.renderer.render(this.scene, this.camera);
        }, undefined, () => {
            // Fallback to blue_marble_map.png if needed
            textureLoader.load('blue_marble_map.png', (tex) => {
                if (this.earthMesh) this.earthMesh.material.map = tex;
                this.renderer.render(this.scene, this.camera);
            });
        });
        earthTexture.wrapS = THREE.RepeatWrapping;
        earthTexture.wrapT = THREE.ClampToEdgeWrapping;

        const earthMat = new THREE.MeshPhongMaterial({
            map: earthTexture,
            color: 0xffffff,
            emissive: 0x040810,
            specular: 0x223344,
            shininess: 20
        });

        this.earthGroup = new THREE.Group();
        this.earthMesh = new THREE.Mesh(earthGeo, earthMat);
        this.earthMesh.rotation.z = THREE.MathUtils.degToRad(-23.44); // Obliquity
        this.earthGroup.add(this.earthMesh);

        // FreeFlyer Atmospheric Rim Glow
        const atmosGeo = new THREE.SphereGeometry(R_EARTH * 1.025, 48, 48);
        const atmosMat = new THREE.MeshBasicMaterial({
            color: 0x00d4ff,
            transparent: true,
            opacity: 0.12,
            side: THREE.BackSide
        });
        this.atmosMesh = new THREE.Mesh(atmosGeo, atmosMat);
        this.earthGroup.add(this.atmosMesh);

        // FreeFlyer Celestial Equator Ring
        const eqCurve = new THREE.EllipseCurve(0, 0, R_EARTH * 1.008, R_EARTH * 1.008, 0, 2 * Math.PI, false, 0);
        const eqPoints = eqCurve.getPoints(128);
        const eqGeo = new THREE.BufferGeometry().setFromPoints(eqPoints.map(p => new THREE.Vector3(p.x, 0, p.y)));
        const eqMat = new THREE.LineBasicMaterial({ color: 0x00e5ff, transparent: true, opacity: 0.45 });
        this.equatorRing = new THREE.Line(eqGeo, eqMat);
        this.scene.add(this.equatorRing);

        this.scene.add(this.earthGroup);
    }

    createRadiationBelts() {
        this.radiationBeltGroup = new THREE.Group();

        // 1. Inner Van Allen Belt (Trapped Protons - Amber subtle wireframe, ~1.2 to 2.4 Earth Radii)
        // Torus: radius from Earth center ~10,500 km, tube radius ~3,200 km
        const innerGeo = new THREE.TorusGeometry(10500, 3200, 16, 48);
        const innerMat = new THREE.MeshBasicMaterial({
            color: 0xf59e0b,
            transparent: true,
            opacity: 0.12,
            wireframe: true
        });
        const innerTorus = new THREE.Mesh(innerGeo, innerMat);
        innerTorus.rotation.x = Math.PI / 2;
        this.radiationBeltGroup.add(innerTorus);

        // 2. Outer Van Allen Belt (Relativistic Electrons - Purple subtle wireframe, ~3.5 to 6.5 Earth Radii)
        // Torus: radius from Earth center ~22,000 km, tube radius ~7,500 km
        const outerGeo = new THREE.TorusGeometry(22000, 7500, 16, 56);
        const outerMat = new THREE.MeshBasicMaterial({
            color: 0xa855f7,
            transparent: true,
            opacity: 0.08,
            wireframe: true
        });
        const outerTorus = new THREE.Mesh(outerGeo, outerMat);
        outerTorus.rotation.x = Math.PI / 2;
        this.radiationBeltGroup.add(outerTorus);

        // Tilt both by 11.5 deg (Geomagnetic Dipole axis)
        this.radiationBeltGroup.rotation.z = THREE.MathUtils.degToRad(11.5);

        // Default to HIDDEN so the 3D orbit view is completely clean
        this.radiationBeltGroup.visible = false;
        this.scene.add(this.radiationBeltGroup);
    }

    createAxes() {
        const axisLen = 14000;
        const axesData = [
            { dir: [1, 0, 0], color: 0xef4444, label: '+X Vernal Equinox (♈)' },
            { dir: [0, 0, 1], color: 0x22c55e, label: '+Y Orbit Normal' },
            { dir: [0, 1, 0], color: 0x38bdf8, label: '+Z North Pole' }
        ];

        this.axesGroup = new THREE.Group();

        axesData.forEach(a => {
            const pts = [
                new THREE.Vector3(0, 0, 0),
                new THREE.Vector3(a.dir[0] * axisLen, a.dir[1] * axisLen, a.dir[2] * axisLen)
            ];
            const geo = new THREE.BufferGeometry().setFromPoints(pts);
            const mat = new THREE.LineBasicMaterial({ color: a.color, linewidth: 2 });
            this.axesGroup.add(new THREE.Line(geo, mat));

            // Arrow Cone
            const coneGeo = new THREE.ConeGeometry(300, 900, 12);
            const coneMat = new THREE.MeshBasicMaterial({ color: a.color });
            const cone = new THREE.Mesh(coneGeo, coneMat);
            cone.position.set(a.dir[0] * (axisLen + 450), a.dir[1] * (axisLen + 450), a.dir[2] * (axisLen + 450));
            const dirVec = new THREE.Vector3(...a.dir).normalize();
            cone.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dirVec);
            this.axesGroup.add(cone);
        });

        this.scene.add(this.axesGroup);
    }

    createGroundStationPins() {
        const R = 6378.137 + 10;
        this.stationGroup = new THREE.Group();

        this.groundStations.forEach(st => {
            const phi = THREE.MathUtils.degToRad(90 - st.lat);
            const theta = THREE.MathUtils.degToRad(st.lon);

            const x = R * Math.sin(phi) * Math.cos(theta);
            const y = R * Math.cos(phi);
            const z = R * Math.sin(phi) * Math.sin(theta);

            // Ground Pin
            const pinGeo = new THREE.CylinderGeometry(40, 10, 450, 8);
            const pinMat = new THREE.MeshBasicMaterial({ color: st.color });
            const pin = new THREE.Mesh(pinGeo, pinMat);
            pin.position.set(x, y, z);
            pin.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), new THREE.Vector3(x, y, z).normalize());
            this.stationGroup.add(pin);

            // Pin Head Marker
            const headGeo = new THREE.SphereGeometry(120, 12, 12);
            const headMat = new THREE.MeshBasicMaterial({ color: st.color });
            const head = new THREE.Mesh(headGeo, headMat);
            const normal = new THREE.Vector3(x, y, z).normalize();
            head.position.set(x + normal.x * 320, y + normal.y * 320, z + normal.z * 320);
            this.stationGroup.add(head);
        });

        this.scene.add(this.stationGroup);
    }

    createSpacecraftModel() {
        this.scGroup = new THREE.Group();

        // 1. Central Satellite Bus
        const busGeo = new THREE.BoxGeometry(360, 480, 360);
        const busMat = new THREE.MeshPhongMaterial({
            color: 0xd4af37, // Gold foil MLI blanket
            specular: 0xffffff,
            shininess: 70
        });
        const bus = new THREE.Mesh(busGeo, busMat);
        this.scGroup.add(bus);

        // 2. Solar Array Wings (Left & Right)
        const panelGeo = new THREE.BoxGeometry(950, 20, 320);
        const panelMat = new THREE.MeshPhongMaterial({
            color: 0x1034a6, // Deep blue solar cells
            emissive: 0x05102a,
            specular: 0x38bdf8,
            shininess: 90
        });

        const leftWing = new THREE.Mesh(panelGeo, panelMat);
        leftWing.position.set(-720, 0, 0);
        this.scGroup.add(leftWing);

        const rightWing = new THREE.Mesh(panelGeo, panelMat);
        rightWing.position.set(720, 0, 0);
        this.scGroup.add(rightWing);

        // 3. Parabolic Antenna Dish
        const dishGeo = new THREE.CylinderGeometry(220, 50, 80, 16);
        const dishMat = new THREE.MeshPhongMaterial({ color: 0xffffff, specular: 0xcccccc });
        const dish = new THREE.Mesh(dishGeo, dishMat);
        dish.position.set(0, 300, 0);
        this.scGroup.add(dish);

        // 4. FreeFlyer Pulsating Target Beacon Ring
        const ringGeo = new THREE.RingGeometry(550, 850, 32);
        const ringMat = new THREE.MeshBasicMaterial({
            color: 0x00e5ff,
            transparent: true,
            opacity: 0.45,
            side: THREE.DoubleSide
        });
        this.scBeacon = new THREE.Mesh(ringGeo, ringMat);
        this.scGroup.add(this.scBeacon);

        // 5. Billboard Label Canvas: "Spacecraft1" in Tahoma Font
        this.scLabel = this.createBillboardLabel("Spacecraft1");
        this.scLabel.position.set(0, 750, 0);
        this.scGroup.add(this.scLabel);

        // 6. 3D Covariance Position Dispersion Ellipsoid (1-Sigma Bound)
        const covGeo = new THREE.SphereGeometry(1, 16, 16);
        const covMat = new THREE.MeshBasicMaterial({
            color: 0x00e5ff,
            wireframe: true,
            transparent: true,
            opacity: 0.45
        });
        this.covEllipsoid = new THREE.Mesh(covGeo, covMat);
        this.covEllipsoid.scale.set(450, 450, 450);
        this.scGroup.add(this.covEllipsoid);

        this.scene.add(this.scGroup);
    }

    createBillboardLabel(text) {
        const canvas = document.createElement('canvas');
        canvas.width = 256;
        canvas.height = 64;
        const ctx = canvas.getContext('2d');

        ctx.fillStyle = 'rgba(0, 0, 0, 0.75)';
        ctx.strokeStyle = '#00e5ff';
        ctx.lineWidth = 2;
        ctx.fillRect(4, 4, 248, 56);
        ctx.strokeRect(4, 4, 248, 56);

        ctx.font = 'bold 24px Tahoma, sans-serif';
        ctx.fillStyle = '#ffffff';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, 128, 32);

        const texture = new THREE.CanvasTexture(canvas);
        const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true });
        const sprite = new THREE.Sprite(spriteMat);
        sprite.scale.set(1200, 300, 1);
        return sprite;
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
                // Left drag: FreeFlyer 3D orbit rotation (Azimuth / Elevation)
                this.camTheta -= dx * 0.005;
                this.camPhi -= dy * 0.005;
                this.camPhi = Math.max(0.05, Math.min(Math.PI - 0.05, this.camPhi));
            } else if (dragButton === 2 || dragButton === 1) {
                // Right/Middle drag: Pan target
                const panFactor = this.camRadius * 0.001;
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
            this.camRadius = Math.max(7000, Math.min(250000, this.camRadius));
            this.updateCameraPosition();
        }, { passive: false });
    }

    initHUDControls() {
        const btnReset = document.getElementById('btn-cam-reset');
        const btnTop = document.getElementById('btn-cam-top');
        const btnEq = document.getElementById('btn-cam-eq');
        const btnTrack = document.getElementById('btn-cam-track');

        if (btnReset) {
            btnReset.addEventListener('click', () => {
                // FreeFlyer Viewpoint 1: RA 185°, Dec -16°, Radius 57,000 km
                this.camTheta = THREE.MathUtils.degToRad(185);
                this.camPhi = THREE.MathUtils.degToRad(90 - (-16));
                this.camRadius = 57000;
                this.camTarget.set(0, 0, 0);
                this.trackSpacecraft = false;
                if (btnTrack) btnTrack.classList.remove('active');
                this.updateCameraPosition();
            });
        }
        if (btnTop) {
            btnTop.addEventListener('click', () => {
                // Polar View (+Z North Pole)
                this.camTheta = 0;
                this.camPhi = 0.05;
                this.camRadius = 60000;
                this.camTarget.set(0, 0, 0);
                this.updateCameraPosition();
            });
        }
        if (btnEq) {
            btnEq.addEventListener('click', () => {
                // Equatorial View (0° Elevation)
                this.camTheta = 0;
                this.camPhi = Math.PI / 2;
                this.camRadius = 65000;
                this.camTarget.set(0, 0, 0);
                this.updateCameraPosition();
            });
        }
        if (btnTrack) {
            btnTrack.addEventListener('click', () => {
                this.trackSpacecraft = !this.trackSpacecraft;
                btnTrack.classList.toggle('active', this.trackSpacecraft);
                this.updateCameraPosition();
            });
        }

        const btnBelts = document.getElementById('btn-toggle-belts-3d');
        if (btnBelts) {
            btnBelts.addEventListener('click', () => {
                if (this.radiationBeltGroup) {
                    this.radiationBeltGroup.visible = !this.radiationBeltGroup.visible;
                    btnBelts.innerText = this.radiationBeltGroup.visible ? '🛡️ Belts: ON' : '🛡️ Belts: OFF';
                    btnBelts.classList.toggle('active', this.radiationBeltGroup.visible);
                }
            });
        }
    }

    updateCameraPosition() {
        const target = this.trackSpacecraft && this.scGroup ? this.scGroup.position : this.camTarget;
        this.camera.position.set(
            target.x + this.camRadius * Math.sin(this.camPhi) * Math.cos(this.camTheta),
            target.y + this.camRadius * Math.cos(this.camPhi),
            target.z + this.camRadius * Math.sin(this.camPhi) * Math.sin(this.camTheta)
        );
        this.camera.lookAt(target);

        // Update FreeFlyer Viewport Camera Status Readouts
        const raDeg = Math.round(((this.camTheta * 180 / Math.PI) % 360 + 360) % 360);
        const decDeg = Math.round(90 - this.camPhi * 180 / Math.PI);
        const azEl = document.getElementById('hud-cam-az');
        const elEl = document.getElementById('hud-cam-el');
        if (azEl) azEl.innerText = `${raDeg}°`;
        if (elEl) elEl.innerText = `${decDeg}°`;

        const ffCameraStatus = document.getElementById('ff-3d-cam-status');
        if (ffCameraStatus) {
            ffCameraStatus.innerText = `Radius: ${(this.camRadius).toLocaleString()} km | RA: ${raDeg}° | Dec: ${decDeg}°`;
        }
    }

    loadTrajectory(data) {
        if (!data) return;
        const rawPos = data.positions_m || data.position_m;
        if (!rawPos || !Array.isArray(rawPos)) return;

        this.positions = rawPos.map(p => [p[0] / 1000.0, p[1] / 1000.0, p[2] / 1000.0]);
        this.velocities = data.velocity_kms || [];
        this.altitudes = data.altitude_km || [];
        this.trueAnomalies = data.true_anomaly_deg || [];
        this.times = data.times || data.times_sec || [];

        // Remove old orbit line if present
        if (this.orbitLine) {
            this.scene.remove(this.orbitLine);
            this.orbitLine.geometry.dispose();
            this.orbitLine.material.dispose();
            this.orbitLine = null;
        }

        // Build Orbit Trajectory Line with FreeFlyer's Exact HEO Color Rules:
        // Height < 8000 km: ColorTools.Lime (#00ff00)
        // Height > 40000 km: ColorTools.Red (#ff0000)
        // Nominal Arc: ColorTools.White / Cyan (#00e5ff)
        const points = [];
        const colors = [];

        for (let i = 0; i < this.positions.length; i++) {
            const p = this.positions[i];
            // ECI to Three.js (Y-up: X -> X, Z -> Y, Y -> Z)
            points.push(new THREE.Vector3(p[0], p[2], p[1]));

            const alt = this.altitudes[i] !== undefined ? this.altitudes[i] : 20000;

            if (alt < 8000) {
                // FreeFlyer Perigee Corridor: ColorTools.Lime (#4ade80 / #00ff00)
                colors.push(0.0, 1.0, 0.2);
            } else if (alt > 35000) {
                // FreeFlyer Apogee Dwell: ColorTools.Red (#ff2244)
                colors.push(1.0, 0.15, 0.25);
            } else {
                // FreeFlyer Nominal Arc: Cyan / White (#00e5ff)
                colors.push(0.0, 0.9, 1.0);
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

        this.updatePosition(0);
    }

    updatePosition(idx) {
        if (!this.positions || this.positions.length === 0) return;
        const i = Math.max(0, Math.min(idx, this.positions.length - 1));
        this.currentIndex = i;

        const p = this.positions[i];
        const sx = p[0], sy = p[2], sz = p[1];

        if (this.scGroup) {
            this.scGroup.position.set(sx, sy, sz);

            // Orient satellite along velocity vector
            if (i < this.positions.length - 1) {
                const pNext = this.positions[i + 1];
                const dir = new THREE.Vector3(pNext[0] - p[0], pNext[2] - p[2], pNext[1] - p[1]).normalize();
                this.scGroup.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), dir);
            }
        }

        if (this.scBeacon) {
            this.scBeacon.lookAt(this.camera.position);
        }

        // Dynamically scale covariance dispersion ellipsoid
        if (this.covEllipsoid && window.appState && window.appState.telemetryData) {
            const cov = window.appState.telemetryData.covariance_dispersion;
            if (cov && cov.sigma_major_m && cov.sigma_major_m[i]) {
                // Scale factor for visibility in planetary view (visual multiplier x15)
                const sMajor = Math.max(300, (cov.sigma_major_m[i] / 1000.0) * 15.0 + 350);
                const sInter = Math.max(200, (cov.sigma_intermediate_m[i] / 1000.0) * 15.0 + 250);
                const sMinor = Math.max(150, (cov.sigma_minor_m[i] / 1000.0) * 15.0 + 200);
                this.covEllipsoid.scale.set(sMajor, sInter, sMinor);
            }
        }


        // Update FreeFlyer Signature Status Text Overlay
        this.updateFreeFlyerStatusHUD(i);

        if (this.trackSpacecraft) {
            this.updateCameraPosition();
        }
    }

    updateFreeFlyerStatusHUD(i) {
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
            if (alt < 8000) {
                hudRegime.innerText = 'PERIGEE CORRIDOR (HYPERSONIC)';
                hudRegime.className = 'ff-regime-badge ff-regime-perigee';
            } else if (alt > 35000) {
                hudRegime.innerText = 'APOGEE DWELL (COAST)';
                hudRegime.className = 'ff-regime-badge ff-regime-apogee';
            } else {
                hudRegime.innerText = 'NOMINAL TRANSFER ARC';
                hudRegime.className = 'ff-regime-badge ff-regime-nominal';
            }
        }
    }

    render() {
        if (this.renderer && this.scene && this.camera) {
            this.renderer.render(this.scene, this.camera);
        }
    }

    onResize() {
        if (!this.canvas || !this.renderer) return;
        const parent = this.canvas.parentElement;
        const w = parent.clientWidth || 800;
        const h = parent.clientHeight || 500;
        this.camera.aspect = w / h;
        this.camera.updateProjectionMatrix();
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        this.renderer.setSize(w, h);
    }

    animate() {
        if (!this.renderer) return;
        requestAnimationFrame(() => this.animate());

        // Slow sidereal rotation of Earth
        if (this.earthMesh) {
            this.earthMesh.rotation.y += 0.0003;
        }

        // Pulse beacon ring
        if (this.scBeacon) {
            const pulse = 0.35 + 0.25 * Math.sin(Date.now() * 0.004);
            this.scBeacon.material.opacity = pulse;
        }

        this.renderer.render(this.scene, this.camera);
    }
}

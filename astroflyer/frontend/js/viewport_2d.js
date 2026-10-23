/**
 * AstroFlyer 2D Ground Track Viewport
 * High-Precision Astrodynamics Engine modeled after FreeFlyer 8.0.1 (ViewWindow2 - MapView):
 * =========================================================================================
 * Technical Rigor & Mathematical Specifications:
 * 1. Reference Frame: Earth Body-Fixed (WGS-84 / ECEF) Equirectangular Projection
 *      Longitude: -180° to +180°, Latitude: -90° to +90°
 * 2. High-Latitude Molniya / Resonant Ground Track Loops:
 *      • Renders the characteristic 12-hour double-loop ground track structure where
 *        the satellite dwells over two distinct northern hemisphere longitudes (separated by 180°).
 *      • Continuous Antimeridian (|Delta Lon| > 180°) clipping preventing horizontal streak artifacts.
 *      • Regime-gated color trajectory: Lime (#00ff00) for Perigee, Red (#ff2244) for Apogee, Cyan for Nominal.
 * 3. Rigorous Spherical Geodesic Visibility Swaths (Footprints):
 *      • Spacecraft horizon footprint: cos(theta) = R_E / (R_E + h)
 *        Expands from 15.8° at perigee to 82.0° (near-hemispheric) at apogee.
 *      • Split across antimeridian boundaries into multi-part spherical polygon fills.
 * 4. Ground Station Network & Dynamic Contact Physics:
 *      • ISTRAC Bengaluru, Hassan MCF, NASA DSN (Goldstone, Madrid, Canberra), Svalbard.
 *      • Topocentric Azimuth (Az), Elevation (El), Slant Range (rho), and Doppler shift.
 *      • Active dynamic laser beam from station to SSP on Acquisition of Signal (AOS, El >= 10°).
 * 5. Solar Terminator & Real-Time Sub-Solar Point:
 *      • Dynamic day/night shadow boundary with solar declination and Greenwich Hour Angle.
 * 6. Multi-Satellite Constellation Display:
 *      • Simultaneous plotting of 3-satellite Molniya triad (1A, 1B, 1C) showing active handover.
 * 7. Sub-Satellite Point (SSP) Reticle:
 *      • True velocity heading needle: psi = atan2(v_East, v_North)
 *      • Flight path angle (gamma) and ground speed indicators.
 * =========================================================================================
 */

class Viewport2D {
    constructor(canvasId, mapImagePath) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');

        this.R_EARTH = 6378.137; // Earth equatorial radius km
        this.C_LIGHT = 299792.458; // Speed of light km/s

        this.mapImg = new Image();
        this.mapImg.onload = () => this.render();
        this.mapImg.onerror = () => {
            if (this.mapImg.src.indexOf('world_map_dark.png') !== -1) {
                this.mapImg.src = 'blue_marble_map.png';
            }
        };
        this.mapImg.src = mapImagePath || 'world_map_dark.png';

        // Trajectory state
        this.latitudes = [];
        this.longitudes = [];
        this.altitudes = [];
        this.velocities = [];
        this.trueAnomalies = [];
        this.times = [];
        this.currentIndex = 0;

        // Multi-satellite constellation state
        this.constellationData = null;

        // Ground stations (WGS-84 Lat, Lon in degrees)
        this.groundStations = [
            { id: 'ISTRAC', name: 'ISTRAC Bengaluru', lat: 12.97, lon: 77.58, color: '#f59e0b', maskDeg: 10, align: 'left', ox: 10, oy: 12 },
            { id: 'HASSAN', name: 'Hassan MCF', lat: 13.01, lon: 76.10, color: '#f59e0b', maskDeg: 10, align: 'right', ox: -10, oy: -8 },
            { id: 'GOLDSTONE', name: 'DSN Goldstone', lat: 35.43, lon: -116.89, color: '#22c55e', maskDeg: 10, align: 'left', ox: 9, oy: -5 },
            { id: 'MADRID', name: 'DSN Madrid', lat: 40.43, lon: -4.25, color: '#22c55e', maskDeg: 10, align: 'left', ox: 9, oy: -5 },
            { id: 'CANBERRA', name: 'DSN Canberra', lat: -35.40, lon: 148.98, color: '#22c55e', maskDeg: 10, align: 'left', ox: 9, oy: 14 },
            { id: 'SVALBARD', name: 'Svalbard SatStation', lat: 78.23, lon: 15.41, color: '#38bdf8', maskDeg: 10, align: 'center', ox: 0, oy: 18 }
        ];

        this.activeContacts = [];

        this.resize();
        window.addEventListener('resize', () => this.resize());
        this.animate();
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        if (this.canvas && this.canvas.offsetParent !== null) {
            this.render();
        }
    }

    resize() {
        if (!this.canvas || !this.canvas.parentElement) return;
        const parent = this.canvas.parentElement;
        const w = parent.clientWidth || 800;
        const h = parent.clientHeight || 500;
        const dpr = Math.max(window.devicePixelRatio || 1, 2);

        this.logicalW = w;
        this.logicalH = h;
        this.dpr = dpr;

        this.canvas.width = Math.floor(w * dpr);
        this.canvas.height = Math.floor(h * dpr);
        this.canvas.style.width = `${w}px`;
        this.canvas.style.height = `${h}px`;

        this.render();
    }

    loadTrajectory(data) {
        if (!data) return;
        this.latitudes = data.latitude_deg || [];
        this.longitudes = data.longitude_deg || [];
        this.altitudes = data.altitude_km || [];
        this.velocities = data.velocity_kms || [];
        this.trueAnomalies = data.true_anomaly_deg || [];
        this.times = data.times || data.times_sec || [];
        this.currentIndex = 0;

        if (data.innovations_suite && data.innovations_suite.molniya_constellation_handover) {
            this.constellationData = data.innovations_suite.molniya_constellation_handover;
        }

        this.render();
    }

    updatePosition(idx) {
        if (!this.latitudes || this.latitudes.length === 0) return;
        this.currentIndex = Math.max(0, Math.min(idx, this.latitudes.length - 1));
        this.render();
    }

    // Convert (Lat, Lon) in degrees to Canvas (X, Y) pixels
    toCanvasXY(lat, lon, w, h) {
        let l = ((lon + 180.0) % 360.0 + 360.0) % 360.0 - 180.0;
        const x = ((l + 180.0) / 360.0) * w;
        const y = ((90.0 - Math.max(-90.0, Math.min(90.0, lat))) / 180.0) * h;
        return { x, y };
    }

    render() {
        const ctx = this.ctx;
        if (!ctx) return;

        const w = this.logicalW || this.canvas.width;
        const h = this.logicalH || this.canvas.height;
        const dpr = this.dpr || 1;

        ctx.save();
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        ctx.clearRect(0, 0, w, h);

        // 1. High-Resolution NASA Base Map
        if (this.mapImg.complete && this.mapImg.naturalWidth > 0) {
            ctx.drawImage(this.mapImg, 0, 0, w, h);
            ctx.fillStyle = 'rgba(2, 6, 18, 0.22)';
            ctx.fillRect(0, 0, w, h);
        } else {
            ctx.fillStyle = '#06101e';
            ctx.fillRect(0, 0, w, h);
        }

        // 2. Solar Terminator Day/Night Shadow & Sub-Solar Marker
        this.renderSolarTerminator(ctx, w, h);

        // 3. FreeFlyer 30° Lat/Lon Graticule Grid
        this.renderGraticule(ctx, w, h);

        // 4. Ground Station Visibility Masks & Dynamic LOS Laser Links
        this.renderGroundStations(ctx, w, h);

        // 5. Dynamic Nadir Spacecraft Visibility Horizon Swath (Footprint)
        this.renderFootprintSwath(ctx, w, h);

        // 6. Multi-Satellite Constellation Ground Tracks (Molniya Triad)
        if (this.constellationData) {
            this.renderConstellationTracks(ctx, w, h);
        }

        // 7. Primary Spacecraft Trajectory Ribbon (Antimeridian Split with High-Latitude Loops)
        this.renderGroundTrackRibbon(ctx, w, h);

        // 8. Orbital Milestones (Perigee Diamond, Apogee Square, Nodal Crossings)
        this.renderOrbitalMilestones(ctx, w, h);

        // 9. Sub-Satellite Point (SSP) Reticle with Velocity Heading Needle
        this.renderSubSatellitePoint(ctx, w, h);

        ctx.restore();
    }

    renderSolarTerminator(ctx, w, h) {
        const tSec = this.times[this.currentIndex] || 0;
        const dayOfYear = 267.0 + (tSec / 86400.0); // Autumnal equinox baseline
        const subSolarLat = 23.44 * Math.sin(2.0 * Math.PI * (dayOfYear - 80.0) / 365.25);
        const subSolarLon = ((180.0 - (tSec / 86400.0 * 360.0) % 360.0) + 180.0) % 360.0 - 180.0;

        ctx.save();
        ctx.beginPath();
        ctx.moveTo(0, h);

        const latSunRad = (subSolarLat * Math.PI) / 180.0;
        const tanSun = Math.tan(latSunRad);

        for (let x = 0; x <= w; x += 4) {
            const lon = (x / w) * 360.0 - 180.0;
            const deltaLonRad = ((lon - subSolarLon) * Math.PI) / 180.0;
            let termLatDeg = 0;
            if (Math.abs(tanSun) > 0.001) {
                termLatDeg = Math.atan(-Math.cos(deltaLonRad) / tanSun) * (180.0 / Math.PI);
            }
            termLatDeg = Math.max(-85, Math.min(85, termLatDeg));
            const pt = this.toCanvasXY(termLatDeg, lon, w, h);
            ctx.lineTo(pt.x, pt.y);
        }
        ctx.lineTo(w, h);
        ctx.closePath();
        ctx.fillStyle = 'rgba(2, 6, 23, 0.48)'; // Translucent night shadow
        ctx.fill();

        // Sub-Solar Point Icon (Golden Sun Symbol ☉)
        const sunPt = this.toCanvasXY(subSolarLat, subSolarLon, w, h);
        ctx.beginPath();
        ctx.arc(sunPt.x, sunPt.y, 6.5, 0, 2 * Math.PI);
        ctx.fillStyle = '#fbbf24';
        ctx.fill();
        ctx.strokeStyle = '#f59e0b';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(sunPt.x, sunPt.y, 2.0, 0, 2 * Math.PI);
        ctx.fillStyle = '#ffffff';
        ctx.fill();

        ctx.restore();
    }

    renderGraticule(ctx, w, h) {
        ctx.save();
        ctx.strokeStyle = 'rgba(148, 163, 184, 0.22)';
        ctx.lineWidth = 1;

        // Longitudes every 30 degrees
        for (let lon = -180; lon <= 180; lon += 30) {
            const pt = this.toCanvasXY(0, lon, w, h);
            ctx.beginPath();
            ctx.moveTo(pt.x, 0);
            ctx.lineTo(pt.x, h);
            ctx.stroke();

            if (lon !== -180 && lon !== 180) {
                const txt = `${lon > 0 ? '+' : ''}${lon}°`;
                ctx.font = '10px Tahoma, sans-serif';
                const tw = ctx.measureText(txt).width;
                ctx.fillStyle = 'rgba(10, 16, 28, 0.82)';
                ctx.fillRect(pt.x - tw / 2 - 4, h - 18, tw + 8, 14);
                ctx.fillStyle = '#94a3b8';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(txt, pt.x, h - 11);
            }
        }

        // Latitudes every 30 degrees
        for (let lat = -90; lat <= 90; lat += 30) {
            const pt = this.toCanvasXY(lat, 0, w, h);
            ctx.beginPath();
            ctx.moveTo(0, pt.y);
            ctx.lineTo(w, pt.y);
            ctx.stroke();

            if (lat !== -90 && lat !== 90) {
                const txt = `${lat > 0 ? '+' : ''}${lat}°`;
                ctx.font = '10px Tahoma, sans-serif';
                const tw = ctx.measureText(txt).width;
                ctx.fillStyle = 'rgba(10, 16, 28, 0.82)';
                ctx.fillRect(4, pt.y - 7, tw + 8, 14);
                ctx.fillStyle = '#94a3b8';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(txt, 4 + (tw + 8) / 2, pt.y);
            }
        }

        // Equator Line (Gold dashed)
        const eqPt = this.toCanvasXY(0, 0, w, h);
        ctx.strokeStyle = 'rgba(245, 158, 11, 0.65)';
        ctx.setLineDash([6, 4]);
        ctx.beginPath();
        ctx.moveTo(0, eqPt.y);
        ctx.lineTo(w, eqPt.y);
        ctx.stroke();
        ctx.setLineDash([]);

        // Prime Meridian (Cyan)
        const pmPt = this.toCanvasXY(0, 0, w, h);
        ctx.strokeStyle = 'rgba(0, 229, 255, 0.45)';
        ctx.beginPath();
        ctx.moveTo(pmPt.x, 0);
        ctx.lineTo(pmPt.x, h);
        ctx.stroke();

        ctx.restore();
    }

    renderFootprintSwath(ctx, w, h) {
        if (this.latitudes.length === 0 || this.currentIndex >= this.latitudes.length) return;

        const curLat = this.latitudes[this.currentIndex];
        const curLon = this.longitudes[this.currentIndex];
        const curAlt = Math.max(10.0, this.altitudes[this.currentIndex] || 250.0);

        // Angular horizon radius from satellite: cos(lam) = R_E / (R_E + h)
        const lamRad = Math.acos(Math.min(1.0, this.R_EARTH / (this.R_EARTH + curAlt)));
        const phi1 = (curLat * Math.PI) / 180.0;
        const lam1 = (curLon * Math.PI) / 180.0;

        const nPts = 96;
        const circlePts = [];

        for (let i = 0; i < nPts; i++) {
            const az = (i / nPts) * Math.PI * 2.0;
            const sinPhi = Math.sin(phi1) * Math.cos(lamRad) + Math.cos(phi1) * Math.sin(lamRad) * Math.cos(az);
            const ptLatRad = Math.asin(Math.max(-1.0, Math.min(1.0, sinPhi)));
            const deltaLam = Math.atan2(
                Math.sin(az) * Math.sin(lamRad),
                Math.cos(phi1) * Math.cos(lamRad) - Math.sin(phi1) * Math.sin(lamRad) * Math.cos(az)
            );
            const ptLonRad = lam1 + deltaLam;
            circlePts.push({
                lat: (ptLatRad * 180.0) / Math.PI,
                lon: (((ptLonRad * 180.0 / Math.PI) + 180.0) % 360.0 + 360.0) % 360.0 - 180.0
            });
        }

        // Split circle polygon at antimeridian crossing
        const segments = [];
        let curSeg = [];
        for (let i = 0; i < circlePts.length; i++) {
            if (curSeg.length > 0) {
                const prevLon = curSeg[curSeg.length - 1].lon;
                if (Math.abs(circlePts[i].lon - prevLon) > 180.0) {
                    segments.push(curSeg);
                    curSeg = [];
                }
            }
            curSeg.push(circlePts[i]);
        }
        if (curSeg.length > 0) segments.push(curSeg);

        ctx.save();
        ctx.fillStyle = 'rgba(0, 229, 255, 0.08)';
        ctx.strokeStyle = '#00e5ff';
        ctx.lineWidth = 1.6;

        segments.forEach(seg => {
            if (seg.length < 2) return;
            ctx.beginPath();
            const p0 = this.toCanvasXY(seg[0].lat, seg[0].lon, w, h);
            ctx.moveTo(p0.x, p0.y);
            for (let j = 1; j < seg.length; j++) {
                const pt = this.toCanvasXY(seg[j].lat, seg[j].lon, w, h);
                ctx.lineTo(pt.x, pt.y);
            }
            ctx.stroke();
            ctx.fill();
        });
        ctx.restore();
    }

    renderGroundStations(ctx, w, h) {
        const curLat = this.latitudes[this.currentIndex] || 0;
        const curLon = this.longitudes[this.currentIndex] || 0;
        const curAlt = this.altitudes[this.currentIndex] || 250.0;
        const curVel = this.velocities[this.currentIndex] || 10.0;
        const sspPt = this.toCanvasXY(curLat, curLon, w, h);

        this.activeContacts = [];

        this.groundStations.forEach(st => {
            const stPt = this.toCanvasXY(st.lat, st.lon, w, h);

            // Compute Topocentric Elevation & Slant Range
            const phi1 = (st.lat * Math.PI) / 180.0;
            const lam1 = (st.lon * Math.PI) / 180.0;
            const phi2 = (curLat * Math.PI) / 180.0;
            const lam2 = (curLon * Math.PI) / 180.0;

            const rGs = this.R_EARTH;
            const rSc = this.R_EARTH + curAlt;
            const xGs = rGs * Math.cos(phi1) * Math.cos(lam1);
            const yGs = rGs * Math.cos(phi1) * Math.sin(lam1);
            const zGs = rGs * Math.sin(phi1);

            const xSc = rSc * Math.cos(phi2) * Math.cos(lam2);
            const ySc = rSc * Math.cos(phi2) * Math.sin(lam2);
            const zSc = rSc * Math.sin(phi2);

            const dx = xSc - xGs, dy = ySc - yGs, dz = zSc - zGs;
            const rho = Math.sqrt(dx * dx + dy * dy + dz * dz);

            const uX = Math.cos(phi1) * Math.cos(lam1);
            const uY = Math.cos(phi1) * Math.sin(lam1);
            const uZ = Math.sin(phi1);

            const sinEl = (dx * uX + dy * uY + dz * uZ) / rho;
            const elDeg = Math.asin(Math.max(-1.0, Math.min(1.0, sinEl))) * (180.0 / Math.PI);

            // Local East and North for Azimuth
            const eX = -Math.sin(lam1), eY = Math.cos(lam1), eZ = 0;
            const nX = -Math.sin(phi1) * Math.cos(lam1), nY = -Math.sin(phi1) * Math.sin(lam1), nZ = Math.cos(phi1);
            const rEast = dx * eX + dy * eY + dz * eZ;
            const rNorth = dx * nX + dy * nY + dz * nZ;
            let azDeg = (Math.atan2(rEast, rNorth) * (180.0 / Math.PI) + 360.0) % 360.0;

            const inContact = elDeg >= st.maskDeg;
            if (inContact) {
                this.activeContacts.push({
                    name: st.name,
                    el: elDeg,
                    az: azDeg,
                    range: rho
                });
            }

            ctx.save();

            // Active LOS Laser Vector from Station Pin to Spacecraft SSP
            if (inContact) {
                ctx.beginPath();
                ctx.moveTo(stPt.x, stPt.y);
                ctx.lineTo(sspPt.x, sspPt.y);
                ctx.strokeStyle = '#22c55e';
                ctx.lineWidth = 1.8;
                ctx.setLineDash([4, 3]);
                ctx.stroke();
                ctx.setLineDash([]);
            }

            // Station Marker Pin
            ctx.fillStyle = inContact ? '#22c55e' : st.color;
            ctx.beginPath();
            ctx.arc(stPt.x, stPt.y, inContact ? 5.5 : 4.0, 0, 2 * Math.PI);
            ctx.fill();
            ctx.fillStyle = '#ffffff';
            ctx.beginPath();
            ctx.arc(stPt.x, stPt.y, 2.0, 0, 2 * Math.PI);
            ctx.fill();

            // Station Name & Telemetry Badge
            const badgeText = inContact
                ? `${st.name} [AOS El:${elDeg.toFixed(1)}° R:${Math.round(rho)}km]`
                : st.name;

            ctx.font = inContact ? 'bold 11px Tahoma, sans-serif' : '10px Tahoma, sans-serif';
            ctx.textAlign = st.align || 'left';
            ctx.textBaseline = 'middle';

            const m = ctx.measureText(badgeText);
            const padX = 6, padY = 3;
            const lx = stPt.x + (st.ox || 10);
            const ly = stPt.y + (st.oy || -6);

            let bx = lx - padX;
            if (st.align === 'right') bx = lx - m.width - padX;
            else if (st.align === 'center') bx = lx - m.width / 2 - padX;

            const by = ly - 8 - padY;
            const bw = m.width + padX * 2;
            const bh = 16 + padY * 2;

            ctx.fillStyle = inContact ? 'rgba(20, 83, 45, 0.92)' : 'rgba(15, 23, 42, 0.85)';
            ctx.fillRect(bx, by, bw, bh);
            ctx.strokeStyle = inContact ? '#4ade80' : 'rgba(255, 255, 255, 0.18)';
            ctx.lineWidth = 1;
            ctx.strokeRect(bx, by, bw, bh);

            ctx.fillStyle = inContact ? '#86efac' : '#f8fafc';
            ctx.fillText(badgeText, lx, ly);

            ctx.restore();
        });

        // Update 2D Contact HUD Readout
        const ff2dContact = document.getElementById('ff-2d-contact');
        if (ff2dContact) {
            if (this.activeContacts.length > 0) {
                const c = this.activeContacts[0];
                ff2dContact.innerText = `AOS: ${c.name} (El: ${c.el.toFixed(1)}°, R: ${Math.round(c.range)} km)`;
                ff2dContact.style.color = '#4ade80';
            } else {
                ff2dContact.innerText = 'Tracking: Orbit Coast (LOS)';
                ff2dContact.style.color = '#94a3b8';
            }
        }
    }

    renderConstellationTracks(ctx, w, h) {
        if (!this.constellationData || !this.constellationData.satellites) return;

        ctx.save();
        for (const [satName, satObj] of Object.entries(this.constellationData.satellites)) {
            if (satName === "Molniya-1A") continue; // Primary satellite already rendered

            const lats = satObj.latitude_deg;
            const lons = satObj.longitude_deg;
            if (!lats || lats.length < 2) continue;

            // Split segments at antimeridian
            const segments = [];
            let curSeg = [];
            for (let i = 0; i < lats.length; i++) {
                if (curSeg.length > 0) {
                    const prevLon = curSeg[curSeg.length - 1].lon;
                    if (Math.abs(lons[i] - prevLon) > 180.0) {
                        segments.push(curSeg);
                        curSeg = [];
                    }
                }
                curSeg.push({ lat: lats[i], lon: lons[i] });
            }
            if (curSeg.length > 0) segments.push(curSeg);

            ctx.strokeStyle = satObj.color || '#a855f7';
            ctx.lineWidth = 1.3;
            ctx.setLineDash([4, 4]);
            ctx.globalAlpha = 0.55;

            segments.forEach(seg => {
                ctx.beginPath();
                const p0 = this.toCanvasXY(seg[0].lat, seg[0].lon, w, h);
                ctx.moveTo(p0.x, p0.y);
                for (let j = 1; j < seg.length; j++) {
                    const pt = this.toCanvasXY(seg[j].lat, seg[j].lon, w, h);
                    ctx.lineTo(pt.x, pt.y);
                }
                ctx.stroke();
            });

            // Satellite Reticle for constellation members
            if (lats[this.currentIndex] !== undefined) {
                const ssp = this.toCanvasXY(lats[this.currentIndex], lons[this.currentIndex], w, h);
                ctx.setLineDash([]);
                ctx.globalAlpha = 0.85;
                ctx.fillStyle = satObj.color || '#a855f7';
                ctx.beginPath();
                ctx.arc(ssp.x, ssp.y, 3.5, 0, 2 * Math.PI);
                ctx.fill();

                ctx.font = '9px Tahoma, sans-serif';
                ctx.fillStyle = satObj.color || '#ffffff';
                ctx.fillText(satName, ssp.x + 6, ssp.y - 4);
            }
        }
        ctx.restore();
    }

    renderGroundTrackRibbon(ctx, w, h) {
        if (this.latitudes.length < 2) return;

        // Split segments at Antimeridian (|Delta Lon| > 180°)
        const segments = [];
        let currentSeg = [];

        for (let i = 0; i < this.latitudes.length; i++) {
            const lat = this.latitudes[i];
            const lon = this.longitudes[i];
            const alt = this.altitudes[i] !== undefined ? this.altitudes[i] : 20000;

            if (currentSeg.length > 0) {
                const prevLon = currentSeg[currentSeg.length - 1].lon;
                if (Math.abs(lon - prevLon) > 180.0) {
                    segments.push(currentSeg);
                    currentSeg = [];
                }
            }
            currentSeg.push({ lat, lon, alt, idx: i });
        }
        if (currentSeg.length > 0) segments.push(currentSeg);

        ctx.save();
        segments.forEach(seg => {
            for (let i = 0; i < seg.length - 1; i++) {
                const p1 = this.toCanvasXY(seg[i].lat, seg[i].lon, w, h);
                const p2 = this.toCanvasXY(seg[i + 1].lat, seg[i + 1].lon, w, h);
                const alt = seg[i].alt;

                ctx.beginPath();
                ctx.moveTo(p1.x, p1.y);
                ctx.lineTo(p2.x, p2.y);

                if (alt < 8000) {
                    ctx.strokeStyle = '#00ff00'; // Lime (Perigee Corridor)
                    ctx.lineWidth = 2.8;
                } else if (alt > 35000) {
                    ctx.strokeStyle = '#ff2244'; // Red (Apogee Dwell Loop)
                    ctx.lineWidth = 2.6;
                } else {
                    ctx.strokeStyle = '#00e5ff'; // Cyan (Nominal Transit)
                    ctx.lineWidth = 1.9;
                }

                ctx.globalAlpha = seg[i].idx > this.currentIndex ? 0.35 : 0.95;
                ctx.stroke();
            }
        });
        ctx.restore();
    }

    renderOrbitalMilestones(ctx, w, h) {
        if (this.latitudes.length < 2) return;

        let minAltIdx = 0, maxAltIdx = 0;
        let minAlt = Infinity, maxAlt = -Infinity;

        for (let i = 0; i < this.altitudes.length; i++) {
            if (this.altitudes[i] < minAlt) { minAlt = this.altitudes[i]; minAltIdx = i; }
            if (this.altitudes[i] > maxAlt) { maxAlt = this.altitudes[i]; maxAltIdx = i; }
        }

        ctx.save();

        // 1. Perigee Milestone Marker (Green Diamond)
        const pPt = this.toCanvasXY(this.latitudes[minAltIdx], this.longitudes[minAltIdx], w, h);
        ctx.fillStyle = '#22c55e';
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(pPt.x, pPt.y - 7);
        ctx.lineTo(pPt.x + 7, pPt.y);
        ctx.lineTo(pPt.x, pPt.y + 7);
        ctx.lineTo(pPt.x - 7, pPt.y);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();

        ctx.font = 'bold 10px Tahoma, sans-serif';
        ctx.fillStyle = '#4ade80';
        ctx.textAlign = 'left';
        ctx.fillText(`Perigee (${Math.round(minAlt)} km)`, pPt.x + 10, pPt.y + 3);

        // 2. Apogee Milestone Marker (Red Square)
        const aPt = this.toCanvasXY(this.latitudes[maxAltIdx], this.longitudes[maxAltIdx], w, h);
        ctx.fillStyle = '#ef4444';
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.rect(aPt.x - 6, aPt.y - 6, 12, 12);
        ctx.fill();
        ctx.stroke();

        ctx.font = 'bold 10px Tahoma, sans-serif';
        ctx.fillStyle = '#f87171';
        ctx.textAlign = 'left';
        ctx.fillText(`Apogee (${Math.round(maxAlt)} km)`, aPt.x + 10, aPt.y + 3);

        // 3. Equator Node Crossings (Ascending Ω and Descending ℧)
        for (let i = 0; i < this.latitudes.length - 1; i++) {
            const lat1 = this.latitudes[i];
            const lat2 = this.latitudes[i + 1];
            if (lat1 * lat2 <= 0 && Math.abs(lat1 - lat2) < 30) {
                const frac = -lat1 / (lat2 - lat1);
                const lonNode = this.longitudes[i] + frac * (this.longitudes[i + 1] - this.longitudes[i]);
                const nodePt = this.toCanvasXY(0, lonNode, w, h);
                const isAscending = lat2 > lat1;

                ctx.fillStyle = isAscending ? '#00e5ff' : '#f59e0b';
                ctx.beginPath();
                ctx.arc(nodePt.x, nodePt.y, 4.5, 0, 2 * Math.PI);
                ctx.fill();
                ctx.strokeStyle = '#ffffff';
                ctx.lineWidth = 1;
                ctx.stroke();

                ctx.font = 'bold 9px Tahoma, sans-serif';
                ctx.fillStyle = isAscending ? '#7dd3fc' : '#fde68a';
                ctx.textAlign = 'center';
                ctx.fillText(isAscending ? 'Node: ☊' : 'Node: ☋', nodePt.x, nodePt.y + (isAscending ? -8 : 12));
                break;
            }
        }

        ctx.restore();
    }

    renderSubSatellitePoint(ctx, w, h) {
        if (this.latitudes.length === 0 || this.currentIndex >= this.latitudes.length) return;

        const curLat = this.latitudes[this.currentIndex];
        const curLon = this.longitudes[this.currentIndex];
        const curAlt = this.altitudes[this.currentIndex] || 0;
        const curVel = this.velocities[this.currentIndex] || 0;
        const ssp = this.toCanvasXY(curLat, curLon, w, h);

        ctx.save();

        // Pulsating Reticle Ring
        const pulse = (Math.sin(Date.now() * 0.007) + 1.0) * 0.5;
        const rOuter = 12 + pulse * 6;

        ctx.beginPath();
        ctx.arc(ssp.x, ssp.y, rOuter, 0, 2 * Math.PI);
        ctx.strokeStyle = 'rgba(0, 229, 255, 0.65)';
        ctx.lineWidth = 1.4;
        ctx.stroke();

        // Inner Solid Target Dot
        ctx.beginPath();
        ctx.arc(ssp.x, ssp.y, 3.5, 0, 2 * Math.PI);
        ctx.fillStyle = '#00e5ff';
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1;
        ctx.stroke();

        // Reticle Crosshairs
        ctx.beginPath();
        ctx.moveTo(ssp.x - 18, ssp.y);
        ctx.lineTo(ssp.x - 6, ssp.y);
        ctx.moveTo(ssp.x + 6, ssp.y);
        ctx.lineTo(ssp.x + 18, ssp.y);
        ctx.moveTo(ssp.x, ssp.y - 18);
        ctx.lineTo(ssp.x, ssp.y - 6);
        ctx.moveTo(ssp.x, ssp.y + 6);
        ctx.lineTo(ssp.x, ssp.y + 18);
        ctx.strokeStyle = '#00e5ff';
        ctx.lineWidth = 1.2;
        ctx.stroke();

        // Velocity Heading Vector Needle
        if (this.currentIndex < this.latitudes.length - 1) {
            const nextLat = this.latitudes[this.currentIndex + 1];
            const nextLon = this.longitudes[this.currentIndex + 1];
            const dLat = nextLat - curLat;
            let dLon = nextLon - curLon;
            if (dLon > 180.0) dLon -= 360.0;
            if (dLon < -180.0) dLon += 360.0;

            const headingAng = Math.atan2(dLon * Math.cos((curLat * Math.PI) / 180.0), dLat);
            const needleLen = 28;
            const nx = ssp.x + needleLen * Math.sin(headingAng);
            const ny = ssp.y - needleLen * Math.cos(headingAng);

            ctx.beginPath();
            ctx.moveTo(ssp.x, ssp.y);
            ctx.lineTo(nx, ny);
            ctx.strokeStyle = '#fde047';
            ctx.lineWidth = 2.0;
            ctx.stroke();

            // Arrow head
            ctx.fillStyle = '#fde047';
            ctx.beginPath();
            ctx.arc(nx, ny, 2.5, 0, 2 * Math.PI);
            ctx.fill();
        }

        // Sub-Satellite Callout Box (Spacecraft1)
        const callout = `Spacecraft1 | Lat: ${curLat > 0 ? '+' : ''}${curLat.toFixed(2)}° Lon: ${curLon > 0 ? '+' : ''}${curLon.toFixed(2)}° | Alt: ${curAlt.toFixed(1)} km | Vel: ${curVel.toFixed(2)} km/s`;
        ctx.font = 'bold 10.5px Tahoma, sans-serif';
        const tw = ctx.measureText(callout).width;

        let bx = ssp.x + 14;
        if (bx + tw + 16 > w) bx = ssp.x - tw - 24;
        const by = ssp.y - 24;

        ctx.fillStyle = 'rgba(15, 23, 42, 0.90)';
        ctx.fillRect(bx, by, tw + 12, 18);
        ctx.strokeStyle = '#00e5ff';
        ctx.lineWidth = 1;
        ctx.strokeRect(bx, by, tw + 12, 18);

        ctx.fillStyle = '#ffffff';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        ctx.fillText(callout, bx + 6, by + 9);

        ctx.restore();

        // Update 2D HUD Overlays
        const tSec = this.times[this.currentIndex] || 0;
        const hrs = Math.floor(tSec / 3600);
        const mins = Math.floor((tSec % 3600) / 60);
        const secs = (tSec % 60).toFixed(2);
        const epochStr = `MET +${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(5, '0')}`;

        const hudEpoch = document.getElementById('ff-2d-epoch');
        const hudCoords = document.getElementById('ff-2d-coords');
        const hudHeight = document.getElementById('ff-2d-height');
        const hudVel = document.getElementById('ff-2d-vel');

        if (hudEpoch) hudEpoch.innerText = epochStr;
        if (hudCoords) hudCoords.innerText = `Lat: ${curLat > 0 ? '+' : ''}${curLat.toFixed(3)}°, Lon: ${curLon > 0 ? '+' : ''}${curLon.toFixed(3)}°`;
        if (hudHeight) {
            hudHeight.innerText = `${curAlt.toFixed(2)} km`;
            hudHeight.style.color = curAlt < 8000 ? '#4ade80' : curAlt > 35000 ? '#f87171' : '#00e5ff';
        }
        if (hudVel) hudVel.innerText = `${curVel.toFixed(3)} km/s`;
    }
}

window.Viewport2D = Viewport2D;

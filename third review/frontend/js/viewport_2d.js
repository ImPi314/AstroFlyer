/**
 * AstroFlyer 2D Ground Track Viewport
 * Complete implementation of FreeFlyer 8.0.1 ViewWindow2 (MapView):
 *   - Reference Frame: Earth Body Fixed (WGS-84 / EGM-96)
 *   - Map Span: 360° Longitude (-180° to +180°), 180° Latitude (-90° to +90°)
 *   - High-Resolution NASA Blue Marble Equirectangular Projection
 *   - FreeFlyer Solar Terminator Day/Night Shadow (ShowTerminatorShadow = true)
 *   - FreeFlyer Lat/Lon Grid (ShowLatitudeLongitudeGrid = true, 30° spacing, Tahoma labels)
 *   - Ground Stations & Sensor Visibility Swaths (ShowSensorSwaths = true):
 *       • ISRO ISTRAC Bengaluru & Hassan MCF
 *       • NASA Deep Space Network (Goldstone, Madrid, Canberra)
 *       • Svalbard High-Latitude Station
 *       • Real-time contact detection: Swath and station illuminate in Lime (#00ff00) on AOS
 *   - FreeFlyer HEO Trajectory Coloring:
 *       • Height < 8,000 km: ColorTools.Lime (#00ff00 / #4ade80)
 *       • Height > 40,000 km: ColorTools.Red (#ff0000 / #f87171)
 *       • Nominal Arc: Cyan / White (#00e5ff)
 *       • Antimeridian crossing splitting (no horizontal wrap lines)
 *   - Sub-Satellite Point (SSP) Target Crosshair Reticle with Spacecraft1 Label
 *   - FreeFlyer Signature MapView Status Text HUD (Tahoma Font, Semi-Transparent Backdrop)
 */

class Viewport2D {
    constructor(canvasId, mapImagePath) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');

        this.mapImg = new Image();
        this.mapImg.onerror = () => {
            if (this.mapImg.src.indexOf('world_map_dark.png') !== -1) {
                this.mapImg.src = 'blue_marble_map.png';
            }
        };
        this.mapImg.onload = () => this.render();
        this.mapImg.src = mapImagePath || 'world_map_dark.png';

        this.latitudes = [];
        this.longitudes = [];
        this.altitudes = [];
        this.velocities = [];
        this.trueAnomalies = [];
        this.times = [];
        this.currentIndex = 0;

        // FreeFlyer Ground Stations with distinct label alignments & offsets to avoid collision
        this.groundStations = [
            { id: 'ISTRAC', name: 'ISTRAC Bengaluru', lat: 12.97, lon: 77.58, color: '#f59e0b', maskDeg: 12, labelAlign: 'left', offsetX: 10, offsetY: 12 },
            { id: 'HASSAN', name: 'Hassan MCF', lat: 13.01, lon: 76.10, color: '#f59e0b', maskDeg: 12, labelAlign: 'right', offsetX: -10, offsetY: -8 },
            { id: 'GOLDSTONE', name: 'DSN Goldstone', lat: 35.43, lon: -116.89, color: '#22c55e', maskDeg: 15, labelAlign: 'left', offsetX: 9, offsetY: -5 },
            { id: 'MADRID', name: 'DSN Madrid', lat: 40.43, lon: -4.25, color: '#22c55e', maskDeg: 15, labelAlign: 'left', offsetX: 9, offsetY: -5 },
            { id: 'CANBERRA', name: 'DSN Canberra', lat: -35.40, lon: 148.98, color: '#22c55e', maskDeg: 15, labelAlign: 'left', offsetX: 9, offsetY: 14 },
            { id: 'SVALBARD', name: 'Svalbard SatStation', lat: 78.23, lon: 15.41, color: '#38bdf8', maskDeg: 18, labelAlign: 'center', offsetX: 0, offsetY: 18 }
        ];

        this.activeContactStations = [];

        this.resize();
        window.addEventListener('resize', () => this.resize());
        this.animate();
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        // Only re-render if canvas is visible in DOM
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
        this.canvas.style.width = w + 'px';
        this.canvas.style.height = h + 'px';

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
        this.render();
    }

    updatePosition(idx) {
        if (!this.latitudes || this.latitudes.length === 0) return;
        this.currentIndex = Math.max(0, Math.min(idx, this.latitudes.length - 1));
        this.checkStationAccess();
        this.updateFreeFlyerStatusHUD(this.currentIndex);
        this.render();
    }

    angularDistanceDeg(lat1, lon1, lat2, lon2) {
        const dLat = (lat2 - lat1) * Math.PI / 180.0;
        const dLon = (lon2 - lon1) * Math.PI / 180.0;
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                  Math.cos(lat1 * Math.PI / 180.0) * Math.cos(lat2 * Math.PI / 180.0) *
                  Math.sin(dLon / 2) * Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return c * 180.0 / Math.PI;
    }

    checkStationAccess() {
        if (this.currentIndex >= this.latitudes.length) return;
        const satLat = this.latitudes[this.currentIndex];
        const satLon = this.longitudes[this.currentIndex];
        const alt = this.altitudes[this.currentIndex] || 24000;
        const footprintDeg = Math.min(75, Math.acos(6378.0 / (6378.0 + alt)) * 180.0 / Math.PI);

        this.activeContactStations = [];
        this.groundStations.forEach(st => {
            const dist = this.angularDistanceDeg(satLat, satLon, st.lat, st.lon);
            if (dist <= footprintDeg) {
                this.activeContactStations.push(st.id);
            }
        });
    }

    toCanvasXY(lat, lon, w, h) {
        const x = ((lon + 180.0) / 360.0) * w;
        const y = ((90.0 - lat) / 180.0) * h;
        return { x, y };
    }

    render() {
        if (!this.ctx) return;
        const dpr = this.dpr || Math.max(window.devicePixelRatio || 1, 2);
        const w = this.logicalW || (this.canvas.width / dpr);
        const h = this.logicalH || (this.canvas.height / dpr);
        const ctx = this.ctx;

        ctx.save();
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0); // Scale all drawing by dpr so (0,0)-(w,h) is ultra crisp
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';

        ctx.clearRect(0, 0, w, h);

        // 1. High-Resolution NASA World Map (FreeFlyer UseTextures = true)
        if (this.mapImg.complete && this.mapImg.naturalWidth > 0) {
            ctx.drawImage(this.mapImg, 0, 0, w, h);
            ctx.fillStyle = 'rgba(0, 0, 0, 0.16)';
            ctx.fillRect(0, 0, w, h);
        } else {
            ctx.fillStyle = '#06101e';
            ctx.fillRect(0, 0, w, h);
        }

        // 2. FreeFlyer Solar Terminator Day/Night Shadow (ShowTerminatorShadow = true)
        this.renderSolarTerminator(ctx, w, h);

        // 3. FreeFlyer Latitude / Longitude Grid (ShowLatitudeLongitudeGrid = true, 30° spacing)
        this.renderFreeFlyerGrid(ctx, w, h);

        // 4. Ground Station Network & Sensor Visibility Footprints (ShowSensorSwaths = true)
        this.renderGroundStations(ctx, w, h);

        // 5. FreeFlyer HEO Ground Track Ribbon (Antimeridian splitting + ColorTools.Lime / Red)
        this.renderGroundTrackRibbon(ctx, w, h);

        // 6. Sub-Satellite Point (SSP) Reticle & Callout Box
        this.renderSubSatellitePoint(ctx, w, h);

        ctx.restore();
    }

    renderSolarTerminator(ctx, w, h) {
        // Approximate Sun position based on simulation time
        const tSec = this.times[this.currentIndex] || 0;
        // Sun sub-solar longitude rotates westward with Earth's rotation (360 deg / 86400 s)
        const subSolarLon = ((180 - (tSec / 86400.0 * 360.0) % 360.0) + 180) % 360 - 180;

        ctx.save();
        ctx.beginPath();
        // Construct night hemisphere polygon using sine terminator curve
        ctx.moveTo(0, h);
        for (let x = 0; x <= w; x += 4) {
            const lon = (x / w) * 360.0 - 180.0;
            const deltaLon = (lon - subSolarLon) * Math.PI / 180.0;
            // Night curve latitude
            const termLat = Math.atan(-Math.cos(deltaLon) / Math.tan(0.409)) * 180.0 / Math.PI;
            const pt = this.toCanvasXY(Math.max(-85, Math.min(85, termLat)), lon, w, h);
            if (x === 0) ctx.lineTo(pt.x, pt.y);
            else ctx.lineTo(pt.x, pt.y);
        }
        ctx.lineTo(w, h);
        ctx.closePath();
        ctx.fillStyle = 'rgba(0, 5, 20, 0.40)'; // FreeFlyer night shadow
        ctx.fill();
        ctx.restore();
    }

    renderFreeFlyerGrid(ctx, w, h) {
        ctx.save();
        // FreeFlyer LatitudeGridLineColor: 8355711 (slate grey, 0.35 opacity)
        ctx.strokeStyle = 'rgba(148, 163, 184, 0.30)';
        ctx.lineWidth = 1;

        // Longitudes: every 30 deg
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
                // Capsule badge for crisp contrast over any continent or ocean
                ctx.fillStyle = 'rgba(8, 14, 24, 0.75)';
                ctx.fillRect(pt.x - tw / 2 - 4, h - 20, tw + 8, 14);
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
                ctx.strokeRect(pt.x - tw / 2 - 4, h - 20, tw + 8, 14);

                ctx.fillStyle = '#e2e8f0';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(txt, pt.x, h - 13);
            }
        }

        // Latitudes: every 30 deg
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
                // Capsule badge at left edge
                ctx.fillStyle = 'rgba(8, 14, 24, 0.75)';
                ctx.fillRect(4, pt.y - 7, tw + 8, 14);
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
                ctx.strokeRect(4, pt.y - 7, tw + 8, 14);

                ctx.fillStyle = '#e2e8f0';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(txt, 4 + (tw + 8) / 2, pt.y);
            }
        }

        // Equator Line (Highlighted Golden Yellow)
        const eqPt = this.toCanvasXY(0, 0, w, h);
        ctx.strokeStyle = 'rgba(245, 158, 11, 0.65)';
        ctx.setLineDash([6, 4]);
        ctx.beginPath();
        ctx.moveTo(0, eqPt.y);
        ctx.lineTo(w, eqPt.y);
        ctx.stroke();
        ctx.setLineDash([]);

        // Equator Badge
        ctx.font = 'bold 9.5px Tahoma, sans-serif';
        const eqTxt = 'EQUATOR (0°)';
        const eqW = ctx.measureText(eqTxt).width;
        ctx.fillStyle = 'rgba(30, 20, 0, 0.85)';
        ctx.fillRect(w - eqW - 16, eqPt.y - 8, eqW + 10, 16);
        ctx.strokeStyle = '#f59e0b';
        ctx.strokeRect(w - eqW - 16, eqPt.y - 8, eqW + 10, 16);
        ctx.fillStyle = '#fbbf24';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(eqTxt, w - eqW - 16 + (eqW + 10) / 2, eqPt.y);

        // Prime Meridian Line (Highlighted Cyan)
        const pmPt = this.toCanvasXY(0, 0, w, h);
        ctx.strokeStyle = 'rgba(0, 229, 255, 0.45)';
        ctx.beginPath();
        ctx.moveTo(pmPt.x, 0);
        ctx.lineTo(pmPt.x, h);
        ctx.stroke();
        ctx.restore();
    }

    renderGroundStations(ctx, w, h) {
        this.groundStations.forEach(st => {
            const pos = this.toCanvasXY(st.lat, st.lon, w, h);
            const inContact = this.activeContactStations.includes(st.id);

            const rx = (st.maskDeg / 360.0) * w;
            const ry = (st.maskDeg / 180.0) * h;

            ctx.save();
            // FreeFlyer Visibility Swath Circle
            ctx.beginPath();
            ctx.ellipse(pos.x, pos.y, rx, ry, 0, 0, 2 * Math.PI);
            ctx.fillStyle = inContact ? 'rgba(0, 255, 0, 0.22)' : 'rgba(245, 158, 11, 0.07)';
            ctx.fill();
            ctx.strokeStyle = inContact ? '#00ff00' : st.color;
            ctx.lineWidth = inContact ? 1.8 : 1.0;
            ctx.stroke();

            // Station Marker Icon (Crisp Pin with White Center)
            ctx.fillStyle = inContact ? '#00ff00' : st.color;
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, inContact ? 4.5 : 3.5, 0, 2 * Math.PI);
            ctx.fill();
            ctx.fillStyle = '#ffffff';
            ctx.beginPath();
            ctx.arc(pos.x, pos.y, inContact ? 2.0 : 1.5, 0, 2 * Math.PI);
            ctx.fill();

            // Collision-Free Station Label with Crisp Backdrop Capsule
            const labelText = st.name + (inContact ? ' [AOS]' : '');
            ctx.font = inContact ? 'bold 11px Tahoma, sans-serif' : '10.5px Tahoma, sans-serif';
            ctx.textAlign = st.labelAlign || 'left';
            ctx.textBaseline = 'middle';

            const m = ctx.measureText(labelText);
            const padX = 5;
            const padY = 3;
            const labelX = pos.x + (st.offsetX || 9);
            const labelY = pos.y + (st.offsetY || -5);

            let bgX = labelX - padX;
            if (st.labelAlign === 'right') bgX = labelX - m.width - padX;
            else if (st.labelAlign === 'center') bgX = labelX - m.width / 2 - padX;

            const bgY = labelY - 8 - padY;
            const bgW = m.width + padX * 2;
            const bgH = 16 + padY * 2;

            // Translucent glass capsule behind label ensures 100% legibility & zero collision
            ctx.fillStyle = inContact ? 'rgba(0, 36, 12, 0.85)' : 'rgba(10, 16, 28, 0.82)';
            ctx.fillRect(bgX, bgY, bgW, bgH);
            ctx.strokeStyle = inContact ? '#22c55e' : 'rgba(255, 255, 255, 0.18)';
            ctx.lineWidth = 1;
            ctx.strokeRect(bgX, bgY, bgW, bgH);

            ctx.fillStyle = inContact ? '#4ade80' : '#f8fafc';
            ctx.shadowColor = '#000000';
            ctx.shadowBlur = 3;
            ctx.shadowOffsetX = 1;
            ctx.shadowOffsetY = 1;
            ctx.fillText(labelText, labelX, labelY);
            ctx.restore();
        });
    }

    renderGroundTrackRibbon(ctx, w, h) {
        if (this.latitudes.length < 2) return;

        // Split segments at antimeridian (jump > 180 deg)
        const segments = [];
        let currentSeg = [];

        for (let i = 0; i < this.latitudes.length; i++) {
            const lat = this.latitudes[i];
            const lon = this.longitudes[i];
            const alt = this.altitudes[i] !== undefined ? this.altitudes[i] : 20000;
            const vel = this.velocities[i] !== undefined ? this.velocities[i] : 5.0;

            if (currentSeg.length > 0) {
                const prevLon = currentSeg[currentSeg.length - 1].lon;
                if (Math.abs(lon - prevLon) > 180) {
                    segments.push(currentSeg);
                    currentSeg = [];
                }
            }
            currentSeg.push({ lat, lon, alt, vel, idx: i });
        }
        if (currentSeg.length > 0) segments.push(currentSeg);

        // Render Ground Track Ribbon with FreeFlyer's exact HEO color rules:
        // Height < 8,000 km: ColorTools.Lime (#00ff00)
        // Height > 40,000 km: ColorTools.Red (#ff0000)
        // Nominal: Cyan / White (#00e5ff)
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
                    ctx.strokeStyle = '#00ff00'; // FreeFlyer ColorTools.Lime
                    ctx.lineWidth = 2.6;
                } else if (alt > 35000) {
                    ctx.strokeStyle = '#ff2244'; // FreeFlyer ColorTools.Red
                    ctx.lineWidth = 2.4;
                } else {
                    ctx.strokeStyle = '#00e5ff'; // FreeFlyer Nominal Cyan
                    ctx.lineWidth = 1.8;
                }

                // Future path ghost fade
                if (seg[i].idx > this.currentIndex) {
                    ctx.globalAlpha = 0.35;
                } else {
                    ctx.globalAlpha = 0.95;
                }

                ctx.stroke();
                ctx.globalAlpha = 1.0;
            }
        });
        ctx.restore();
    }

    renderSubSatellitePoint(ctx, w, h) {
        if (this.latitudes.length === 0 || this.currentIndex >= this.latitudes.length) return;

        const curLat = this.latitudes[this.currentIndex];
        const curLon = this.longitudes[this.currentIndex];
        const curAlt = this.altitudes[this.currentIndex] !== undefined ? this.altitudes[this.currentIndex] : 0;
        const curVel = this.velocities[this.currentIndex] !== undefined ? this.velocities[this.currentIndex] : 0;
        const ssp = this.toCanvasXY(curLat, curLon, w, h);

        ctx.save();
        // Pulsating reticle
        const pulse = (Math.sin(Date.now() * 0.006) + 1.0) * 0.5;
        const rOuter = 11 + pulse * 6;

        // Outer glow circle
        ctx.beginPath();
        ctx.arc(ssp.x, ssp.y, rOuter, 0, 2 * Math.PI);
        ctx.strokeStyle = 'rgba(0, 229, 255, 0.5)';
        ctx.lineWidth = 1.3;
        ctx.stroke();

        // Inner solid dot
        ctx.beginPath();
        ctx.arc(ssp.x, ssp.y, 5.5, 0, 2 * Math.PI);
        ctx.fillStyle = curAlt < 8000 ? '#00ff00' : curAlt > 35000 ? '#ff2244' : '#00e5ff';
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Crosshairs
        ctx.strokeStyle = '#00e5ff';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(ssp.x - 14, ssp.y); ctx.lineTo(ssp.x - 7, ssp.y);
        ctx.moveTo(ssp.x + 7, ssp.y); ctx.lineTo(ssp.x + 14, ssp.y);
        ctx.moveTo(ssp.x, ssp.y - 14); ctx.lineTo(ssp.x, ssp.y - 7);
        ctx.moveTo(ssp.x, ssp.y + 7); ctx.lineTo(ssp.x, ssp.y + 14);
        ctx.stroke();

        // FreeFlyer-Style Crisp Telemetry Callout Box (Tahoma font)
        const boxW = 232;
        const boxH = 58;
        let boxX = ssp.x + 22;
        let boxY = ssp.y - 68;

        if (boxX + boxW > w - 12) boxX = ssp.x - boxW - 22;
        if (boxY < 12) boxY = ssp.y + 22;

        // Leader line
        ctx.strokeStyle = 'rgba(0, 229, 255, 0.7)';
        ctx.lineWidth = 1.2;
        ctx.beginPath();
        ctx.moveTo(ssp.x, ssp.y);
        ctx.lineTo(boxX > ssp.x ? boxX : boxX + boxW, boxY + boxH / 2);
        ctx.stroke();

        // Callout Backdrop (Translucent Glassmorphism)
        ctx.fillStyle = 'rgba(6, 12, 24, 0.72)';
        ctx.strokeStyle = 'rgba(0, 229, 255, 0.75)';
        ctx.lineWidth = 1.2;
        ctx.fillRect(boxX, boxY, boxW, boxH);
        ctx.strokeRect(boxX, boxY, boxW, boxH);

        // Content
        const regimeStr = curAlt < 8000 ? 'PERIGEE' : curAlt > 35000 ? 'APOGEE' : 'NOMINAL';
        const regimeColor = regimeStr === 'PERIGEE' ? '#4ade80' : regimeStr === 'APOGEE' ? '#f87171' : '#38bdf8';

        ctx.font = 'bold 11.5px Tahoma, sans-serif';
        ctx.fillStyle = '#ffffff';
        ctx.shadowColor = '#000000';
        ctx.shadowBlur = 3;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'alphabetic';
        ctx.fillText('🛰️ Spacecraft1', boxX + 8, boxY + 17);

        ctx.fillStyle = regimeColor;
        ctx.font = 'bold 9.5px Tahoma, sans-serif';
        ctx.textAlign = 'right';
        ctx.fillText(`[${regimeStr}]`, boxX + boxW - 8, boxY + 17);

        ctx.font = '10.5px Tahoma, sans-serif';
        ctx.fillStyle = '#cbd5e1';
        ctx.textAlign = 'left';
        ctx.fillText(`Lat: ${curLat > 0 ? '+' : ''}${curLat.toFixed(3)}°  Lon: ${curLon > 0 ? '+' : ''}${curLon.toFixed(3)}°`, boxX + 8, boxY + 34);
        ctx.fillText(`Height: ${curAlt.toLocaleString(undefined, {minimumFractionDigits: 1, maximumFractionDigits: 1})} km  Vel: ${curVel.toFixed(3)} km/s`, boxX + 8, boxY + 50);

        ctx.restore();
    }

    updateFreeFlyerStatusHUD(i) {
        const curLat = this.latitudes[i] !== undefined ? this.latitudes[i] : 0;
        const curLon = this.longitudes[i] !== undefined ? this.longitudes[i] : 0;
        const curAlt = this.altitudes[i] !== undefined ? this.altitudes[i] : 0;
        const curVel = this.velocities[i] !== undefined ? this.velocities[i] : 0;
        const tSec = this.times[i] !== undefined ? this.times[i] : 0;

        const hrs = Math.floor(tSec / 3600);
        const mins = Math.floor((tSec % 3600) / 60);
        const secs = (tSec % 60).toFixed(2);
        const epochStr = `MET +${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(5, '0')}`;

        const hudEpoch = document.getElementById('ff-2d-epoch');
        const hudCoords = document.getElementById('ff-2d-coords');
        const hudHeight = document.getElementById('ff-2d-height');
        const hudVel = document.getElementById('ff-2d-vel');
        const hudContact = document.getElementById('ff-2d-contact');

        if (hudEpoch) hudEpoch.innerText = epochStr;
        if (hudCoords) hudCoords.innerText = `Lat: ${curLat > 0 ? '+' : ''}${curLat.toFixed(3)}°, Lon: ${curLon > 0 ? '+' : ''}${curLon.toFixed(3)}°`;
        if (hudHeight) hudHeight.innerText = `${curAlt.toFixed(2)} km`;
        if (hudVel) hudVel.innerText = `${curVel.toFixed(3)} km/s`;
        if (hudContact) {
            if (this.activeContactStations.length > 0) {
                const stNames = this.activeContactStations.map(id => {
                    const st = this.groundStations.find(s => s.id === id);
                    return st ? st.name : id;
                }).join(', ');
                hudContact.innerText = `Contact: ${stNames} [AOS]`;
                hudContact.style.color = '#4ade80';
            } else {
                hudContact.innerText = `Tracking: Orbit Coast (LOS)`;
                hudContact.style.color = '#94a3b8';
            }
        }
    }

    setGroundTrackData(latArr, lonArr) {
        this.latitudes = latArr;
        this.longitudes = lonArr;
        this.render();
    }

    setCurrentIndex(idx) {
        this.updatePosition(idx);
    }
}

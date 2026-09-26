/**
 * AstroFlyer 2D Geodetic Ground Track Viewport
 * NASA Blue Marble Map Projection with Analytical Antimeridian Boundary-Crossing Splitting.
 */

class Viewport2D {
    constructor(canvasId, mapImagePath) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        
        this.mapImg = new Image();
        this.mapImg.src = mapImagePath || 'blue_marble_map.png';
        this.mapImg.onload = () => this.render();

        this.latitudes = [];
        this.longitudes = [];
        this.currentIndex = 0;

        this.resize();
        window.addEventListener('resize', () => this.resize());
    }

    resize() {
        if (!this.canvas) return;
        this.canvas.width = this.canvas.parentElement.clientWidth || 800;
        this.canvas.height = this.canvas.parentElement.clientHeight || 500;
        this.render();
    }

    setGroundTrackData(latArr, lonArr) {
        this.latitudes = latArr;
        this.longitudes = lonArr;
        this.render();
    }

    setCurrentIndex(idx) {
        this.currentIndex = Math.max(0, Math.min(idx, this.latitudes.length - 1));
        this.render();
    }

    toCanvasXY(lat, lon, w, h) {
        const x = ((lon + 180.0) / 360.0) * w;
        const y = ((90.0 - lat) / 180.0) * h;
        return { x, y };
    }

    render() {
        if (!this.ctx) return;
        const w = this.canvas.width;
        const h = this.canvas.height;
        const ctx = this.ctx;

        ctx.clearRect(0, 0, w, h);

        // 1. Render Map Background
        if (this.mapImg.complete && this.mapImg.naturalWidth !== 0) {
            ctx.drawImage(this.mapImg, 0, 0, w, h);
        } else {
            ctx.fillStyle = '#0b131e';
            ctx.fillRect(0, 0, w, h);
        }

        // 2. Draw Grid Lines (Lat/Lon)
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
        ctx.lineWidth = 0.8;

        for (let lon = -180; lon <= 180; lon += 30) {
            const pt = this.toCanvasXY(0, lon, w, h);
            ctx.beginPath(); ctx.moveTo(pt.x, 0); ctx.lineTo(pt.x, h); ctx.stroke();
        }
        for (let lat = -90; lat <= 90; lat += 30) {
            const pt = this.toCanvasXY(lat, 0, w, h);
            ctx.beginPath(); ctx.moveTo(0, pt.y); ctx.lineTo(w, pt.y); ctx.stroke();
        }

        // Equator & Prime Meridian Highlight
        const eq = this.toCanvasXY(0, 0, w, h);
        ctx.strokeStyle = 'rgba(2, 132, 199, 0.4)';
        ctx.lineWidth = 1.2;
        ctx.beginPath(); ctx.moveTo(0, eq.y); ctx.lineTo(w, eq.y); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(eq.x, 0); ctx.lineTo(eq.x, h); ctx.stroke();

        if (this.latitudes.length === 0) return;

        // 3. Render Ground Track Trail with Antimeridian Splitting
        ctx.lineWidth = 2.0;
        ctx.strokeStyle = '#0284c7';
        ctx.beginPath();

        let lastPt = null;
        for (let i = 0; i <= this.currentIndex; i++) {
            const lat = this.latitudes[i];
            const lon = this.longitudes[i];
            const pt = this.toCanvasXY(lat, lon, w, h);

            if (i === 0) {
                ctx.moveTo(pt.x, pt.y);
            } else {
                const prevLon = this.longitudes[i - 1];
                // Check antimeridian wrap-around (|Δλ| > 180°)
                if (Math.abs(lon - prevLon) > 180.0) {
                    ctx.stroke();
                    ctx.beginPath();
                    ctx.moveTo(pt.x, pt.y);
                } else {
                    ctx.lineTo(pt.x, pt.y);
                }
            }
            lastPt = pt;
        }
        ctx.stroke();

        // 4. Draw Sub-Satellite Marker
        if (lastPt) {
            ctx.beginPath();
            ctx.arc(lastPt.x, lastPt.y, 7, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(239, 68, 68, 0.4)';
            ctx.fill();

            ctx.beginPath();
            ctx.arc(lastPt.x, lastPt.y, 4, 0, Math.PI * 2);
            ctx.fillStyle = '#ef4444';
            ctx.fill();
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 1.2;
            ctx.stroke();

            ctx.fillStyle = '#ffffff';
            ctx.font = '11px Geist Mono, monospace';
            const curLat = this.latitudes[this.currentIndex].toFixed(2);
            const curLon = this.longitudes[this.currentIndex].toFixed(2);
            ctx.fillText(`SSP (${curLat}°, ${curLon}°)`, lastPt.x + 10, lastPt.y - 6);
        }
    }
}

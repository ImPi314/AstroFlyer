/**
 * AstroFlyer 3D Inertial Celestial Orbit Viewport
 * Hardware-Accelerated Canvas 3D Orbital Studio with ECI Axes, Orbit Ribbon, and Mouse Camera Controls.
 */

class Viewport3D {
    constructor(canvasId) {
        self.canvas = document.getElementById(canvasId);
        if (!self.canvas) return;
        this.canvas = self.canvas;
        this.ctx = this.canvas.getContext('2d');
        
        // Camera Angles
        this.rotX = 0.4;
        this.rotY = 0.6;
        this.zoom = 1.0;
        this.isDragging = false;
        this.lastMouseX = 0;
        this.lastMouseY = 0;
        
        // Trajectory Data
        this.trajectory = [];
        this.currentIndex = 0;
        
        this.initMouseControls();
        this.resize();
        window.addEventListener('resize', () => this.resize());
    }

    resize() {
        if (!this.canvas) return;
        this.canvas.width = this.canvas.parentElement.clientWidth || 800;
        this.canvas.height = this.canvas.parentElement.clientHeight || 500;
        this.render();
    }

    initMouseControls() {
        this.canvas.addEventListener('mousedown', (e) => {
            this.isDragging = true;
            this.lastMouseX = e.clientX;
            this.lastMouseY = e.clientY;
        });

        window.addEventListener('mouseup', () => {
            this.isDragging = false;
        });

        this.canvas.addEventListener('mousemove', (e) => {
            if (!this.isDragging) return;
            const dx = e.clientX - this.lastMouseX;
            const dy = e.clientY - this.lastMouseY;
            this.rotY += dx * 0.008;
            this.rotX += dy * 0.008;
            this.lastMouseX = e.clientX;
            this.lastMouseY = e.clientY;
            this.render();
        });

        this.canvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            this.zoom *= e.deltaY > 0 ? 0.9 : 1.1;
            this.zoom = Math.max(0.2, Math.min(this.zoom, 5.0));
            this.render();
        });
    }

    setPresetCamera(view) {
        if (view === 'isometric') { this.rotX = 0.4; this.rotY = 0.6; }
        else if (view === 'polar') { this.rotX = 1.57; this.rotY = 0.0; }
        else if (view === 'equatorial') { this.rotX = 0.0; this.rotY = 0.0; }
        this.render();
    }

    setTrajectoryData(data) {
        this.trajectory = data;
        this.render();
    }

    setCurrentIndex(idx) {
        this.currentIndex = Math.max(0, Math.min(idx, this.trajectory.length - 1));
        this.render();
    }

    project(x, y, z, cx, cy, scale) {
        // Rotate Y
        let x1 = x * Math.cos(this.rotY) - z * Math.sin(this.rotY);
        let z1 = x * Math.sin(this.rotY) + z * Math.cos(this.rotY);
        let y1 = y;

        // Rotate X
        let y2 = y1 * Math.cos(this.rotX) - z1 * Math.sin(this.rotX);
        let z2 = y1 * Math.sin(this.rotX) + z1 * Math.cos(this.rotX);
        let x2 = x1;

        return {
            px: cx + x2 * scale * this.zoom,
            py: cy - y2 * scale * this.zoom,
            depth: z2
        };
    }

    render() {
        if (!this.ctx) return;
        const w = this.canvas.width;
        const h = this.canvas.height;
        const cx = w / 2;
        const cy = h / 2;
        const scale = Math.min(w, h) / 100000.0;

        const ctx = this.ctx;
        ctx.clearRect(0, 0, w, h);

        // Background Space Gradient
        const bgGrad = ctx.createRadialGradient(cx, cy, 50, cx, cy, Math.max(w, h));
        bgGrad.addColorStop(0, '#0c131d');
        bgGrad.addColorStop(1, '#05080c');
        ctx.fillStyle = bgGrad;
        ctx.fillRect(0, 0, w, h);

        // 1. Draw ECI Reference Axes
        const axisLen = 12000.0 * 1000.0;
        const orig = this.project(0, 0, 0, cx, cy, scale);
        const xAxis = this.project(axisLen, 0, 0, cx, cy, scale);
        const yAxis = this.project(0, axisLen, 0, cx, cy, scale);
        const zAxis = this.project(0, 0, axisLen, cx, cy, scale);

        ctx.lineWidth = 1.5;
        // X-Axis (Red / Vernal Equinox)
        ctx.strokeStyle = '#ef4444'; ctx.beginPath(); ctx.moveTo(orig.px, orig.py); ctx.lineTo(xAxis.px, xAxis.py); ctx.stroke();
        ctx.fillStyle = '#ef4444'; ctx.fillText('+X (♈)', xAxis.px + 4, xAxis.py);

        // Y-Axis (Green)
        ctx.strokeStyle = '#22c55e'; ctx.beginPath(); ctx.moveTo(orig.px, orig.py); ctx.lineTo(yAxis.px, yAxis.py); ctx.stroke();
        ctx.fillStyle = '#22c55e'; ctx.fillText('+Y', yAxis.px + 4, yAxis.py);

        // Z-Axis (Blue / North)
        ctx.strokeStyle = '#3b82f6'; ctx.beginPath(); ctx.moveTo(orig.px, orig.py); ctx.lineTo(zAxis.px, zAxis.py); ctx.stroke();
        ctx.fillStyle = '#3b82f6'; ctx.fillText('+Z (North)', zAxis.px + 4, zAxis.py);

        // 2. Draw Earth Sphere
        const rEarthPixels = 6371000.0 * scale * this.zoom;
        const earthGrad = ctx.createRadialGradient(
            orig.px - rEarthPixels * 0.3, orig.py - rEarthPixels * 0.3, rEarthPixels * 0.1,
            orig.px, orig.py, rEarthPixels
        );
        earthGrad.addColorStop(0, '#38bdf8');
        earthGrad.addColorStop(0.6, '#1d4ed8');
        earthGrad.addColorStop(1, '#0f172a');

        ctx.beginPath();
        ctx.arc(orig.px, orig.py, Math.max(2, rEarthPixels), 0, Math.PI * 2);
        ctx.fillStyle = earthGrad;
        ctx.fill();
        ctx.strokeStyle = '#0284c7';
        ctx.lineWidth = 1;
        ctx.stroke();

        if (this.trajectory.length === 0) return;

        // 3. Draw Orbit Trajectory Ribbon
        ctx.beginPath();
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = 'rgba(56, 189, 248, 0.6)';

        for (let i = 0; i < this.trajectory.length; i++) {
            const pos = this.trajectory[i];
            const pt = this.project(pos[0], pos[1], pos[2], cx, cy, scale);
            if (i === 0) ctx.moveTo(pt.px, pt.py);
            else ctx.lineTo(pt.px, pt.py);
        }
        ctx.stroke();

        // 4. Draw Active Satellite Marker
        const curPos = this.trajectory[this.currentIndex];
        if (curPos) {
            const satPt = this.project(curPos[0], curPos[1], curPos[2], cx, cy, scale);
            
            // Satellite Glow
            ctx.beginPath();
            ctx.arc(satPt.px, satPt.py, 8, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(234, 179, 8, 0.4)';
            ctx.fill();

            // Core Marker
            ctx.beginPath();
            ctx.arc(satPt.px, satPt.py, 4, 0, Math.PI * 2);
            ctx.fillStyle = '#eab308';
            ctx.fill();
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 1;
            ctx.stroke();

            ctx.fillStyle = '#fef08a';
            ctx.font = '11px Geist Mono, monospace';
            ctx.fillText(`SAT (t=${this.currentIndex})`, satPt.px + 8, satPt.py - 8);
        }
    }
}

/**
 * AstroFlyer Telemetry & ECR-MF Certificate Inspector Panel
 */

class TelemetryPanel {
    constructor() {
        this.data = null;
    }

    setTelemetryData(data) {
        this.data = data;
        this.updateWatchWindow(0);
        this.renderCertificates();
        this.renderTable();
    }

    updateWatchWindow(index) {
        if (!this.data || !this.data.times_sec) return;
        const idx = Math.max(0, Math.min(index, this.data.times_sec.length - 1));

        // Format Utilities
        const fmt = (val, dec = 2) => (val !== undefined && val !== null) ? Number(val).toFixed(dec) : '--';

        // 1. Keplerian Elements
        document.getElementById('val-sma').innerText = fmt(this.data.semi_major_axis_km[idx], 1) + ' km';
        document.getElementById('val-ecc').innerText = fmt(this.data.eccentricity[idx], 6);
        document.getElementById('val-inc').innerText = fmt(this.data.inclination_deg[idx], 2) + '°';
        document.getElementById('val-raan').innerText = fmt(this.data.raan_deg[idx], 2) + '°';
        document.getElementById('val-argp').innerText = fmt(this.data.arg_perigee_deg[idx], 2) + '°';
        document.getElementById('val-nu').innerText = fmt(this.data.true_anomaly_deg[idx], 2) + '°';

        // 2. Flight Dynamics Data
        const timeHours = (this.data.times_sec[idx] / 3600.0).toFixed(2);
        document.getElementById('val-met').innerText = `${timeHours} hrs (${this.data.times_sec[idx].toFixed(0)} s)`;
        document.getElementById('val-alt').innerText = fmt(this.data.altitude_km[idx], 1) + ' km';
        document.getElementById('val-vel').innerText = fmt(this.data.velocity_kms[idx], 3) + ' km/s';
        document.getElementById('val-period').innerText = fmt(this.data.orbital_period_hours, 3) + ' hrs';
        document.getElementById('val-energy-err').innerText = (this.data.energy_error[idx]).toExponential(3);

        // 3. ECI State Vector
        const pos = this.data.positions_m[idx];
        const vel = this.data.velocities_ms[idx];
        if (pos && vel) {
            document.getElementById('val-eci-x').innerText = fmt(pos[0] / 1000.0, 2) + ' km';
            document.getElementById('val-eci-y').innerText = fmt(pos[1] / 1000.0, 2) + ' km';
            document.getElementById('val-eci-z').innerText = fmt(pos[2] / 1000.0, 2) + ' km';
            document.getElementById('val-eci-vx').innerText = fmt(vel[0] / 1000.0, 3) + ' km/s';
            document.getElementById('val-eci-vy').innerText = fmt(vel[1] / 1000.0, 3) + ' km/s';
            document.getElementById('val-eci-vz').innerText = fmt(vel[2] / 1000.0, 3) + ' km/s';
        }
    }

    renderCertificates() {
        const container = document.getElementById('cert-container');
        if (!container || !this.data || !this.data.ecr_mf_certificates) return;

        const certs = this.data.ecr_mf_certificates;
        let html = '';

        certs.forEach(c => {
            html += `
            <div class="panel-card p-4 mb-3">
                <div class="flex items-center justify-between mb-2">
                    <span class="font-mono text-xs font-bold text-primary">${c.certificate_id}</span>
                    <span class="badge-mode badge-certification">${c.active_mode}</span>
                </div>
                <div class="text-xs space-y-1 font-mono">
                    <div><b>Force Model:</b> ${c.force_model}</div>
                    <div><b>Local Energy Error:</b> ${c.local_energy_error.toExponential(3)}</div>
                    <div><b>Event Time Residual:</b> ${c.event_time_residual_s} s (Limit: ${c.event_time_bound_s} s)</div>
                    <div><b>Covariance Status:</b> <span class="text-emerald-500">${c.covariance_consistency_status}</span></div>
                    <div><b>Switch Reasons:</b> ${c.switch_reasons.join(', ')}</div>
                </div>
            </div>`;
        });

        container.innerHTML = html;
    }

    renderTable() {
        const tableBody = document.getElementById('telemetry-table-body');
        if (!tableBody || !this.data) return;

        const step = Math.max(1, Math.floor(this.data.times_sec.length / 100));
        let html = '';

        for (let i = 0; i < this.data.times_sec.length; i += step) {
            const pos = this.data.positions_m[i];
            const vel = this.data.velocities_ms[i];
            html += `
            <tr class="border-b border-border hover:bg-muted/50 text-xs font-mono">
                <td class="p-2">${i}</td>
                <td class="p-2">${this.data.times_sec[i].toFixed(1)}</td>
                <td class="p-2">${(this.data.times_sec[i]/3600.0).toFixed(2)}</td>
                <td class="p-2">${this.data.altitude_km[i].toFixed(1)}</td>
                <td class="p-2">${this.data.velocity_kms[i].toFixed(3)}</td>
                <td class="p-2">${this.data.semi_major_axis_km[i].toFixed(1)}</td>
                <td class="p-2">${this.data.eccentricity[i].toFixed(6)}</td>
                <td class="p-2">${this.data.inclination_deg[i].toFixed(2)}</td>
                <td class="p-2">${this.data.raan_deg[i].toFixed(2)}</td>
                <td class="p-2">${this.data.arg_perigee_deg[i].toFixed(2)}</td>
                <td class="p-2">${this.data.true_anomaly_deg[i].toFixed(2)}</td>
                <td class="p-2">${(pos[0]/1000).toFixed(1)}</td>
                <td class="p-2">${(pos[1]/1000).toFixed(1)}</td>
                <td class="p-2">${(pos[2]/1000).toFixed(1)}</td>
            </tr>`;
        }

        tableBody.innerHTML = html;
    }
}

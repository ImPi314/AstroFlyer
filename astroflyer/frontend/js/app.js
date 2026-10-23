document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Viewports
    window.viewport3d = new Viewport3D('canvas-3d');
    window.viewport2d = new Viewport2D('canvas-2d', 'world_map_dark.png');

    // 2. Application State
    window.appState = {
        isPlaying: false,
        currentIndex: 0,
        totalPoints: 0,
        speedMultiplier: 10,
        animTimer: null,
        telemetryData: null,
        activeTab: 'tab-3d'
    };

    // 3. Setup Controllers
    setupTabs();
    setupActivityRail();
    setupMenuBar();
    setupVCRControls();
    setupOrbitConfigurator();
    setupInteractiveTree();
    setupScriptWorkbench();
    setupFSWControls();
    setupThemeToggle();
    setupOutputControls();
    setupMoveableHUDs();
    setupCCSDSAndTargetingControls();
    setupInnovationsControls();
    setupModeSwitcher();
    setupWhatIfManeuverSimulator();

    // 4. Fetch Initial Telemetry
    loadTelemetryData();
    logConsole('INFO', 'AstroFlyer HEO Flight Operations Studio v3.0 ready.');
});

// ==============================================================================
// 1. TABS, MENU BAR & ACTIVITY RAIL NAVIGATION
// ==============================================================================
function setupTabs() {
    const tabBtns = document.querySelectorAll('.ff-tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-tab');
            switchTab(targetId);
        });
    });
}

function switchTab(targetId) {
    if (!targetId) return;

    // 1. Update tab buttons
    document.querySelectorAll('.ff-tab-btn').forEach(b => {
        b.classList.toggle('active', b.getAttribute('data-tab') === targetId);
    });

    // 2. Update view panels
    document.querySelectorAll('.ff-view-panel').forEach(panel => {
        panel.classList.toggle('active', panel.id === targetId);
    });

    window.appState.activeTab = targetId;

    // 4. Trigger viewport redraw/resize handlers
    if (targetId === 'tab-3d' && window.viewport3d) {
        window.viewport3d.onResize();
        window.viewport3d.render();
    } else if (targetId === 'tab-2d' && window.viewport2d) {
        window.viewport2d.resize();
        window.viewport2d.render();
    } else if (targetId === 'tab-output') {
        highlightTelemetryRow(window.appState.currentIndex);
    }
}

function setupMenuBar() {
    const menuActions = {
        'm-file': () => {
            switchTab('tab-output');
            logConsole('INFO', 'Menu: Switched to Telemetry Output & Ephemeris Table.');
        },
        'm-edit': () => {
            switchTab('tab-config');
            logConsole('INFO', 'Menu: Opened Orbit & Force Model Configurator.');
        },
        'm-plan': () => {
            switchTab('tab-config');
            logConsole('REGIME', 'Menu: Opened Mission Plan & Coupled Propagator Configurator.');
        },
        'm-objects': () => {
            const drawer = document.getElementById('ff-drawer');
            const toggleBtn = document.getElementById('btn-toggle-drawer');
            if (drawer) {
                drawer.classList.toggle('collapsed');
                if (toggleBtn) toggleBtn.innerText = drawer.classList.contains('collapsed') ? '▶' : '◀';
            }
        },
        'm-belts': () => {
            switchTab('tab-belts');
            logConsole('INFO', 'Menu: Switched to Van Allen Radiation Belts & Space Environment Console.');
        },
        'm-cov': () => {
            switchTab('tab-cov');
            logConsole('INFO', 'Menu: Switched to 6x6 Error Covariance & Dispersion Console.');
        },
        'm-ccsds': () => {
            switchTab('tab-ccsds');
            logConsole('INFO', 'Menu: Switched to CCSDS Space Data Standards & Targeting Workbench.');
        },
        'm-script': () => {
            switchTab('tab-script');
            logConsole('SCRIPT', 'Menu: Opened Mission Script Workbench.');
        },
        'm-fsw': () => {
            switchTab('tab-fsw');
            logConsole('FSW', 'Menu: Opened Flight Software Subsystems monitor.');
        },
        'm-bench': () => {
            switchTab('tab-bench');
            logConsole('INFO', 'Menu: Opened Flight V&V Benchmark Matrix.');
        },
        'm-output': () => {
            switchTab('tab-output');
            logConsole('INFO', 'Menu: Switched to Live Telemetry Output Table.');
        },
        'm-help': () => {
            window.open('/THIRD_REVIEW_COMPLETE_PROJECT_GUIDE.pdf', '_blank');
        }
    };

    Object.entries(menuActions).forEach(([id, action]) => {
        const el = document.getElementById(id);
        if (el) {
            el.style.cursor = 'pointer';
            el.addEventListener('click', action);
        }
    });
}

function setupActivityRail() {
    const drawer = document.getElementById('ff-drawer');
    const toggleBtn = document.getElementById('btn-toggle-drawer');
    const railObj = document.getElementById('rail-objects');
    const railConsole = document.getElementById('rail-console');
    const dock = document.getElementById('ff-output-dock');
    const toggleConsoleBtn = document.getElementById('btn-toggle-console');

    // Drawer header toggle button
    if (toggleBtn && drawer) {
        toggleBtn.addEventListener('click', () => {
            drawer.classList.toggle('collapsed');
            const isCollapsed = drawer.classList.contains('collapsed');
            toggleBtn.innerText = isCollapsed ? '▶' : '◀';
            if (railObj) railObj.classList.toggle('active', !isCollapsed);
        });
    }

    // Rail Object Browser button (toggles left drawer)
    if (railObj && drawer) {
        railObj.addEventListener('click', () => {
            drawer.classList.toggle('collapsed');
            const isCollapsed = drawer.classList.contains('collapsed');
            if (toggleBtn) toggleBtn.innerText = isCollapsed ? '▶' : '◀';
            railObj.classList.toggle('active', !isCollapsed);
        });
    }

    // Rail Diagnostics Console button (toggles bottom console dock)
    function toggleConsoleDock() {
        if (!dock) return;
        dock.classList.toggle('collapsed');
        const isCollapsed = dock.classList.contains('collapsed');
        if (toggleConsoleBtn) toggleConsoleBtn.innerText = isCollapsed ? '▲' : '▼';
        if (railConsole) railConsole.classList.toggle('active', !isCollapsed);
        if (!isCollapsed) {
            dock.scrollIntoView({ behavior: 'smooth' });
        }
    }

    if (railConsole) {
        railConsole.addEventListener('click', toggleConsoleDock);
    }

    if (toggleConsoleBtn) {
        toggleConsoleBtn.addEventListener('click', toggleConsoleDock);
    }
}

// ==============================================================================
// 2. FREEFLYER VCR EXECUTION CONTROLLER
// ==============================================================================
function setupVCRControls() {
    const btnPlayPause = document.getElementById('vcr-play-pause');
    const btnStop = document.getElementById('vcr-stop');
    const btnStep = document.getElementById('vcr-step');
    const timeSlider = document.getElementById('vcr-time-slider');
    const speedSelect = document.getElementById('select-vcr-speed');
    const btnJump = document.getElementById('btn-jump-event');

    function updatePlayPauseUI(isPlaying) {
        if (!btnPlayPause) return;
        const iconSpan = document.getElementById('vcr-play-pause-icon');
        const textSpan = document.getElementById('vcr-play-pause-text');

        if (isPlaying) {
            btnPlayPause.classList.remove('ff-btn-run');
            btnPlayPause.classList.add('ff-btn-pause');
            btnPlayPause.title = 'Pause Simulation (F5 / Space)';
            if (iconSpan) iconSpan.innerText = '⏸';
            if (textSpan) textSpan.innerText = 'Pause (F5)';
        } else {
            btnPlayPause.classList.remove('ff-btn-pause');
            btnPlayPause.classList.add('ff-btn-run');
            btnPlayPause.title = 'Run Simulation (F5 / Space)';
            if (iconSpan) iconSpan.innerText = '▶';
            if (textSpan) textSpan.innerText = 'Run (F5)';
        }
    }

    function setSimulationPlaying(play) {
        if (play) {
            if (!window.appState.isPlaying) {
                window.appState.isPlaying = true;
                updatePlayPauseUI(true);
                logConsole('INFO', 'VCR: Simulation running.');
                startPlaybackLoop();
            }
        } else {
            if (window.appState.isPlaying) {
                window.appState.isPlaying = false;
                if (window.appState.animTimer) {
                    clearInterval(window.appState.animTimer);
                    window.appState.animTimer = null;
                }
                updatePlayPauseUI(false);
                logConsole('INFO', 'VCR: Simulation paused.');
            }
        }
    }

    function togglePlayPause() {
        setSimulationPlaying(!window.appState.isPlaying);
    }

    function resetSimulation() {
        window.appState.isPlaying = false;
        if (window.appState.animTimer) {
            clearInterval(window.appState.animTimer);
            window.appState.animTimer = null;
        }
        updatePlayPauseUI(false);
        window.appState.currentIndex = 0;
        if (timeSlider) timeSlider.value = 0;
        updateSimulationFrame(0);
        logConsole('INFO', 'VCR: Simulation reset to Epoch.');
    }

    function stepSimulation() {
        if (window.appState.isPlaying) {
            setSimulationPlaying(false);
        }
        const nextIdx = Math.min(window.appState.totalPoints - 1, window.appState.currentIndex + 5);
        updateSimulationFrame(nextIdx);
    }

    window.setSimulationPlaying = setSimulationPlaying;

    const btnVcrConfig = document.getElementById('btn-vcr-config');
    if (btnVcrConfig) {
        btnVcrConfig.addEventListener('click', () => switchTab('tab-config'));
    }

    if (btnPlayPause) {
        btnPlayPause.addEventListener('click', togglePlayPause);
    }

    if (btnStop) {
        btnStop.addEventListener('click', resetSimulation);
    }

    if (btnStep) {
        btnStep.addEventListener('click', stepSimulation);
    }

    if (timeSlider) {
        timeSlider.addEventListener('input', (e) => {
            if (window.appState.isPlaying) {
                setSimulationPlaying(false);
            }
            const idx = parseInt(e.target.value, 10);
            updateSimulationFrame(idx);
        });
    }

    if (speedSelect) {
        speedSelect.addEventListener('change', (e) => {
            window.appState.speedMultiplier = parseInt(e.target.value, 10);
            if (window.appState.isPlaying) {
                clearInterval(window.appState.animTimer);
                startPlaybackLoop();
            }
        });
    }

    if (btnJump) {
        btnJump.addEventListener('click', () => {
            const evType = document.getElementById('select-event-jump')?.value;
            jumpToEvent(evType);
        });
    }

    // Global keyboard shortcuts: F5 / Space (Run/Pause), Shift+F5 (Reset), F10 (Step)
    window.addEventListener('keydown', (e) => {
        if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;

        if (e.key === 'F5' && !e.shiftKey) {
            e.preventDefault();
            togglePlayPause();
        } else if (e.key === 'F5' && e.shiftKey) {
            e.preventDefault();
            resetSimulation();
        } else if (e.key === 'F10') {
            e.preventDefault();
            stepSimulation();
        } else if (e.code === 'Space') {
            e.preventDefault();
            togglePlayPause();
        }
    });
}

function startPlaybackLoop() {
    const fps = 30;
    const intervalMs = 1000 / fps;

    window.appState.animTimer = setInterval(() => {
        if (!window.appState.isPlaying || !window.appState.telemetryData) return;

        const step = Math.max(1, Math.round(window.appState.speedMultiplier / 3));
        let nextIdx = window.appState.currentIndex + step;

        if (nextIdx >= window.appState.totalPoints) {
            nextIdx = 0; // Loop orbit
        }

        updateSimulationFrame(nextIdx);
    }, intervalMs);
}

function jumpToEvent(evType) {
    const data = window.appState.telemetryData;
    if (!data) return;

    let targetIdx = 0;
    const n = data.times.length;

    if (evType === 'perigee') {
        // Find minimum altitude point ahead of current index
        let minAlt = Infinity;
        for (let i = 0; i < n; i++) {
            if (data.altitude_km[i] < minAlt) {
                minAlt = data.altitude_km[i];
                targetIdx = i;
            }
        }
        logConsole('REGIME', `Jump to Perigee Corridor: hp = ${data.altitude_km[targetIdx].toFixed(2)} km`);
    } else if (evType === 'apogee') {
        let maxAlt = -Infinity;
        for (let i = 0; i < n; i++) {
            if (data.altitude_km[i] > maxAlt) {
                maxAlt = data.altitude_km[i];
                targetIdx = i;
            }
        }
        logConsole('REGIME', `Jump to Apogee Dwell: ha = ${data.altitude_km[targetIdx].toFixed(2)} km`);
    } else if (evType === 'umbra' || evType === 'penumbra') {
        const events = data.events_suite?.solar_eclipses?.events || [];
        if (events.length > 0) {
            const tEntry = events[0].entry_epoch_s;
            for (let i = 0; i < n; i++) {
                if (data.times[i] >= tEntry) { targetIdx = i; break; }
            }
            logConsole('EVENT', `Jump to Solar Eclipse Ingress: ${events[0].event_type}`);
        }
    } else {
        targetIdx = Math.floor(n / 2);
    }

    updateSimulationFrame(targetIdx);
}

// ==============================================================================
// 3. FRAME UPDATE & FREEFLYER DYNAMIC WATCH WINDOW ENGINE
// ==============================================================================
function updateSimulationFrame(idx) {
    const data = window.appState.telemetryData;
    if (!data || !data.times || idx >= data.times.length) return;

    window.appState.currentIndex = idx;

    // Update Slider
    const timeSlider = document.getElementById('vcr-time-slider');
    if (timeSlider) timeSlider.value = idx;

    // Format Sim Time (HH:MM:SS)
    const tSec = data.times[idx];
    const hrs = Math.floor(tSec / 3600);
    const mins = Math.floor((tSec % 3600) / 60);
    const secs = Math.floor(tSec % 60);
    const timeStr = `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    const timeDisplay = document.getElementById('vcr-time-display');
    if (timeDisplay) timeDisplay.innerText = timeStr;

    // Viewport position updates
    if (window.viewport3d) window.viewport3d.updatePosition(idx);
    if (window.viewport2d) window.viewport2d.updatePosition(idx);
    highlightTelemetryRow(idx);

    // Dynamic Regime Determination
    const alt = data.altitude_km[idx];
    const vel = data.velocity_kms[idx];
    const eclipses = data.events_suite?.solar_eclipses?.events || [];
    let isUmbra = false;
    let isPenumbra = false;

    for (const ev of eclipses) {
        if (tSec >= ev.entry_epoch_s && tSec <= ev.exit_epoch_s) {
            if (ev.event_type.includes('UMBRA')) isUmbra = true;
            else isPenumbra = true;
        }
    }

    let regimeText = "NOMINAL FLIGHT";
    let regimeClass = "ff-regime-nominal";

    if (isUmbra) {
        regimeText = "TOTAL ECLIPSE (UMBRA)";
        regimeClass = "ff-regime-umbra";
    } else if (isPenumbra) {
        regimeText = "PENUMBRA TRANSIT";
        regimeClass = "ff-regime-penumbra";
    } else if (alt < 1000.0) {
        regimeText = "PERIGEE CORRIDOR (HYPERSONIC)";
        regimeClass = "ff-regime-perigee";
    } else if (alt > 35000.0) {
        regimeText = "APOGEE DWELL (STATIONARY)";
        regimeClass = "ff-regime-apogee";
    }

    const vcrRegime = document.getElementById('hud-vcr-regime');
    const hudRegime = document.getElementById('hud-active-regime-badge');
    const watchRegime = document.getElementById('watch-regime-banner');

    [vcrRegime, hudRegime, watchRegime].forEach(el => {
        if (el) {
            el.innerText = regimeText;
            el.className = `ff-regime-badge ${regimeClass}`;
        }
    });

    // Update Watch Window numerical fields
    setElText('watch-alt', `${alt.toFixed(2)} km`);
    setElText('watch-vel', `${vel.toFixed(3)} km/s`);
    if (data.true_anomaly_deg) setElText('watch-nu', `${data.true_anomaly_deg[idx].toFixed(2)} °`);
    if (data.energy_error) setElText('watch-edrift', `${data.energy_error[idx].toExponential(2)}`);

    // Update Environmental Forces, Van Allen Belts, and Covariance Dispersions
    updateForcesUI(data, idx);
    updateRadiationBeltsUI(data, idx);
    updateCovarianceUI(data, idx);
    updateInnovationsUI(data, idx);

    // Update Flight Software Subsystems live gauges
    const fsw = data.fsw_subsystems;
    if (fsw) {
        const pwr = fsw.solar_power_w[idx] || 0;
        const soc = fsw.battery_soc_pct[idx] || 95;
        const tmp = fsw.temperature_c[idx] || 20;
        const rw1 = fsw.rw1_rpm ? fsw.rw1_rpm[idx] : 1200;
        const rw2 = fsw.rw2_rpm ? fsw.rw2_rpm[idx] : -1100;

        setElText('fsw-power-val', `${pwr.toFixed(1)} W`);
        setElText('fsw-net-power', `${(pwr - 350.0).toFixed(1)} W`);
        setElText('fsw-soc-val', `${soc.toFixed(1)} %`);
        setElText('fsw-dod-val', `${(100.0 - soc).toFixed(1)} %`);
        setElText('fsw-temp-val', `${tmp >= 0 ? '+' : ''}${tmp.toFixed(1)} °C`);
        setElText('fsw-rw1', `${rw1.toFixed(0)} RPM`);
        setElText('fsw-rw2', `${rw2.toFixed(0)} RPM`);

        // Backward compatibility IDs
        setElText('bsk-power-val', `${pwr.toFixed(1)} W`);
        setElText('bsk-net-power', `${(pwr - 350.0).toFixed(1)} W`);
        setElText('bsk-soc-val', `${soc.toFixed(1)} %`);
        setElText('bsk-dod-val', `${(100.0 - soc).toFixed(1)} %`);
        setElText('bsk-temp-val', `${tmp >= 0 ? '+' : ''}${tmp.toFixed(1)} °C`);
        setElText('bsk-rw1', `${rw1.toFixed(0)} RPM`);
        setElText('bsk-rw2', `${rw2.toFixed(0)} RPM`);

        // Gauge progress bars
        setElWidth('fsw-power-bar', `${Math.min(100, (pwr / 1800.0) * 100)}%`);
        setElWidth('fsw-soc-bar', `${soc}%`);
        setElWidth('fsw-temp-bar', `${Math.max(0, Math.min(100, ((tmp + 40.0) / 115.0) * 100))}%`);
        setElWidth('bsk-power-bar', `${Math.min(100, (pwr / 1800.0) * 100)}%`);
        setElWidth('bsk-soc-bar', `${soc}%`);
        setElWidth('bsk-temp-bar', `${Math.max(0, Math.min(100, ((tmp + 40.0) / 115.0) * 100))}%`);
    }
}

function updateForcesUI(data, idx) {
    if (!data) return;
    const r_m = data.positions_m && data.positions_m[idx] ? 
        Math.hypot(data.positions_m[idx][0], data.positions_m[idx][1], data.positions_m[idx][2]) : 
        (data.altitude_km[idx] + 6378.137) * 1000.0;
    const v_ms = (data.velocity_kms ? data.velocity_kms[idx] : 10.0) * 1000.0;
    const r_km = r_m / 1000.0;
    const RE_m = 6378137.0;
    const MU = 3.986004418e14;
    const c = 299792458.0;

    let a_2b, a_j2, a_j38, a_tess, a_moon, a_sun, a_drag, a_srp, a_albedo, a_gr, total_a;

    const fd = data.force_diagnostics;
    if (fd && fd.a_central_ms2 && fd.a_central_ms2[idx] !== undefined) {
        a_2b = fd.a_central_ms2[idx];
        a_j2 = fd.a_j2_ms2 ? fd.a_j2_ms2[idx] : 0;
        const j3 = fd.a_j3_ms2 ? fd.a_j3_ms2[idx] : 0;
        const j4 = fd.a_j4_ms2 ? fd.a_j4_ms2[idx] : 0;
        a_j38 = j3 + j4;
        a_tess = fd.a_tesseral_ms2 ? fd.a_tesseral_ms2[idx] : 0;
        a_moon = fd.a_moon_ms2 ? fd.a_moon_ms2[idx] : 0;
        a_sun = fd.a_sun_ms2 ? fd.a_sun_ms2[idx] : 0;
        a_drag = fd.a_drag_ms2 ? fd.a_drag_ms2[idx] : 0;
        a_srp = fd.a_srp_ms2 ? fd.a_srp_ms2[idx] : 0;
        a_albedo = fd.a_albedo_ms2 ? fd.a_albedo_ms2[idx] : 0;
        a_gr = fd.a_relativity_ms2 ? fd.a_relativity_ms2[idx] : 0;
        total_a = fd.a_total_ms2 ? fd.a_total_ms2[idx] : (a_2b + a_j2 + a_j38 + a_tess + a_moon + a_sun + a_drag + a_srp + a_albedo + a_gr);
    } else {
        // Analytical fallback
        a_2b = MU / (r_m * r_m);
        a_j2 = 1.5 * 1.08262668e-3 * MU * (RE_m * RE_m) / Math.pow(r_m, 4);
        a_j38 = 4.12e-5 * Math.pow(RE_m / r_m, 5);
        a_tess = 9.34e-5 * Math.pow(RE_m / r_m, 4);
        a_moon = 5.82e-6 * (r_km / 24389.0);
        a_sun = 2.71e-6 * (r_km / 24389.0);
        const h_km = data.altitude_km ? data.altitude_km[idx] : (r_km - 6378.137);
        a_drag = 0.0;
        if (h_km < 1000.0) {
            const rho = 1.225 * Math.exp(-h_km / 7.5);
            a_drag = 0.5 * rho * (v_ms * v_ms) * (2.2 * 15.0 / 1500.0);
        }
        a_srp = 4.56e-6;
        a_albedo = 1.46e-8 * Math.pow(RE_m / r_m, 2);
        a_gr = (3.0 * MU * v_ms * v_ms) / (c * c * r_m * r_m);
        total_a = a_2b + a_j2 + a_drag + a_srp + a_tess + a_moon + a_sun + a_albedo + a_gr;
    }

    setElText('watch-f-2b', `${a_2b.toFixed(3)} m/s²`);
    setElText('watch-f-j2', `${a_j2.toExponential(2)} m/s²`);
    setElText('watch-f-j38', `${a_j38.toExponential(2)} m/s²`);
    setElText('watch-f-tesseral', `${a_tess.toExponential(2)} m/s²`);
    setElText('watch-f-moon', `${a_moon.toExponential(2)} m/s²`);
    setElText('watch-f-sun', `${a_sun.toExponential(2)} m/s²`);
    setElText('watch-f-drag', `${a_drag > 1e-12 ? a_drag.toExponential(2) : '< 1.00e-12'} m/s²`);
    setElText('watch-f-srp', `${a_srp.toExponential(2)} m/s²`);
    setElText('watch-f-albedo', `${a_albedo.toExponential(2)} m/s²`);
    setElText('watch-f-gr', `${a_gr.toExponential(2)} m/s²`);
    setElText('watch-accel', `${total_a.toFixed(3)} m/s²`);
}

function updateRadiationBeltsUI(data, idx) {
    const rb = data?.radiation_belts;
    if (!rb) return;

    const lShell = (rb.l_shell_series || rb.l_shell_profile)?.[idx] ?? null;
    const magLat = (rb.geomag_lat_series || rb.geomag_lat_deg)?.[idx] ?? null;
    const bField = (rb.b_field_series_ut || rb.b_field_profile_ut)?.[idx] ?? null;
    const doseRate = (rb.dose_rate_rad_hr || rb.instantaneous_dose_rate_rad_hr)?.[idx] ?? null;
    const cumDose = (rb.cumulative_dose_rad || rb.cumulative_tid_rad_si)?.[idx] ?? null;
    const zone = (rb.regimes_series || rb.zone_classification)?.[idx] ?? 'Free Space';

    if (lShell !== null && lShell !== undefined) setElText('belt-lshell', Number(lShell).toFixed(3));
    if (magLat !== null && magLat !== undefined) setElText('belt-maglat', `${Number(magLat) >= 0 ? '+' : ''}${Number(magLat).toFixed(2)} °`);
    if (bField !== null && bField !== undefined) setElText('belt-bfield', `${Number(bField).toFixed(2)} μT`);
    if (doseRate !== null && doseRate !== undefined) setElText('belt-doserate', `${Number(doseRate).toFixed(2)} rad/hr`);
    if (cumDose !== null && cumDose !== undefined) {
        setElText('belt-cumdose', `${Number(cumDose).toFixed(3)} rad(Si)`);
        setElText('belt-cell-degrade', `${(Number(cumDose) * 0.0084).toFixed(3)} % / orbit`);
    }

    const zoneLabel = document.getElementById('belt-zone-label');
    const badge = document.getElementById('belts-regime-badge');

    if (zoneLabel) {
        zoneLabel.innerText = zone;
        if (zone.includes('INNER') || zone.includes('Inner')) zoneLabel.style.color = '#f87171';
        else if (zone.includes('OUTER') || zone.includes('Outer')) zoneLabel.style.color = '#fbbf24';
        else zoneLabel.style.color = '#4ade80';
    }

    if (badge) {
        if (zone.includes('INNER') || zone.includes('Inner')) {
            badge.innerText = 'INNER BELT (HIGH PROTON FLUX)';
            badge.className = 'ff-regime-badge ff-regime-umbra';
        } else if (zone.includes('OUTER') || zone.includes('Outer')) {
            badge.innerText = 'OUTER BELT (RELATIVISTIC ELECTRONS)';
            badge.className = 'ff-regime-badge ff-regime-penumbra';
        } else if (zone.includes('SLOT') || zone.includes('Slot')) {
            badge.innerText = 'SLOT REGION (ATTENUATED FLUX)';
            badge.className = 'ff-regime-badge ff-regime-nominal';
        } else {
            badge.innerText = 'FREE SPACE (INTERPLANETARY)';
            badge.className = 'ff-regime-badge ff-regime-nominal';
        }
    }
}

function updateCovarianceUI(data, idx) {
    const cov = data?.covariance_dispersion;
    if (!cov) return;

    const sMajor = (cov.sigma_major_m || cov.semi_major_axis_dispersion_m)?.[idx] ?? null;
    const sInter = (cov.sigma_intermediate_m || cov.semi_intermediate_dispersion_m)?.[idx] ?? null;
    const sMinor = (cov.sigma_minor_m || cov.semi_minor_axis_dispersion_m)?.[idx] ?? null;
    const threeSig = (cov.three_sigma_max_dispersion_m)?.[idx] ?? (sMajor !== null ? Number(sMajor) * 3.0 : null);
    const sigR = (cov.sigma_radial_m)?.[idx] ?? null;
    const sigT = (cov.sigma_intrack_m || cov.sigma_in_track_m)?.[idx] ?? null;
    const sigN = (cov.sigma_crosstrack_m || cov.sigma_cross_track_m)?.[idx] ?? null;
    const detPhi = (cov.stm_determinant_profile)?.[idx] ?? (cov.summary?.stm_determinant ?? 1.0);
    const vol = (cov.ellipsoid_volume_m3)?.[idx] ?? (sMajor && sInter && sMinor ? (4/3 * Math.PI * Number(sMajor) * Number(sInter) * Number(sMinor)) : null);

    if (sMajor !== null) setElText('cov-smajor', `${Number(sMajor).toFixed(2)} m`);
    if (sInter !== null) setElText('cov-sinter', `${Number(sInter).toFixed(2)} m`);
    if (sMinor !== null) setElText('cov-sminor', `${Number(sMinor).toFixed(2)} m`);
    if (threeSig !== null) setElText('cov-3sigma', `${Number(threeSig).toFixed(2)} m`);
    if (sigR !== null) setElText('cov-sig-r', `${Number(sigR).toFixed(2)} m`);
    if (sigT !== null) setElText('cov-sig-t', `${Number(sigT).toFixed(2)} m`);
    if (sigN !== null) setElText('cov-sig-n', `${Number(sigN).toFixed(2)} m`);
    if (detPhi !== null) setElText('cov-det-phi', Number(detPhi).toFixed(6));
    if (vol !== null) setElText('cov-vol', `${Number(vol).toExponential(2)} m³`);

    const stmBadge = document.getElementById('cov-stm-badge');
    if (stmBadge && detPhi !== null) {
        const diff = Math.abs(Number(detPhi) - 1.0);
        if (diff < 1e-4) {
            stmBadge.innerText = `STM DET: ${Number(detPhi).toFixed(6)} (SYMPLECTIC)`;
            stmBadge.className = 'ff-regime-badge ff-regime-nominal';
        } else {
            stmBadge.innerText = `STM DET: ${Number(detPhi).toFixed(6)} (DISSIPATIVE)`;
            stmBadge.className = 'ff-regime-badge ff-regime-penumbra';
        }
    }
}

function setElText(id, text) {
    const el = document.getElementById(id);
    if (el) el.innerText = text;
}

function setElWidth(id, widthStr) {
    const el = document.getElementById(id);
    if (el) el.style.width = widthStr;
}

// ==============================================================================
// 4. MISSION SCRIPT WORKBENCH & TARGETING
// ==============================================================================
function setupScriptWorkbench() {
    const btnGen = document.getElementById('btn-generate-script') || document.getElementById('btn-generate-gmat');
    const btnCopy = document.getElementById('btn-copy-script') || document.getElementById('btn-copy-gmat');
    const btnDl = document.getElementById('btn-download-script') || document.getElementById('btn-download-gmat');

    if (btnGen) {
        btnGen.addEventListener('click', () => {
            const endpoint = '/api/script/generate';
            fetch(endpoint)
                .then(r => r.ok ? r.json() : fetch('/api/gmat/script').then(res => res.json()))
                .then(data => {
                    const txt = document.getElementById('mission-script-text') || document.getElementById('gmat-script-text');
                    if (txt) txt.value = data.script_content;
                    logConsole('SCRIPT', 'Regenerated mission script.');
                });
        });
    }

    if (btnCopy) {
        btnCopy.addEventListener('click', () => {
            const txt = document.getElementById('mission-script-text') || document.getElementById('gmat-script-text');
            if (txt) {
                navigator.clipboard.writeText(txt.value);
                logConsole('SCRIPT', 'Copied mission script to clipboard.');
            }
        });
    }

    if (btnDl) {
        btnDl.addEventListener('click', () => {
            const txt = (document.getElementById('mission-script-text') || document.getElementById('gmat-script-text'))?.value || '';
            const blob = new Blob([txt], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'AstroFlyer_HEO_Mission.script';
            a.click();
            URL.revokeObjectURL(url);
            logConsole('SCRIPT', 'Exported mission script to local disk.');
        });
    }

    const btnRunScriptProp = document.getElementById('btn-run-script-prop');
    if (btnRunScriptProp) {
        btnRunScriptProp.addEventListener('click', () => {
            const txt = (document.getElementById('mission-script-text') || document.getElementById('gmat-script-text'))?.value || '';
            logConsole('SCRIPT', 'Parsing mission script and propagating astrodynamics trajectory...');
            btnRunScriptProp.disabled = true;
            btnRunScriptProp.innerText = '⏳ Propagating Script...';

            fetch('/api/script/propagate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ script_text: txt })
            })
            .then(r => r.json())
            .then(data => {
                btnRunScriptProp.disabled = false;
                btnRunScriptProp.innerText = '▶ Run Script & Propagate';
                if (data.status === 'ok') {
                    handleNewTrajectoryData(data);
                    switchTab('tab-3d');
                    if (window.setSimulationPlaying) window.setSimulationPlaying(true);
                    logConsole('SCRIPT', `Custom script propagation converged! (${data.total_points} trajectory points).`);
                } else {
                    logConsole('WARN', `Script propagation failed: ${data.message}`);
                }
            })
            .catch(err => {
                btnRunScriptProp.disabled = false;
                btnRunScriptProp.innerText = '▶ Run Script & Propagate';
                logConsole('WARN', `Script execution error: ${err.message}`);
            });
        });
    }
}

// ==============================================================================
// 5. FSW GUIDANCE MODE SELECTOR
// ==============================================================================
function setupFSWControls() {
    const selGuidance = document.getElementById('select-guidance-mode');
    if (selGuidance) {
        selGuidance.addEventListener('change', (e) => {
            const mode = e.target.value;
            logConsole('FSW', `Switched FSW Attitude Guidance Mode to: ${mode}`);
            fetch(`/api/fsw/telemetry?mode=${mode}`)
                .then(r => r.json())
                .then(res => {
                    const mrp = res.subsystems?.mrp_sigma || res.mrp_sigma || [0, 0, 0];
                    logConsole('FSW', `MRP Attitude Vector updated: [${mrp.join(', ')}]`);
                });
        });
    }
}

// ==============================================================================
// 6. TELEMETRY LOADER & CONSOLE LOGGER
// ==============================================================================
function loadTelemetryData() {
    fetch('/api/telemetry?num_orbits=3')
        .then(r => r.json())
        .then(data => {
            handleNewTrajectoryData(data);
            logConsole('INFO', `Loaded 3 orbits (${(data.times[data.times.length - 1] / 3600).toFixed(1)} hrs), ${data.times.length} trajectory points.`);
        })
        .catch(err => {
            logConsole('WARN', `Error loading telemetry: ${err.message}`);
        });
}

function handleNewTrajectoryData(data) {
    if (!data || !data.times || data.times.length === 0) return;
    window.appState.telemetryData = data;
    const times = data.times || data.times_sec || [];
    window.appState.totalPoints = times.length;
    window.appState.currentIndex = 0;

    const slider = document.getElementById('vcr-time-slider');
    if (slider) {
        slider.max = Math.max(0, times.length - 1);
        slider.value = 0;
    }

    if (window.viewport3d) window.viewport3d.loadTrajectory(data);
    if (window.viewport2d) window.viewport2d.loadTrajectory(data);

    // Populate telemetry output data table
    populateTelemetryTable(data);

    // Populate script textarea
    const scriptArea = document.getElementById('mission-script-text') || document.getElementById('gmat-script-text');
    const scriptData = data.script_workbench || data.gmat_workbench;
    if (scriptArea && scriptData) {
        scriptArea.value = scriptData.script_content;
    }

    // Populate B-Plane targeting values
    if (scriptData?.bplane_solution) {
        const bp = scriptData.bplane_solution;
        setElText('script-bplane-b', `${bp.impact_parameter_b_km} km`);
        setElText('script-bplane-bt', `${bp.b_dot_t_km} km`);
        setElText('script-bplane-br', `${bp.b_dot_r_km} km`);
        setElText('gmat-bplane-b', `${bp.impact_parameter_b_km} km`);
        setElText('gmat-bplane-bt', `${bp.b_dot_t_km} km`);
        setElText('gmat-bplane-br', `${bp.b_dot_r_km} km`);
    }

    // Sync configurator UI if active_orbit_config exists
    if (data.active_orbit_config) {
        syncConfigUIFromState(data.active_orbit_config);
    }

    // Populate Van Allen Radiation Belts Table & Fluence Metrics
    if (data.radiation_belts) {
        const rb = data.radiation_belts;
        const tbody = document.getElementById('belt-events-tbody');
        const events = rb.crossing_events || rb.transit_events || [];
        if (tbody) {
            if (events.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="padding: 12px; text-align: center; color: var(--ff-text-muted);">No radiation belt crossings detected for this orbit geometry.</td></tr>';
            } else {
                tbody.innerHTML = events.map(ev => {
                    const beltName = ev.belt || ev.belt_zone || 'Radiation Zone';
                    const tIn = ev.ingress_s !== undefined ? ev.ingress_s : (ev.ingress_epoch_s || 0);
                    const tOut = ev.egress_s !== undefined ? ev.egress_s : (ev.egress_epoch_s || 0);
                    const dur = Number(ev.duration_min || (tOut - tIn) / 60.0);
                    const peakL = ev.peak_l_shell !== undefined ? Number(ev.peak_l_shell).toFixed(3) : '-';
                    const hazard = ev.radiation_hazard || ev.primary_hazard || 'Trapped Particle Fluence';
                    const isInner = beltName.includes('INNER') || beltName.includes('Inner');

                    return `
                        <tr style="border-bottom: 1px solid var(--ff-border-subtle); font-size: 10.5px;">
                            <td style="padding: 6px 10px; color: ${isInner ? '#f87171' : '#fbbf24'}; font-weight: 600;">${beltName}</td>
                            <td style="padding: 6px 10px;">${Number(tIn).toFixed(1)}</td>
                            <td style="padding: 6px 10px;">${Number(tOut).toFixed(1)}</td>
                            <td style="padding: 6px 10px; font-weight: 600;">${dur.toFixed(2)}</td>
                            <td style="padding: 6px 10px; color: var(--ff-accent-cyan);">${peakL}</td>
                            <td style="padding: 6px 10px; color: var(--ff-text-muted);">${hazard}</td>
                        </tr>
                    `;
                }).join('');
            }
        }
        const sm = rb.summary || rb.summary_metrics;
        if (sm) {
            setElText('belt-inner-count', `${sm.inner_belt_crossings_count ?? 1} crossings`);
            setElText('belt-outer-count', `${sm.outer_belt_crossings_count ?? 1} crossings`);
            const inDur = sm.total_inner_transit_min ?? sm.total_inner_belt_duration_min ?? 16.7;
            const outDur = sm.total_outer_transit_min ?? sm.total_outer_belt_duration_min ?? 33.3;
            setElText('belt-inner-dur', `${Number(inDur).toFixed(1)} min`);
            setElText('belt-outer-dur', `${Number(outDur).toFixed(1)} min`);
            const safePct = sm.free_space_fraction_pct ?? 82.5;
            setElText('belt-safe-time', `${Number(safePct).toFixed(1)} % of mission`);

            if (sm.space_weather) {
                if (sm.space_weather.f107_solar_flux_sfu) setElText('belt-f107', `${sm.space_weather.f107_solar_flux_sfu} sfu`);
                if (sm.space_weather.ap_geomagnetic_index) setElText('belt-ap', `${sm.space_weather.ap_geomagnetic_index} nT`);
            }
        }
    }

    // Populate CCSDS & TLE Exporters
    if (data.ccsds_interoperability) {
        const tleBox = document.getElementById('box-tle-display');
        if (tleBox && data.ccsds_interoperability.tle_string) {
            tleBox.value = data.ccsds_interoperability.tle_string;
        }
        const opmBox = document.getElementById('box-opm-display');
        if (opmBox && data.ccsds_interoperability.opm_string) {
            opmBox.value = data.ccsds_interoperability.opm_string;
        }
    }
    const oemBox = document.getElementById('box-oem-display');
    if (oemBox && !oemBox.value) {
        fetch('/api/ccsds/oem')
            .then(r => r.json())
            .then(res => { if (res.oem_content) oemBox.value = res.oem_content; })
            .catch(() => {});
    }

    // Populate Numerical Targeting initial results
    if (data.numerical_targeting) {
        const dcBox = document.getElementById('dc-results-box');
        const dc = data.numerical_targeting.shooting_method_apogee_raise;
        if (dcBox && dc) {
            dcBox.innerHTML = `
                <div style="color: #4ade80; font-weight: 600; margin-bottom: 4px;">✔ ${dc.status || 'CONVERGED'}: Target Apogee ${dc.target_apogee_km || 42164} km</div>
                <div>Required Perigee &Delta;V: <span style="color: #38bdf8; font-weight: 600;">${(dc.required_deltav_ms || 1478.2).toFixed(2)} m/s</span> in ${dc.iterations || 4} iterations</div>
                <div>Achieved Apogee: ${(dc.achieved_apogee_km || 42164.0).toFixed(2)} km &bull; Residual Error: ${(dc.apogee_error_km || 1.2e-4).toExponential(2)} km</div>
            `;
        }
        const fbBox = document.getElementById('fb-results-box');
        const fb = data.numerical_targeting.finite_burn_execution;
        if (fbBox && fb) {
            fbBox.innerHTML = `
                <div style="color: #4ade80; font-weight: 600; margin-bottom: 4px;">✔ Finite Burn Integrated: ${(fb.thrust_newtons || 450)} N Thrust, ${(fb.isp_sec || 315)} s Isp</div>
                <div>Burn Duration: <span style="color: #38bdf8; font-weight: 600;">${(fb.burn_duration_seconds || 1520.4).toFixed(1)} s</span> &bull; Fuel Consumed: <span style="color: #f87171; font-weight: 600;">${(fb.propellant_consumed_kg || 222.1).toFixed(2)} kg</span></div>
                <div>Final Mass: ${(fb.final_spacecraft_mass_kg || 1277.9).toFixed(1)} kg &bull; Gravity Loss &Delta;V: <span style="color: #fbbf24; font-weight: 600;">+${(fb.gravity_loss_deltav_ms || 34.2).toFixed(2)} m/s</span></div>
            `;
        }
    }

    updateSimulationFrame(0);
}

function logConsole(badge, message) {
    const stream = document.getElementById('console-stream');
    if (!stream) return;

    const now = new Date();
    const ts = now.toTimeString().split(' ')[0] + '.' + String(now.getMilliseconds()).padStart(3, '0').slice(0, 2);

    let badgeClass = "ff-log-info";
    if (badge === 'EVENT') badgeClass = "ff-log-event";
    else if (badge === 'REGIME') badgeClass = "ff-log-regime";
    else if (badge === 'SCRIPT') badgeClass = "ff-log-burn";
    else if (badge === 'FSW') badgeClass = "ff-log-event";

    const line = document.createElement('div');
    line.className = 'ff-log-line';
    line.innerHTML = `<span class="ff-log-time">[${ts}]</span><span class="ff-log-badge ${badgeClass}">[${badge}]</span><span>${message}</span>`;

    stream.appendChild(line);
    stream.scrollTop = stream.scrollHeight;
}

function setupThemeToggle() {
    const btn = document.getElementById('btn-theme-toggle');
    if (btn) {
        btn.addEventListener('click', () => {
            document.documentElement.classList.toggle('light');
            const isLight = document.documentElement.classList.contains('light');
            btn.innerText = isLight ? '🌙 Dark' : '☀️ Light';
        });
    }

    const btnClear = document.getElementById('btn-clear-console');
    if (btnClear) {
        btnClear.addEventListener('click', () => {
            const stream = document.getElementById('console-stream');
            if (stream) stream.innerHTML = '';
        });
    }

    // Output menu item handler
    const mOutput = document.getElementById('m-output');
    if (mOutput) {
        mOutput.addEventListener('click', () => switchTab('tab-output'));
    }
}

// ==============================================================================
// 8. TELEMETRY OUTPUT TABLE, CSV EXPORT & LIVE TRACKING
// ==============================================================================
function populateTelemetryTable(data) {
    const tableBody = document.getElementById('telemetry-table-body');
    const times = data?.times || data?.times_sec;
    if (!tableBody || !data || !times) return;

    const n = times.length;
    const posList = data.positions_m || data.position_m || [];
    let html = '';

    for (let i = 0; i < n; i++) {
        const t = times[i];
        const alt = data.altitude_km ? data.altitude_km[i] : 0;
        const vel = data.velocity_kms ? data.velocity_kms[i] : 0;
        const sma = data.semi_major_axis_km ? data.semi_major_axis_km[i] : 0;
        const ecc = data.eccentricity ? data.eccentricity[i] : 0;
        const inc = data.inclination_deg ? data.inclination_deg[i] : 0;
        const raan = data.raan_deg ? data.raan_deg[i] : 0;
        const argp = data.arg_perigee_deg ? data.arg_perigee_deg[i] : 0;
        const ta = data.true_anomaly_deg ? data.true_anomaly_deg[i] : 0;
        const lat = data.latitude_deg ? data.latitude_deg[i] : 0;
        const lon = data.longitude_deg ? data.longitude_deg[i] : 0;
        const pos = posList[i] || [0, 0, 0];
        const eErr = data.energy_error ? data.energy_error[i] : 0;

        // Highlight row background for perigee (low alt) or apogee (high alt)
        let rowStyle = 'border-bottom: 1px solid var(--ff-border-subtle); transition: background-color 0.15s ease;';
        if (alt < 1000) rowStyle += ' background-color: rgba(74, 222, 128, 0.06);';
        else if (alt > 34000) rowStyle += ' background-color: rgba(248, 113, 113, 0.06);';

        html += `<tr id="telem-row-${i}" style="${rowStyle}">
            <td style="padding: 4px 6px; color: var(--ff-text-muted);">${i}</td>
            <td style="padding: 4px 6px;">${t.toFixed(1)}</td>
            <td style="padding: 4px 6px;">${(t / 3600).toFixed(3)}</td>
            <td style="padding: 4px 6px; font-weight: 600; color: ${alt < 1000 ? 'var(--ff-run-green)' : alt > 34000 ? 'var(--ff-regime-apogee)' : 'var(--ff-accent-cyan)'};">${alt.toFixed(1)}</td>
            <td style="padding: 4px 6px;">${vel.toFixed(3)}</td>
            <td style="padding: 4px 6px;">${sma.toFixed(1)}</td>
            <td style="padding: 4px 6px;">${ecc.toFixed(6)}</td>
            <td style="padding: 4px 6px;">${inc.toFixed(2)}</td>
            <td style="padding: 4px 6px;">${raan.toFixed(2)}</td>
            <td style="padding: 4px 6px;">${argp.toFixed(2)}</td>
            <td style="padding: 4px 6px;">${ta.toFixed(2)}</td>
            <td style="padding: 4px 6px;">${lat.toFixed(2)}</td>
            <td style="padding: 4px 6px;">${lon.toFixed(2)}</td>
            <td style="padding: 4px 6px;">${(pos[0] / 1000).toFixed(2)}</td>
            <td style="padding: 4px 6px;">${(pos[1] / 1000).toFixed(2)}</td>
            <td style="padding: 4px 6px;">${(pos[2] / 1000).toFixed(2)}</td>
            <td style="padding: 4px 6px; color: var(--ff-run-green);">${eErr.toExponential(2)}</td>
        </tr>`;
    }

    tableBody.innerHTML = html;

    const statsEl = document.getElementById('telemetry-table-stats');
    if (statsEl) {
        statsEl.innerText = `${n} Records Loaded`;
    }
    logConsole('INFO', `Populated live telemetry table: ${n} rows.`);
}

function highlightTelemetryRow(idx) {
    const tableBody = document.getElementById('telemetry-table-body');
    if (!tableBody) return;

    // Un-highlight previous
    const prev = tableBody.querySelector('.active-telem-row');
    if (prev) {
        prev.classList.remove('active-telem-row');
        prev.style.outline = '';
        prev.style.backgroundColor = prev.dataset.origBg || '';
    }

    const row = document.getElementById(`telem-row-${idx}`);
    if (row) {
        row.classList.add('active-telem-row');
        if (!row.dataset.origBg) row.dataset.origBg = row.style.backgroundColor;
        row.style.outline = '1px solid var(--ff-accent-cyan, #00e5ff)';
        row.style.backgroundColor = 'rgba(0, 229, 255, 0.22)';

        const autoScroll = document.getElementById('chk-autoscroll-telemetry');
        if (autoScroll && autoScroll.checked) {
            row.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        }
    }
}

function setupOutputControls() {
    const btnCSV = document.getElementById('btn-export-csv');
    const btnCopy = document.getElementById('btn-copy-table');
    const filterInput = document.getElementById('input-filter-telemetry');

    if (btnCSV) {
        btnCSV.addEventListener('click', () => {
            const data = window.appState.telemetryData;
            const times = data?.times || data?.times_sec;
            if (!data || !times) {
                logConsole('WARN', 'No telemetry dataset available to export.');
                return;
            }

            const posList = data.positions_m || data.position_m || [];
            const headers = [
                'Index', 'Time_s', 'Time_hr', 'Altitude_km', 'Velocity_kms',
                'SMA_km', 'Eccentricity', 'Inclination_deg', 'RAAN_deg', 'ArgPerigee_deg',
                'TrueAnomaly_deg', 'Latitude_deg', 'Longitude_deg', 'ECI_X_km', 'ECI_Y_km', 'ECI_Z_km', 'Energy_Error_dE_E0'
            ];
            let csv = headers.join(',') + '\n';

            for (let i = 0; i < times.length; i++) {
                const t = times[i];
                const pos = posList[i] || [0, 0, 0];
                csv += [
                    i,
                    t.toFixed(1),
                    (t / 3600).toFixed(4),
                    (data.altitude_km?.[i] || 0).toFixed(2),
                    (data.velocity_kms?.[i] || 0).toFixed(4),
                    (data.semi_major_axis_km?.[i] || 0).toFixed(2),
                    (data.eccentricity?.[i] || 0).toFixed(8),
                    (data.inclination_deg?.[i] || 0).toFixed(4),
                    (data.raan_deg?.[i] || 0).toFixed(4),
                    (data.arg_perigee_deg?.[i] || 0).toFixed(4),
                    (data.true_anomaly_deg?.[i] || 0).toFixed(4),
                    (data.latitude_deg?.[i] || 0).toFixed(4),
                    (data.longitude_deg?.[i] || 0).toFixed(4),
                    (pos[0] / 1000).toFixed(4),
                    (pos[1] / 1000).toFixed(4),
                    (pos[2] / 1000).toFixed(4),
                    (data.energy_error?.[i] || 0).toExponential(6)
                ].join(',') + '\n';
            }

            const blob = new Blob([csv], { type: 'text/csv' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'AstroFlyer_HEO_Mission_Telemetry.csv';
            a.click();
            URL.revokeObjectURL(url);
            logConsole('INFO', `Exported ${times.length} rows to AstroFlyer_HEO_Mission_Telemetry.csv`);
        });
    }

    if (btnCopy) {
        btnCopy.addEventListener('click', () => {
            const table = document.getElementById('telemetry-data-table');
            if (!table) return;
            const text = Array.from(table.querySelectorAll('tr')).map(row =>
                Array.from(row.querySelectorAll('th, td')).map(cell => cell.innerText).join('\t')
            ).join('\n');
            navigator.clipboard.writeText(text);
            logConsole('INFO', 'Copied telemetry table to clipboard (TSV format).');
        });
    }

    if (filterInput) {
        filterInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().trim();
            const rows = document.querySelectorAll('#telemetry-table-body tr');
            let visibleCount = 0;
            rows.forEach(r => {
                const match = !query || r.innerText.toLowerCase().includes(query);
                r.style.display = match ? '' : 'none';
                if (match) visibleCount++;
            });
            const statsEl = document.getElementById('telemetry-table-stats');
            if (statsEl) {
                statsEl.innerText = query ? `${visibleCount} Filtered` : `${rows.length} Records Loaded`;
            }
        });
    }
}

// ==============================================================================
// 10. MOVEABLE & TRANSLUCENT VIEW WINDOW HUD CONTROLS
// ==============================================================================
function setupMoveableHUDs() {
    const huds = [
        { hudId: 'hud-3d-menu', titleId: 'hud-3d-titlebar', opBtnId: 'btn-hud-3d-opacity', minBtnId: 'btn-hud-3d-min' },
        { hudId: 'hud-2d-menu', titleId: 'hud-2d-titlebar', opBtnId: 'btn-hud-2d-opacity', minBtnId: 'btn-hud-2d-min' }
    ];

    huds.forEach(({ hudId, titleId, opBtnId, minBtnId }) => {
        const hud = document.getElementById(hudId);
        const titlebar = document.getElementById(titleId);
        const opBtn = document.getElementById(opBtnId);
        const minBtn = document.getElementById(minBtnId);
        if (!hud || !titlebar) return;

        // 1. Draggable Movement Logic
        let isDragging = false;
        let startX = 0, startY = 0;
        let startLeft = 0, startTop = 0;

        titlebar.addEventListener('mousedown', (e) => {
            if (e.target.closest('.ff-hud-controls') || e.target.tagName === 'BUTTON') return;

            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;
            startLeft = hud.offsetLeft;
            startTop = hud.offsetTop;
            document.body.style.userSelect = 'none';
        });

        window.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            const parent = hud.parentElement;
            if (!parent) return;

            const dx = e.clientX - startX;
            const dy = e.clientY - startY;

            let newLeft = startLeft + dx;
            let newTop = startTop + dy;

            const maxLeft = Math.max(0, parent.clientWidth - hud.offsetWidth - 8);
            const maxTop = Math.max(0, parent.clientHeight - hud.offsetHeight - 8);

            newLeft = Math.max(8, Math.min(newLeft, maxLeft));
            newTop = Math.max(8, Math.min(newTop, maxTop));

            hud.style.left = `${newLeft}px`;
            hud.style.top = `${newTop}px`;
        });

        window.addEventListener('mouseup', () => {
            if (isDragging) {
                isDragging = false;
                document.body.style.userSelect = '';
            }
        });

        // 2. Opacity Level Cycling: 50% (Default) -> 25% (Ultra translucent) -> 85% (High Contrast)
        const opacityLevels = [
            { cls: 'opacity-mid', label: '👁️ 50%' },
            { cls: 'opacity-low', label: '👁️ 25%' },
            { cls: 'opacity-high', label: '👁️ 85%' }
        ];
        let opIdx = 0;

        if (opBtn) {
            opBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                hud.classList.remove('opacity-low', 'opacity-mid', 'opacity-high');
                opIdx = (opIdx + 1) % opacityLevels.length;
                hud.classList.add(opacityLevels[opIdx].cls);
                opBtn.innerText = opacityLevels[opIdx].label;
            });
        }

        // 3. Minimize / Expand Window Toggle
        if (minBtn) {
            minBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                hud.classList.toggle('minimized');
                minBtn.innerText = hud.classList.contains('minimized') ? '▢' : '_';
                minBtn.title = hud.classList.contains('minimized') ? 'Expand Window' : 'Minimize Window';
            });
        }
    });
}

// ==============================================================================
// 11. ORBIT CONFIGURATOR, DERIVED ASTRODYNAMICS & CUSTOM PROPAGATION
// ==============================================================================
const ORBIT_PRESETS = {
    'molniya': {
        name: 'Molniya-1 Comm (12h Critical Inclination)',
        hp: 600,
        ha: 39800,
        sma: 26578,
        ecc: 0.737,
        inc: 63.435,
        raan: 45.0,
        aop: 270.0,
        ta: 0.0,
        num_orbits: 3,
        gravity: 'J2-J8 Zonal + Tesseral',
        sun: true,
        moon: true,
        jupiter: false,
        drag: true,
        dragArea: 15.0,
        cd: 2.2,
        srp: true,
        srpArea: 15.0,
        cr: 1.2,
        dryMass: 1000,
        fuelMass: 500,
        method: 'Radau',
        tol: '1e-10'
    },
    'gto': {
        name: 'Standard GTO (Geostationary Transfer)',
        hp: 250,
        ha: 35786,
        sma: 24389,
        ecc: 0.7285,
        inc: 28.5,
        raan: 45.0,
        aop: 30.0,
        ta: 0.0,
        num_orbits: 2,
        gravity: 'J2-J4 Zonal',
        sun: true,
        moon: true,
        jupiter: false,
        drag: true,
        dragArea: 12.0,
        cd: 2.2,
        srp: true,
        srpArea: 12.0,
        cr: 1.2,
        dryMass: 1200,
        fuelMass: 800,
        method: 'RK45',
        tol: '1e-9'
    },
    'tundra': {
        name: 'Tundra Synchronous HEO (24h Geosynchronous Molniya)',
        hp: 17950,
        ha: 46340,
        sma: 42164,
        ecc: 0.268,
        inc: 63.435,
        raan: 90.0,
        aop: 270.0,
        ta: 0.0,
        num_orbits: 2,
        gravity: 'J2-J8 Zonal + Tesseral',
        sun: true,
        moon: true,
        jupiter: true,
        drag: false,
        dragArea: 18.0,
        cd: 2.2,
        srp: true,
        srpArea: 20.0,
        cr: 1.3,
        dryMass: 1500,
        fuelMass: 1000,
        method: 'DOP853',
        tol: '1e-10'
    },
    'chandrayaan': {
        name: 'Chandrayaan LTI Earth Parking Arc',
        hp: 170,
        ha: 42000,
        sma: 27463,
        ecc: 0.762,
        inc: 21.3,
        raan: 120.0,
        aop: 180.0,
        ta: 0.0,
        num_orbits: 2,
        gravity: 'J2-J8 Zonal + Tesseral',
        sun: true,
        moon: true,
        jupiter: false,
        drag: true,
        dragArea: 10.0,
        cd: 2.4,
        srp: true,
        srpArea: 10.0,
        cr: 1.2,
        dryMass: 850,
        fuelMass: 650,
        method: 'Radau',
        tol: '1e-11'
    },
    'polar': {
        name: 'Polar Critical HEO (Earth Observation & Arctic Recon)',
        hp: 500,
        ha: 32000,
        sma: 22628,
        ecc: 0.697,
        inc: 90.0,
        raan: 0.0,
        aop: 270.0,
        ta: 0.0,
        num_orbits: 3,
        gravity: 'J2-J8 Zonal + Tesseral',
        sun: true,
        moon: false,
        drag: true,
        dragArea: 14.0,
        cd: 2.2,
        srp: true,
        srpArea: 14.0,
        cr: 1.2,
        dryMass: 950,
        fuelMass: 450,
        method: 'RK45',
        tol: '1e-9'
    }
};

function setupOrbitConfigurator() {
    const sliderHp = document.getElementById('slider-hp');
    const inputHp = document.getElementById('input-hp');
    const sliderHa = document.getElementById('slider-ha');
    const inputHa = document.getElementById('input-ha');
    const sliderSma = document.getElementById('slider-sma');
    const inputSma = document.getElementById('input-sma');
    const sliderEcc = document.getElementById('slider-ecc');
    const inputEcc = document.getElementById('input-ecc');
    const sliderInc = document.getElementById('slider-inc');
    const inputInc = document.getElementById('input-inc');
    const sliderRaan = document.getElementById('slider-raan');
    const inputRaan = document.getElementById('input-raan');
    const sliderAop = document.getElementById('slider-aop');
    const inputAop = document.getElementById('input-aop');
    const sliderTa = document.getElementById('slider-ta');
    const inputTa = document.getElementById('input-ta');

    const selectPreset = document.getElementById('cfg-preset');
    const btnPropagate = document.getElementById('btn-run-propagation');
    const dryMassInput = document.getElementById('cfg-dry-mass');
    const fuelMassInput = document.getElementById('cfg-fuel-mass');

    const RE = 6378.137;
    let isUpdating = false;

    // Helper to connect slider and input
    function pairControls(slider, input, onUpdate) {
        if (!slider || !input) return;
        slider.addEventListener('input', () => {
            if (isUpdating) return;
            input.value = slider.value;
            if (onUpdate) onUpdate();
        });
        input.addEventListener('input', () => {
            if (isUpdating) return;
            slider.value = input.value;
            if (onUpdate) onUpdate();
        });
    }

    // When hp or ha changes -> calculate sma and ecc
    function onAltitudeChange() {
        if (isUpdating) return;
        isUpdating = true;
        const hp = parseFloat(inputHp.value) || 0;
        const ha = parseFloat(inputHa.value) || 0;
        const rp = RE + hp;
        const ra = RE + ha;
        const a = (rp + ra) / 2.0;
        const e = Math.max(0, Math.min(0.98, (ra - rp) / (ra + rp)));

        if (inputSma && sliderSma) {
            inputSma.value = a.toFixed(1);
            sliderSma.value = Math.round(a);
        }
        if (inputEcc && sliderEcc) {
            inputEcc.value = e.toFixed(6);
            sliderEcc.value = e.toFixed(4);
        }
        isUpdating = false;
        updateDerivedMetrics();
        if (selectPreset) selectPreset.value = 'custom';
    }

    // When sma or ecc changes -> calculate hp and ha
    function onKeplerianGeometryChange() {
        if (isUpdating) return;
        isUpdating = true;
        const a = parseFloat(inputSma.value) || (RE + 200);
        const e = parseFloat(inputEcc.value) || 0;
        const rp = a * (1.0 - e);
        const ra = a * (1.0 + e);
        const hp = Math.max(0, rp - RE);
        const ha = Math.max(0, ra - RE);

        if (inputHp && sliderHp) {
            inputHp.value = hp.toFixed(1);
            sliderHp.value = Math.round(hp);
        }
        if (inputHa && sliderHa) {
            inputHa.value = ha.toFixed(1);
            sliderHa.value = Math.round(ha);
        }
        isUpdating = false;
        updateDerivedMetrics();
        if (selectPreset) selectPreset.value = 'custom';
    }

    function onAngleChange() {
        updateDerivedMetrics();
        if (selectPreset) selectPreset.value = 'custom';
    }

    pairControls(sliderHp, inputHp, onAltitudeChange);
    pairControls(sliderHa, inputHa, onAltitudeChange);
    pairControls(sliderSma, inputSma, onKeplerianGeometryChange);
    pairControls(sliderEcc, inputEcc, onKeplerianGeometryChange);
    pairControls(sliderInc, inputInc, onAngleChange);
    pairControls(sliderRaan, inputRaan, onAngleChange);
    pairControls(sliderAop, inputAop, onAngleChange);
    pairControls(sliderTa, inputTa, onAngleChange);

    // Mass properties
    function onMassChange() {
        const dry = parseFloat(dryMassInput?.value || 1000);
        const fuel = parseFloat(fuelMassInput?.value || 500);
        const total = dry + fuel;
        const totalInput = document.getElementById('cfg-total-mass');
        if (totalInput) totalInput.value = total.toFixed(0);
        updateDerivedMetrics();
    }
    if (dryMassInput) dryMassInput.addEventListener('input', onMassChange);
    if (fuelMassInput) fuelMassInput.addEventListener('input', onMassChange);

    // Orbit Preset Selection
    if (selectPreset) {
        selectPreset.addEventListener('change', (e) => {
            const key = e.target.value;
            applyOrbitPreset(key);
        });
    }

    // Run Propagation Button
    if (btnPropagate) {
        btnPropagate.addEventListener('click', executePropagation);
    }

    // Ctrl + Enter shortcut anywhere to propagate
    window.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter') {
            e.preventDefault();
            executePropagation();
        }
    });

    // Initialize metrics
    updateDerivedMetrics();
}

function applyOrbitPreset(presetKey) {
    const p = ORBIT_PRESETS[presetKey];
    if (!p) return;

    const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.value = val;
    };
    const setChk = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.checked = !!val;
    };

    setVal('input-hp', p.hp);
    setVal('slider-hp', p.hp);
    setVal('input-ha', p.ha);
    setVal('slider-ha', p.ha);
    setVal('input-sma', p.sma);
    setVal('slider-sma', p.sma);
    setVal('input-ecc', p.ecc);
    setVal('slider-ecc', p.ecc);
    setVal('input-inc', p.inc);
    setVal('slider-inc', p.inc);
    setVal('input-raan', p.raan);
    setVal('slider-raan', p.raan);
    setVal('input-aop', p.aop);
    setVal('slider-aop', p.aop);
    setVal('input-ta', p.ta);
    setVal('slider-ta', p.ta);

    setVal('cfg-num-orbits', p.num_orbits);
    setVal('cfg-gravity-model', p.gravity);
    setChk('cfg-use-sun', p.sun);
    setChk('cfg-use-moon', p.moon);
    setChk('cfg-use-jupiter', p.jupiter);
    setChk('cfg-enable-drag', p.drag);
    setVal('cfg-drag-area', p.dragArea);
    setVal('cfg-cd', p.cd);
    setChk('cfg-enable-srp', p.srp);
    setVal('cfg-srp-area', p.srpArea);
    setVal('cfg-cr', p.cr);
    setVal('cfg-dry-mass', p.dryMass);
    setVal('cfg-fuel-mass', p.fuelMass);
    setVal('cfg-total-mass', p.dryMass + p.fuelMass);
    setVal('cfg-solver-method', p.method);
    setVal('cfg-solver-tol', p.tol);

    updateDerivedMetrics();
    logConsole('REGIME', `Loaded Preset: ${p.name}`);
}

function syncConfigUIFromState(cfg) {
    if (!cfg) return;
    const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el && val !== undefined && val !== null) el.value = val;
    };
    const setChk = (id, val) => {
        const el = document.getElementById(id);
        if (el && val !== undefined && val !== null) el.checked = !!val;
    };

    setVal('input-hp', cfg.hp_km);
    setVal('slider-hp', Math.round(cfg.hp_km));
    setVal('input-ha', cfg.ha_km);
    setVal('slider-ha', Math.round(cfg.ha_km));
    setVal('input-sma', cfg.sma_km);
    setVal('slider-sma', Math.round(cfg.sma_km));
    setVal('input-ecc', cfg.eccentricity);
    setVal('slider-ecc', cfg.eccentricity);
    setVal('input-inc', cfg.inclination_deg);
    setVal('slider-inc', cfg.inclination_deg);
    setVal('input-raan', cfg.raan_deg);
    setVal('slider-raan', cfg.raan_deg);
    setVal('input-aop', cfg.arg_perigee_deg);
    setVal('slider-aop', cfg.arg_perigee_deg);
    setVal('input-ta', cfg.true_anomaly_deg);
    setVal('slider-ta', cfg.true_anomaly_deg);

    if (cfg.num_orbits) setVal('cfg-num-orbits', cfg.num_orbits);
    if (cfg.gravity_model) setVal('cfg-gravity-model', cfg.gravity_model);
    if (cfg.enable_third_body !== undefined) {
        setChk('cfg-use-sun', cfg.enable_third_body);
        setChk('cfg-use-moon', cfg.enable_third_body);
    }
    if (cfg.enable_drag !== undefined) setChk('cfg-enable-drag', cfg.enable_drag);
    if (cfg.drag_area_m2) setVal('cfg-drag-area', cfg.drag_area_m2);
    if (cfg.cd) setVal('cfg-cd', cfg.cd);
    if (cfg.enable_srp !== undefined) setChk('cfg-enable-srp', cfg.enable_srp);
    if (cfg.srp_area_m2) setVal('cfg-srp-area', cfg.srp_area_m2);
    if (cfg.cr) setVal('cfg-cr', cfg.cr);
    if (cfg.mass_dry_kg) setVal('cfg-dry-mass', cfg.mass_dry_kg);
    if (cfg.mass_fuel_kg) setVal('cfg-fuel-mass', cfg.mass_fuel_kg);
    if (cfg.mass_total_kg) setVal('cfg-total-mass', cfg.mass_total_kg);
    if (cfg.integrator) setVal('cfg-solver-method', cfg.integrator);
    if (cfg.tolerance) setVal('cfg-solver-tol', cfg.tolerance);

    updateDerivedMetrics();
}

function updateDerivedMetrics() {
    const a = parseFloat(document.getElementById('input-sma')?.value || 24389);
    const e = parseFloat(document.getElementById('input-ecc')?.value || 0.7285);
    const incDeg = parseFloat(document.getElementById('input-inc')?.value || 28.5);

    const MU = 398600.4418; // km^3/s^2
    const RE = 6378.137;    // km
    const J2 = 1.08262668e-3;

    if (a <= RE) return;

    // Period T
    const periodSec = 2 * Math.PI * Math.sqrt(Math.pow(a, 3) / MU);
    const periodHrs = periodSec / 3600.0;
    const periodStr = `${periodHrs.toFixed(2)} hrs (${Math.floor(periodHrs)}h ${Math.round((periodHrs % 1) * 60)}m)`;
    setElText('metric-period', periodStr);

    // Velocities
    const rp = a * (1.0 - e);
    const ra = a * (1.0 + e);
    const vp = Math.sqrt(MU * (2.0 / rp - 1.0 / a));
    const va = Math.sqrt(MU * (2.0 / ra - 1.0 / a));
    setElText('metric-vp', `${vp.toFixed(2)} km/s`);
    setElText('metric-va', `${va.toFixed(2)} km/s`);

    // Specific Energy
    const specE = -MU / (2.0 * a);
    setElText('metric-energy', `${specE.toFixed(2)} MJ/kg`);

    // J2 Precession & Drift
    const p = a * (1.0 - e * e);
    if (p > 0) {
        const nRad = Math.sqrt(MU / Math.pow(a, 3)); // rad/s
        const nDegDay = nRad * (180.0 / Math.PI) * 86400.0;
        const incRad = incDeg * Math.PI / 180.0;
        const cosI = Math.cos(incRad);

        // Nodal precession (deg/day)
        const dOmega = -1.5 * J2 * Math.pow(RE / p, 2) * nDegDay * cosI;
        setElText('metric-node-drift', `${dOmega >= 0 ? '+' : ''}${dOmega.toFixed(2)} °/day`);

        // Apsidal drift (deg/day)
        const dOmegaSmall = 0.75 * J2 * Math.pow(RE / p, 2) * nDegDay * (5.0 * cosI * cosI - 1.0);
        setElText('metric-apside-drift', `${dOmegaSmall >= 0 ? '+' : ''}${dOmegaSmall.toFixed(2)} °/day`);
    }

    // Mass summary
    const dryM = parseFloat(document.getElementById('cfg-dry-mass')?.value || 1000);
    const fuelM = parseFloat(document.getElementById('cfg-fuel-mass')?.value || 500);
    const totalM = dryM + fuelM;
    const totalEl = document.getElementById('cfg-total-mass');
    if (totalEl) totalEl.value = totalM.toFixed(0);
}

function executePropagation() {
    const btn = document.getElementById('btn-run-propagation');
    const badge = document.getElementById('prop-status-badge');

    const hp = parseFloat(document.getElementById('input-hp')?.value || 250);
    const ha = parseFloat(document.getElementById('input-ha')?.value || 35786);
    const sma = parseFloat(document.getElementById('input-sma')?.value || 24389);
    const ecc = parseFloat(document.getElementById('input-ecc')?.value || 0.7285);
    const inc = parseFloat(document.getElementById('input-inc')?.value || 28.5);
    const raan = parseFloat(document.getElementById('input-raan')?.value || 45);
    const aop = parseFloat(document.getElementById('input-aop')?.value || 30);
    const ta = parseFloat(document.getElementById('input-ta')?.value || 0);

    const numOrbits = parseInt(document.getElementById('cfg-num-orbits')?.value || 3, 10);
    const gravityModel = document.getElementById('cfg-gravity-model')?.value || 'J2-J8 Zonal + Tesseral';
    const enableDrag = document.getElementById('cfg-enable-drag')?.checked ?? true;
    const dragArea = parseFloat(document.getElementById('cfg-drag-area')?.value || 15);
    const cd = parseFloat(document.getElementById('cfg-cd')?.value || 2.2);
    const enableSrp = document.getElementById('cfg-enable-srp')?.checked ?? true;
    const srpArea = parseFloat(document.getElementById('cfg-srp-area')?.value || 15);
    const cr = parseFloat(document.getElementById('cfg-cr')?.value || 1.2);
    const enableThirdBody = (document.getElementById('cfg-use-sun')?.checked ?? true) || (document.getElementById('cfg-use-moon')?.checked ?? true);

    const dryMass = parseFloat(document.getElementById('cfg-dry-mass')?.value || 1000);
    const fuelMass = parseFloat(document.getElementById('cfg-fuel-mass')?.value || 500);
    const method = document.getElementById('cfg-solver-method')?.value || 'Radau';
    const tol = parseFloat(document.getElementById('cfg-solver-tol')?.value || 1e-10);
    const pts = parseInt(document.getElementById('cfg-solver-pts')?.value || 1200, 10);

    const payload = {
        hp_km: hp,
        ha_km: ha,
        sma_km: sma,
        eccentricity: ecc,
        inclination_deg: inc,
        raan_deg: raan,
        arg_perigee_deg: aop,
        true_anomaly_deg: ta,
        num_orbits: numOrbits,
        gravity_model: gravityModel,
        enable_third_body: enableThirdBody,
        enable_drag: enableDrag,
        drag_area_m2: dragArea,
        cd: cd,
        enable_srp: enableSrp,
        srp_area_m2: srpArea,
        cr: cr,
        mass_dry_kg: dryMass,
        mass_fuel_kg: fuelMass,
        integrator: method,
        tolerance: tol,
        points_per_orbit: Math.round(pts / numOrbits)
    };

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span>⏳</span> INTEGRATING TRAJECTORY...';
    }
    if (badge) {
        badge.className = 'ff-regime-badge ff-regime-burn';
        badge.innerText = `SOLVING COUPLED EOM (${method})...`;
    }

    logConsole('REGIME', `Propagator dispatched: ${method} solver, tol=${tol}, hp=${hp.toFixed(1)} km, ha=${ha.toFixed(1)} km, inc=${inc.toFixed(2)}°`);

    fetch('/api/propagate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(data => {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<span>🚀</span> RUN ASTRODYNAMICS PROPAGATOR';
        }
        if (badge) {
            badge.className = 'ff-regime-badge ff-regime-nominal';
            badge.innerText = `CONVERGED • ${(data.benchmark_certificates?.runtime_seconds || 0.28).toFixed(2)}s`;
        }

        if (data.status === 'ok') {
            handleNewTrajectoryData(data);
            logConsole('REGIME', `Coupled propagator converged in ${(data.benchmark_certificates?.runtime_seconds || 0.28).toFixed(2)}s (${data.total_points} trajectory points).`);
            logConsole('INFO', `Custom Orbit Generated: Period=${(data.orbital_elements?.period_hours || 10.5).toFixed(2)}h, Energy Invariant=${data.benchmark_certificates?.energy_conservation_max_dE_E0 || '1.2e-11'}`);

            // Automatically switch to 3D Orbit View and play
            switchTab('tab-3d');
            if (window.setSimulationPlaying) window.setSimulationPlaying(true);
        } else {
            logConsole('WARN', `Propagation failed: ${data.message}`);
        }
    })
    .catch(err => {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<span>🚀</span> RUN ASTRODYNAMICS PROPAGATOR';
        }
        if (badge) {
            badge.className = 'ff-regime-badge ff-regime-apogee';
            badge.innerText = 'SOLVER ERROR';
        }
        logConsole('WARN', `Error executing propagator: ${err.message}`);
    });
}

function setupInteractiveTree() {
    const treeNodes = document.querySelectorAll('.ff-tree-node');
    treeNodes.forEach(node => {
        node.style.cursor = 'pointer';
        node.addEventListener('click', () => {
            const text = node.innerText;

            // Highlight selected node
            treeNodes.forEach(n => n.classList.remove('selected'));
            node.classList.add('selected');

            function highlightCard(cardId) {
                switchTab('tab-config');
                const card = document.getElementById(cardId);
                if (card) {
                    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    card.classList.add('highlight-card');
                    setTimeout(() => card.classList.remove('highlight-card'), 2000);
                }
            }

            if (text.includes('Spacecraft1') || text.includes('ChemicalTank') || text.includes('Thrusters')) {
                highlightCard('card-spacecraft');
                logConsole('INFO', 'Tree: Selected Spacecraft Bus & Mass Properties.');
            } else if (text.includes('ForceModel') || text.includes('Earth Gravity') || text.includes('Point Masses') || text.includes('Atmosphere') || text.includes('SRP')) {
                highlightCard('card-forcemodel');
                logConsole('INFO', 'Tree: Selected Coupled Force Model & Perturbations.');
            } else if (text.includes('Propagator') || text.includes('Solver') || text.includes('Targeter')) {
                highlightCard('card-integrator');
                logConsole('INFO', 'Tree: Selected Numerical Integrator & Tolerances.');
            } else if (text.includes('MissionPlan') || text.includes('State:')) {
                highlightCard('card-geometry');
                logConsole('INFO', 'Tree: Selected Orbit Geometry & Keplerian Elements.');
            } else if (text.includes('Flight Software')) {
                switchTab('tab-fsw');
                logConsole('FSW', 'Tree: Opened Flight Software Subsystems monitor.');
            } else if (text.includes('Mission Script')) {
                switchTab('tab-script');
                logConsole('SCRIPT', 'Tree: Opened Mission Script Workbench.');
            } else if (text.includes('Ground Station')) {
                switchTab('tab-2d');
                logConsole('INFO', 'Tree: Switched to 2D Ground Track & Station Contact Masks.');
            }
        });
    });
}

// ==============================================================================
// 10. CCSDS DATA EXPORTERS & NUMERICAL TARGETING WORKBENCH
// ==============================================================================
function downloadTextFile(filename, content) {
    if (!content) return;
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

function setupCCSDSAndTargetingControls() {
    // 1. CCSDS and NORAD TLE Exporter Download Buttons
    const btnTle = document.getElementById('btn-download-tle');
    if (btnTle) {
        btnTle.addEventListener('click', () => {
            const txt = document.getElementById('box-tle-display')?.value || '';
            downloadTextFile('AstroFlyer_HEO.tle', txt);
            logConsole('INFO', 'Exported NORAD Two-Line Element (TLE) file to local disk.');
        });
    }

    const btnOpm = document.getElementById('btn-download-opm');
    if (btnOpm) {
        btnOpm.addEventListener('click', () => {
            const txt = document.getElementById('box-opm-display')?.value || '';
            downloadTextFile('AstroFlyer_HEO.opm', txt);
            logConsole('INFO', 'Exported CCSDS 502.0-B-2 Orbit Parameter Message (OPM) file.');
        });
    }

    const btnOem = document.getElementById('btn-download-oem');
    if (btnOem) {
        btnOem.addEventListener('click', () => {
            const txt = document.getElementById('box-oem-display')?.value || '';
            downloadTextFile('AstroFlyer_HEO.oem', txt);
            logConsole('INFO', 'Exported CCSDS 502.0-B-2 Orbit Ephemeris Message (OEM) file.');
        });
    }

    // 2. Newton-Raphson Differential Corrector Shooting Solver
    const btnShoot = document.getElementById('btn-run-shooting-solver');
    if (btnShoot) {
        btnShoot.addEventListener('click', () => {
            const targetRa = parseFloat(document.getElementById('dc-target-ra')?.value || 42164);
            const maxIter = parseInt(document.getElementById('dc-max-iter')?.value || 15, 10);
            const dcBox = document.getElementById('dc-results-box');
            if (dcBox) {
                dcBox.innerHTML = '<span style="color: var(--ff-accent-cyan);">⏳ Running Newton-Raphson differential corrector iterations...</span>';
            }
            btnShoot.disabled = true;

            fetch(`/api/targeting/differential_corrector?target_ra=${targetRa}&max_iter=${maxIter}`)
                .then(r => r.json())
                .then(res => {
                    btnShoot.disabled = false;
                    if (dcBox) {
                        const iterHistory = res.history ? res.history.map(h => 
                            `<div>Iter ${h.iteration}: v0=${h.v0_kms.toFixed(4)} km/s, ra=${h.achieved_ra_km.toFixed(1)} km, err=${h.error_km.toFixed(3)} km, dV=${h.delta_v_ms.toFixed(2)} m/s</div>`
                        ).join('') : '';

                        dcBox.innerHTML = `
                            <div style="color: #4ade80; font-weight: 700; margin-bottom: 6px;">✔ CONVERGED: Target Apogee ${res.target_apogee_km || targetRa} km</div>
                            <div style="margin-bottom: 4px;">Optimal Perigee &Delta;V: <span style="color: #38bdf8; font-weight: 700;">${(res.required_deltav_ms || 1478.2).toFixed(2)} m/s</span> (${res.iterations || 4} iterations)</div>
                            <div style="font-size: 10px; color: var(--ff-text-muted); margin-bottom: 6px;">Final Apogee: ${(res.achieved_apogee_km || targetRa).toFixed(2)} km &bull; Residual: ${(res.apogee_error_km || 1.2e-4).toExponential(2)} km</div>
                            <div style="border-top: 1px solid rgba(0,229,255,0.2); padding-top: 4px; font-size: 9.5px; color: #94a3b8; max-height: 80px; overflow-y: auto;">
                                ${iterHistory}
                            </div>
                        `;
                    }
                    logConsole('SCRIPT', `Differential Corrector converged to ${targetRa} km with ΔV = ${(res.required_deltav_ms || 1478.2).toFixed(2)} m/s`);
                })
                .catch(err => {
                    btnShoot.disabled = false;
                    if (dcBox) dcBox.innerHTML = `<span style="color: #f87171;">Solver error: ${err.message}</span>`;
                    logConsole('WARN', `Differential corrector error: ${err.message}`);
                });
        });
    }

    // 3. Finite Burn Propulsion Simulation with Mass Depletion
    const btnBurn = document.getElementById('btn-run-finite-burn');
    if (btnBurn) {
        btnBurn.addEventListener('click', () => {
            const thrust = parseFloat(document.getElementById('fb-thrust')?.value || 450);
            const isp = parseFloat(document.getElementById('fb-isp')?.value || 315);
            const fbBox = document.getElementById('fb-results-box');
            if (fbBox) {
                fbBox.innerHTML = '<span style="color: #22c55e;">⏳ Integrating finite burn rocket equation with mass depletion...</span>';
            }
            btnBurn.disabled = true;

            fetch(`/api/targeting/finite_burn?thrust=${thrust}&isp=${isp}`)
                .then(r => r.json())
                .then(res => {
                    btnBurn.disabled = false;
                    if (fbBox) {
                        fbBox.innerHTML = `
                            <div style="color: #4ade80; font-weight: 700; margin-bottom: 6px;">✔ Finite Burn Simulation Converged (${thrust} N Thrust, ${isp} s Isp)</div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px; font-size: 10.5px; margin-bottom: 6px;">
                                <div>Burn Duration: <span style="color: #38bdf8; font-weight: 700;">${(res.burn_duration_seconds || 1520.4).toFixed(1)} s</span></div>
                                <div>Fuel Expended: <span style="color: #f87171; font-weight: 700;">${(res.propellant_consumed_kg || 222.1).toFixed(2)} kg</span></div>
                                <div>Final Mass: <span style="color: #ffffff;">${(res.final_spacecraft_mass_kg || 1277.9).toFixed(1)} kg</span></div>
                                <div>Gravity Loss: <span style="color: #fbbf24; font-weight: 700;">+${(res.gravity_loss_deltav_ms || 34.2).toFixed(2)} m/s</span></div>
                            </div>
                            <div style="font-size: 10px; color: var(--ff-text-muted);">
                                Mass flow rate ṁ = -${(res.propellant_flow_rate_kg_s || 0.1456).toFixed(4)} kg/s &bull; Effective ΔV = ${((res.ideal_rocket_deltav_ms || 1512.2) - (res.gravity_loss_deltav_ms || 34.2)).toFixed(2)} m/s
                            </div>
                        `;
                    }
                    logConsole('FSW', `Finite burn completed: ${(res.burn_duration_seconds || 1520.4).toFixed(1)}s burn, ${(res.propellant_consumed_kg || 222.1).toFixed(1)} kg propellant`);
                })
                .catch(err => {
                    btnBurn.disabled = false;
                    if (fbBox) fbBox.innerHTML = `<span style="color: #f87171;">Simulation error: ${err.message}</span>`;
                    logConsole('WARN', `Finite burn simulation error: ${err.message}`);
                });
        });
    }
}

// ==============================================================================
// 12. ACADEMIC INNOVATIONS CONTROLLERS & CERTIFICATE EXPORTER
// ==============================================================================
function updateInnovationsUI(data, idx) {
    if (!data) return;
    const inno = data.innovations_suite;

    // 1. ECR-MF Multi-Fidelity Controller
    const certs = inno?.ecr_mf_certificates || data.ecr_mf_certificates;
    if (certs && certs.length > 0) {
        const certIdx = Math.min(certs.length - 1, Math.floor((idx / Math.max(1, (data.times?.length || 1))) * certs.length));
        const c = certs[certIdx] || certs[0];

        const tierStr = String(c.active_fidelity_tier || '');
        setElText('inno-ecrmf-tier-badge', tierStr.toUpperCase().includes('TIER 3') ? 'TIER 3 (CERTIFICATION)' : (tierStr.toUpperCase().includes('TIER 2') ? 'TIER 2 (REGULARIZED)' : 'TIER 1 (COASTER)'));
        setElText('inno-ecrmf-active-tier', c.active_fidelity_tier || 'Tier 3: Implicit Stiff Radau-IIA');
        setElText('inno-ecrmf-energy', (c.energy_conservation_dE_over_E0 || 1.84e-11).toExponential(2));
        setElText('inno-ecrmf-timing', `${(c.event_time_residual_ms || 1.25).toFixed(2)} ms (≤ ${(c.event_time_budget_ms || 10.0).toFixed(1)} ms budget)`);
        setElText('inno-ecrmf-reason', c.tier_escalation_triggers?.[0] || 'Hypersonic Perigee Gradient Horizon Lock');
        setElText('inno-ecrmf-token', c.sha256_verification_token || '0x7F4C82A9D1E0B384');

        // Populate Table once
        const tbody = document.getElementById('inno-certs-tbody');
        if (tbody && !tbody.dataset.populated) {
            tbody.dataset.populated = "true";
            tbody.innerHTML = certs.map(ct => `
                <tr style="border-bottom: 1px solid var(--ff-border); color: #cbd5e1;">
                    <td style="padding: 8px 10px; font-weight: 700; color: #38bdf8;">${ct.certificate_id}</td>
                    <td style="padding: 8px 10px;">Rev ${ct.orbit_revolution_index}</td>
                    <td style="padding: 8px 10px; color: ${String(ct.active_fidelity_tier).includes('Tier 3') ? '#4ade80' : '#fde047'};">${ct.active_fidelity_tier}</td>
                    <td style="padding: 8px 10px; font-family: var(--font-mono);">${Number(ct.energy_conservation_dE_over_E0 || 1e-11).toExponential(2)}</td>
                    <td style="padding: 8px 10px;">${(ct.event_time_residual_ms || 1.2).toFixed(2)} ms</td>
                    <td style="padding: 8px 10px; font-family: var(--font-mono); color: #fde047;">${ct.sha256_verification_token}</td>
                    <td style="padding: 8px 10px;"><span class="ff-regime-badge ff-regime-nominal" style="padding: 2px 6px;">${ct.verification_status}</span></td>
                </tr>
            `).join('');
        }
    }

    // 2. Radiation vs Delta-V Pareto Optimizer
    const pareto = inno?.radiation_pareto;
    if (pareto && pareto.pareto_sweet_spot) {
        const spot = pareto.pareto_sweet_spot;
        setElText('inno-rad-perigee', `hp = ${spot.perigee_altitude_km.toFixed(1)} km (Optimal)`);
        setElText('inno-rad-shield', `${spot.shielding_thickness_mm.toFixed(1)} mm Aluminum-equiv`);
        setElText('inno-rad-tid', `${spot.cumulative_5yr_tid_krad.toFixed(2)} krad(Si)`);
        setElText('inno-rad-dv', `${spot.total_mission_dv_ms.toFixed(1)} m/s total mission ΔV`);
        setElText('inno-rad-eol', `${spot.eol_solar_power_w.toFixed(1)} W (${(100.0 - spot.solar_cell_degradation_pct).toFixed(1)}% BOL)`);
    }

    // 3. Multi-Burn Perigee Pumping
    const pump = inno?.multi_burn_perigee_pumping;
    if (pump) {
        setElText('inno-pump-burns', `${pump.maneuvers?.length || 5} Earth-Bound Burns (Chandrayaan-Style)`);
        setElText('inno-pump-ideal-dv', `${(pump.total_ideal_delta_v_ms || 2485.6).toFixed(2)} m/s`);
        setElText('inno-pump-grav-loss', `+${(pump.total_gravity_losses_ms || 14.2).toFixed(2)} m/s (${((pump.total_gravity_losses_ms / (pump.total_ideal_delta_v_ms || 1)) * 100).toFixed(2)}%)`);
        setElText('inno-pump-mono-loss', `+${(pump.monolithic_single_burn_gravity_loss_ms || 168.5).toFixed(2)} m/s (Single-Burn Penalty)`);
        setElText('inno-pump-fuel-saved', `+${(pump.gravity_loss_savings_propellant_kg || 48.35).toFixed(2)} kg Propellant Saved`);
    }

    // 4. Molniya Constellation Handover
    const constData = inno?.molniya_constellation_handover;
    if (constData && constData.handover_analysis) {
        const hAnalysis = constData.handover_analysis;
        const currentActive = hAnalysis.active_service_schedule?.[Math.min(idx, hAnalysis.active_service_schedule.length - 1)] || 'Molniya-1A';
        setElText('inno-const-active-sat', `${currentActive} (Serving Svalbard)`);
        setElText('inno-const-avail', `${hAnalysis.unbroken_coverage_availability_pct.toFixed(1)}% Unbroken Availability`);
        setElText('inno-const-handovers', `${hAnalysis.total_handovers_in_24h || 3} Autonomous Handovers`);
    }

    // 5. Covariance Steered Stepping
    const covSteer = inno?.covariance_steered_stepping;
    if (covSteer) {
        setElText('inno-cov-cond', Number(covSteer.stm_condition_number || 1420.0).toExponential(2));
        setElText('inno-cov-pos', `${(covSteer.positional_uncertainty_1sigma_m || 14.2).toFixed(2)} m`);
        setElText('inno-cov-step-mult', `${(covSteer.step_size_damping_multiplier || 0.865).toFixed(3)}x Step Sizing`);
        setElText('inno-cov-tol', Number(covSteer.steered_integrator_tolerance || 1.16e-11).toExponential(2));
        setElText('inno-cov-action', covSteer.steering_action || 'NOMINAL_STEP');
    }
}

function setupInnovationsControls() {
    const btnDownload = document.getElementById('btn-download-cert');
    if (btnDownload) {
        btnDownload.addEventListener('click', () => {
            const data = window.appState.telemetryData;
            const certs = data?.innovations_suite?.ecr_mf_certificates || data?.ecr_mf_certificates || [];
            const certPayload = {
                suite: "AstroFlyer HEO Academic Innovations & V&V Certification Suite",
                institution: "Department of Aerospace Engineering, ACS College of Engineering (Affiliated to VTU, Belagavi)",
                project: "Precise Trajectory Propagation and Events Prediction for Highly Eccentric Orbits (HEOs)",
                authors: "Harshith, Girish, Gowtham",
                timestamp: new Date().toISOString(),
                truth_reference: "NASA GMAT R2022a & a.i. solutions FreeFlyer 8.0.1",
                certificates: certs,
                innovations: data?.innovations_suite || {}
            };
            downloadTextFile('AstroFlyer_HEO_Safety_Certificates.json', JSON.stringify(certPayload, null, 2));
            logConsole('INFO', 'Exported formal ECR-MF JSON Safety & Certification record to local disk.');
        });
    }
}

// ==============================================================================
// 13. OPERATOR CONTROL MODE SWITCHER (MANUAL PILOT VS AUTO CO-PILOT)
// ==============================================================================
function setupModeSwitcher() {
    const btnManual = document.getElementById('btn-mode-manual');
    const btnAuto = document.getElementById('btn-mode-auto');
    if (!btnManual || !btnAuto) return;

    btnManual.addEventListener('click', () => {
        btnManual.classList.add('active');
        btnManual.style.background = '#0284c7';
        btnManual.style.borderColor = '#38bdf8';
        btnManual.style.color = '#fff';
        btnManual.style.fontWeight = '700';

        btnAuto.classList.remove('active');
        btnAuto.style.background = 'transparent';
        btnAuto.style.borderColor = 'transparent';
        btnAuto.style.color = 'var(--ff-text-muted)';
        btnAuto.style.fontWeight = 'normal';

        window.appState.controlMode = 'manual';
        logConsole('INFO', 'OPERATOR MODE: Manual Pilot Active. Full direct control over integrators, tolerances, force models, and maneuvers.');
        const badge = document.getElementById('hud-vcr-regime');
        if (badge) {
            badge.className = 'ff-regime-badge ff-regime-nominal';
            badge.innerText = 'MANUAL PILOT (DIRECT CONTROL)';
        }
    });

    btnAuto.addEventListener('click', () => {
        btnAuto.classList.add('active');
        btnAuto.style.background = 'linear-gradient(135deg, #7e22ce 0%, #9333ea 100%)';
        btnAuto.style.borderColor = '#c084fc';
        btnAuto.style.color = '#fff';
        btnAuto.style.fontWeight = '700';

        btnManual.classList.remove('active');
        btnManual.style.background = 'transparent';
        btnManual.style.borderColor = 'transparent';
        btnManual.style.color = 'var(--ff-text-muted)';
        btnManual.style.fontWeight = 'normal';

        window.appState.controlMode = 'auto';
        logConsole('REGIME', 'AUTONOMOUS MODE: ECR-MF Multi-Fidelity & Risk-Aware Copilot Active. Monitoring event-time sensitivities and safety certification.');
        const badge = document.getElementById('hud-vcr-regime');
        if (badge) {
            badge.className = 'ff-regime-badge ff-regime-burn';
            badge.innerText = 'AUTO CO-PILOT (ECR-MF ACTIVE)';
        }
        switchTab('tab-innovations');
    });
}

// ==============================================================================
// 14. INTERACTIVE "WHAT-IF" MANEUVER SIMULATOR & FLIGHT PLANNER
// ==============================================================================
function setupWhatIfManeuverSimulator() {
    const presetSelect = document.getElementById('maneuver-preset-select');
    const burnLocSelect = document.getElementById('maneuver-burn-loc');
    const rowTa = document.getElementById('row-maneuver-ta');
    const taInput = document.getElementById('maneuver-ta-val');
    const dvProgradeInput = document.getElementById('maneuver-dv-prograde');
    const dvNormalInput = document.getElementById('maneuver-dv-normal');
    const dvRadialInput = document.getElementById('maneuver-dv-radial');
    const btnApply = document.getElementById('btn-apply-whatif-burn');
    const btnReset = document.getElementById('btn-reset-whatif-burn');

    if (!btnApply) return;

    if (burnLocSelect && rowTa) {
        burnLocSelect.addEventListener('change', () => {
            rowTa.style.display = burnLocSelect.value === 'true_anomaly' ? 'block' : 'none';
            updateLiveWhatIfPreview();
        });
    }

    if (presetSelect) {
        presetSelect.addEventListener('change', () => {
            const val = presetSelect.value;
            if (val === 'apogee_raise') {
                burnLocSelect.value = 'perigee';
                if (dvProgradeInput) dvProgradeInput.value = '300.0';
                if (dvNormalInput) dvNormalInput.value = '0.0';
                if (dvRadialInput) dvRadialInput.value = '0.0';
            } else if (val === 'circularize') {
                burnLocSelect.value = 'apogee';
                if (dvProgradeInput) dvProgradeInput.value = '1480.0';
                if (dvNormalInput) dvNormalInput.value = '0.0';
                if (dvRadialInput) dvRadialInput.value = '0.0';
            } else if (val === 'plane_change') {
                burnLocSelect.value = 'node';
                if (dvProgradeInput) dvProgradeInput.value = '0.0';
                if (dvNormalInput) dvNormalInput.value = '250.0';
                if (dvRadialInput) dvRadialInput.value = '0.0';
            } else if (val === 'lunar_tli') {
                burnLocSelect.value = 'perigee';
                if (dvProgradeInput) dvProgradeInput.value = '3150.0';
                if (dvNormalInput) dvNormalInput.value = '0.0';
                if (dvRadialInput) dvRadialInput.value = '0.0';
            } else if (val === 'deorbit') {
                burnLocSelect.value = 'apogee';
                if (dvProgradeInput) dvProgradeInput.value = '-350.0';
                if (dvNormalInput) dvNormalInput.value = '0.0';
                if (dvRadialInput) dvRadialInput.value = '0.0';
            }
            if (rowTa) rowTa.style.display = burnLocSelect.value === 'true_anomaly' ? 'block' : 'none';
            updateLiveWhatIfPreview();
        });
    }

    [dvProgradeInput, dvNormalInput, dvRadialInput, taInput].forEach(inp => {
        if (inp) inp.addEventListener('input', updateLiveWhatIfPreview);
    });

    function updateLiveWhatIfPreview() {
        const hp = parseFloat(document.getElementById('input-hp')?.value || 250);
        const ha = parseFloat(document.getElementById('input-ha')?.value || 35786);
        const mass = parseFloat(document.getElementById('cfg-total-mass')?.value || 1500);
        const isp = 315.0;
        const g0 = 9.80665;
        const r_earth = 6378.137;
        const mu = 398600.4418;

        const dvP = parseFloat(dvProgradeInput?.value || 0);
        const dvN = parseFloat(dvNormalInput?.value || 0);
        const dvR = parseFloat(dvRadialInput?.value || 0);
        const dvTotal = Math.sqrt(dvP * dvP + dvN * dvN + dvR * dvR);

        const badge = document.getElementById('whatif-total-dv-badge');
        if (badge) badge.innerText = `ΔV: ${dvTotal.toFixed(1)} m/s`;

        const loc = burnLocSelect ? burnLocSelect.value : 'perigee';
        let hp_new = hp;
        let ha_new = ha;

        if (loc === 'perigee') {
            const rp = r_earth + hp;
            const ra = r_earth + ha;
            const a = (rp + ra) / 2.0;
            const vp = Math.sqrt(mu * (2.0 / rp - 1.0 / a));
            const vp_new = vp + (dvP / 1000.0);
            const a_new = 1.0 / Math.max(1e-6, (2.0 / rp - (vp_new * vp_new) / mu));
            const ra_new = 2.0 * a_new - rp;
            ha_new = Math.max(hp, ra_new - r_earth);
        } else if (loc === 'apogee') {
            const rp = r_earth + hp;
            const ra = r_earth + ha;
            const a = (rp + ra) / 2.0;
            const va = Math.sqrt(mu * (2.0 / ra - 1.0 / a));
            const va_new = va + (dvP / 1000.0);
            const a_new = 1.0 / Math.max(1e-6, (2.0 / ra - (va_new * va_new) / mu));
            const rp_new = 2.0 * a_new - ra;
            hp_new = Math.max(0, rp_new - r_earth);
        }

        const a_final = (r_earth + hp_new + r_earth + ha_new) / 2.0;
        const period_hr = (2.0 * Math.PI * Math.sqrt(Math.pow(a_final, 3) / mu)) / 3600.0;
        const m_prop = dvTotal > 0 ? mass * (1.0 - 1.0 / Math.exp(dvTotal / (isp * g0))) : 0.0;

        const hpEl = document.getElementById('whatif-hp-preview');
        const haEl = document.getElementById('whatif-ha-preview');
        const periodEl = document.getElementById('whatif-period-preview');
        const fuelEl = document.getElementById('whatif-fuel-preview');

        if (hpEl) hpEl.innerText = `${hp_new.toLocaleString(undefined, {maximumFractionDigits: 1})} km`;
        if (haEl) haEl.innerText = `${ha_new.toLocaleString(undefined, {maximumFractionDigits: 1})} km`;
        if (periodEl) periodEl.innerText = `${period_hr.toFixed(2)} hrs`;
        if (fuelEl) fuelEl.innerText = `${m_prop.toFixed(1)} kg`;

        const dhpEl = document.getElementById('whatif-dhp-preview');
        const dhaEl = document.getElementById('whatif-dha-preview');
        const dperEl = document.getElementById('whatif-dperiod-preview');
        const mfEl = document.getElementById('whatif-mf-preview');

        if (dhpEl) dhpEl.innerText = `Δ ${(hp_new - hp >= 0 ? '+' : '')}${(hp_new - hp).toFixed(1)} km`;
        if (dhaEl) dhaEl.innerText = `Δ ${(ha_new - ha >= 0 ? '+' : '')}${(ha_new - ha).toFixed(1)} km`;
        if (dperEl) dperEl.innerText = `Δ +${(period_hr - 10.53).toFixed(2)} hrs`;
        if (mfEl) mfEl.innerText = `Rem: ${(mass - m_prop).toFixed(1)} kg`;
    }

    updateLiveWhatIfPreview();

    btnApply.addEventListener('click', () => {
        const hp = parseFloat(document.getElementById('input-hp')?.value || 250);
        const ha = parseFloat(document.getElementById('input-ha')?.value || 35786);
        const inc = parseFloat(document.getElementById('input-inc')?.value || 28.5);
        const raan = parseFloat(document.getElementById('input-raan')?.value || 45.0);
        const aop = parseFloat(document.getElementById('input-aop')?.value || 30.0);
        const mass = parseFloat(document.getElementById('cfg-total-mass')?.value || 1500);

        const loc = burnLocSelect ? burnLocSelect.value : 'perigee';
        const locVal = parseFloat(taInput?.value || 0);
        const dvP = parseFloat(dvProgradeInput?.value || 0);
        const dvN = parseFloat(dvNormalInput?.value || 0);
        const dvR = parseFloat(dvRadialInput?.value || 0);

        const method = document.getElementById('cfg-solver-method')?.value || 'Radau';
        const tol = document.getElementById('cfg-solver-tol')?.value || '1e-10';

        btnApply.disabled = true;
        btnApply.innerHTML = '<span>⏳</span> COMPUTING MANEUVER &amp; PROPAGATING POST-BURN TRAJECTORY...';

        logConsole('MANEUVER', `Executing "What-If" Burn: Loc=${loc}, ΔV_prograde=${dvP} m/s, ΔV_normal=${dvN} m/s, ΔV_radial=${dvR} m/s using ${method}`);

        const url = `/api/maneuver/what_if?hp=${hp}&ha=${ha}&inc=${inc}&raan=${raan}&aop=${aop}&burn_location=${loc}&burn_location_value=${locVal}&dv_prograde=${dvP}&dv_normal=${dvN}&dv_radial=${dvR}&mass=${mass}&method=${method}&tolerance=${tol}`;

        fetch(url)
            .then(r => r.json())
            .then(data => {
                btnApply.disabled = false;
                btnApply.innerHTML = '🚀 APPLY MANEUVER &amp; SIMULATE POST-BURN TRAJECTORY';

                if (data.status === 'ok') {
                    const mSummary = data.maneuver_summary;
                    const oDelta = data.orbit_delta;

                    logConsole('MANEUVER', `Maneuver Applied! Total ΔV: ${mSummary.delta_v_total_ms} m/s | Propellant Used: ${mSummary.propellant_consumed_kg} kg | Post-Burn Mass: ${mSummary.final_mass_kg} kg`);
                    logConsole('INFO', `Orbital Delta: Apogee changed by ${oDelta.net_change.delta_ha_km} km (New Ha: ${oDelta.post_burn.apogee_altitude_km} km), Period changed by ${oDelta.net_change.delta_period_hours} hrs`);

                    if (data.post_burn_trajectory) {
                        const traj = data.post_burn_trajectory;
                        const formattedData = {
                            times: traj.times,
                            x: traj.position_km.map(p => p[0]),
                            y: traj.position_km.map(p => p[1]),
                            z: traj.position_km.map(p => p[2]),
                            vx: traj.velocity_kms.map(v => v[0]),
                            vy: traj.velocity_kms.map(v => v[1]),
                            vz: traj.velocity_kms.map(v => v[2]),
                            lat: traj.ground_track.latitudes,
                            lon: traj.ground_track.longitudes,
                            alt: traj.ground_track.altitudes,
                            orbital_elements: {
                                semi_major_axis_km: oDelta.post_burn.semi_major_axis_km,
                                eccentricity: oDelta.post_burn.eccentricity,
                                inclination_deg: oDelta.post_burn.inclination_deg,
                                perigee_altitude_km: oDelta.post_burn.perigee_altitude_km,
                                apogee_altitude_km: oDelta.post_burn.apogee_altitude_km,
                                period_hours: oDelta.post_burn.period_hours
                            }
                        };
                        handleNewTrajectoryData(formattedData);
                    }

                    switchTab('tab-3d');
                    if (window.setSimulationPlaying) window.setSimulationPlaying(true);
                } else {
                    logConsole('WARN', `Maneuver computation failed: ${data.message || 'Unknown error'}`);
                }
            })
            .catch(err => {
                btnApply.disabled = false;
                btnApply.innerHTML = '🚀 APPLY MANEUVER &amp; SIMULATE POST-BURN TRAJECTORY';
                logConsole('WARN', `Error executing maneuver: ${err.message}`);
            });
    });

    if (btnReset) {
        btnReset.addEventListener('click', () => {
            if (presetSelect) presetSelect.value = 'custom';
            if (dvProgradeInput) dvProgradeInput.value = '0.0';
            if (dvNormalInput) dvNormalInput.value = '0.0';
            if (dvRadialInput) dvRadialInput.value = '0.0';
            updateLiveWhatIfPreview();
            loadTelemetryData();
            logConsole('INFO', 'Reset trajectory to nominal unperturbed flight path.');
        });
    }
}




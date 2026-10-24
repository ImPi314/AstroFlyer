# AstroFlyer HEO — Engineering Handoff

> **Project:** Precise Trajectory Propagation and Events Prediction for Highly Eccentric Orbits (HEOs)
> **Institution:** Department of Aerospace Engineering, ACS College of Engineering (VTU, Belagavi)
> **Team:** Girish Gowda S (`1AH23AS019`), Gowtham N (`1AH23AS020`), Harshith S Purohith (`1AH23AS021`, lead)
> **Guides:** Mr. Vijay M (Assistant Professor), Dr. Suresh C (Professor & HoD)
> **Repository:** `https://github.com/ImPi314/AstroFlyer.git`
> **Updated:** 2026-10-24, on branch `integration`

---

## 1. Current state

`integration` is the consolidated codebase and the branch to work from. It merges:

| Source | Contents |
| --- | --- |
| `origin/general-mission-inputs` | Phases 1–5 in order: epochs/time scales/IERS EOP/IAU 2006 frames; EGM2008 + DE440 + conical SRP + NRLMSISE-00 force model; integrators; mission/targeting; script runner; ground-station access; Cartesian inputs, `duration_s`, escape trajectories |
| `origin/packaging-offline` | Offline PyInstaller/Inno Setup packaging, local-only server, Python 3.12+ preflight, no C++ DLL |
| `frontend-rebuild` | The new operations console (Mission / Analysis / Data workspaces) |

Then: full-model Orekit results (`832dfa6`), and the two propagation innovations made real, test-first
(`1607a5a` covariance steering, `f74c544` ECR-MF tiers, `2113e52` API reports from the run, `b929a9d`
cross-check variants), re-measured against Orekit (see §4).

**Pushed** to `origin/integration` on 2026-10-24. The other remote branches (`origin/phase*`, `origin/general-mission-inputs`,
`origin/frontend-rebuild`, …) are still on GitHub and are all contained in `integration`. `main` is still the old
pre-restructure state (`46cfb86`).

**Verified on 2026-10-24:** pytest — 143 pass without Orekit installed (the 4 Orekit cross-check tests then
error; Orekit now runs on this machine with `JAVA_HOME` set to the Temurin 25 JDK); 27 frontend `node:test` tests pass; in the browser a Molniya run, Events, Access analysis and a
mission script all worked with no console or server errors.

---

## 2. Architecture

```
Operations console (astroflyer/frontend, plain ES modules, Three.js + uPlot, bundled assets)
        │  fetch() JSON over HTTP, 127.0.0.1 only
        ▼
HTTP API (astroflyer/backend/app_server.py, http.server, default port 8003)
        │
        ▼
Astrodynamics backend (astroflyer/backend/*.py — NumPy/SciPy, optional Numba)
        │
        ▼
Bundled data (astroflyer/resources: DE440, EGM2008, IERS, space weather; manifest.json)
```

`astroflyer/main.py` binds the server, runs it on a background thread and opens a pywebview (WebView2)
window on the main thread; `--browser` opens the default browser instead. The C++ kernel in
`astroflyer/cpp_engine/` is **retired** (see its README): it only implemented the older simplified physics.

---

## 3. Backend module map (`astroflyer/backend/`)

| Area | Modules |
| --- | --- |
| Time & frames | `epoch.py` (Epoch, all scales), `eop.py` (leap seconds, finals2000A), `frames.py` (GCRF↔ITRF, RTN/VNC/LVLH), `time_systems.py` (older wrapper) |
| Forces | `forces.py` (EGM2008, third body, SRP + shadow, drag, relativity, albedo/IR; `ForceModelConfig`), `ephemeris.py` (DE440), `nrlmsise00.py` + `nrlmsise00_data.py` |
| Propagation | `astro_engine.py` (`ThirdReviewEngine.propagate`, orbit events), `integrators.py` (RKF78, BS, RK4), `analytic.py` (Kepler, J2 mean, SGP4), `eclipse.py` (segmented `solve_ivp` restarts) |
| Events & access | `event_predictor.py`, `access.py` (stations, masks, eclipses, beta angle, reports) |
| Mission design | `mission.py` (Spacecraft, burns, Propagator, DifferentialCorrector, targeting), `script_runner.py` (mission-script interpreter), `differential_corrector.py` (B-plane, finite burn, perigee pumping) |
| Innovations | `covariance_engine.py` (`CovarianceSteering`: STM + step limiter; dispersion), `ecr_mf_controller.py` (`FidelitySchedule`: gravity degree by radius tier with a certified omitted-acceleration bound) |
| Analysis | `radiation_belts.py`, `constellation_engine.py`, `fsw_subsystems.py` |
| Data exchange | `ephemeris_io.py` (OEM/OPM/SP3), `ccsds_exporter.py` (TLE/OEM/OPM text), `mission_plan_io.py` (.MissionPlan XML) |
| Legacy / thin | `trajectory_engine.py`, `gmat_engine.py`, `basilisk_fsw.py`, `freeflyer_interop.py`, `benchmark_comparison.py` |

Propagator methods: `DOP853`/`PD853`, `Radau` (SciPy, with restarts), `RKF78`, `BS`, `RK4`, `KEPLER`, `J2MEAN`,
`SGP4`. Force-model presets: `two_body`, `j2`, `j2_j3_j4`, anything else = full model (8×8 default).
Options: `steering="covariance"` (RKF78/BS; returns `stm`, `steps`), `fidelity="ecr_mf"` (returns `ecr_mf`);
`/api/propagate` takes the same two and reports them under `innovations_suite`.

**Endpoints the new frontend uses:** `/api/propagate`, `/api/script/propagate`, `/api/script/run`,
`/api/analysis/access`, `/api/targeting/differential_corrector`, `/api/targeting/finite_burn`. The server
also still exposes the older endpoints (CCSDS, radiation, covariance, constellation, FSW, what-if, lifetime, …)
listed in `ThirdReviewAppHandler.handle_api`.

---

## 4. Validation

`python -m astroflyer.validation.orekit_crosscheck` compares against Orekit 13.1 (orekit-jpype) with identical
EGM2008 coefficients, on Molniya, Tundra, GTO and an HEO stress case, levels L0 (two-body) to L7 (full model).
Results in `astroflyer/validation/results/`: every case passes; largest differences 1.01 m over 1 day and
31.7 m over 7 days, both Molniya with SRP on. Gravity/third-body/drag agree to centimetres per day.

These Orekit numbers are the project's measured accuracy evidence. Do **not** quote the older figures below.

**Innovations re-measured** (`results/innovations/README.md`, `--variant`): covariance steering cuts plain RKF7(8)'s
error on many cases (HEO stress L7, 7 days: 28.4 → 4.4 m) at ~3.6× the run time, but does not beat the DOP853
baseline overall and made GTO L7 over 7 days worse (RKF7(8) has no shadow/drag restarts). ECR-MF is exact at 8×8
(nothing to drop); at 70×70 its tiers are 70/58/8, it stays within mm over a day of the full model, and gives
no speed-up — gravity is not the costly force. Present it as certified fidelity, not acceleration.

---

## 5. Known issues and stale material

* **Unmeasured benchmark numbers.** `backend/benchmark_comparison.py` returns hard-coded figures (C++ Radau-IIA
  0.445 s, "26.35× faster than FreeFlyer", GMAT/Orekit-12 rows). They were not produced by the current code. The
  same claims appear in `astroflyer/TECHNICAL_REPORT.md`, `astroflyer/THIRD_REVIEW_REPORT.md`,
  `astroflyer/docs/THIRD_REVIEW_REPORT.md`, `docs/reports/FREEFLYER_CROSS_VALIDATION_REPORT.md` and the
  review PDFs.
* `scripts/benchmark_against_freeflyer.py` needs a local FreeFlyer install (`ff-cli.exe`) and the FreeFlyer
  mission plans that Phase 0 removed.
* FreeFlyer naming remains in code: `freeflyer_interop.py`, `/api/freeflyer/theme`, `.MissionPlan` I/O.
* `ccsds_exporter.py` uses deprecated `datetime.utcnow()`.
* The RKF7(8)/BS path has no shadow-edge or drag-jump restarts (only the SciPy path does), which limits its
  accuracy with SRP and drag on, steered or not.
* No Sundman regularisation exists; the review documents still describe one, and still describe the removed
  post-hoc ECR-MF "certificates" and the cond(Φ) step factor.
* Threading: the server is a `ThreadingHTTPServer` and runs on a background thread beside pywebview; tests also
  start servers on threads. Whether the user's no-multiple-threads rule applies to app code is still undecided.
* Leftover folder `Desktop/major_project_py-frontend` (no longer a git worktree) could not be deleted because a
  process held it open; safe to delete by hand.

---

## 6. Run, test, build

```powershell
python -m pip install -r requirements.txt     # Python 3.12+
python main.py                                # desktop window
python main.py --browser                      # default browser
python astroflyer/backend/app_server.py       # server only, http://127.0.0.1:8003
python -m pytest astroflyer/tests             # backend tests
node --test --test-concurrency=1 astroflyer/tests/frontend/*.test.mjs   # frontend tests
python build_release.py                       # PyInstaller exe + Inno Setup installer
python tools/fetch_offline_data.py            # refresh bundled space weather (needs internet)
```

---

## 7. Working rules (Harshith's standards)

1. **Zero-error outputs.** Code must run on Windows x64, Python 3.12+. Test and verify before calling anything done.
2. **Technical rigour.** Faculty/defence audience: use proper astrodynamics formulations, no casual analogies.
3. **No redundancy.** No duplicate scripts or files in the root; root imports go through `core/` or `astroflyer/`.
4. **Console look.** Keep the dark operations theme defined in `astroflyer/frontend/css/tokens.css`.
5. **No multiple threads in the work itself.** Work sequentially: no subagents, parallel sessions or workflow fan-out.
6. **Use every relevant skill** (e.g. `tdd`, `frontend-design`, `codebase-design`, `grilling`, `find-skills`).
   `/grill-me` and `/improve-codebase-architecture` can only be started by the user.
7. **Record milestones.** When a milestone or phase completes, update the project-status memory and this handoff.
8. **Ask before pushing or deleting.** Nothing goes to GitHub, and no branch or file is removed, without approval.

# AstroFlyer HEO — Engineering Handoff

> **Project:** Precise Trajectory Propagation and Events Prediction for Highly Eccentric Orbits (HEOs)
> **Institution:** Department of Aerospace Engineering, ACS College of Engineering (VTU, Belagavi)
> **Team:** Girish Gowda S (`1AH23AS019`), Gowtham N (`1AH23AS020`), Harshith S Purohith (`1AH23AS021`, lead)
> **Guides:** Mr. Vijay M (Assistant Professor), Dr. Suresh C (Professor & HoD)
> **Repository:** `https://github.com/ImPi314/AstroFlyer.git`
> **Updated:** 2026-10-25, on branch `integration` (draft PR #15 into `main`)

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

Since then (2026-10-24/25): release fixes (no documentation inside the app, computed `/api/manifest`,
quiet WebView2, WebView2 offline installer), orbit-following output sampling, ground-track fixes, removal of
every demo module, endpoint and FreeFlyer-derived file, DOP853 as the default integrator, and cross-checks
against NASA GMAT and Basilisk alongside Orekit (§4).

**Verified on 2026-10-25:** 184 pytest pass in `astroflyer/tests` (Orekit tests need `JAVA_HOME` set to the
Temurin 25 JDK; GMAT and Basilisk tests skip if those tools are absent); 44 frontend `node:test` tests pass.

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
window on the main thread; `--browser` opens the default browser instead. There is no C++ kernel; the
untracked `astroflyer/cpp_engine/` binaries are leftovers of a retired one and are not used.

---

## 3. Backend module map (`astroflyer/backend/`)

| Area | Modules |
| --- | --- |
| Time & frames | `epoch.py` (Epoch, all scales), `eop.py` (leap seconds, finals2000A), `frames.py` (GCRF↔ITRF, RTN/VNC/LVLH) |
| Forces | `forces.py` (EGM2008, third body, SRP + shadow, drag, relativity, albedo/IR; `ForceModelConfig`), `ephemeris.py` (DE440), `nrlmsise00.py` + `nrlmsise00_data.py` |
| Propagation | `astro_engine.py` (`ThirdReviewEngine.propagate`, orbit events), `integrators.py` (RKF78, BS, RK4), `analytic.py` (Kepler, J2 mean, SGP4), `eclipse.py` (segmented `solve_ivp` restarts) |
| Events & access | `event_predictor.py`, `access.py` (stations, masks, eclipses, beta angle, reports) |
| Mission design | `mission.py` (Spacecraft, burns, Propagator, DifferentialCorrector, targeting), `script_runner.py` (mission-script interpreter), `differential_corrector.py` (B-plane, finite burn, perigee pumping) |
| Innovations | `covariance_engine.py` (`CovarianceSteering`: STM + step limiter; dispersion), `ecr_mf_controller.py` (`FidelitySchedule`: gravity degree by radius tier with a certified omitted-acceleration bound) |
| Analysis | `radiation_belts.py` (L-shell, field, belt crossings) |
| Data exchange | `ephemeris_io.py` (OEM/OPM/SP3), `ccsds_exporter.py` (TLE/OEM/OPM text) |
| Legacy / thin | `trajectory_engine.py` |

Propagator methods: `DOP853`/`PD853`, `Radau` (SciPy, with restarts), `RKF78`, `BS`, `RK4`, `KEPLER`, `J2MEAN`,
`SGP4`. Force-model presets: `two_body`, `j2`, `j2_j3_j4`, anything else = full model (8×8 default).
Options: `steering="covariance"` (RKF78/BS; returns `stm`, `steps`), `fidelity="ecr_mf"` (returns `ecr_mf`);
`/api/propagate` takes the same two and reports them under `innovations_suite`.

**Endpoints the new frontend uses:** `/api/propagate`, `/api/script/propagate`, `/api/script/run`,
`/api/analysis/access`, `/api/targeting/differential_corrector`, `/api/targeting/finite_burn`. The server
also exposes `/api/manifest`, `/api/mission/target`, CCSDS TLE/OPM/OEM, `/api/covariance/propagate`,
`/api/covariance/steered` and the eclipse and ground-station event endpoints (`ThirdReviewAppHandler.handle_api`).

---

## 4. Validation

Three cross-checks on the same cases (Molniya, Tundra, GTO, HEO stress; epoch 2026-01-01 TT; force levels
L0 two-body … L7 full model; AstroFlyer's own EGM2008 coefficients given to every tool):

| Tool | Module | 1 day | 7 days |
| --- | --- | --- | --- |
| Orekit 13.1 | `validation/orekit_crosscheck.py` | 32/32, ≤ 0.63 m | 20/20, ≤ 6.1 m |
| NASA GMAT R2026a | `validation/gmat_crosscheck.py` (`~/GMAT/R2026a` or `GMAT_CONSOLE`) | 32/32, ≤ 1.06 m | 20/20, ≤ 32.6 m |
| Basilisk 2.11.1 (L0–L6) | `validation/basilisk_crosscheck.py` (`~/bsk-venv` or `BSK_PYTHON`) | 26/28 | 14/16 |

Basilisk's two failures per run are drag on Molniya and GTO: its atmosphere uses spherical altitude. Every
difference and how it was traced is in `astroflyer/validation/results/README.md`; the summary for readers is
`astroflyer/TECHNICAL_REPORT.md`. These are the project's measured accuracy evidence.

**Innovations re-measured** (`results/innovations/README.md`, `--variant`): covariance steering cuts plain RKF7(8)'s
error on several cases (HEO stress L7, 7 days: 26.3 → 6.0 m) at ~4× the run time, but does not beat the DOP853
baseline overall and made GTO L7 over 7 days worse (RKF7(8) has no shadow/drag restarts). ECR-MF is exact at 8×8
(nothing to drop); at 70×70 its tiers are 70/58/8, it stays within mm over a day of the full model, and gives
no speed-up — gravity is not the costly force. Present it as certified fidelity, not acceleration.

---

## 5. Known issues and stale material

* **Old review documents.** `astroflyer/docs/THIRD_REVIEW_REPORT.md` and the review handbook PDFs in
  `docs/handbooks/` (as submitted) describe a C++ kernel, PyQt6, Sundman regularisation, a FreeFlyer comparison
  and a "26.35×" speed-up that were never built or measured. Each carries or is covered by a correction notice;
  `TECHNICAL_REPORT.md` §7 lists the corrections. The abstract (`docs/abstract/`) is regenerated from
  `scripts/generate_formal_abstract_docs.py` with measured results only.
* **No FreeFlyer comparison.** Check FreeFlyer's licence before publishing any FreeFlyer numbers; never open
  `mp_archive/datasources/freeflyer_extracted` (clean-room rule).
* `ccsds_exporter.py` uses deprecated `datetime.utcnow()`.
* The RKF7(8)/BS path has no shadow-edge or drag-jump restarts (only the SciPy path does), which limits its
  accuracy with SRP and drag on, steered or not.
* Unexplained: 0.37 m a day difference from Basilisk on Molniya with J2 or 8×8 gravity.
* SPICE rejects the bundled DE440 subset (one segment ends a word short); jplephem reads it. GMAT and Basilisk
  use GMAT's DE424 instead.
* Threading: the server is a `ThreadingHTTPServer` and runs on a background thread beside pywebview; tests also
  start servers on threads. Whether the user's no-multiple-threads rule applies to app code is still undecided.

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
3. **No redundancy.** No duplicate scripts or files in the root; root imports go through `astroflyer/`.
4. **Console look.** Keep the dark operations theme defined in `astroflyer/frontend/css/tokens.css`.
5. **No multiple threads in the work itself.** Work sequentially: no subagents, parallel sessions or workflow fan-out.
6. **Use every relevant skill** (e.g. `tdd`, `frontend-design`, `codebase-design`, `grilling`, `find-skills`).
   `/grill-me` and `/improve-codebase-architecture` can only be started by the user.
7. **Record milestones.** When a milestone or phase completes, update the project-status memory and this handoff.
8. **Ask before pushing or deleting.** Nothing goes to GitHub, and no branch or file is removed, without approval.

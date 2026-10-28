"""
Figures for the Validation sections of README.md and TECHNICAL_REPORT.md, drawn from the stored results.

Run from the project root (needs matplotlib; only the steering figure propagates anything):
    python astroflyer/validation/results/make_validation_figures.py
Writes PNGs to docs/figures/validation/.
"""

import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, os.getcwd())

from astroflyer.backend import forces  # noqa: E402
from astroflyer.backend.astro_engine import ThirdReviewEngine, keplerian_to_cartesian  # noqa: E402
from astroflyer.backend.ecr_mf_controller import FidelitySchedule, omitted_gravity_bound  # noqa: E402
from astroflyer.validation import cases as C  # noqa: E402

RESULTS = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.getcwd(), "docs", "figures", "validation")
ORBITS = ["molniya", "tundra", "gto", "heo_stress"]
LABEL = {"molniya": "Molniya", "tundra": "Tundra", "gto": "GTO", "heo_stress": "HEO stress (e = 0.88)"}
RERUN = os.path.join(RESULTS, "rerun_2026-10-28")


def load(path):
    with open(path) as f:
        return json.load(f)["results"]


def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, name), dpi=150)
    plt.close(fig)
    print("wrote", name)


def crosscheck_overview():
    """Worst difference over the four orbits, per force level, for each reference and duration."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, days, limit in zip(axes, (1, 7), (10.0, 100.0)):
        for tool, colour in (("orekit", "C0"), ("gmat", "C1"), ("basilisk", "C2")):
            rows = load(os.path.join(RERUN, f"{tool}_{days}day", f"{tool}_crosscheck.json"))
            levels = sorted({r["level"] for r in rows})
            worst = [max(r["max_pos_err_m"] for r in rows if r["level"] == lv) for lv in levels]
            ax.plot(levels, worst, "o-", color=colour, label={"orekit": "Orekit 13.1.9", "gmat": "GMAT R2026a",
                                                              "basilisk": "Basilisk 2.11.1"}[tool])
        ax.axhline(limit, color="k", ls="--", lw=1, label=f"limit {limit:g} m")
        ax.set_yscale("log")
        ax.set_title(f"{days} day{'s' if days > 1 else ''}: largest difference over the four orbits")
        ax.set_xlabel("force level (L0 two-body … L7 full model)")
        ax.grid(True, which="both", alpha=0.3)
    axes[0].set_ylabel("max position difference (m)")
    axes[1].legend(fontsize=8)
    save(fig, "crosscheck_overview.png")


def restart_bars():
    """Max difference from Orekit over 7 days, restarts on and off, L5-L7."""
    rows = load(os.path.join(RESULTS, "discontinuity_restarts", "restart_ablation_7day.json"))
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), sharey=True)
    cases = [(o, lv) for o in ORBITS for lv in ("L5", "L6", "L7")]
    x = np.arange(len(cases))
    for ax, variant, title in zip(axes, ("dop853", "rkf78"), ("DOP853", "RKF7(8)")):
        def pick(on):
            return [next(r["max_pos_err_m"] for r in rows if r["orbit"] == o and r["level"] == lv
                         and r["variant"] == variant and r["restarts"] == on) for o, lv in cases]
        ax.bar(x - 0.2, pick(False), 0.4, label="stepping across the discontinuities", color="C3")
        ax.bar(x + 0.2, pick(True), 0.4, label="restart at each discontinuity (as shipped)", color="C0")
        ax.set_xticks(x, [f"{LABEL[o].split(' ')[0]}\n{lv}" for o, lv in cases], fontsize=8)
        ax.set_yscale("log")
        ax.set_title(f"{title}, 7 days, difference from Orekit")
        ax.grid(True, axis="y", which="both", alpha=0.3)
    axes[0].set_ylabel("max position difference (m)")
    axes[0].set_ylim(top=1e3)
    axes[0].legend(fontsize=8, loc="upper left")
    save(fig, "restarts_7day.png")


def restart_series():
    s = np.load(os.path.join(RESULTS, "discontinuity_restarts", "restart_ablation_7day_series.npz"))
    t_days = s["t"] / 86400.0
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, orbit in zip(axes, ("molniya", "heo_stress")):
        ax.plot(t_days, s[f"{orbit}_L5_dop853_off"], color="C3", label="stepping across")
        ax.plot(t_days, s[f"{orbit}_L5_dop853_on"], color="C0", label="restart at each edge")
        ax.set_title(f"{LABEL[orbit]}, SRP on (L5), DOP853")
        ax.set_xlabel("days")
        ax.grid(True, alpha=0.3)
    axes[0].set_ylabel("position difference from Orekit (m)")
    axes[0].legend(fontsize=8)
    save(fig, "restarts_molniya_stress_series.png")


def steering_steps():
    """Steps chosen by covariance steering along one GTO revolution (8x8 gravity, RKF7(8), eta 0.02)."""
    a, e, i, raan, argp, nu = C.ORBITS["gto"]
    r0, v0 = keplerian_to_cartesian(a, e, math.radians(i), math.radians(raan), math.radians(argp),
                                    math.radians(nu), mu=forces.MU_EARTH)
    period = 2 * math.pi * math.sqrt(a ** 3 / forces.MU_EARTH)
    common = dict(num_points=2000, model="coupled", method="RKF78", rtol=1e-12, atol=1e-6, enable_drag=False,
                  enable_third_body=False, enable_srp=False, enable_relativity=False, enable_albedo=False,
                  gravity_degree=8, gravity_order=8)
    sol = ThirdReviewEngine(np.concatenate([r0, v0])).propagate((0.0, period), steering="covariance", **common)
    st = sol["steps"]
    t = np.asarray(st["t_s"])
    r_km = np.interp(t, sol["times"], np.linalg.norm(sol["position_m"], axis=1)) / 1e3
    h = np.asarray(st["h_s"])
    limited = np.asarray(st["limited"], dtype=bool)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    ax1.plot(t / 3600, h, ".", ms=3, color="0.6", label="step")
    ax1.plot(t[limited] / 3600, h[limited], ".", ms=4, color="C3", label="capped by the uncertainty limit")
    ax1.set_yscale("log")
    ax1.set_xlabel("hours from perigee")
    ax1.set_ylabel("step (s)")
    ax1.set_title("Covariance-steered steps, GTO, one revolution")
    ax1.legend(fontsize=8)
    ax1.grid(True, which="both", alpha=0.3)
    ax2.plot(t / 3600, st["sigma_pos_m"], color="C0")
    ax2b = ax2.twinx()
    ax2b.plot(t / 3600, r_km, color="0.5", lw=0.8)
    ax2b.set_ylabel("radius (km)", color="0.5")
    ax2.set_xlabel("hours from perigee")
    ax2.set_ylabel("1-sigma position uncertainty (m)", color="C0")
    ax2.set_title("The quantity the step control limits")
    ax2.grid(True, alpha=0.3)
    save(fig, "steering_gto_steps.png")
    return {"steps": int(len(h) - 1), "limited": int(limited[1:].sum()), "eta": st["eta"]}


def ecr_mf_bound():
    """Certified bound on the gravity ECR-MF leaves out, against altitude, at 70x70."""
    cfg = forces.ForceModelConfig(gravity_degree=70, gravity_order=70)
    sched = FidelitySchedule(cfg)
    alt_km = np.geomspace(200, 40000, 400)
    r = forces.R_EARTH_EQ + alt_km * 1e3
    fig, ax = plt.subplots(figsize=(7.5, 4.3))
    for kept in (8, 20, 40, 58):
        ax.plot(alt_km, [omitted_gravity_bound(x, kept, 70) for x in r], label=f"degrees above {kept} left out")
    ax.axhline(sched.epsilon, color="k", ls="--", lw=1, label="epsilon = 1e-10 m/s²")
    for b in (2000, 20000):
        ax.axvline(b, color="0.5", ls=":", lw=1)
    for tier, x in zip(sched.tiers, (600, 6000, 28000)):
        ax.text(x, 1e-2, f"degree {tier['gravity_degree']}", ha="center", fontsize=8)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_ylim(1e-16, 1e-1)
    ax.set_xlabel("altitude (km)")
    ax.set_ylabel("bound on omitted acceleration (m/s²)")
    ax.set_title("ECR-MF: gravity degree kept per radius tier (EGM2008 70×70)")
    ax.legend(fontsize=7, loc="lower left")
    ax.grid(True, which="both", alpha=0.3)
    save(fig, "ecr_mf_bound.png")
    return sched.tiers


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    crosscheck_overview()
    restart_bars()
    restart_series()
    print("steering:", steering_steps())
    print("ecr_mf tiers:", [(t["tier"], t["gravity_degree"], t["omitted_bound_ms2"]) for t in ecr_mf_bound()])

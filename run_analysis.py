"""Regenerate figures and machine-readable data from config.json."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import platform
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sram_model import sample_thresholds, snm_batch, snm_reference, summarize

ROOT = Path(__file__).resolve().parent
BLUE, ORANGE, TEAL = "#205493", "#c56824", "#16756c"


def write_csv(path, rows):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def generate(config_path=ROOT / "config.json", output=ROOT):
    config_path, output = Path(config_path), Path(output)
    cfg = json.loads(config_path.read_text())
    data, figs = output / "data", output / "figures"
    data.mkdir(parents=True, exist_ok=True)
    figs.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titleweight": "bold", "savefig.dpi": 170})
    samples = sample_thresholds(cfg["samples"], cfg["vth_mean_v"], cfg["vth_sigma_v"], cfg["seed"])
    kwargs = {k: cfg[k] for k in ["gain_per_v", "diagonal_points", "vtc_points", "batch_size"]}
    values = np.asarray([snm_batch(samples, vdd=v, **kwargs) for v in cfg["supplies_v"]])
    rows = [{"vdd_v": v, **summarize(a, cfg["criterion_v"])} for v, a in zip(cfg["supplies_v"], values)]
    write_csv(data / "supply_sweep.csv", rows)
    nominal = snm_batch(samples, vdd=1., **kwargs)
    sample_rows = [{"sample_id": i, **dict(zip(["vth_n1_v", "vth_p1_v", "vth_n2_v", "vth_p2_v"], t)),
                    "snm_1v_mv": s*1000} for i, (t, s) in enumerate(zip(samples, nominal))]
    sample_dir = data / "samples_1v"
    sample_dir.mkdir(exist_ok=True)
    # Small complete tables make all raw samples easy to inspect in GitHub.
    for previous in sample_dir.glob("part-*.csv"):
        previous.unlink()
    parts = []
    for start in range(0, len(sample_rows), 1000):
        name = f"part-{start//1000+1:03d}.csv"
        write_csv(sample_dir / name, sample_rows[start:start+1000])
        parts.append({"file": name, "first_sample_id": start,
                      "rows": len(sample_rows[start:start+1000])})
    (sample_dir / "manifest.json").write_text(json.dumps({"total_rows": len(sample_rows), "parts": parts}, indent=2)+"\n")
    sensitivity = [{"criterion_mv": m, **summarize(nominal, m/1000)} for m in [160, 170, 180, 190, 200]]
    write_csv(data / "criterion_sensitivity.csv", sensitivity)

    def save(fig, name):
        fig.savefig(figs / name, bbox_inches="tight", facecolor="white")
        plt.close(fig)

    # The 30 mV distribution is an illustration, separate from the 40 mV MC study.
    demo = sample_thresholds(cfg["samples"], cfg["vth_mean_v"], cfg["illustration_sigma_v"], cfg["seed"])[:, 0]
    fig, ax = plt.subplots(figsize=(8, 4.4), layout="constrained")
    ax.hist(demo, bins=45, color=BLUE, alpha=.8, edgecolor="white", linewidth=.4)
    ax.axvline(cfg["vth_mean_v"], color=ORANGE, ls="--", label=f'Mean parameter: {cfg["vth_mean_v"]:.2f} V')
    ax.set(title="Threshold variation: illustrative input distribution", xlabel="Threshold voltage (V)", ylabel="Samples")
    ax.text(.02, .94, f'n = {len(demo):,}; sigma = {cfg["illustration_sigma_v"]*1000:.0f} mV; seed = {cfg["seed"]}', transform=ax.transAxes, va="top")
    ax.legend(loc="upper right", frameon=False)
    save(fig, "step1_vth_hist.png")

    fig, axs = plt.subplots(1, 2, figsize=(10.4, 4.7), layout="constrained")
    reference_results = []
    for ax, t, label in zip(axs, [[.4]*4, [.31, .48, .47, .32]], ["Matched inverter pair", "Illustrative threshold mismatch"]):
        snm, detail = snm_reference(t, gain_per_v=cfg["gain_per_v"])
        reference_results.append(snm*1000)
        ax.plot(detail["v"], detail["f1"], color=BLUE, label="Inverter 1")
        ax.plot(detail["f2"], detail["v"], color=ORANGE, label="Mirrored inverter 2")
        for x, y, s in detail["squares"]:
            ax.add_patch(plt.Rectangle((x, y), s, s, fill=False, edgecolor=TEAL, ls="--", lw=1.7))
        ax.set(title=f"{label}\nSNM = {snm*1000:.2f} mV", xlabel="Node voltage V1 (V)", ylabel="Node voltage V2 (V)", xlim=(0, 1), ylim=(0, 1), aspect="equal")
        ax.legend(loc="lower left", fontsize=8, frameon=False)
        ax.grid(alpha=.16)
    save(fig, "step2_butterfly.png")

    stats = summarize(nominal, cfg["criterion_v"])
    fig, ax = plt.subplots(figsize=(8, 4.5), layout="constrained")
    ax.hist(nominal*1000, bins=50, color=TEAL, alpha=.8, edgecolor="white", linewidth=.4)
    ax.axvline(cfg["criterion_v"]*1000, color=ORANGE, lw=2, label=f'Chosen criterion: {cfg["criterion_v"]*1000:g} mV')
    ax.axvline(stats["mean_snm_mv"], color=BLUE, ls="--", label=f'Mean: {stats["mean_snm_mv"]:.2f} mV')
    ax.set(title="Behavioral stability margin at VDD = 1.0 V", xlabel="Static noise margin (mV)", ylabel="Samples")
    ax.text(.02, .95, f'{stats["below_threshold_count"]} / {stats["n"]:,} below criterion\n95% Wilson interval: {stats["ci95_low_pct"]:.3f}–{stats["ci95_high_pct"]:.3f}%', transform=ax.transAxes, va="top", fontsize=9, bbox={"facecolor": "white", "edgecolor": "none", "alpha": .95})
    ax.legend(loc="upper left", bbox_to_anchor=(0, .78), fontsize=9, frameon=True, facecolor="white", edgecolor="none", framealpha=.95)
    save(fig, "step3_mc_snm_dist.png")

    fig, (ax, bx) = plt.subplots(1, 2, figsize=(11, 4.4), layout="constrained")
    v = np.asarray(cfg["supplies_v"])
    ax.plot(v, [r["mean_snm_mv"] for r in rows], "o-", color=BLUE, label="Mean")
    ax.plot(v, [r["p01_snm_mv"] for r in rows], "s--", color=TEAL, label="Empirical 1st percentile")
    ax.axhline(cfg["criterion_v"]*1000, color=ORANGE, ls=":", label=f'Chosen {cfg["criterion_v"]*1000:g} mV criterion')
    ax.set(title="Margin versus supply voltage", xlabel="Supply voltage (V)", ylabel="SNM (mV)")
    ax.legend(frameon=False, fontsize=8)
    p = np.array([r["below_threshold_pct"] for r in rows])
    lower, upper = np.array([r["ci95_low_pct"] for r in rows]), np.array([r["ci95_high_pct"] for r in rows])
    bx.errorbar(v, p, yerr=np.maximum(0, np.vstack([p-lower, upper-p])), color=ORANGE, fmt="o-", capsize=3, label="Estimate and 95% Wilson interval")
    bx.set(title="Fraction below the chosen criterion", xlabel="Supply voltage (V)", ylabel="Samples below criterion (%)", ylim=(-3, 103))
    bx.legend(frameon=False, fontsize=8)
    for ax in (ax, bx): ax.grid(alpha=.16)
    fig.suptitle(f'Fixed physical gain: {cfg["gain_per_v"]:g} V⁻¹ | Paired threshold samples across supplies', fontsize=11)
    save(fig, "step4_vdd_scaling.png")

    result = {"config": cfg, "at_1v": stats,
              "reference_nominal_snm_mv": reference_results[0], "reference_mismatch_snm_mv": reference_results[1],
              "supply_sweep": rows,
              "environment": {"python": platform.python_version(), "numpy": np.__version__, "matplotlib": matplotlib.__version__},
              "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT / "sram_model.py", ROOT / "run_analysis.py", config_path]}}
    (data / "summary.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(stats, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config.json")
    parser.add_argument("--output", type=Path, default=ROOT)
    args = parser.parse_args()
    generate(args.config, args.output)

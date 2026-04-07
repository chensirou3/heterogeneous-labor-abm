"""
Unified Benchmark Comparison: 7 models/benchmarks on real data.
Generates tables + charts for paper.

Usage: python run_benchmarks.py [--quick]
"""
import sys, time, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from models.config import TOTAL_MONTHS, TRAIN_END, VALID_END
from models.real_data import load_real_targets, load_real_environment
from models.loss import compute_loss, DEFAULT_WEIGHTS
from models.model_a import run_model_a
from models.model_b import run_model_b
from models.model_c import run_model_c
from models.benchmarks import (
    run_benchmark_d, run_benchmark_e, run_benchmark_f, run_benchmark_g, CORE_KEYS,
)

# Frozen baseline params
BP_B = {"mu_rw_E":10.58,"sigma_rw_E":0.46,"mu_rw_N":11.42,"sigma_rw_N":0.99,
        "alpha_oab_E":4.88,"beta_oab_E":7.75,"alpha_oab_N":4.68,"beta_oab_N":8.00,
        "p_search_mid":0.10,"p_search_high":0.16,"pp_delta":-0.032}
BP_C = {"mu_rw_E":10.32,"sigma_rw_E":0.93,"mu_rw_N":11.06,"sigma_rw_N":1.10,
        "alpha_oab_E":3.09,"beta_oab_E":3.37,"alpha_oab_N":3.52,"beta_oab_N":10.94,
        "p_search_mid":0.20,"p_search_high":0.10,"pp_delta":0.040}

os.makedirs("figures", exist_ok=True)


def compute_rmse(pred, actual, start, end):
    p, a = pred[start:end], actual[start:end]
    mask = ~(np.isnan(p) | np.isnan(a))
    if mask.sum() == 0:
        return np.nan
    return float(np.sqrt(np.mean((p[mask] - a[mask])**2)))


def benchmark_loss(preds, targets, start, end, weights=None):
    """Compute var-normalized weighted MSE loss for benchmark predictions."""
    if weights is None:
        weights = DEFAULT_WEIGHTS
    total = 0.0
    result = {}
    for key, w in weights.items():
        if key not in preds or key not in targets:
            continue
        s = preds[key][start:end]
        d = targets[key][start:end]
        mask = ~(np.isnan(s) | np.isnan(d))
        if mask.sum() == 0:
            continue
        var_d = max(np.var(d[mask]), 1e-10)
        mse = np.mean((s[mask] - d[mask])**2) / var_d
        wm = w * mse
        result[f"loss_{key}"] = float(wm)
        total += wm
    result["total_loss"] = float(total)
    return result


def eval_abm(run_fn, params, env, targets, start, end, n_seeds, n_agents):
    """Evaluate ABM model across seeds, return mean predictions + loss."""
    from models.config import SimulationOutput
    losses = []
    all_preds = {}
    for s in range(n_seeds):
        kw = dict(env=env, params=params, seed=s, n_agents=n_agents)
        if run_fn == run_model_a:
            kw.pop("n_agents")
        sim = run_fn(**kw)
        sd = sim.to_dict()
        for k, v in sd.items():
            all_preds.setdefault(k, []).append(v)
        ld = compute_loss(sim, targets, None, start, end)
        losses.append(ld["total_loss"])
    mean_preds = {k: np.mean(v, axis=0) for k, v in all_preds.items()}
    return mean_preds, float(np.mean(losses)), float(np.std(losses))


def main():
    quick = "--quick" in sys.argv
    n_seeds = 3 if quick else 5
    n_agents = 2000 if quick else 3000
    print(f"{'='*70}\n  UNIFIED BENCHMARK COMPARISON (7 models)\n{'='*70}")

    # Load data
    targets, ok = load_real_targets(2014, 2024, TOTAL_MONTHS)
    if not ok:
        from models.loss import generate_synthetic_targets
        targets = generate_synthetic_targets(TOTAL_MONTHS)
    env = load_real_environment(targets, TOTAL_MONTHS)
    for k in targets:
        v = targets[k]
        nans = np.isnan(v)
        if nans.any() and not nans.all():
            v[nans] = np.interp(np.flatnonzero(nans), np.flatnonzero(~nans), v[~nans])

    # ═══ Run all models ═══
    results = {}  # name -> {preds, train_loss, valid_loss, test_loss}

    # ABM models
    print("\n[1] Running ABM models...")
    for name, fn, params in [("A_Traditional",run_model_a,BP_B),
                              ("B_StdABM",run_model_b,BP_B),
                              ("C_HeteroABM",run_model_c,BP_C)]:
        preds, _, _ = eval_abm(fn, params, env, targets, VALID_END, None, n_seeds, n_agents)
        tr = benchmark_loss(preds, targets, 0, TRAIN_END)
        vl = benchmark_loss(preds, targets, TRAIN_END, VALID_END)
        ts = benchmark_loss(preds, targets, VALID_END, None)
        results[name] = {"preds":preds, "train":tr["total_loss"],
                         "valid":vl["total_loss"], "test":ts["total_loss"],
                         "per_target_test": ts}
        print(f"  {name:<20} train={tr['total_loss']:10.0f} test={ts['total_loss']:10.0f}")

    # Benchmarks D-G
    print("\n[2] Running traditional benchmarks...")
    bm_runners = [("D_ARIMA", run_benchmark_d), ("E_VAR", run_benchmark_e),
                  ("F_BevRedForm", run_benchmark_f), ("G_DMP", run_benchmark_g)]
    for name, fn in bm_runners:
        kw = {"targets": targets}
        preds = fn(**kw)
        tr = benchmark_loss(preds, targets, 0, TRAIN_END)
        vl = benchmark_loss(preds, targets, TRAIN_END, VALID_END)
        ts = benchmark_loss(preds, targets, VALID_END, None)
        results[name] = {"preds":preds, "train":tr["total_loss"],
                         "valid":vl["total_loss"], "test":ts["total_loss"],
                         "per_target_test": ts}
        print(f"  {name:<20} train={tr['total_loss']:10.0f} test={ts['total_loss']:10.0f}")


    # ═══ TABLE 1: Total Loss Comparison ═══
    print(f"\n{'='*70}")
    print(f"  TABLE 1: TOTAL LOSS COMPARISON")
    print(f"{'='*70}")
    names_sorted = sorted(results.keys(), key=lambda n: results[n]["test"])
    c_test = results["C_HeteroABM"]["test"]
    print(f"  {'Model':<20} {'Train':>10} {'Valid':>10} {'Test':>10} {'vs C':>10} {'Rank':>5}")
    print("  " + "-" * 68)
    for rank, name in enumerate(names_sorted, 1):
        r = results[name]
        delta = (r["test"] - c_test) / max(c_test, 1e-10) * 100
        print(f"  {name:<20} {r['train']:10.0f} {r['valid']:10.0f} {r['test']:10.0f}"
              f" {delta:+9.1f}% {rank:5d}")

    # TABLE 1b: Fair comparison (only UR/LFPR/EPOP — all models produce these)
    fair_keys = ["unemployment_rate", "lfpr", "epop"]
    fair_w = {k: DEFAULT_WEIGHTS.get(k, 1.0) for k in fair_keys}
    print(f"\n  TABLE 1b: FAIR COMPARISON (UR + LFPR + EPOP only)")
    print(f"  {'Model':<20} {'Test(fair)':>12} {'Rank':>5}")
    print("  " + "-" * 40)
    fair_results = {}
    for name in results:
        fl = benchmark_loss(results[name]["preds"], targets, VALID_END, None, fair_w)
        fair_results[name] = fl["total_loss"]
    fair_sorted = sorted(fair_results, key=fair_results.get)
    for rank, name in enumerate(fair_sorted, 1):
        print(f"  {name:<20} {fair_results[name]:12.0f} {rank:5d}")

    # ═══ TABLE 2: Per-series RMSE ═══
    print(f"\n{'='*70}")
    print(f"  TABLE 2: TEST-PERIOD RMSE (x100)")
    print(f"{'='*70}")
    rmse_keys = ["unemployment_rate","lfpr","epop","quits_rate","layoffs_rate","hires_rate"]
    header = f"  {'Model':<20}" + "".join(f" {k[:8]:>10}" for k in rmse_keys)
    print(header)
    print("  " + "-" * (20 + 11 * len(rmse_keys)))
    rmse_data = {}
    for name in names_sorted:
        preds = results[name]["preds"]
        row = f"  {name:<20}"
        rmses = {}
        for k in rmse_keys:
            if k in preds:
                rmse = compute_rmse(preds[k], targets[k], VALID_END, TOTAL_MONTHS)
                rmses[k] = rmse
                row += f" {rmse*100:10.3f}" if not np.isnan(rmse) else f" {'N/A':>10}"
            else:
                rmses[k] = np.nan
                row += f" {'N/A':>10}"
        rmse_data[name] = rmses
        print(row)

    # ═══ CHARTS ═══
    print("\n[3] Generating charts...")
    colors = {"A_Traditional":"#999999","B_StdABM":"#4DBEEE","C_HeteroABM":"#D95319",
              "D_ARIMA":"#77AC30","E_VAR":"#7E2F8E","F_BevRedForm":"#EDB120","G_DMP":"#0072BD"}

    # Chart 1: Test Loss Bar Chart
    fig, ax = plt.subplots(figsize=(10, 5))
    x = range(len(names_sorted))
    bars = ax.bar(x, [results[n]["test"] for n in names_sorted],
                  color=[colors.get(n,"#333") for n in names_sorted])
    ax.set_xticks(x)
    ax.set_xticklabels([n.replace("_","\n") for n in names_sorted], fontsize=8)
    ax.set_ylabel("Test Loss")
    ax.set_title("Figure 1: Test Loss — All Models & Benchmarks")
    ax.axhline(y=c_test, color='red', linestyle='--', alpha=0.5, label=f"Model C={c_test:.0f}")
    ax.legend()
    for bar, name in zip(bars, names_sorted):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+200,
                f"{results[name]['test']:.0f}", ha='center', fontsize=7)
    plt.tight_layout()
    plt.savefig("figures/fig1_test_loss_bars.png", dpi=150)
    plt.close()

    # Chart 2: RMSE Heatmap
    fig, ax = plt.subplots(figsize=(10, 5))
    matrix = np.array([[rmse_data[n].get(k,np.nan)*100 for k in rmse_keys] for n in names_sorted])
    im = ax.imshow(matrix, aspect='auto', cmap='YlOrRd')
    ax.set_xticks(range(len(rmse_keys)))
    ax.set_xticklabels([k[:10] for k in rmse_keys], fontsize=8, rotation=30)
    ax.set_yticks(range(len(names_sorted)))
    ax.set_yticklabels(names_sorted, fontsize=8)
    for i in range(len(names_sorted)):
        for j in range(len(rmse_keys)):
            v = matrix[i,j]
            if not np.isnan(v):
                ax.text(j,i,f"{v:.2f}",ha='center',va='center',fontsize=7,
                        color='white' if v>np.nanmedian(matrix) else 'black')
    ax.set_title("Figure 2: Test RMSE Heatmap (x100)")
    plt.colorbar(im, ax=ax)
    plt.tight_layout()
    plt.savefig("figures/fig2_rmse_heatmap.png", dpi=150)
    plt.close()

    # Chart 3: Key Series Time Plots
    months = np.arange(TOTAL_MONTHS)
    for key, title in [("unemployment_rate","Unemployment Rate"),
                        ("lfpr","LFPR"),("epop","EPOP")]:
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(months, targets[key], 'k-', lw=2.5, label="Actual (BLS)")
        ax.axvline(TRAIN_END, color='grey', ls=':', alpha=0.5)
        ax.axvline(VALID_END, color='grey', ls=':', alpha=0.5)
        for nm in ["C_HeteroABM","B_StdABM","D_ARIMA","F_BevRedForm","G_DMP"]:
            if key in results[nm]["preds"]:
                ax.plot(months, results[nm]["preds"][key], '--',
                        color=colors.get(nm,"#333"), lw=1.2, alpha=0.8, label=nm)
        ax.set_title(f"Figure 3: {title}"); ax.legend(fontsize=7)
        plt.tight_layout(); plt.savefig(f"figures/fig3_{key}.png", dpi=150); plt.close()

    # Chart 4: C vs Strongest Traditional
    trad = {n:results[n]["test"] for n in ["D_ARIMA","E_VAR","F_BevRedForm","G_DMP"]}
    strongest = min(trad, key=trad.get)
    fig, axes = plt.subplots(1,3,figsize=(15,4))
    for ax, key, title in zip(axes, ["unemployment_rate","lfpr","epop"], ["UR","LFPR","EPOP"]):
        ax.plot(months[VALID_END:], targets[key][VALID_END:], 'k-', lw=2, label="Actual")
        for nm, ls in [("C_HeteroABM","-"),(strongest,"--")]:
            if key in results[nm]["preds"]:
                ax.plot(months[VALID_END:], results[nm]["preds"][key][VALID_END:],
                        ls, color=colors.get(nm,"#333"), lw=1.5, label=nm)
        ax.set_title(title); ax.legend(fontsize=7)
    plt.suptitle(f"Figure 4: Model C vs {strongest} (Test Period)")
    plt.tight_layout(); plt.savefig("figures/fig4_c_vs_strongest.png", dpi=150); plt.close()

    print(f"  Charts saved to figures/")
    print(f"\n{'='*70}\n  FINAL SUMMARY\n{'='*70}")
    print(f"  Ranking: {', '.join(names_sorted)}")
    c_rank = names_sorted.index("C_HeteroABM") + 1
    print(f"  Model C rank: {c_rank}/{len(names_sorted)}")
    print(f"  Strongest traditional: {strongest} (test={trad[strongest]:.0f},"
          f" C vs it: {(c_test-trad[strongest])/max(trad[strongest],1e-10)*100:+.1f}%)")

if __name__ == "__main__":
    main()

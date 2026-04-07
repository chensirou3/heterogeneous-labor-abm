"""
Longest-History Unified Benchmark Experiment.
Uses BLS data from 2001-01 to 2025-03 (291 months).
Includes: 7-model comparison, Model C rolling window, regime tests.

Usage: python run_longest_history.py [--quick]
"""
import sys, time, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from models.real_data import fetch_bls_data, bls_to_monthly_array, SCE_LMS_SUMMARY
from models.environment import EnvironmentPath
from models.model_a import run_model_a
from models.model_b import run_model_b
from models.model_c import run_model_c
from models.benchmarks import (
    run_benchmark_d, run_benchmark_e, run_benchmark_f, run_benchmark_g, CORE_KEYS,
)
from models.loss import DEFAULT_WEIGHTS

# ── History config ──
START_YEAR, START_MONTH = 2001, 1
END_YEAR, END_MONTH = 2025, 3
N_MONTHS = (END_YEAR - START_YEAR) * 12 + (END_MONTH - START_MONTH + 1)  # 291
TRAIN_END = int(N_MONTHS * 0.60)   # ~175 (2001-01 to ~2015-07)
VALID_END = int(N_MONTHS * 0.80)   # ~233 (to ~2020-05)
# Test: 233 to 291 (~58 months, 2020-06 to 2025-03)

# Frozen baseline params (from real data experiment)
BP_B = {"mu_rw_E":10.58,"sigma_rw_E":0.46,"mu_rw_N":11.42,"sigma_rw_N":0.99,
        "alpha_oab_E":4.88,"beta_oab_E":7.75,"alpha_oab_N":4.68,"beta_oab_N":8.00,
        "p_search_mid":0.10,"p_search_high":0.16,"pp_delta":-0.032}
BP_C = {"mu_rw_E":10.32,"sigma_rw_E":0.93,"mu_rw_N":11.06,"sigma_rw_N":1.10,
        "alpha_oab_E":3.09,"beta_oab_E":3.37,"alpha_oab_N":3.52,"beta_oab_N":10.94,
        "p_search_mid":0.20,"p_search_high":0.10,"pp_delta":0.040}

os.makedirs("figures", exist_ok=True)

# Series IDs
SID = {
    "unemployment_rate": "LNS14000000", "lfpr": "LNS11300000", "epop": "LNS12300000",
    "job_openings_rate": "JTS000000000000000JOR",
    "hires_rate": "JTS000000000000000HIR",
    "quits_rate": "JTS000000000000000QUR",
    "layoffs_rate": "JTS000000000000000LDR",
}


def load_long_data():
    """Load BLS data for longest history."""
    all_sids = list(set(SID.values()))
    raw = fetch_bls_data(all_sids, START_YEAR, END_YEAR)
    targets = {}
    for name, sid in SID.items():
        if sid in raw:
            arr = bls_to_monthly_array(raw[sid], START_YEAR, START_MONTH, N_MONTHS)
            if name in ("unemployment_rate","lfpr","epop","job_openings_rate",
                        "hires_rate","quits_rate","layoffs_rate"):
                arr = arr / 100.0
            targets[name] = arr
    # Approximate gross flows from CPS macro series
    if "unemployment_rate" in targets and "lfpr" in targets:
        ur, lfpr = targets["unemployment_rate"], targets["lfpr"]
        targets["flow_EU"] = np.clip(0.012 + 0.3*np.diff(np.append(ur[0],ur)), 0.005, 0.05)
        targets["flow_UE"] = np.clip(0.28 - 2.0*(ur-0.04), 0.10, 0.50)
        targets["flow_EN"] = np.clip(0.025 - 0.5*np.diff(np.append(lfpr[0],lfpr)), 0.01, 0.05)
        targets["flow_NE"] = np.clip(0.04 + 0.5*np.diff(np.append(lfpr[0],lfpr)), 0.02, 0.08)
        targets["flow_UN"] = np.clip(0.20 + 0.8*(ur-0.04) - 0.3*np.diff(np.append(lfpr[0],lfpr)), 0.12, 0.35)
        targets["flow_NU"] = np.clip(0.025 - 0.15*(ur-0.04) + 0.1*np.diff(np.append(lfpr[0],lfpr)), 0.01, 0.05)
    # Fill NaN
    for k in targets:
        v = targets[k]
        nans = np.isnan(v)
        if nans.any() and not nans.all():
            v[nans] = np.interp(np.flatnonzero(nans), np.flatnonzero(~nans), v[~nans])
    return targets


def make_env(targets):
    """Build environment path from targets."""
    vr = targets.get("job_openings_rate", np.full(N_MONTHS, 0.04)) * 100
    lr = targets.get("layoffs_rate", np.full(N_MONTHS, 0.012)) * 100
    mow = np.full(N_MONTHS, 10.5)  # log mean offer wage
    return EnvironmentPath(n_months=N_MONTHS, vacancy_rate=vr,
                           layoff_rate_env=lr, mean_offer_wage=mow)


def benchmark_loss(preds, targets, start, end, weights=None):
    if weights is None: weights = DEFAULT_WEIGHTS
    total, result = 0.0, {}
    for key, w in weights.items():
        if key not in preds or key not in targets: continue
        s, d = preds[key][start:end], targets[key][start:end]
        mask = ~(np.isnan(s)|np.isnan(d))
        if mask.sum() == 0: continue
        mse = np.mean((s[mask]-d[mask])**2) / max(np.var(d[mask]), 1e-10)
        wm = w * mse
        result[f"loss_{key}"] = float(wm)
        total += wm
    result["total_loss"] = float(total)
    return result


def rmse(pred, actual, start, end):
    p, a = pred[start:end], actual[start:end]
    m = ~(np.isnan(p)|np.isnan(a))
    return float(np.sqrt(np.mean((p[m]-a[m])**2))) if m.sum() > 0 else np.nan


def eval_abm(run_fn, params, env, n_seeds, n_agents):
    """Run ABM, return mean predictions dict."""
    all_p = {}
    for s in range(n_seeds):
        kw = dict(env=env, params=params, seed=s, n_agents=n_agents)
        if run_fn == run_model_a:
            kw.pop("n_agents")
        sim = run_fn(**kw)
        sd = sim.to_dict()
        for k, v in sd.items():
            all_p.setdefault(k, []).append(v)
    return {k: np.mean(v, axis=0) for k, v in all_p.items()}


def main():
    quick = "--quick" in sys.argv
    n_seeds = 3 if quick else 5
    n_agents = 1500 if quick else 3000
    print("=" * 75)
    print(f"  LONGEST HISTORY EXPERIMENT ({N_MONTHS} months, {START_YEAR}-{START_MONTH:02d} to {END_YEAR}-{END_MONTH:02d})")
    print(f"  Split: Train 0-{TRAIN_END} | Valid {TRAIN_END}-{VALID_END} | Test {VALID_END}-{N_MONTHS}")
    print(f"  Mode: {'QUICK' if quick else 'FULL'} | Seeds={n_seeds} Agents={n_agents}")
    print("=" * 75)

    # ═══ Load Data ═══
    print("\n[1] Loading BLS data...")
    targets = load_long_data()
    env = make_env(targets)
    n_avail = sum(1 for v in targets.values() if not np.all(np.isnan(v)))
    print(f"  Loaded {n_avail}/{len(targets)} series, {N_MONTHS} months")

    # ═══ Task 2: All 7 models ═══
    print("\n[2] Running 7 models on longest history...")
    results = {}  # name -> {preds, train, valid, test}
    colors = {"A_Traditional":"#999","B_StdABM":"#4DBEEE","C_HeteroABM":"#D95319",
              "D_ARIMA":"#77AC30","E_VAR":"#7E2F8E","F_BevRedForm":"#EDB120","G_DMP":"#0072BD"}

    # ABMs
    for name, fn, params in [("A_Traditional",run_model_a,BP_B),
                              ("B_StdABM",run_model_b,BP_B),
                              ("C_HeteroABM",run_model_c,BP_C)]:
        t0 = time.time()
        preds = eval_abm(fn, params, env, n_seeds, n_agents)
        tr = benchmark_loss(preds, targets, 0, TRAIN_END)
        vl = benchmark_loss(preds, targets, TRAIN_END, VALID_END)
        ts = benchmark_loss(preds, targets, VALID_END, N_MONTHS)
        results[name] = {"preds":preds,"train":tr["total_loss"],
                         "valid":vl["total_loss"],"test":ts["total_loss"]}
        print(f"  {name:<20} train={tr['total_loss']:8.0f}  test={ts['total_loss']:8.0f}  ({time.time()-t0:.0f}s)")

    # Benchmarks
    bm_kw = {"targets": targets, "train_end": TRAIN_END}
    for name, fn in [("D_ARIMA",run_benchmark_d),("E_VAR",run_benchmark_e),
                     ("F_BevRedForm",run_benchmark_f),("G_DMP",run_benchmark_g)]:
        t0 = time.time()
        preds = fn(**bm_kw)
        tr = benchmark_loss(preds, targets, 0, TRAIN_END)
        vl = benchmark_loss(preds, targets, TRAIN_END, VALID_END)
        ts = benchmark_loss(preds, targets, VALID_END, N_MONTHS)
        results[name] = {"preds":preds,"train":tr["total_loss"],
                         "valid":vl["total_loss"],"test":ts["total_loss"]}
        print(f"  {name:<20} train={tr['total_loss']:8.0f}  test={ts['total_loss']:8.0f}  ({time.time()-t0:.0f}s)")

    # ═══ TABLE 1: Total Loss ═══
    print(f"\n{'='*75}\n  TABLE 1: LONGEST HISTORY TOTAL LOSS\n{'='*75}")
    sorted_names = sorted(results, key=lambda n: results[n]["test"])
    c_test = results["C_HeteroABM"]["test"]
    print(f"  {'Model':<20} {'Train':>10} {'Valid':>10} {'Test':>10} {'vs C':>10} {'Rank':>5}")
    print("  "+"-"*68)
    for rank, nm in enumerate(sorted_names, 1):
        r = results[nm]
        d = (r["test"]-c_test)/max(c_test,1e-10)*100
        print(f"  {nm:<20} {r['train']:10.0f} {r['valid']:10.0f} {r['test']:10.0f} {d:+9.1f}% {rank:5d}")

    # TABLE 1b: Fair comparison (UR+LFPR+EPOP)
    fair_w = {k: DEFAULT_WEIGHTS.get(k,1.0) for k in ["unemployment_rate","lfpr","epop"]}
    fair = {nm: benchmark_loss(results[nm]["preds"], targets, VALID_END, N_MONTHS, fair_w)["total_loss"]
            for nm in results}
    fair_sorted = sorted(fair, key=fair.get)
    print(f"\n  TABLE 1b: FAIR (UR+LFPR+EPOP only)")
    print(f"  {'Model':<20} {'Test(fair)':>12} {'Rank':>5}")
    print("  "+"-"*40)
    for rank, nm in enumerate(fair_sorted, 1):
        print(f"  {nm:<20} {fair[nm]:12.0f} {rank:5d}")

    # TABLE 2: RMSE
    rk = ["unemployment_rate","lfpr","epop","quits_rate","layoffs_rate","hires_rate"]
    print(f"\n  TABLE 2: TEST RMSE (x100)")
    print(f"  {'Model':<20}" + "".join(f" {k[:8]:>10}" for k in rk))
    print("  "+"-"*(20+11*len(rk)))
    rmse_data = {}
    for nm in sorted_names:
        p = results[nm]["preds"]
        row = f"  {nm:<20}"
        rmses = {}
        for k in rk:
            if k in p:
                r = rmse(p[k], targets[k], VALID_END, N_MONTHS)
                rmses[k] = r
                row += f" {r*100:10.3f}" if not np.isnan(r) else f" {'N/A':>10}"
            else:
                rmses[k] = np.nan; row += f" {'N/A':>10}"
        rmse_data[nm] = rmses
        print(row)

    # ═══ Task 3: Model C Rolling Window ═══
    print(f"\n{'='*75}\n  TASK 3: MODEL C ROLLING WINDOW TEST\n{'='*75}")
    WINDOW = 36  # 36-month test windows
    STEP = 24    # step by 24 months
    rolling = []
    t_start = max(TRAIN_END, 60)  # need at least 60 months for train
    for test_start in range(t_start, N_MONTHS - WINDOW + 1, STEP):
        test_end = test_start + WINDOW
        # Train on everything before test_start - 12 (leave 12-month gap as validation)
        local_train_end = test_start - 12
        if local_train_end < 24:
            continue
        local_env = make_env(targets)
        preds_c = eval_abm(run_model_c, BP_C, local_env, n_seeds, n_agents)
        preds_b = eval_abm(run_model_b, BP_B, local_env, n_seeds, n_agents)
        loss_c = benchmark_loss(preds_c, targets, test_start, test_end, fair_w)["total_loss"]
        loss_b = benchmark_loss(preds_b, targets, test_start, test_end, fair_w)["total_loss"]
        # Also run ARIMA for comparison
        preds_d = run_benchmark_d(targets, train_end=local_train_end)
        loss_d = benchmark_loss(preds_d, targets, test_start, test_end, fair_w)["total_loss"]
        yr_s = START_YEAR + (START_MONTH - 1 + test_start) // 12
        mo_s = (START_MONTH - 1 + test_start) % 12 + 1
        yr_e = START_YEAR + (START_MONTH - 1 + test_end - 1) // 12
        mo_e = (START_MONTH - 1 + test_end - 1) % 12 + 1
        period = f"{yr_s}-{mo_s:02d} to {yr_e}-{mo_e:02d}"
        ur_rmse = rmse(preds_c.get("unemployment_rate", np.full(N_MONTHS,np.nan)),
                       targets["unemployment_rate"], test_start, test_end)
        rolling.append({"period":period, "start":test_start, "end":test_end,
                        "loss_c":loss_c, "loss_b":loss_b, "loss_d":loss_d,
                        "ur_rmse":ur_rmse})

    print(f"\n  TABLE 4: MODEL C ROLLING WINDOW RESULTS")
    print(f"  {'Window':<25} {'C(fair)':>10} {'B(fair)':>10} {'D(fair)':>10} {'C vs D':>10} {'UR RMSE':>10}")
    print("  "+"-"*78)
    for w in rolling:
        d = (w["loss_c"]-w["loss_d"])/max(w["loss_d"],1e-10)*100
        print(f"  {w['period']:<25} {w['loss_c']:10.0f} {w['loss_b']:10.0f} {w['loss_d']:10.0f}"
              f" {d:+9.1f}% {w['ur_rmse']*100:9.2f}%")

    # ═══ Task 4: Regime Tests ═══
    print(f"\n{'='*75}\n  TASK 4: MODEL C REGIME ANALYSIS\n{'='*75}")
    ur = targets["unemployment_rate"]
    # Define regimes by UR level and volatility
    regimes = {}
    for t in range(N_MONTHS):
        yr = START_YEAR + (START_MONTH - 1 + t) // 12
        mo = (START_MONTH - 1 + t) % 12 + 1
        if (yr == 2020 and mo >= 3) or (yr == 2020 and mo <= 12 and ur[t] > 0.06):
            regimes.setdefault("Shock (COVID)", []).append(t)
        elif yr >= 2021 and yr <= 2022:
            regimes.setdefault("Recovery (2021-22)", []).append(t)
        elif ur[t] < 0.05:
            regimes.setdefault("Stable Low UR", []).append(t)
        else:
            regimes.setdefault("Elevated UR", []).append(t)

    preds_c_full = results["C_HeteroABM"]["preds"]
    preds_d_full = results["D_ARIMA"]["preds"]
    print(f"\n  TABLE 5: MODEL C vs ARIMA BY REGIME")
    print(f"  {'Regime':<25} {'Months':>6} {'C UR_RMSE':>10} {'D UR_RMSE':>10} {'C better?':>10}")
    print("  "+"-"*65)
    regime_results = []
    for rname, indices in sorted(regimes.items()):
        indices = np.array(indices)
        if len(indices) < 3:
            continue
        ur_c = preds_c_full.get("unemployment_rate", np.full(N_MONTHS,np.nan))
        ur_d = preds_d_full.get("unemployment_rate", np.full(N_MONTHS,np.nan))
        ur_a = targets["unemployment_rate"]
        c_err = np.sqrt(np.nanmean((ur_c[indices]-ur_a[indices])**2))
        d_err = np.sqrt(np.nanmean((ur_d[indices]-ur_a[indices])**2))
        better = "✅" if c_err < d_err else "❌"
        regime_results.append({"regime":rname, "n":len(indices),
                               "c_rmse":c_err, "d_rmse":d_err, "c_wins":c_err<d_err})
        print(f"  {rname:<25} {len(indices):6d} {c_err*100:9.2f}% {d_err*100:9.2f}% {better:>10}")

    # ═══ Task 5: Charts ═══
    print(f"\n[5] Generating charts...")
    months = np.arange(N_MONTHS)

    # Fig A: Total Loss Bar Chart
    fig, ax = plt.subplots(figsize=(10,5))
    x = range(len(sorted_names))
    bars = ax.bar(x, [results[n]["test"] for n in sorted_names],
                  color=[colors.get(n,"#333") for n in sorted_names])
    ax.set_xticks(x); ax.set_xticklabels([n.replace("_","\n") for n in sorted_names], fontsize=7)
    ax.set_ylabel("Test Loss"); ax.set_title(f"Fig A: Longest History Test Loss ({N_MONTHS} months)")
    ax.axhline(c_test, color='red', ls='--', alpha=0.5, label=f"C={c_test:.0f}")
    ax.legend(); plt.tight_layout(); plt.savefig("figures/figA_long_test_loss.png", dpi=150); plt.close()

    # Fig B: RMSE Heatmap
    fig, ax = plt.subplots(figsize=(10,5))
    matrix = np.array([[rmse_data[n].get(k,np.nan)*100 for k in rk] for n in sorted_names])
    im = ax.imshow(matrix, aspect='auto', cmap='YlOrRd')
    ax.set_xticks(range(len(rk))); ax.set_xticklabels([k[:10] for k in rk], fontsize=8, rotation=30)
    ax.set_yticks(range(len(sorted_names))); ax.set_yticklabels(sorted_names, fontsize=8)
    for i in range(len(sorted_names)):
        for j in range(len(rk)):
            v = matrix[i,j]
            if not np.isnan(v):
                ax.text(j,i,f"{v:.2f}",ha='center',va='center',fontsize=6,
                        color='white' if v>np.nanmedian(matrix) else 'black')
    ax.set_title(f"Fig B: Longest History RMSE (x100)"); plt.colorbar(im,ax=ax)
    plt.tight_layout(); plt.savefig("figures/figB_long_rmse_heatmap.png", dpi=150); plt.close()

    # Fig C: Key series time plots
    for key, title in [("unemployment_rate","Unemployment Rate"),("lfpr","LFPR"),("epop","EPOP")]:
        fig, ax = plt.subplots(figsize=(14,5))
        ax.plot(months, targets[key], 'k-', lw=2, label="Actual (BLS)")
        ax.axvline(TRAIN_END, color='grey', ls=':'); ax.axvline(VALID_END, color='grey', ls=':')
        for nm in ["C_HeteroABM","D_ARIMA","G_DMP"]:
            if key in results[nm]["preds"]:
                ax.plot(months, results[nm]["preds"][key], '--',
                        color=colors.get(nm,"#333"), lw=1.2, alpha=0.8, label=nm)
        ax.set_title(f"Fig C: {title} ({N_MONTHS} months)"); ax.legend(fontsize=7)
        ax.set_xlabel("Month index"); plt.tight_layout()
        plt.savefig(f"figures/figC_{key}_long.png", dpi=150); plt.close()

    # Fig D: Rolling window
    if rolling:
        fig, ax = plt.subplots(figsize=(10,5))
        xs = [w["start"] for w in rolling]
        ax.plot(xs, [w["loss_c"] for w in rolling], 'o-', color=colors["C_HeteroABM"], label="C_HeteroABM")
        ax.plot(xs, [w["loss_d"] for w in rolling], 's--', color=colors["D_ARIMA"], label="D_ARIMA")
        ax.plot(xs, [w["loss_b"] for w in rolling], '^:', color=colors["B_StdABM"], label="B_StdABM")
        ax.set_xlabel("Test window start (month index)"); ax.set_ylabel("Test Loss (fair)")
        ax.set_title("Fig D: Rolling Window Test Loss"); ax.legend(); plt.tight_layout()
        plt.savefig("figures/figD_rolling_window.png", dpi=150); plt.close()

    # Fig E: Regime bar chart
    if regime_results:
        fig, ax = plt.subplots(figsize=(8,5))
        rnames = [r["regime"] for r in regime_results]
        x = range(len(rnames))
        w = 0.35
        ax.bar([i-w/2 for i in x], [r["c_rmse"]*100 for r in regime_results], w,
               color=colors["C_HeteroABM"], label="C_HeteroABM")
        ax.bar([i+w/2 for i in x], [r["d_rmse"]*100 for r in regime_results], w,
               color=colors["D_ARIMA"], label="D_ARIMA")
        ax.set_xticks(x); ax.set_xticklabels(rnames, fontsize=8)
        ax.set_ylabel("UR RMSE (%)"); ax.set_title("Fig E: UR RMSE by Regime")
        ax.legend(); plt.tight_layout()
        plt.savefig("figures/figE_regime.png", dpi=150); plt.close()

    print(f"  Charts saved to figures/")

    # ═══ Final Summary ═══
    print(f"\n{'='*75}\n  FINAL SUMMARY\n{'='*75}")
    print(f"  History: {N_MONTHS} months ({START_YEAR}-{START_MONTH:02d} to {END_YEAR}-{END_MONTH:02d})")
    print(f"  Full ranking: {', '.join(sorted_names)}")
    print(f"  Fair ranking: {', '.join(fair_sorted)}")
    c_rank_full = sorted_names.index("C_HeteroABM") + 1
    c_rank_fair = fair_sorted.index("C_HeteroABM") + 1
    print(f"  C rank: full={c_rank_full}/7, fair={c_rank_fair}/7")
    if rolling:
        c_wins = sum(1 for w in rolling if w["loss_c"] < w["loss_d"])
        print(f"  Rolling: C beats ARIMA in {c_wins}/{len(rolling)} windows")
    if regime_results:
        c_reg_wins = sum(1 for r in regime_results if r["c_wins"])
        print(f"  Regime: C beats ARIMA in {c_reg_wins}/{len(regime_results)} regimes")


if __name__ == "__main__":
    main()


"""
Real Data Integration & Main Empirical Run.
Fetches BLS data (CPS + JOLTS), constructs real environment,
and runs three-model comparison + ablation on real data.

Usage:
    python run_real_data.py [--quick]
"""
import sys, time
import numpy as np
from models.config import TOTAL_MONTHS, TRAIN_END, VALID_END
from models.real_data import (
    load_real_targets, load_real_environment, SCE_LMS_SUMMARY,
)
from models.loss import compute_loss, train_loss, valid_loss, test_loss, DEFAULT_WEIGHTS
from models.model_a import run_model_a
from models.model_b import run_model_b
from models.model_c import run_model_c
from models.calibration import run_search, select_top_candidates

# ── Settings ──
ABLATIONS = {
    "baseline":          {},
    "no_matching_mkt":   {"no_matching_market": True},
    "no_rw_hetero":      {"no_rw_hetero": True},
    "no_declining_rw":   {"no_declining_rw": True},
    "no_pp_hetero":      {"no_pp_hetero": True},
    "no_oab_hetero":     {"no_oab_hetero": True},
    "no_type_behavior":  {"no_type_behavior": True},
    "no_si_hetero":      {"no_si_hetero": True},
}


def eval_model(run_fn, params, env, targets, loss_fn, n_seeds, n_agents,
               ablation=None, model_name=""):
    losses, per = [], {}
    for s in range(n_seeds):
        kw = dict(env=env, params=params, seed=s, n_agents=n_agents)
        if ablation is not None:
            kw["ablation"] = ablation
        if run_fn == run_model_a:
            kw.pop("n_agents", None)
            kw.pop("ablation", None)
        sim = run_fn(**kw)
        ld = loss_fn(sim, targets)
        losses.append(ld["total_loss"])
        for k, v in ld.items():
            per.setdefault(k, []).append(v)
    return {
        "name": model_name,
        "mean_loss": float(np.mean(losses)),
        "std_loss": float(np.std(losses)),
        "per_target": {k: float(np.mean(v)) for k, v in per.items()},
    }


def main():
    quick = "--quick" in sys.argv
    n_samples = 30 if quick else 150
    n_seeds = 3 if quick else 10
    n_agents = 2000 if quick else 3000
    print("=" * 70)
    print("  REAL DATA INTEGRATION & MAIN EMPIRICAL RUN")
    print(f"  Mode: {'QUICK' if quick else 'FULL'} | {n_samples}×{n_seeds}×{n_agents}")
    print("=" * 70)

    # ═══ TASK A: Data Loading ═════════════════════════════════
    print("\n[A] LOADING REAL DATA...")
    targets, success = load_real_targets(2014, 2024, TOTAL_MONTHS)
    if not success:
        print("  [FALLBACK] Using synthetic targets with real structure")
        from models.loss import generate_synthetic_targets
        targets = generate_synthetic_targets(TOTAL_MONTHS)

    env = load_real_environment(targets, TOTAL_MONTHS)

    # Print data summary
    print("\n  Data availability:")
    for k, v in targets.items():
        n_valid = np.sum(~np.isnan(v))
        print(f"    {k:<25} {n_valid:>3}/{TOTAL_MONTHS} months"
              f"  range=[{np.nanmin(v):.4f}, {np.nanmax(v):.4f}]")

    # Fill NaN in targets with interpolation for loss computation
    for k in targets:
        v = targets[k]
        nans = np.isnan(v)
        if nans.any() and not nans.all():
            v[nans] = np.interp(np.flatnonzero(nans), np.flatnonzero(~nans), v[~nans])

    # ═══ TASK B-C: Variable Engineering & Experiment Design ═══
    print("\n[B-C] SCE LMS parameter anchors (published summary):")
    rw = SCE_LMS_SUMMARY["reservation_wage"]
    print(f"  RW(E): LogN(μ={rw['employed']['log_mean']}, σ={rw['employed']['log_sd']})")
    print(f"  RW(N): LogN(μ={rw['non_employed']['log_mean']}, σ={rw['non_employed']['log_sd']})")
    oab = SCE_LMS_SUMMARY["offer_arrival_belief"]
    print(f"  OAB(E): Beta(α={oab['employed']['beta_alpha']}, β={oab['employed']['beta_beta']})")
    print(f"  OAB(N): Beta(α={oab['non_employed']['beta_alpha']}, β={oab['non_employed']['beta_beta']})")
    si = SCE_LMS_SUMMARY["search_intensity"]
    print(f"  SI: p_low={si['p_low']}, p_mid={si['p_mid']}, p_high={si['p_high']}")

    # ═══ TASK D: Main Experiment ═════════════════════════════
    print(f"\n[D] PARAMETER SEARCH ({n_samples}×{n_seeds})...")
    best_by_model = {}
    for label, fn, search_seed in [("B", run_model_b, 42), ("C", run_model_c, 137)]:
        t0 = time.time()
        sr = run_search(fn, env, targets, lambda s, t: train_loss(s, t),
                        n_samples, n_seeds, n_agents, search_seed, verbose=True)
        vr = select_top_candidates(sr, fn, env, targets,
                                   lambda s, t: valid_loss(s, t),
                                   top_n=5, n_seeds=n_seeds, n_agents=n_agents)
        best_by_model[label] = vr[0]
        print(f"  Model {label}: train={vr[0]['train_loss']:.1f} valid={vr[0]['valid_loss']:.1f}"
              f"  ({time.time()-t0:.0f}s)")

    # Final three-model comparison
    print("\n[D] THREE-MODEL COMPARISON ON REAL DATA")
    bp_b, bp_c = best_by_model["B"]["params"], best_by_model["C"]["params"]
    results = {}
    for name, fn, params in [("A", run_model_a, bp_b), ("B", run_model_b, bp_b), ("C", run_model_c, bp_c)]:
        for split, lfn in [("train", train_loss), ("valid", valid_loss), ("test", test_loss)]:
            r = eval_model(fn, params, env, targets, lfn, n_seeds, n_agents, model_name=name)
            results[(name, split)] = r

    print(f"\n  {'Model':<10} {'Train':>10} {'Valid':>10} {'Test':>10} {'Test/Train':>10}")
    print("  " + "-" * 55)
    for m in ["A", "B", "C"]:
        tr = results[(m, "train")]["mean_loss"]
        vl = results[(m, "valid")]["mean_loss"]
        ts = results[(m, "test")]["mean_loss"]
        print(f"  {m:<10} {tr:10.1f} {vl:10.1f} {ts:10.1f} {ts/max(tr,1e-10):10.2f}")

    # Per-target test breakdown
    print(f"\n  Per-target TEST loss:")
    print(f"  {'Target':<22} {'A':>10} {'B':>10} {'C':>10} {'C vs B':>10}")
    print("  " + "-" * 65)
    for key in sorted(k for k in results[("A","test")]["per_target"] if k.startswith("loss_")):
        la = results[("A","test")]["per_target"].get(key, 0)
        lb = results[("B","test")]["per_target"].get(key, 0)
        lc = results[("C","test")]["per_target"].get(key, 0)
        d = (lc - lb) / max(lb, 1e-10) * 100
        print(f"  {key[5:]:<22} {la:10.1f} {lb:10.1f} {lc:10.1f} {d:+9.1f}%")

    # ═══ TASK E: Ablation ═════════════════════════════════════
    print(f"\n[E] ABLATION ON REAL DATA (test set)")
    abl_res = []
    for aname, adict in ABLATIONS.items():
        r = eval_model(run_model_c, bp_c, env, targets, test_loss,
                       n_seeds, n_agents, ablation=adict, model_name=aname)
        abl_res.append(r)
    base_loss = abl_res[0]["mean_loss"]
    for r in abl_res:
        d = (r["mean_loss"] - base_loss) / max(base_loss, 1e-10) * 100
        print(f"  {r['name']:<25} test={r['mean_loss']:10.1f}  Δ={d:+8.1f}%")

    # Summary
    print("\n" + "=" * 70)
    print("  REAL DATA RUN COMPLETE")
    print("=" * 70)
    ts_c = results[("C","test")]["mean_loss"]
    ts_b = results[("B","test")]["mean_loss"]
    ts_a = results[("A","test")]["mean_loss"]
    print(f"  C vs A (test): {(ts_c-ts_a)/max(ts_a,1e-10)*100:+.1f}%")
    print(f"  C vs B (test): {(ts_c-ts_b)/max(ts_b,1e-10)*100:+.1f}%")
    worst = max(abl_res[1:], key=lambda r: r["mean_loss"])
    print(f"  Most critical: {worst['name']} (+{(worst['mean_loss']-base_loss)/max(base_loss,1e-10)*100:.1f}%)")
    print(f"\n  Best C params: { {k: round(v,4) for k,v in bp_c.items()} }")


if __name__ == "__main__":
    main()

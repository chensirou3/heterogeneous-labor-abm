"""
Traditional / reduced-form benchmarks for unified comparison.

Benchmark D: AR/ARIMA (per-series univariate)
Benchmark E: VAR (multivariate)
Benchmark F: Beveridge reduced-form (dynamic OLS)
Benchmark G: Simplified DMP search-and-matching
"""
import numpy as np
import warnings
from typing import Dict, Optional
from models.config import TRAIN_END, VALID_END, TOTAL_MONTHS

# Suppress statsmodels convergence warnings for clean output
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# Keys that benchmarks can produce
CORE_KEYS = [
    "unemployment_rate", "lfpr", "epop",
    "quits_rate", "layoffs_rate", "hires_rate",
]


def _fill_nan(arr):
    """Interpolate NaN values."""
    a = arr.copy()
    nans = np.isnan(a)
    if nans.any() and not nans.all():
        a[nans] = np.interp(np.flatnonzero(nans), np.flatnonzero(~nans), a[~nans])
    return a


# ═══════════════════════════════════════════════════════════════
# Benchmark D: AR / ARIMA (per-series univariate)
# ═══════════════════════════════════════════════════════════════

def run_benchmark_d(
    targets: Dict[str, np.ndarray],
    train_end: int = TRAIN_END,
    valid_end: int = VALID_END,
    max_p: int = 6,
) -> Dict[str, np.ndarray]:
    """
    Fit AR(p) per series on train, select p by AIC on validation,
    produce full-length predictions.
    """
    from statsmodels.tsa.ar_model import AutoReg

    n = len(next(iter(targets.values())))
    preds = {}

    for key in CORE_KEYS:
        if key not in targets:
            continue
        y = _fill_nan(targets[key])
        train_y = y[:train_end]

        # Select lag order by AIC on validation
        best_aic, best_p = np.inf, 1
        for p in range(1, max_p + 1):
            try:
                model = AutoReg(train_y, lags=p).fit()
                aic = model.aic
                if aic < best_aic:
                    best_aic, best_p = aic, p
            except Exception:
                continue

        # Refit on train and predict full horizon
        try:
            model = AutoReg(train_y, lags=best_p).fit()
            pred = np.full(n, np.nan)
            # fittedvalues starts at index best_p
            fv = model.fittedvalues
            pred[best_p:train_end] = fv[-(train_end - best_p):]
            for t in range(best_p):
                pred[t] = train_y[t]
            # Recursive forecast for validation + test
            last_vals = list(train_y[-best_p:])
            for t in range(train_end, n):
                fc = model.params[0] + sum(model.params[i+1] * last_vals[-(i+1)]
                                           for i in range(best_p))
                pred[t] = fc
                last_vals.append(fc)
            preds[key] = pred
        except Exception as e:
            print(f"  [D] {key} failed: {e}")
            # Fallback: last-value persistence
            pred = np.full(n, np.nan)
            pred[:train_end] = train_y
            for t in range(train_end, n):
                pred[t] = train_y[-1]
            preds[key] = pred

    return preds


# ═══════════════════════════════════════════════════════════════
# Benchmark E: VAR (multivariate)
# ═══════════════════════════════════════════════════════════════

def run_benchmark_e(
    targets: Dict[str, np.ndarray],
    train_end: int = TRAIN_END,
    max_p: int = 8,
) -> Dict[str, np.ndarray]:
    """
    Fit VAR(p) on core series, select p by AIC, forecast test period.
    """
    from statsmodels.tsa.api import VAR

    available = [k for k in CORE_KEYS if k in targets]
    if len(available) < 2:
        print("  [E] Not enough series for VAR")
        return {}

    n = len(targets[available[0]])
    # Build matrix
    data = np.column_stack([_fill_nan(targets[k])[:train_end] for k in available])

    try:
        model = VAR(data)
        max_lag = min(max_p, train_end // 3 - 1)
        result = model.fit(maxlags=max_lag, ic="aic")
        chosen_p = result.k_ar

        fc_horizon = n - train_end
        forecast = result.forecast(data[-chosen_p:], steps=fc_horizon)

        preds = {}
        fv = result.fittedvalues  # shape: (train_end - chosen_p, n_vars)
        for i, key in enumerate(available):
            pred = np.full(n, np.nan)
            # fittedvalues starts at index chosen_p
            pred[chosen_p:train_end] = fv[:, i]
            for t in range(chosen_p):
                pred[t] = _fill_nan(targets[key])[t]
            pred[train_end:] = forecast[:, i]
            preds[key] = pred
    except Exception as e:
        print(f"  [E] VAR failed: {e}")
        # Fallback: persistence
        preds = {}
        for k in available:
            y = _fill_nan(targets[k])
            pred = np.full(n, np.nan)
            pred[:train_end] = y[:train_end]
            for t in range(train_end, n):
                pred[t] = y[train_end - 1]
            preds[k] = pred

    return preds


# ═══════════════════════════════════════════════════════════════
# Benchmark F: Beveridge / Reduced-form labor tightness
# ═══════════════════════════════════════════════════════════════

def run_benchmark_f(
    targets: Dict[str, np.ndarray],
    train_end: int = TRAIN_END,
) -> Dict[str, np.ndarray]:
    """
    Dynamic reduced-form:
      u_t = α + β1*u_{t-1} + β2*openings_t + β3*layoffs_t + β4*quits_t + ε
    Also: lfpr_t = α + β1*lfpr_{t-1} + β2*u_t + β3*epop_{t-1} + ε
    """
    n = len(targets.get("unemployment_rate", np.array([])))
    if n == 0:
        return {}

    ur = _fill_nan(targets["unemployment_rate"])
    preds = {}

    # --- UR equation ---
    jor = _fill_nan(targets.get("job_openings_rate", np.zeros(n)))
    lr = _fill_nan(targets.get("layoffs_rate", np.zeros(n)))
    qr = _fill_nan(targets.get("quits_rate", np.zeros(n)))

    # Build X: [1, u_{t-1}, jor_t, lr_t, qr_t] for t=1..train_end-1
    t_range = range(1, train_end)
    X = np.column_stack([
        np.ones(len(t_range)),
        ur[[t-1 for t in t_range]],
        jor[list(t_range)],
        lr[list(t_range)],
        qr[list(t_range)],
    ])
    y = ur[list(t_range)]

    try:
        beta_ur = np.linalg.lstsq(X, y, rcond=None)[0]
        pred_ur = np.full(n, np.nan)
        pred_ur[0] = ur[0]
        for t in range(1, n):
            u_prev = pred_ur[t-1] if t >= train_end else ur[t-1]
            pred_ur[t] = beta_ur[0] + beta_ur[1]*u_prev + beta_ur[2]*jor[t] + \
                         beta_ur[3]*lr[t] + beta_ur[4]*qr[t]
            pred_ur[t] = np.clip(pred_ur[t], 0.01, 0.20)
        preds["unemployment_rate"] = pred_ur
    except Exception as e:
        print(f"  [F] UR equation failed: {e}")

    # --- LFPR equation ---
    lfpr = _fill_nan(targets.get("lfpr", np.zeros(n)))
    epop = _fill_nan(targets.get("epop", np.zeros(n)))
    X2 = np.column_stack([
        np.ones(len(t_range)),
        lfpr[[t-1 for t in t_range]],
        ur[list(t_range)],
        epop[[t-1 for t in t_range]],
    ])
    y2 = lfpr[list(t_range)]
    try:
        beta_lf = np.linalg.lstsq(X2, y2, rcond=None)[0]
        pred_lf = np.full(n, np.nan)
        pred_lf[0] = lfpr[0]
        for t in range(1, n):
            lf_prev = pred_lf[t-1] if t >= train_end else lfpr[t-1]
            u_val = preds.get("unemployment_rate", ur)[t]
            ep_prev = epop[t-1] if t < train_end else (lf_prev * (1 - u_val))
            pred_lf[t] = beta_lf[0] + beta_lf[1]*lf_prev + beta_lf[2]*u_val + beta_lf[3]*ep_prev
            pred_lf[t] = np.clip(pred_lf[t], 0.55, 0.70)
        preds["lfpr"] = pred_lf
    except Exception as e:
        print(f"  [F] LFPR equation failed: {e}")

    # EPOP derived
    if "unemployment_rate" in preds and "lfpr" in preds:
        preds["epop"] = preds["lfpr"] * (1 - preds["unemployment_rate"])

    # Note: F does NOT model JOLTS flows — omitted (not pass-through)
    return preds


# ═══════════════════════════════════════════════════════════════
# Benchmark G: Simplified DMP search-and-matching
# ═══════════════════════════════════════════════════════════════

def run_benchmark_g(
    targets: Dict[str, np.ndarray],
    train_end: int = TRAIN_END,
) -> Dict[str, np.ndarray]:
    """
    Simplified DMP:
      θ_t = v_t / u_t                    (labor market tightness)
      f(θ) = A * θ^α                     (matching function, Cobb-Douglas)
      s_t = layoffs_rate_t               (separation rate)
      u_{t+1} = u_t + s_t*(1-u_t) - f(θ_t)*u_t  (unemployment law of motion)

    Calibrate A, α on train by least squares.
    """
    n = len(targets.get("unemployment_rate", np.array([])))
    if n == 0:
        return {}

    ur = _fill_nan(targets["unemployment_rate"])
    jor = _fill_nan(targets.get("job_openings_rate", np.full(n, 0.04)))
    lr = _fill_nan(targets.get("layoffs_rate", np.full(n, 0.012)))

    # Tightness θ = v/u (openings rate / unemployment rate)
    theta = np.clip(jor / np.maximum(ur, 0.005), 0.1, 20.0)

    # Calibrate matching function f(θ) = A * θ^α
    # From law of motion: f(θ_t) = (u_t + s_t*(1-u_t) - u_{t+1}) / u_t
    f_implied = np.zeros(train_end - 1)
    for t in range(train_end - 1):
        f_implied[t] = (ur[t] + lr[t]*(1-ur[t]) - ur[t+1]) / max(ur[t], 0.005)
    f_implied = np.clip(f_implied, 0.01, 1.0)

    # Log-linear regression: log(f) = log(A) + α*log(θ)
    log_f = np.log(np.maximum(f_implied, 1e-6))
    log_theta = np.log(np.maximum(theta[:train_end-1], 1e-6))
    X = np.column_stack([np.ones(train_end-1), log_theta])
    try:
        beta = np.linalg.lstsq(X, log_f, rcond=None)[0]
        A = np.exp(beta[0])
        alpha = np.clip(beta[1], 0.1, 0.9)  # standard range
    except Exception:
        A, alpha = 0.5, 0.5  # fallback

    # Simulate forward
    pred_ur = np.full(n, np.nan)
    pred_ur[0] = ur[0]
    for t in range(n - 1):
        u_t = pred_ur[t] if t >= train_end else ur[t]
        th = np.clip(jor[t] / max(u_t, 0.005), 0.1, 20.0)
        f_t = A * th ** alpha
        s_t = lr[t]
        u_next = u_t + s_t * (1 - u_t) - f_t * u_t
        pred_ur[t+1] = np.clip(u_next, 0.01, 0.20)

    preds = {"unemployment_rate": pred_ur}

    # Derive LFPR and EPOP using simple persistence
    lfpr = _fill_nan(targets.get("lfpr", np.full(n, 0.625)))
    pred_lfpr = np.full(n, np.nan)
    pred_lfpr[0] = lfpr[0]
    for t in range(1, n):
        pred_lfpr[t] = 0.98 * (pred_lfpr[t-1] if t >= train_end else lfpr[t-1]) + \
                        0.02 * np.mean(lfpr[:train_end])
    preds["lfpr"] = pred_lfpr
    preds["epop"] = pred_lfpr * (1 - pred_ur)

    # Note: G does NOT model JOLTS flows — omitted (not pass-through)
    return preds


"""
Real data loader for BLS (CPS + JOLTS) and SCE LMS summary statistics.
Fetches data via BLS Public Data API v2 and constructs model-compatible inputs.
"""
import json
import os
import numpy as np
from typing import Dict, Tuple, Optional
from urllib.request import urlopen, Request
from models.config import BASELINE_LFPR
from models.environment import EnvironmentPath

# BLS API endpoint
BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

# ═══ BLS Series IDs ══════════════════════════════════════════
# CPS (seasonally adjusted)
SERIES_UR = "LNS14000000"       # Unemployment Rate (%)
SERIES_LFPR = "LNS11300000"     # Labor Force Participation Rate (%)
SERIES_EPOP = "LNS12300000"     # Employment-Population Ratio (%)

# JOLTS (seasonally adjusted, total nonfarm)
SERIES_JO_LEVEL = "JTS000000000000000JOL"   # Job Openings Level (thousands)
SERIES_JO_RATE = "JTS000000000000000JOR"     # Job Openings Rate (%)
SERIES_HIRES = "JTS000000000000000HIL"       # Hires Level (thousands)
SERIES_QUITS_RATE = "JTS000000000000000QUR"  # Quits Rate (%)
SERIES_LAYOFFS_RATE = "JTS000000000000000LDR"  # Layoffs & Discharges Rate (%)

# CPS Gross Flows (not seasonally adjusted - calculated from matched CPS)
# These are published by BLS as flows between E/U/N
SERIES_FLOWS = {
    "flow_EU": "LNS17100000",  # E→U flow (thousands)
    "flow_UE": "LNS17200000",  # U→E flow (thousands)
}
# Note: Full 6-flow matrix requires BLS Gross Flows tables, not individual series

ALL_SERIES = [
    SERIES_UR, SERIES_LFPR, SERIES_EPOP,
    SERIES_JO_RATE, SERIES_HIRES, SERIES_QUITS_RATE, SERIES_LAYOFFS_RATE,
]


def fetch_bls_data(
    series_ids: list,
    start_year: int = 2014,
    end_year: int = 2024,
    api_key: str = "",
) -> Dict[str, list]:
    """
    Fetch time series data from BLS API v2.
    Returns dict of {series_id: [(year, month, value), ...]}.
    """
    results = {}
    # BLS API limits to 10 years per request
    for chunk_start in range(start_year, end_year + 1, 10):
        chunk_end = min(chunk_start + 9, end_year)
        payload = {
            "seriesid": series_ids,
            "startyear": str(chunk_start),
            "endyear": str(chunk_end),
        }
        if api_key:
            payload["registrationkey"] = api_key

        data = json.dumps(payload).encode("utf-8")
        req = Request(BLS_API_URL, data=data,
                      headers={"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"  [WARN] BLS API request failed: {e}")
            continue

        if body.get("status") != "REQUEST_SUCCEEDED":
            print(f"  [WARN] BLS API returned: {body.get('message', 'unknown')}")
            continue

        for series in body.get("Results", {}).get("series", []):
            sid = series["seriesID"]
            if sid not in results:
                results[sid] = []
            for entry in series.get("data", []):
                if entry["period"].startswith("M") and entry["period"] != "M13":
                    year = int(entry["year"])
                    month = int(entry["period"][1:])
                    val = float(entry["value"])
                    results[sid].append((year, month, val))

    # Sort by date
    for sid in results:
        results[sid].sort(key=lambda x: (x[0], x[1]))

    return results


def bls_to_monthly_array(
    data: list,
    start_year: int = 2014,
    start_month: int = 1,
    n_months: int = 132,
) -> np.ndarray:
    """Convert BLS (year, month, value) list to aligned monthly array."""
    arr = np.full(n_months, np.nan)
    for year, month, val in data:
        idx = (year - start_year) * 12 + (month - start_month)
        if 0 <= idx < n_months:
            arr[idx] = val
    return arr


def load_real_targets(
    start_year: int = 2014,
    end_year: int = 2024,
    n_months: int = 132,
    api_key: str = "",
    cache_file: str = "data/bls_cache.json",
) -> Tuple[Dict[str, np.ndarray], bool]:
    """
    Load real CPS + JOLTS target data.
    Returns (targets_dict, success).

    If API fails, falls back to cache or returns (None, False).
    """
    # Try loading from cache first
    if os.path.exists(cache_file):
        print(f"  Loading cached BLS data from {cache_file}")
        with open(cache_file, "r") as f:
            cached = json.load(f)
        raw = {k: [(d[0], d[1], d[2]) for d in v] for k, v in cached.items()}
    else:
        print(f"  Fetching data from BLS API ({start_year}-{end_year})...")
        raw = fetch_bls_data(ALL_SERIES, start_year, end_year, api_key)
        if raw:
            os.makedirs(os.path.dirname(cache_file) or ".", exist_ok=True)
            with open(cache_file, "w") as f:
                json.dump({k: list(v) for k, v in raw.items()}, f)
            print(f"  Cached to {cache_file}")

    if not raw:
        print("  [ERROR] No BLS data available.")
        return None, False

    targets = {}

    # CPS targets (convert from % to proportion)
    if SERIES_UR in raw:
        targets["unemployment_rate"] = bls_to_monthly_array(raw[SERIES_UR],
                                                             start_year, 1, n_months) / 100.0
    if SERIES_LFPR in raw:
        targets["lfpr"] = bls_to_monthly_array(raw[SERIES_LFPR],
                                                start_year, 1, n_months) / 100.0
    if SERIES_EPOP in raw:
        targets["epop"] = bls_to_monthly_array(raw[SERIES_EPOP],
                                                start_year, 1, n_months) / 100.0

    # JOLTS targets (already in % for rates)
    if SERIES_JO_RATE in raw:
        targets["job_openings_rate"] = bls_to_monthly_array(raw[SERIES_JO_RATE],
                                                             start_year, 1, n_months) / 100.0
    if SERIES_QUITS_RATE in raw:
        targets["quits_rate"] = bls_to_monthly_array(raw[SERIES_QUITS_RATE],
                                                      start_year, 1, n_months) / 100.0
    if SERIES_LAYOFFS_RATE in raw:
        targets["layoffs_rate"] = bls_to_monthly_array(raw[SERIES_LAYOFFS_RATE],
                                                        start_year, 1, n_months) / 100.0

    # Hires: convert level to rate (hires / employment)
    if SERIES_HIRES in raw:
        hires_level = bls_to_monthly_array(raw[SERIES_HIRES], start_year, 1, n_months)
        # Approximate employment level ~ 150,000 thousands (adjust as needed)
        emp_level = 150000.0
        if "epop" in targets:
            # Better: use EPOP × civilian noninstitutional pop (~260M)
            emp_level = targets["epop"] * 260000.0
            emp_level[np.isnan(emp_level)] = 150000.0
        targets["hires_rate"] = hires_level / emp_level

    # Gross flows: approximate from transitions
    # CPS Gross Flows are published quarterly by BLS
    # For MVP, estimate flow rates from UR/LFPR changes
    if "unemployment_rate" in targets and "lfpr" in targets:
        ur = targets["unemployment_rate"]
        lfpr = targets["lfpr"]
        # Approximate E→U: ~1.2% average (CPS historical)
        targets["flow_EU"] = np.where(np.isnan(ur), np.nan,
                                       np.clip(0.012 + 0.3 * np.diff(np.append(ur[0], ur)), 0.005, 0.05))
        # Approximate U→E: ~28% average
        targets["flow_UE"] = np.where(np.isnan(ur), np.nan,
                                       np.clip(0.28 - 2.0 * (ur - 0.04), 0.10, 0.50))
        # E→N, N→E, U→N, N→U: use historical averages with UR modulation
        targets["flow_EN"] = np.where(np.isnan(lfpr), np.nan,
                                       np.clip(0.025 - 0.5 * np.diff(np.append(lfpr[0], lfpr)), 0.01, 0.05))
        targets["flow_NE"] = np.where(np.isnan(lfpr), np.nan,
                                       np.clip(0.04 + 0.5 * np.diff(np.append(lfpr[0], lfpr)), 0.02, 0.08))
        # U→N: ~20% average, modulated by UR and LFPR
        # Higher UR → more discouragement → higher U→N
        targets["flow_UN"] = np.where(np.isnan(ur), np.nan,
                                       np.clip(0.20 + 0.8 * (ur - 0.04) - 0.3 * np.diff(np.append(lfpr[0], lfpr)),
                                               0.12, 0.35))
        # N→U: ~2.5% average, modulated by UR (lower UR → more re-entry)
        targets["flow_NU"] = np.where(np.isnan(ur), np.nan,
                                       np.clip(0.025 - 0.15 * (ur - 0.04) + 0.1 * np.diff(np.append(lfpr[0], lfpr)),
                                               0.01, 0.05))

    # Check completeness
    n_available = sum(1 for v in targets.values() if not np.all(np.isnan(v)))
    print(f"  Loaded {n_available}/{len(targets)} target series")

    return targets, n_available >= 3


def load_real_environment(
    targets: Dict[str, np.ndarray],
    n_months: int = 132,
) -> EnvironmentPath:
    """
    Construct real environment path from JOLTS data.
    Falls back to synthetic for missing values.
    """
    from models.environment import generate_synthetic_environment
    synth = generate_synthetic_environment(n_months)

    # Vacancy rate from JOLTS JOR (in proportion, convert to %)
    vr = synth.vacancy_rate.copy()
    if "job_openings_rate" in targets:
        real_vr = targets["job_openings_rate"] * 100  # back to %
        mask = ~np.isnan(real_vr)
        vr[mask] = real_vr[mask]

    # Layoff rate from JOLTS LDR (in proportion, convert to %)
    lr = synth.layoff_rate_env.copy()
    if "layoffs_rate" in targets:
        real_lr = targets["layoffs_rate"] * 100
        mask = ~np.isnan(real_lr)
        lr[mask] = real_lr[mask]

    # Fill NaN with interpolation
    for arr in [vr, lr]:
        nans = np.isnan(arr)
        if nans.any() and not nans.all():
            arr[nans] = np.interp(np.flatnonzero(nans), np.flatnonzero(~nans), arr[~nans])

    return EnvironmentPath(
        n_months=n_months,
        vacancy_rate=vr,
        layoff_rate_env=lr,
        mean_offer_wage=synth.mean_offer_wage,  # wage path: use synthetic for now
    )


# ═══ SCE LMS Summary Statistics ══════════════════════════════
# Source: NY Fed SCE Labor Market Survey published charts/tables
# These are aggregate statistics used to anchor parameter distributions
# when microdata is not yet loaded.

SCE_LMS_SUMMARY = {
    "reservation_wage": {
        "employed": {"mean_annual": 81_362, "median_annual": 63_341,
                     "log_mean": 11.01, "log_sd": 0.65},
        "non_employed": {"mean_annual": 57_000, "median_annual": 42_000,
                         "log_mean": 10.65, "log_sd": 0.75},
        "source": "SCE LMS 2014-2024 published charts",
    },
    "offer_arrival_belief": {
        "employed": {"mean_pct": 20.5, "median_pct": 10.0,
                     "beta_alpha": 1.8, "beta_beta": 7.0},
        "non_employed": {"mean_pct": 30.2, "median_pct": 18.0,
                         "beta_alpha": 2.5, "beta_beta": 5.8},
        "source": "SCE LMS p(job offer next 4 months)",
    },
    "search_intensity": {
        "pct_searched": 28.0,  # % who searched in past 4 weeks
        "p_low": 0.72, "p_mid": 0.15, "p_high": 0.13,
        "source": "SCE LMS search activity variable",
    },
    "job_transition_belief": {
        "employed_mean_pct": 15.0,
        "non_employed_mean_pct": 25.0,
        "source": "SCE LMS p(move into employment)",
    },
}

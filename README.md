# Heterogeneous Labor Market ABM

A research codebase for studying whether **survey-constrained behavioral heterogeneity** in a labor market agent-based model (ABM) improves the ability to reproduce U.S. labor market dynamics — particularly during structural breaks and extreme shocks.

## Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Data](#data)
- [Methodology](#methodology)
- [Experiment Pipeline](#experiment-pipeline)
- [Results](#results)
- [Reproducibility](#reproducibility)
- [Limitations](#limitations)
- [Citation](#citation)
- [License](#license)

## Overview

**Research question.** Does introducing individual-level labor behavioral heterogeneity — anchored to public survey data — into a search-and-matching ABM improve its ability to replicate aggregate labor market series, and under what conditions?

**Approach.** We build three progressively complex structural models (traditional Markov benchmark → homogeneous ABM → heterogeneous ABM) and compare them against four standard statistical/econometric benchmarks (AR/ARIMA, VAR, Beveridge reduced-form, canonical DMP) on official BLS time series (CPS + JOLTS). All seven models are evaluated under a unified multi-objective loss function, identical train/validation/test splits, and consistent evaluation metrics.

**Main finding.** On the longest available history (291 months, 2001–2025), the heterogeneous ABM does not outperform standard time series methods in aggregate forecast accuracy. However, during the COVID-19 shock — an unprecedented nonlinear labor market event — it is the only model that outperforms ARIMA on unemployment rate prediction (RMSE 2.51% vs 4.13%). The ABM's primary value lies in mechanism decomposability (via ablation), counterfactual capability, and robustness under regime change, rather than point-forecast superiority.

**Status.** This is an active research project. Results are preliminary. See [Limitations](#limitations).

## Project Structure

```
models/
├── config.py            # Constants, parameter bounds, SimulationOutput dataclass
├── environment.py       # Exogenous environment path (vacancy rate, layoff dynamics)
├── worker.py            # Worker agent with 4 behavioral parameters + type modifiers
├── model_a.py           # Model A: deterministic Markov-chain benchmark
├── model_b.py           # Model B: homogeneous multi-agent ABM
├── model_c.py           # Model C: heterogeneous ABM + matching market competition
├── loss.py              # Multi-objective variance-normalized MSE loss function
├── calibration.py       # Latin Hypercube parameter search + validation selection
├── real_data.py         # BLS API data loader (CPS + JOLTS) + SCE LMS anchors
└── benchmarks.py        # AR/ARIMA, VAR, Beveridge reduced-form, simplified DMP

run_experiment.py        # Synthetic-data three-model comparison (Stage 2)
run_stage3.py            # Out-of-sample evaluation, ablation, robustness (Stage 3)
run_real_data.py         # Real BLS data integration + main empirical run
run_benchmarks.py        # 7-model unified benchmark comparison (132-month window)
run_longest_history.py   # 291-month longest-history experiment + rolling/regime tests
check_history.py         # BLS series availability checker

figures/                 # Generated charts (bar plots, heatmaps, time series)
data/                    # Cached BLS API responses (auto-generated)
数据可行性报告/            # Stage-by-stage research reports (in Chinese)
方案/                     # Research design documents
```

## Installation

**Requirements:** Python ≥ 3.8, internet access for BLS API (first run only).

```bash
pip install numpy scipy statsmodels matplotlib
```

No GPU required. All experiments run on CPU.

## Quick Start

Each script supports `--quick` (fewer seeds, smaller agent population, ~2–5 min) and full mode (more seeds, larger population, ~15–60 min).

```bash
# 1. Synthetic data experiment — validates model logic without network access
python run_experiment.py --quick

# 2. Real data experiment — fetches BLS data via API, runs 3-model comparison
python run_real_data.py --quick

# 3. 7-model benchmark comparison (132-month window) — generates figures/
python run_benchmarks.py --quick

# 4. Longest-history experiment (291 months) — rolling window + regime analysis
python run_longest_history.py --quick
```

**Output:** console tables + PNG charts in `figures/`. BLS data is cached to `data/bls_cache.json` after first download; subsequent runs work offline.

**`--quick` vs full mode:**

| Parameter | `--quick` | Full |
|-----------|----------|------|
| Random seeds | 3 | 5–10 |
| Agent population | 1,500–2,000 | 3,000–10,000 |
| Parameter search samples | 30 | 150 |
| Approximate runtime | 2–5 min | 15–60 min |

## Data

All data sources are publicly available. No restricted-access data is used.

| Source | Series | Role in Model | Access Method |
|--------|--------|--------------|---------------|
| **CPS** (Bureau of Labor Statistics) | Unemployment rate, LFPR, EPOP | Calibration targets, state distribution | BLS Public Data API v2 |
| **JOLTS** (Bureau of Labor Statistics) | Job openings rate, hires, quits rate, layoffs rate | Exogenous environment path, calibration targets | BLS Public Data API v2 |
| **SCE Labor Market Survey** (NY Fed) | Reservation wage, offer arrival belief, search activity | Parameter distribution anchors | Published summary statistics |

**Gross flows** (E↔U, E↔N, U↔N) are approximated from CPS macro series changes, not from directly published BLS gross flow tables. This is a known limitation (see [Limitations](#limitations)).

**BLS API note:** the public API has rate limits (25 requests/day for unregistered users). Register at [https://data.bls.gov/registrationEngine/](https://data.bls.gov/registrationEngine/) for higher limits. A free API key can be set via the `api_key` parameter in `real_data.py`.

## Methodology

### Models

| Label | Name | Description |
|-------|------|-------------|
| **A** | Traditional benchmark | Deterministic representative-agent Markov chain. Aggregate E/U/N transition rates. |
| **B** | Standard ABM | Multi-agent stochastic model with homogeneous behavioral parameters. |
| **C** | Heterogeneous ABM | Heterogeneous parameters drawn from survey-anchored distributions, 3 worker types, finite-vacancy matching market. |

### Behavioral Parameters (Model C)

Four per-worker parameters, each anchored to public survey data:

1. **Reservation wage** — LogNormal distribution, differentiated by employment status (SCE LMS)
2. **Offer arrival belief** — Beta distribution, subjective job-offer probability (SCE LMS)
3. **Search intensity** — 3-tier discrete (low/mid/high), calibrated to SCE search activity
4. **Participation propensity** — 12 demographic groups (age × education × sex), from CPS LFPR

### Key Mechanisms

- **Matching market competition:** finite job openings allocated by search-intensity priority, creating endogenous composition effects
- **Reservation wage heterogeneity:** differential acceptance thresholds across workers
- **Type-specific behavioral rules:** Active Searchers (lower layoff risk), Low-Threshold Acceptors, Marginal Workers (higher exit propensity)
- **Declining reservation wage:** RW decays with unemployment duration

### Statistical Benchmarks

| Label | Method | Variables modeled |
|-------|--------|-------------------|
| **D** | AR/ARIMA (per-series) | All 6 core series independently |
| **E** | VAR | 6 core series jointly |
| **F** | Beveridge reduced-form | UR, LFPR, EPOP via dynamic OLS with JOLTS regressors |
| **G** | Simplified DMP | UR via matching function f(θ) = Aθ^α, LFPR/EPOP derived |

### Loss Function

Multi-objective variance-normalized weighted MSE across 12 target series (UR, LFPR, EPOP, 6 gross flows, hires rate, quits rate, layoffs rate). Weights prioritize UR (3.0), EPOP (2.0), and LFPR (1.5). See `models/loss.py` for details.

## Experiment Pipeline

The project follows a staged research pipeline. Each stage has a corresponding report in `数据可行性报告/`.

| Stage | Script | Description | Report |
|-------|--------|-------------|--------|
| 1 | — | Data–parameter mapping feasibility | [阶段一报告](数据可行性报告/阶段一_综合报告_数据参数落地实验.md) |
| 2 | `run_experiment.py` | Synthetic data: model prototyping & calibration | [阶段二报告](数据可行性报告/阶段二_综合报告_模型原型与校准实验.md) |
| 3 | `run_stage3.py` | Synthetic data: test-set evaluation, ablation, robustness | [阶段三报告](数据可行性报告/阶段三_综合报告_测试集评估与稳健性.md) |
| 4 | `run_real_data.py` | Real BLS data: 3-model comparison (132 months) | [真实数据报告](数据可行性报告/真实数据_综合报告_主实验结果.md) |
| 5 | `run_benchmarks.py` | 7-model unified benchmark comparison (132 months) | [扩展基准报告](数据可行性报告/扩展基准测试_综合报告.md) |
| 6 | `run_longest_history.py` | 291-month longest history + rolling window + regime tests | [最长历史报告](数据可行性报告/最长历史_综合报告.md) |

## Results

### Longest-History Experiment (291 months, 2001-01 to 2025-03)

Test period: 59 months (2020-06 to 2025-03), covering COVID shock, recovery, and stabilization.

**7-model comparison (UR + LFPR + EPOP, variance-normalized MSE):**

| Rank | Model | Test Loss | Type |
|------|-------|----------|------|
| 1 | E_VAR | 49 | Multivariate time series |
| 2 | D_ARIMA | 66 | Univariate time series |
| 3 | G_DMP | 110 | Structural reduced-form |
| 4 | F_BevRedForm | 154 | Dynamic OLS |
| 5 | B_StdABM | 207 | Homogeneous ABM |
| 6 | C_HeteroABM | 361 | Heterogeneous ABM |
| 7 | A_Traditional | 6,734 | Deterministic benchmark |

**Regime-conditional analysis (UR RMSE):**

| Regime | Months | C_HeteroABM | D_ARIMA | C wins? |
|--------|--------|-------------|---------|---------|
| Stable low UR | 108 | 3.94% | 1.83% | No |
| Elevated UR | 149 | 4.33% | 0.17% | No |
| **COVID shock** | **10** | **2.51%** | **4.13%** | **Yes** |
| Recovery (2021–22) | 24 | 2.84% | 2.20% | No |

**Interpretation.** Standard time series methods outperform the ABM in aggregate forecast accuracy across most regimes. The heterogeneous ABM's advantage is specific to the COVID shock period — the only regime where autoregressive models fail to track the unprecedented nonlinear dynamics. The ABM's structural value lies in mechanism identification (via ablation) and counterfactual analysis, not in forecast superiority.

### Ablation (132-month real data experiment)

| Mechanism removed | Test loss change |
|-------------------|-----------------|
| Reservation wage heterogeneity | +212% |
| Matching market competition | +179% |
| Search intensity heterogeneity | +40% |
| Offer arrival belief heterogeneity | +35% |
| Type-specific behavioral rules | +26% |

## Reproducibility

### Recommended execution order

```bash
python run_experiment.py         # Stage 2 (no network needed)
python run_stage3.py             # Stage 3 (no network needed)
python run_real_data.py          # Stage 4 (needs BLS API, first run)
python run_benchmarks.py         # Stage 5 (uses cached BLS data)
python run_longest_history.py    # Stage 6 (needs BLS API for extended range)
```

### Random seed control

All simulation functions accept a `seed` parameter. Default experiments iterate over multiple seeds (3 in quick mode, 5–10 in full mode) and report mean ± std.

### Frozen baseline parameters

Calibrated parameters for Models B and C are hardcoded in each runner script (e.g., `BP_B`, `BP_C` in `run_benchmarks.py`). These were obtained via Latin Hypercube search in Stage 2 and are kept frozen for all subsequent experiments.

### Data caching

BLS API responses are cached to `data/bls_cache.json`. Delete this file to force a fresh download.

## Limitations

- **Gross flows are approximated.** E↔U, E↔N, U↔N transition rates are estimated from CPS macro series changes using semi-empirical formulas, not from directly published BLS gross flow tables.
- **SCE LMS uses summary statistics only.** Parameter distributions are anchored to published aggregate statistics from the NY Fed, not fitted from individual-level microdata.
- **Model C underperforms time series methods in most regimes.** On the 291-month test, the heterogeneous ABM ranks 6th out of 7 models in aggregate forecast accuracy. Its advantage is limited to the COVID shock regime.
- **Model B slightly outperforms Model C on longest history.** Under extreme volatility (COVID + recovery), the simpler homogeneous ABM shows more stable predictions than the heterogeneous version.
- **Fixed behavioral parameters.** Worker parameters do not adapt over time. The ABM cannot track rapid structural shifts (e.g., post-COVID recovery) where the true behavioral distribution changes.
- **No formal statistical inference.** Model comparison uses point-estimate loss differences without confidence intervals or formal hypothesis tests.

## Citation

```
[TODO: Paper in preparation]
```

If you use this codebase, please cite this repository:

```bibtex
@misc{heterogeneous-labor-abm,
  title  = {Heterogeneous Labor Market ABM},
  author = {[TODO]},
  year   = {2025},
  url    = {https://github.com/chensirou3/heterogeneous-labor-abm}
}
```

## License

MIT

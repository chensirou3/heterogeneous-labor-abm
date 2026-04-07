# Heterogeneous Labor Market ABM

An agent-based model (ABM) of the U.S. labor market with heterogeneous worker behavior, built for empirical research on how individual-level behavioral differences shape aggregate labor market dynamics.

## Key Finding

> Introducing survey-constrained labor behavioral heterogeneity into a search-and-matching ABM achieves **VAR-comparable accuracy** on core macro indicators (UR/LFPR/EPOP) while retaining full **mechanism decomposability** and **counterfactual capability** — properties that no reduced-form benchmark can provide.

## Project Structure

```
models/
├── config.py          # Shared configuration, parameter space, SimulationOutput
├── environment.py     # Exogenous environment path (vacancy, layoff dynamics)
├── worker.py          # Worker agent: 4 behavioral blocks + type modifiers + declining RW
├── model_a.py         # Model A: Traditional deterministic Markov-chain benchmark
├── model_b.py         # Model B: Homogeneous multi-agent ABM
├── model_c.py         # Model C: Heterogeneous ABM + matching market competition
├── loss.py            # Multi-objective variance-normalized MSE loss
├── calibration.py     # Latin Hypercube parameter search + validation selection
├── real_data.py       # BLS API data loader (CPS + JOLTS) + SCE LMS anchors
└── benchmarks.py      # Traditional benchmarks: AR/ARIMA, VAR, Beveridge RF, DMP

run_experiment.py      # Stage 2: Synthetic data three-model comparison
run_stage3.py          # Stage 3: Test-set evaluation, ablation, robustness
run_real_data.py       # Real data: BLS integration + main empirical run
run_benchmarks.py      # Extended benchmarks: 7-model unified comparison + charts

figures/               # Generated charts (bar plots, heatmaps, time series)
数据可行性报告/         # Stage reports (Chinese, research documentation)
```

## Three Models Compared

| Model | Description | Core Mechanism |
|-------|------------|----------------|
| **A** Traditional | Representative-agent deterministic Markov chain | Aggregate transition rates |
| **B** Standard ABM | Multi-agent stochastic transitions, homogeneous parameters | Individual randomness |
| **C** Heterogeneous ABM | Heterogeneous behavioral parameters + type-specific rules + matching market | Behavioral diversity + competition |

## Four Core Behavioral Parameters

All anchored to public survey data (SCE LMS + CPS):

1. **Reservation Wage** — minimum acceptable wage (LogNormal, by employment status)
2. **Offer Arrival Belief** — subjective probability of receiving a job offer (Beta distribution)
3. **Search Intensity** — job search effort level (3-tier discrete)
4. **Participation Propensity** — labor force attachment (12 demographic groups × CPS LFPR)

## Key Mechanisms in Model C

- **Matching Market Competition**: Finite job openings allocated by search intensity priority — creates endogenous composition effects
- **Reservation Wage Heterogeneity**: Differential acceptance decisions across workers
- **Type-Specific Behavioral Rules**: Active Searchers (lower layoff risk), Low-Threshold Acceptors, Marginal Workers (higher exit propensity)
- **Declining Reservation Wage**: RW decays with unemployment duration (Krueger & Mueller 2016)

## Results Summary

### Real Data (BLS CPS + JOLTS, test period 2023.07–2024.12)

**7-model unified comparison (fair: UR + LFPR + EPOP only):**

| Rank | Model | Test Loss | Type |
|------|-------|----------|------|
| 1 | G_DMP | 65 | Structural reduced-form |
| 2 | D_ARIMA | 147 | Time series |
| 3 | E_VAR | 599 | Multivariate time series |
| **4** | **C_HeteroABM** | **600** | **Structural ABM** |
| 5 | F_BevRedForm | 680 | Reduced-form |
| 6 | B_StdABM | 16,865 | Structural ABM |
| 7 | A_Traditional | 57,218 | Simplified benchmark |

- Model C ≈ VAR in prediction accuracy (600 vs 599)
- Model C is the **strongest structural model** — far ahead of B (+2711%) and A (+9436%)
- Model C is the **only model** that simultaneously generates 12 target series from 4 behavioral parameters, supports ablation, and enables counterfactual analysis

### Ablation (mechanism importance on real data)

| Mechanism | Test Loss Δ when removed |
|-----------|------------------------|
| RW Heterogeneity | **+212%** (most critical) |
| Matching Market | **+179%** |
| SI Heterogeneity | +40% |
| OAB Heterogeneity | +35% |
| Type-Specific Rules | +26% |

## Data Sources

| Source | Role | Access |
|--------|------|--------|
| **CPS** (BLS API) | UR, LFPR, EPOP, gross flow proxies | Public, automated |
| **JOLTS** (BLS API) | Job openings, hires, quits, layoffs | Public, automated |
| **SCE LMS** (NY Fed) | Parameter distribution anchors | Published summary statistics |

## Quick Start

```bash
# Install dependencies
pip install numpy scipy statsmodels matplotlib

# Run synthetic experiment (fast, ~2 min)
python run_experiment.py --quick

# Run real data experiment (requires internet for BLS API)
python run_real_data.py --quick

# Run full 7-model benchmark comparison with charts
python run_benchmarks.py --quick
```

## Research Stages

1. **Stage 1** — Data-parameter mapping feasibility ([report](数据可行性报告/阶段一_综合报告_数据参数落地实验.md))
2. **Stage 2** — Model prototyping & calibration ([report](数据可行性报告/阶段二_综合报告_模型原型与校准实验.md))
3. **Stage 3** — Out-of-sample evaluation, ablation, robustness ([report](数据可行性报告/阶段三_综合报告_测试集评估与稳健性.md))
4. **Real Data** — BLS integration & main empirical run ([report](数据可行性报告/真实数据_综合报告_主实验结果.md))
5. **Extended Benchmarks** — 7-model unified comparison ([report](数据可行性报告/扩展基准测试_综合报告.md))

## License

MIT

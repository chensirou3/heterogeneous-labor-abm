# CPS 接入与状态转移矩阵构造审查报告

> 审查日期：2026-04-06
> 目标：确认 CPS 能否为劳动市场 ABM 提供宏观校准目标、微观状态转移矩阵、以及 `participation_propensity` 和 `search_intensity` 的增强构造
> 方法：基于 BLS 官方网站、CPS Codebook、Census Bureau PUMD 文档、IPUMS CPS 文档、以及学术文献中的 CPS 使用方法论

---

## Part 1：CPS 数据总表

### 1.1 数据层级与获取方式

| 数据类型 | 官方来源 | 层级 | 频率 | 时间范围 | 免费？ | Codebook？ | 适用性 |
|---------|---------|------|------|---------|--------|-----------|--------|
| **BLS 汇总时间序列** | BLS Public Data API (api.bls.gov) | 总量/分层 | 月度 | 1940s至今（取决于系列） | ✅ 免费，v1无需注册 | N/A | ✅ **宏观校准目标** |
| **BLS 汇总表格** | bls.gov/cps → Tables | 总量/分层 | 月度 | 变化 | ✅ 免费 | 在线说明 | ✅ **宏观校准** |
| **Census PUMD (Basic Monthly CPS)** | census.gov/data/datasets/time-series/demo/cps/cps-basic.html | 个体微观 | 月度 | 1994至今（1994年重新设计后） | ✅ 免费下载 | ✅ 有详细 codebook (data dictionary) | ✅ **状态转移矩阵构造** |
| **IPUMS CPS (推荐)** | cps.ipums.org | 个体微观（已清洗、已协调） | 月度 | 1962至今 | ✅ 免费（需注册） | ✅ 完整变量文档+链接文档 | ✅ **最推荐的微观数据入口** |
| **BLS Flows Data (官方状态转移)** | bls.gov/cps/cps_flows.htm | 汇总流量 | 月度 | 1990至今 | ✅ 免费 | 在线说明 | ✅ **可直接用于校准** |

### 1.2 核心系列 ID（BLS API）

| 指标 | Series ID | 说明 |
|------|-----------|------|
| **Unemployment Rate (SA)** | `LNS14000000` | 季调失业率 |
| **LFPR (SA)** | `LNS11300000` | 季调劳动参与率 |
| **EPOP (SA)** | `LNS12300000` | 季调就业人口比 |
| Employment Level (SA) | `LNS12000000` | 就业水平 |
| Unemployment Level (SA) | `LNS13000000` | 失业水平 |
| Not in Labor Force Level | `LNS15000000` | 非劳动力水平 |

**API 调用示例：**
```
GET https://api.bls.gov/publicAPI/v2/timeseries/data/LNS14000000?startyear=2014&endyear=2026
```

### 1.3 CPS 关键方法论参数

| 参数 | 值 |
|------|---|
| **样本量** | 约 60,000 户 / 约 110,000 个人（月） |
| **代表性** | 全国代表性（按 state、age、sex、race、Hispanic ethnicity 加权） |
| **调查参考周** | 通常包含每月12日的那一周 |
| **轮换结构** | **4-8-4 rotation**：4个月在样本→8个月退出→4个月重新进入→永久退出 |
| **月间重叠** | 约 75% 的样本在相邻月份重叠 |
| **年间重叠** | 约 50% 的样本在同月的相邻年份重叠 |
| **调查方式** | 面对面或电话访谈（非自填） |
| **微观数据格式** | 固定宽度文本文件 + codebook；IPUMS 提供 Stata/CSV/SAS 格式 |


---

## Part 2：变量与模型映射表

### 2.1 宏观校准目标

| 指标 | 是否直接可得 | 获取方式 | 时间覆盖 | 分层可得？ | 风险点 | MVP建议 |
|------|------------|---------|---------|-----------|--------|--------|
| **Unemployment Rate** | ✅ 直接可得 | BLS API: `LNS14000000` | 1948至今(月度) | ✅ 按 age/sex/race/education | 无 | ✅ **第一版直接纳入** |
| **LFPR** | ✅ 直接可得 | BLS API: `LNS11300000` | 1948至今(月度) | ✅ 按 age/sex/race/education | 无 | ✅ **第一版直接纳入** |
| **EPOP** | ✅ 直接可得 | BLS API: `LNS12300000` | 1948至今(月度) | ✅ 按 age/sex/race/education | 无 | ✅ **第一版直接纳入** |

**说明：** 这三个指标是 BLS 最核心的劳动市场指标，每月 Employment Situation 新闻稿首页报告。全部可通过 API 一次获取，按人口特征分层的 Series ID 也有标准化编码规则。**数据获取零障碍。**

### 2.2 微观状态与转移

#### 微观状态变量

| 变量 | CPS 原始变量名 | 编码 | 是否直接可得 | 风险点 | MVP建议 |
|------|--------------|------|------------|--------|--------|
| **E (Employed)** | `PEMLR` = 1 或 2 | 1=At Work; 2=Absent from work | ✅ 直接 | 无 | ✅ 纳入 |
| **U (Unemployed)** | `PEMLR` = 3 或 4 | 3=On Layoff; 4=Looking | ✅ 直接 | 无 | ✅ 纳入 |
| **N (NILF)** | `PEMLR` = 5, 6, 或 7 | 5=Retired; 6=Disabled; 7=Other | ✅ 直接 | NILF 内部可细分但第一版不需要 | ✅ 纳入 |

**`PEMLR` (Monthly Labor Force Recode)** 是 CPS 微观文件中最核心的变量，直接对应 BLS 官方的 E/U/N 三分类。**状态定义完全清晰，与官方统计口径一致。**

**人口特征变量（用于分层）：**

| 变量 | CPS 变量名 | 用途 |
|------|-----------|------|
| 年龄 | `PRTAGE` | 分层/分组 |
| 性别 | `PESEX` | 分层/分组 |
| 教育 | `PEEDUCA` | 分层/分组 (31=Less than 1st grade → 46=Doctorate degree) |
| 种族 | `PTDTRACE` | 分层/分组 |
| Hispanic | `PEHSPNON` | 分层/分组 |

#### 状态转移

| 转移 | 是否可构造 | 构造方式 | 数据来源 | 风险点 | MVP建议 |
|------|----------|---------|---------|--------|--------|
| **E → U** | ✅ 可构造 | 匹配相邻月份个体，比较 PEMLR 变化 | PUMD 月度文件 | 匹配损耗~10-15% | ✅ **第一版纳入** |
| **U → E** | ✅ 可构造 | 同上 | PUMD 月度文件 | 同上 | ✅ **第一版纳入** |
| **E → N** | ✅ 可构造 | 同上 | PUMD 月度文件 | 同上 | ✅ **第一版纳入** |
| **N → E** | ✅ 可构造 | 同上 | PUMD 月度文件 | 同上 | ✅ **第一版纳入** |
| **U → N** | ✅ 可构造 | 同上 | PUMD 月度文件 | 同上 | ✅ **第一版纳入** |
| **N → U** | ✅ 可构造 | 同上 | PUMD 月度文件 | 同上 | ✅ **第一版纳入** |

**重要发现：BLS 官方已发布现成的 Gross Flows 数据！**

BLS 自 1990 年起每月发布 CPS 状态转移流量数据（Labor Force Status Flows），可在 `bls.gov/cps/cps_flows.htm` 直接下载。这意味着：
- **第一版可以直接使用 BLS 官方 Flows 数据作为校准目标，无需自行构造转移矩阵**
- 自行构造仅在需要按人口特征分层（如 age×education）时才需要

### 2.3 参数增强

| 参数 | 是否直接可得 | CPS 变量 | 构造方式 | 风险点 | MVP建议 |
|------|------------|---------|---------|--------|--------|
| **participation_propensity** | ✅ 可构造 | PEMLR + PRTAGE + PEEDUCA + PESEX | 分组 LFPR = (E+U)/(E+U+N) by age×edu×sex | 无 | ✅ **第一版直接纳入** |
| **search_intensity** | ✅ 可构造（增强版） | PELKM1-PELKM6 | 搜索方法数量归一化 | 仅针对失业者(PEMLR=4) | ✅ **第一版纳入增强版** |

---

## Part 3：状态转移矩阵实施建议

### 3.1 CPS 轮换结构详解

CPS 采用 **4-8-4 轮换设计（4-in, 8-out, 4-in）**：

```
月份:  1  2  3  4 | 5 ... 12 | 13 14 15 16
状态:  IN IN IN IN | OUT      | IN IN IN IN  → 退出
```

- 每个住户在样本中出现 **8 个月**（不连续）
- 第1-4月连续在样本中（Rotation Groups 1-4 → Month-in-Sample 1-4）
- 第5-12月退出样本（8个月间隔）
- 第13-16月重新进入（Rotation Groups 5-8 → Month-in-Sample 5-8）

**关键含义：**
- 任意相邻两个月份的 CPS 文件中，约 **75%** 的样本是相同的人（6/8 个轮换组重叠）
- 可以通过匹配相邻月份的个体记录来构造月度状态转移

### 3.2 个体匹配方法（Longitudinal Linking）

**标准匹配算法（Madrian & Lefgren 2000；Shimer 2012；Elsby, Hobijn & Şahin 2015）：**

匹配键：`HRHHID`（户ID）+ `PULINENO`（个人行号）+ 人口特征验证（age, sex, race）

```python
# 伪代码：匹配月份 t 和月份 t+1
match_keys = ['HRHHID', 'HRHHID2', 'PULINENO']
verify_keys = ['PESEX', 'PRTAGE']  # age 差应为 0 或 1

merged = pd.merge(cps_month_t, cps_month_t1, on=match_keys, suffixes=('_t', '_t1'))
merged = merged[merged['PESEX_t'] == merged['PESEX_t1']]
merged = merged[abs(merged['PRTAGE_t1'] - merged['PRTAGE_t']) <= 1]
```

**匹配损耗（Attrition）：**

| 问题 | 描述 | 影响程度 |
|------|------|---------|
| **轮换退出** | 2/8 的轮换组在下月不在样本中 | ~25%（设计性） |
| **地址变动** | 搬家导致不在原住址被访 | ~3-5% |
| **拒访/缺失** | 拒绝回答或联系不上 | ~2-3% |
| **总匹配率** | 相邻月份可成功匹配的比例 | 约 **70-75%** |

**损耗校正方法：**
- 标准做法：Logit 回归估计匹配概率 → 逆概率加权（IPW）
- Elsby, Hobijn & Şahin (2015) 方法：对 bootstrapped 匹配样本做 margin adjustment，使匹配后的 E/U/N 分布与当月官方总量一致
- **第一版建议：使用 margin adjustment 而非 IPW，更简单且效果已被验证**

### 3.3 构造月度转移矩阵

**方法 A：直接使用 BLS Gross Flows（最简单，推荐 MVP）**

BLS 官方从 1990 年起每月发布 CPS 状态转移流量表：

| 来源状态 \ 去向状态 | E(t+1) | U(t+1) | N(t+1) |
|-------------------|--------|--------|--------|
| **E(t)** | EE | EU | EN |
| **U(t)** | UE | UU | UN |
| **N(t)** | NE | NU | NN |

- 数据位置：`https://www.bls.gov/cps/cps_flows.htm`
- 格式：Excel 表格，月度
- 覆盖时间：1990年至今
- **优势：无需自行匹配，无需处理损耗**
- **劣势：仅有总量，不能按人口特征分层**

**方法 B：自行匹配 PUMD 微观文件（分层转移矩阵所需）**

```python
# 从匹配后的数据构造转移概率
def compute_transition_matrix(matched_df, group_vars=None):
    if group_vars:
        grouped = matched_df.groupby(group_vars)
    else:
        grouped = [(None, matched_df)]

    for name, group in grouped:
        total = len(group)
        for state_t in ['E', 'U', 'N']:
            for state_t1 in ['E', 'U', 'N']:
                count = len(group[(group['state_t'] == state_t) &
                                  (group['state_t1'] == state_t1)])
                denom = len(group[group['state_t'] == state_t])
                prob = count / denom if denom > 0 else 0
                # P(state_t1 | state_t, group)
```

### 3.4 MVP 实施建议

| 问题 | 回答 |
|------|------|
| **CPS 是否足以构造第一版月度 transition matrix？** | ✅ **完全足够。且有两种路径——官方 Flows 或自行匹配。** |
| **MVP 应构造哪些转移？** | 完整的 3×3 矩阵（E/U/N 之间的全部 9 个转移概率），月度。 |
| **第一版是否做分层转移矩阵？** | ⚠️ **建议第一版先用总量矩阵（BLS Gross Flows），第二版再做分层。** |
| **分层最多细到什么程度？** | age 3组 × education 2组 × sex 2组 = 12组 比较稳。再细则每组失业者样本量不足。 |

**分层样本量估算：**
- 每月 CPS 约 110,000 个体
- 失业者约 4-5%（~5,000人/月）
- 12 个分组 → 每组约 400 失业者/月
- 匹配后（75%）→ 每组约 300 失业者对
- **够用，但不建议再细分**

---

## Part 3 补充：`participation_propensity` 的具体实现

### E.1 CPS 是否足以分层构造 LFPR？

**✅ 完全足够。** CPS 是美国劳动参与率的官方来源。

**分层 LFPR 构造：**
```python
# 按 age_group × education × sex 计算 LFPR
LFPR = (Employed + Unemployed) / (Employed + Unemployed + NILF)
# 即 (PEMLR in [1,2,3,4]) / Total
```

**推荐分组：**

| 分层维度 | 分组 | 样本量评估 |
|---------|------|-----------|
| 年龄 | 16-34 / 35-54 / 55+ | 每组 ~30,000-40,000人/月 |
| 教育 | No College / College+ | 每组 ~50,000人/月 |
| 性别 | Male / Female | 每组 ~55,000人/月 |
| 交叉 | age3 × edu2 × sex2 = 12组 | 每组 ~9,000人/月 ✅ 充足 |

### E.2 是否只用静态分组 LFPR，还是结合 N→E / E→N 转移率？

**建议第一版分两层：**

1. **静态基准（Level 1）：** 用分组 LFPR 作为 `participation_propensity` 的基准值
   ```
   participation_propensity_baseline[age, edu, sex] = LFPR[age, edu, sex]
   ```

2. **动态增强（Level 2，后期）：** 结合 N→E 和 E→N 月度转移率做动态调整
   ```
   participation_propensity_dynamic = f(LFPR_baseline, N→E_rate, E→N_rate)
   ```
   其中 N→E 反映"退出劳动力→重新参与"的倾向，E→N 反映"就业→退出"的倾向

**第一版最稳实现：**
- 只用静态分组 LFPR（3 age × 2 edu × 2 sex = 12 组）
- 每个 agent 的 `participation_propensity` = 其所属组的 LFPR
- 简单、可解释、数据完全充足

---

## Part 3 补充：`search_intensity` 的增强构造

### F.1 CPS 搜索相关变量确认

**核心变量：`PELKM1` — `PELKM6`**

**题目原文（已从 CPS codebook 确认）：**
> *"What are all of the things you have done to find work during the last 4 weeks?"*

**适用对象：** 仅失业者中的 "Looking"（`PEMLR = 4`）

**最多可记录 6 种搜索方法。编码如下：**

| 代码 | 搜索方法 | 类型 |
|------|---------|------|
| 1 | Contacted employer directly / interview | 主动 |
| 2 | Contacted public employment agency | 主动 |
| 3 | Contacted private employment agency | 主动 |
| 4 | Contacted friends or relatives | 主动 |
| 5 | Contacted school/university employment center | 主动 |
| 6 | Sent out resumes / filled out applications | 主动 |
| 7 | Checked union/professional registers | 主动 |
| 8 | Placed or answered ads | 主动 |
| 9 | Other active | 主动 |
| 10 | Looked at ads | 被动 |
| 11 | Attended job training programs/courses | 被动 |
| 13 | Other passive | 被动 |

**辅助变量：**
- `PULK`："Have you been doing anything to find work during the last 4 weeks?" (1=Yes, 2=No)
- `PEJHRSN`："What is the main reason you left your last job?"

### F.2 search_intensity 构造方案

**简单版（推荐 MVP）：**
```
search_intensity = num_active_methods / 9
```
其中 `num_active_methods` = PELKM1-PELKM6 中属于主动方法（代码 1-9）的数量
归一化到 0-1 区间（最多 9 种主动方法）

**增强版：**
```
search_intensity = w1 × (num_active_methods / 9) + w2 × contacted_employer + w3 × sent_resumes
```
给"直接联系雇主"和"投简历"更高权重（更直接的搜索行为）

### F.3 与 SCE LMS 的互补关系

| 数据源 | 搜索变量 | 优势 | 劣势 |
|--------|---------|------|------|
| **SCE LMS** | searched (0/1) + offer数量 | 覆盖就业者和非就业者都问 | 仅二分类，无搜索方法细节 |
| **CPS** | PELKM1-PELKM6（最多6种方法） | 搜索渠道精细，可构造连续指标 | 仅针对失业者（PEMLR=4） |

**联合方案：**
- **就业者的搜索强度**：用 SCE LMS 的 searched(0/1)（CPS 不对就业者问搜索）
- **失业者的搜索强度**：用 CPS 的 PELKM1-PELKM6 构造连续指标（更精细）
- **非劳动力的搜索强度**：默认为 0（定义上不在搜索）

```python
def get_search_intensity(agent):
    if agent.status == 'E':
        return agent.sce_searched  # SCE LMS: 0 or 1
    elif agent.status == 'U':
        return agent.cps_active_methods / 9  # CPS: 0-1 continuous
    else:  # N
        return 0.0
```

---

## Part 4：最终结论

### 1. CPS 能否补足当前劳动市场 ABM 中最缺的一块？

**✅ 完全可以。CPS 恰好补足了 SCE LMS 的三个缺口：**

| 缺口 | CPS 解决方案 | 可靠性 |
|------|------------|--------|
| `participation_propensity` 无法由 SCE LMS 独立实现 | CPS 分层 LFPR（age×edu×sex = 12组） | 🟢 最可靠（CPS 是 LFPR 的官方来源） |
| `search_intensity` 仅有二分类 | CPS PELKM1-6 搜索方法数量→连续指标 | 🟢 可靠（变量已确认，codebook 清晰） |
| 缺少状态转移矩阵作为校准目标 | BLS Gross Flows（官方现成）或自行匹配 PUMD | 🟢 最可靠（官方数据 + 成熟学术方法） |

### 2. `participation_propensity` 是否可以由 CPS 稳定实现？

**✅ 完全可以。**

- CPS 是美国劳动参与率的**唯一官方来源**
- 每月约 110,000 人，12 个分组每组约 9,000 人 → **样本量绝对充足**
- 第一版直接用分组 LFPR 作为 `participation_propensity`
- 后期可升级为动态版（结合 N→E / E→N 转移率）

### 3. `search_intensity` 是否能通过 CPS 明显增强？

**✅ 明显增强。**

- SCE LMS 只有 searched(0/1) 二分类
- CPS 有 PELKM1-PELKM6（最多6种搜索方法 × 12种方法类型）
- 可构造 0-1 连续的 `search_intensity`
- **但 CPS 搜索变量仅针对失业者（PEMLR=4），就业者的搜索仍需依赖 SCE LMS**

### 4. 接完 CPS 后，下一步应该优先接 JOLTS 还是 CES？为什么？

**➡️ JOLTS 优先。** 理由：

| 比较 | JOLTS | CES |
|------|-------|-----|
| **独立增量** | ✅ **高**——空缺率、招聘率、辞职率、解雇率是 CPS 完全不覆盖的流量数据 | 🟡 中——非农就业变化与 CPS 重叠；平均时薪/工时有用但非核心 |
| **对搜索匹配模型的必要性** | ✅ **核心**——空缺率是 Beveridge 曲线的另一轴；hiring rate 是 matching function 的直接校准目标 | 🟡 补充——工资增长可用于验证，非核心校准 |
| **获取难度** | 极简单（BLS API，同一套接口） | 极简单 |

JOLTS 提供的**空缺率 + 招聘率**是搜索匹配模型的必要输入，而 CPS 不覆盖企业侧的空缺和招聘数据。CES 的非农就业变化虽然重要，但与 CPS 的就业水平指标有高度相关，独立增量较小。

**建议顺序：CPS → JOLTS → CES**

---

## 附：MVP 数据架构总览

完成 CPS 接入后，第一版模型的完整数据架构如下：

```
┌─────────────────────────────────────────────────────────┐
│                    MVP 数据架构                           │
├──────────────┬──────────────────────────────────────────┤
│ 参数层        │                                          │
│              │  reservation_wage ← SCE LMS              │
│              │  offer_arrival_belief ← SCE LMS          │
│              │  search_intensity ← SCE LMS + CPS        │
│              │  participation_propensity ← CPS          │
├──────────────┼──────────────────────────────────────────┤
│ 校准目标层    │                                          │
│              │  unemployment_rate ← CPS (BLS API)       │
│              │  LFPR ← CPS (BLS API)                    │
│              │  EPOP ← CPS (BLS API)                    │
│              │  E↔U↔N 转移矩阵 ← CPS Gross Flows       │
│              │  空缺率/招聘率/辞职率 ← JOLTS (BLS API)  │
│              │  非农就业/工资/工时 ← CES (BLS API)       │
├──────────────┼──────────────────────────────────────────┤
│ 验证指标层    │                                          │
│              │  job_transition_belief ← SCE LMS         │
│              │  separation_belief ← SCE LMS             │
│              │  P(move into employment) ← SCE LMS      │
└──────────────┴──────────────────────────────────────────┘
```

### 下一步行动项

| 优先级 | 行动 | 目的 |
|--------|------|------|
| **P0** | 通过 BLS API 获取 Unemployment Rate / LFPR / EPOP 月度序列 | 宏观校准目标 |
| **P0** | 下载 BLS Gross Flows 数据（bls.gov/cps/cps_flows.htm） | 状态转移矩阵校准目标 |
| **P1** | 下载 CPS PUMD（选 2 个相邻月份）| 测试 PEMLR 编码 + PELKM 搜索变量 + 个体匹配 |
| **P1** | 用 CPS PUMD 计算分层 LFPR（12 组）| `participation_propensity` 落地 |
| **P2** | 通过 BLS API 获取 JOLTS 月度序列 | 空缺/招聘/辞职/解雇 |
| **P3** | 通过 BLS API 获取 CES 月度序列 | 非农就业/工资/工时 |

---

> **本报告结论：CPS 完全可以补足当前 ABM 的数据缺口。`participation_propensity` 可由 CPS 分层 LFPR 稳定实现；`search_intensity` 可通过 CPS 搜索方法变量从二分类升级为连续指标；状态转移矩阵有 BLS 官方 Gross Flows 可直接使用。下一步优先接 JOLTS。**
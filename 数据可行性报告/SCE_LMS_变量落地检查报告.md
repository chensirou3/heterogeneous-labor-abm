# SCE Labor Market Survey 变量落地检查报告（Variable Implementation Audit）

> 审查日期：2026-04-06
> 目标：确认 SCE LMS 微观数据中的关键变量能否真正落地为劳动市场 ABM 的参数输入
> 方法：基于 NY Fed 官方页面、问卷描述、新闻稿、官方博客文章和 FAQ 中的变量级信息

---

## Step 1：文件和文档核验

### 1.1 已确认的官方文档清单

| 项目 | 确认状态 | 来源 | 说明 |
|------|---------|------|------|
| **Complete Microdata** | ✅ 存在，免费下载 | Data Bank → SCE LMS → Complete Microdata | 18个月滞后发布；个体级微观数据 |
| **Questionnaire** | ✅ 存在，可下载 | Data Bank → SCE LMS → Questionnaire；同时在 LMS 主页 Downloads 中 | 完整问卷 |
| **Chart Guide** | ✅ 存在，可下载 | Data Bank → SCE LMS → Interactive Chart Guide | 相当于变量说明/codebook，解释图表中每个指标的定义 |
| **Chart Data** | ✅ 存在，可下载 | Data Bank → SCE LMS → Interactive Chart Data | 汇总层面图表数据 |
| **FAQ** | ✅ 存在 | newyorkfed.org/microeconomics/sce/sce-faq | 解答数据发布时间、方法论、样本等 |

### 1.2 数据基本参数

| 参数 | 值 |
|------|---|
| **起始时间** | 2014年3月 |
| **频率** | 每4个月一次（3月/7月/11月） |
| **样本量** | 约 1,000-1,300 人/波次 |
| **面板结构** | 旋转面板，每位受访者参与最多12个月 |
| **代表性** | 全国代表性（按收入、教育、年龄、Census Region 加权） |
| **微观数据发布滞后** | 18个月 |
| **最新可用微观数据** | 约2024年底（2024年11月或2025年3月波次） |
| **累计波次** | 约36个波次（2014.3—2025.11） |
| **累计最大人次观测** | 约 36 × 1,200 ≈ 43,000 人次（含重复面板成员） |

### 1.3 官方确认的变量覆盖范围

根据 2017年介绍性博客（Conlon, Kosar, Topa, Zafar）和 2024年新闻稿，SCE LMS 收集以下类别的信息：

**经历侧（Experiences）：**
1. 当前（或最近一份）工作的详细信息
2. 过去4个月的工作转换（job transitions）
3. 过去4个月的搜索行为和结果（job search effort and outcomes）
4. 过去4个月收到的 offer 数量和 offer 工资
5. 当前工作的满意度（工资、非工资福利、晋升机会）（仅就业者）

**预期侧（Expectations）：**
6. 未来4个月的工作转换预期
7. 未来4个月收到至少一份 offer 的概率
8. 未来4个月预期收到的 offer 数量
9. 未来4个月预期 offer 工资
10. 保留工资（Reservation wage）
11. 在62岁/67岁后仍工作的概率

---

## Step 2：逐变量核验

### 变量 1：Reservation Wage（保留工资）

| 字段 | 内容 |
|------|------|
| **存在性** | ✅ **确认存在**。官方题目原文已被多篇官方文献引用。 |
| **题目原文** | *"Suppose someone offered you a job today in a line of work that you would consider. What is the lowest wage or salary you would accept (BEFORE taxes and other deductions) for this job?"* |
| **数据类型** | 连续型，美元金额（年薪） |
| **询问对象** | **所有受访者**（就业者 + 失业者 + 非劳动力）— 这在 2024年 Kosar et al. 论文中明确确认，回归中同时报告 Employed 和 Non-Employed 样本 |
| **取值范围** | 连续正实数。2024年7月平均 $81,147；2025年7月 $82,472（系列最高）；2024年3月系列高点 $81,822 |
| **按人口特征分层** | 官方图表按年龄(Age)、教育(Education)、性别(Gender)、家庭收入(Household Income)分层报告 |
| **缺失率** | **预计低**。题目对所有受访者提问，且是核心指标，官方每期都报告。 |
| **回归样本量** | 2024年博客回归表：就业者 7,253 观测；非就业者 1,164 观测（合并多波次） |
| **官方来源** | ① 2024-08-19 Liberty Street Economics 博客；② 每期新闻稿；③ 问卷原文 |

**核验结论：** 🟢 **最可靠的变量。直接可用，无需重编码。**

- 连续型年薪金额，直接映射 `reservation_wage` 参数
- 全样本覆盖（就业者 + 非就业者），无条件缺失问题
- 官方已使用此变量做计量回归（with individual fixed effects），证明微观数据质量高
- 按人口特征有官方分层统计，可直接用于 worker type 划分

**已知限制：**
- 自我报告可能存在偏误（但有学术先例支持 SCE 保留工资测度的有效性）
- 极端值可能需要 winsorize（top/bottom 1%），建议第一版采用 log(reservation_wage) 建模

---

### 变量 2：Current Employment Status（当前就业状态）

| 字段 | 内容 |
|------|------|
| **存在性** | ✅ **确认存在** |
| **分类** | 至少三类：Employed / Unemployed / Not in Labor Force (Non-employed) |
| **数据类型** | 分类型 |
| **询问对象** | 所有受访者 |
| **编码方式** | 官方新闻稿和回归表中使用 "Employed" vs "Non-Employed" 二分类；图表按 employment status 分组 |
| **缺失率** | **极低**（基础人口学变量） |
| **样本量** | 从2024年博客回归：就业者 7,253 次观测 vs 非就业者 1,164 次观测 → **就业者占比约 86%，非就业者约14%** |

**核验结论：** 🟢 **可靠。直接可用于分组和 worker type 划分。**

**关键发现：非就业者子样本约占14%（每波约 140-180人）。** 这意味着：
- 非就业者的精细分组（如按教育×年龄）样本量将非常小
- 但合并多波次后（1,164 次），总量勉强够用
- 建议第一版只做 Employed / Non-Employed 二分组，不再细分失业 vs NILF

---

### 变量 3：Search Behavior in Past Four Weeks（过去4周搜索行为）

| 字段 | 内容 |
|------|------|
| **存在性** | ✅ **确认存在**。官方每期报告搜索者比例。 |
| **基本指标** | "过去4周是否搜索工作"（searched / not searched） |
| **数据类型** | 至少有二分类（是/否） |
| **询问对象** | 所有受访者 |
| **取值范围** | 2024年7月：28.4%（系列最高，since March 2014）；2025年11月：23.8%；2025年7月新闻稿未单独报告 |
| **按人口特征分层** | 2024年新闻稿明确指出：增长主要由"45岁以上、无大学学位、年收入<$60K"群体驱动 → 说明可按这些特征分组 |

**搜索子问题结构——关键不确定性：**

从 2017年介绍性博客原文："Respondents are asked about job transitions, as well as about their **job search effort and outcomes** (**number of job offers** and **offer wages**), over the past four months."

从 2024年新闻稿的经历部分："19.4% of individuals reported **receiving at least one job offer** in the past four months"

这证实微观数据中至少存在以下搜索/offer 相关子变量：
1. ✅ 是否搜索（二分类）
2. ✅ 过去4个月收到 offer 的数量（1, 2, 3, 4+）— 2017年博客有按 offer 数量分组的图表
3. ✅ 过去4个月实际 offer 工资（美元金额）
4. ⚠️ 搜索方法/渠道数量 — **未在官方报告中明确提及**，需打开微观数据验证
5. ⚠️ 申请数/面试数 — **未在官方报告中提及**

**search_intensity 的构造方案：**

**简单版（可确认可行）：**
```
search_intensity_simple = searched_past_4_weeks (0/1)
```
二分类代理。可用但粗糙。

**增强版 A（需验证子问题，但有合理依据）：**
```
search_intensity_enhanced = f(searched, num_offers_received, offer_wage)
```
搜索行为 × offer 结果的复合指标。

**增强版 B（如有搜索方法/渠道数量）：**
```
search_intensity_robust = num_search_methods / max_possible_methods
```
类似 CPS 的搜索渠道数量归一化。但 SCE LMS 可能没有此子问题。

**核验结论：** 🟡 **可用但有限。**
- 二分类搜索变量确认存在且可用
- offer 数量可作为搜索结果的代理（间接反映搜索强度）
- **搜索方法/渠道的精细度是最大不确定性——必须打开微观数据验证**
- 如果 SCE LMS 搜索子问题不够丰富，**必须用 CPS 的搜索方法变量补充**

---

### 变量 4：Offer Arrival Belief（工作机会到达信念）

| 字段 | 内容 |
|------|------|
| **存在性** | ✅ **确认存在**。官方核心指标，每期新闻稿首段报告。 |
| **题目含义** | "未来4个月收到至少一份工作机会(job offer)的预期概率" |
| **数据类型** | 连续型，概率 0-100 |
| **询问对象** | 所有受访者 |
| **取值范围** | 2024年7月：平均 22.2%；2025年3月：19.3%；2025年7月：18.8%（连续三期下降）；2025年11月：继续下降 |
| **配套变量** | "Expected likelihood of receiving **multiple** offers"：2024年7月 25.4% |
| **缺失率** | **极低**。概率引出是 SCE 的核心方法论，有丰富的方法论检验文献。 |

**核验结论：** 🟢 **最可靠的变量之一。直接可用，无需重编码。**
- 0-100 概率，直接映射 `offer_arrival_belief` 参数（缩放到 0-1 即可）
- 全样本覆盖
- 连续型，分布信息丰富
- 可按就业状态分组比较（就业者预期 vs 非就业者预期会有系统差异）

---

### 变量 5：Expected Offer Wage / Actual Offer Wage（预期/实际 Offer 工资）

| 字段 | 内容 |
|------|------|
| **存在性** | ✅ **确认存在**（两个变量） |
| **(a) 实际 offer 工资** | 过去4个月实际收到的 offer 工资。2024年7月：平均全职 $68,905 |
| **(b) 预期 offer 工资** | 未来4个月预期 offer 工资（conditional on receiving one）。2024年7月：$65,272；2025年7月未单独公布 |
| **数据类型** | 连续型，美元金额（年薪） |
| **询问对象** | (a) 仅收到 offer 的人（约19%样本 → 每波约190-250人）；(b) "conditional on expecting an offer"，覆盖更广但仍有条件 |
| **缺失率** | (a) **高**（~81%未收到 offer → 该变量缺失）；(b) **中**（需要预期收到 offer 才有此变量） |

**offer_acceptance_threshold 的构造：**

```
offer_acceptance_threshold = reservation_wage / expected_offer_wage
```

当 ratio > 1 → 保留工资 > 预期 offer 工资 → 更倾向拒绝
当 ratio < 1 → 保留工资 < 预期 offer 工资 → 更倾向接受

**核验结论：** 🟡 **可用但有条件缺失。**
- reservation_wage 本身已是 acceptance threshold 的直接度量（更低 = 更容易接受）
- expected_offer_wage 有条件缺失，但与 reservation_wage 的比值可构造 threshold
- **建议第一版直接用 reservation_wage 作为 acceptance threshold 的代理，不构造比值**

---

### 变量 6：Job Transition Belief（工作转换信念）

| 字段 | 内容 |
|------|------|
| **存在性** | ✅ **确认存在** |
| **题目含义** | 就业者在未来4个月：(a) 换到不同雇主的预期概率；(b) 仍在同一雇主的概率 |
| **数据类型** | 连续型，概率 0-100 |
| **询问对象** | 就业者 |
| **取值范围** | 换雇主概率：2024年7月平均 11.6%；回归表 Dep. Var. Mean = 8.172（多波平均） |
| **回归样本量** | 7,253 观测 |
| **缺失率** | 对就业者低；非就业者不适用 |

**核验结论：** 🟢 **可靠。建议第一版作为验证指标而非直接参数。**
- 可用于验证模型输出的 job-to-job transition rate 是否与数据吻合
- 也可作为 `search_intensity` 的辅助代理（主动换工作的意愿 → 搜索动机）

---

### 变量 7：Job Separation Belief（失业/离职信念）

| 字段 | 内容 |
|------|------|
| **存在性** | ✅ **确认存在** |
| **题目含义** | 就业者在未来4个月进入非就业状态的预期概率 |
| **数据类型** | 连续型，概率 0-100 |
| **询问对象** | 就业者 |
| **取值范围** | 2024年7月：4.4%（系列最高）；回归表 Dep. Var. Mean = 3.143 |
| **回归样本量** | 7,245 观测 |
| **缺失率** | 对就业者低 |

**另一侧：非就业者 → 就业预期**
- 回归表第三列 "Probability of Moving into Employment"：Dep. Var. Mean = 14.078
- 样本量 1,164 观测

**核验结论：** 🟢 **可靠。建议第一版作为验证指标。**
- separation belief 可用于验证模型的 E→U 转移率
- 非就业者的 U→E 预期（14%）可验证模型的 job-finding rate

---

### 变量 8：Earnings Expectations（收入预期）

| 字段 | 内容 |
|------|------|
| **存在性** | 🟡 **SCE LMS 本身部分存在** |
| **LMS 中可得** | 工资满意度（wage satisfaction）、非工资福利满意度、晋升满意度 |
| **LMS 满意度数据** | 2024年7月：工资满意度 56.7%（↓ from 59.9%）；非工资福利 56.3%（↓ from 64.9%）；晋升 44.2%（↓ from 53.5%） |
| **完整收入预期** | 在 **SCE Core Survey**（月度主调查）中有 expected earnings growth 概率分布 |
| **整合可行性** | SCE Core 和 SCE LMS 共享同一面板，可通过受访者 ID 链接 |

**核验结论：** 🟡 **第一版建议暂时搁置。**
- LMS 的满意度是有序分类变量（satisfied/dissatisfied），不是连续的收入增长预期
- 完整的收入增长预期在 SCE Core 中，需要跨数据集合并
- **这增加了数据处理复杂度，不适合 MVP 阶段**
- 建议 MVP 阶段先不纳入 earnings_expectations，后期用 SCE Core 增强

---

### 补充变量 9：Working Beyond Age 62/67（工作到62/67岁以上的概率）

| 字段 | 内容 |
|------|------|
| **存在性** | ✅ **确认存在** |
| **题目含义** | "你在62/67岁后仍然工作的预期概率"（percent chance of working beyond age 62/67） |
| **数据类型** | 连续型，概率 0-100 |
| **取值范围** | Working beyond 62: 2024年7月 48.3%；2025年11月 50.4%。Working beyond 67: 34.2% |

**核验结论：** 🟡 **间接有用，但不适合作为全年龄 participation_propensity。**
- 仅反映老年端劳动参与意愿
- 年轻人和中年人的参与倾向需要其他变量
- 可用于构造 55+ 年龄组的 `participation_propensity` 先验

---

## Step 3：缺失率与样本量核查汇总

| 变量 | 总体缺失率评估 | 就业者样本量 | 非就业者样本量 | 分组可行性 |
|------|---------------|------------|-------------|-----------|
| Reservation wage | 🟢 低 | ~7,253次(多波) | ~1,164次(多波) | ✅ 官方已按 age/edu/gender/income 分层 |
| Employment status | 🟢 极低 | ~86% | ~14% | ✅ 基础变量 |
| Search behavior | 🟢 低 | ~72%未搜索 | ~28%搜索 | ⚠️ 搜索者每波约280-370人 |
| Offer arrival belief | 🟢 低 | 全样本 | 全样本 | ✅ |
| Actual offer wage | 🔴 高(~81%缺失) | ~19%收到offer | — | ❌ 每波仅~190-250人 |
| Expected offer wage | 🟡 中 | 条件于预期 | 条件于预期 | ⚠️ |
| Job transition belief | 🟢 低 | ~7,253次 | N/A | ✅ |
| Separation belief | 🟢 低 | ~7,245次 | N/A | ✅ |
| P(move into employment) | 🟢 低 | N/A | ~1,164次 | ⚠️ 非就业者子样本小 |
| Work beyond 62/67 | 🟢 低 | 全样本 | 全样本 | ✅ |

### 关键样本量风险

**精细交叉分组估算：**
- 每波约 1,200 人
- 教育3组(< HS / HS-Some College / Bachelor+) × 年龄3组(<35 / 35-54 / 55+) × 性别2组 = 18组
- 每组约 67 人/波
- 合并10个波次 → 每组约 670 人次（勉强够用）
- 合并全部36波次 → 每组约 2,400 人次（充足）

**非就业者精细分组：**
- 每波约 170 人 → 18组每组约 9 人/波 ❌ **完全不够**
- 合并全部36波 → 每组约 340 人次 → **勉强可用但需谨慎**
- **建议：非就业者只做 2-3 组粗分组（如年龄二分或教育二分）**


---

## Step 4：分布检查（基于官方报告的汇总统计）

> 注意：以下统计基于官方新闻稿和博客中报告的汇总值，不是直接从微观数据计算。
> 完整的分位数统计需要打开 Complete Microdata 后计算。

### Reservation Wage 分布

| 统计量 | 值 | 来源 |
|--------|---|------|
| Mean（2024年7月） | $81,147 | 2024年8月新闻稿 |
| Mean（2025年7月） | $82,472（系列最高） | 2025年7月新闻稿 |
| Mean（2024年3月） | $81,822（前系列最高） | 2024年8月博客 |
| Trend | 疫情后持续上升，2019年前稳定在 ~$60K-65K | 2024年博客时间序列图 |
| P10/P25/P75/P90 | **需打开微观数据计算** | — |
| 按教育分组 | 有分组图表（College+ 更高） | 官方交互图表 |
| 按年龄分组 | 有分组图表（中年组最高） | 官方交互图表 |
| 按性别 | 有分组图表（男性更高） | 官方交互图表 |
| 极端值处理 | 官方政策："As it is the SCE's practice to not remove or top-code any outliers" → **官方不做截尾** | FAQ |

**分布判断：**
- 右偏分布（少数人报告极高 reservation wage）
- 官方报告 median 和 mean 可能有较大差异
- **建议建模时使用 log(reservation_wage) 或做 top 1% winsorize**

### Offer Arrival Belief 分布

| 统计量 | 值 |
|--------|---|
| Mean（2024年7月） | 22.2% |
| Mean（2025年7月） | 18.8% |
| Mean（2025年11月） | 继续下降 |
| 范围 | 0-100（概率） |
| 预期形状 | 高度右偏（大多数人预期概率很低，少数人预期很高） |

### Offer Wage 分布

| 变量 | Mean |
|------|------|
| 实际 offer wage（全职，2024年7月） | $68,905 |
| 预期 offer wage（条件，2024年7月） | $65,272 |
| Reservation wage vs 实际 offer | Reservation ($81K) > Actual offer ($69K) → 存在系统差异 |

---

## Step 5：参数构造可行性判断

### A. reservation_wage ✅

| 问题 | 回答 |
|------|------|
| 是否可直接用单一变量表示？ | ✅ 是。直接使用 SCE LMS 的 reservation wage 变量 |
| 是否需要缩放/对数化/标准化？ | 建议 log 变换。原始美元金额右偏，log 后更接近正态 |
| 是否建议按就业状态使用不同分布？ | ✅ 是。就业者和非就业者的 reservation wage 分布有系统差异 |
| **实现方案** | `reservation_wage_param = log(reservation_wage_dollar)` |
| 是否可由 SCE LMS 单独完成？ | ✅ **完全可以** |

### B. offer_arrival_belief ✅

| 问题 | 回答 |
|------|------|
| 是否可直接使用 0-100 概率？ | ✅ 是 |
| 是否建议转换到 0-1？ | ✅ 是，除以 100 |
| 是否应按就业状态分布建模？ | ✅ 是。就业者和非就业者的 offer 预期有系统差异 |
| **实现方案** | `offer_arrival_belief_param = P(offer in 4m) / 100` |
| 是否可由 SCE LMS 单独完成？ | ✅ **完全可以** |

### C. search_intensity ⚠️

| 问题 | 回答 |
|------|------|
| 是否能从 SCE LMS 直接构造？ | ⚠️ **部分可以** |
| **简单构造（可确认可行）** | `search_intensity = searched_past_4_weeks (0/1)` — 二分类代理 |
| **增强构造（需验证可行性）** | `search_intensity = w1 × searched + w2 × log(1 + num_offers_received) + w3 × job_transition_belief/100` — 复合指标 |
| 如果不够，CPS 需要补什么？ | CPS 失业者搜索方法数量（contacted employer directly, sent resume, used agency 等）→ 可构造 0-1 连续搜索强度 |
| **实现方案（第一版）** | 先用二分类 searched(0/1)；后续用 CPS 搜索方法数量做增强 |
| 是否可由 SCE LMS 单独完成？ | ⚠️ **简单版可以；稳健版需要 CPS** |

### D. participation_propensity ⚠️

| 问题 | 回答 |
|------|------|
| SCE LMS 本身能支持到什么程度？ | 仅覆盖老年端（P(work beyond 62/67)）和非就业者→就业转移概率 |
| 哪部分必须依赖 CPS/SIPP？ | 全年龄段的劳动参与率分布必须依赖 CPS。CPS 按 age×education×gender 的 LFPR 可直接锚定 |
| **实现方案（第一版）** | 用 CPS 的分组 LFPR 作为基准 participation_propensity；SCE LMS 的 P(work beyond 62/67) 仅用于 55+ 组微调 |
| 第一版建议 | **做粗分组（3组：<35 / 35-54 / 55+），不做精确连续参数** |
| 是否可由 SCE LMS 单独完成？ | ❌ **不可以。必须依赖 CPS** |

---

## Step 6：Worker Types 初步可行性

### 方案论文中预设的3类 Worker Types：

1. **Type A：高 reservation wage / 高 search** — "挑剔搜索者"
2. **Type B：低 reservation wage / 高接受** — "灵活接受者"
3. **Type C：低 search / 高退出风险** — "边缘参与者"

### 可行性判断：

| Worker Type | 构造变量 | 可行性 | 说明 |
|-------------|---------|--------|------|
| **Type A** | 高 reservation_wage + searched=1 | ✅ **最容易识别** | reservation_wage 和 search 都可直接从 SCE LMS 获得；高/低可用中位数或分位数切分 |
| **Type B** | 低 reservation_wage + 高 offer_arrival_belief | ✅ **可以识别** | 两个变量都直接可得 |
| **Type C** | searched=0 + 高 separation_belief | 🟡 **部分可识别** | searched=0 直接可得；separation_belief 仅就业者有。非就业中的"边缘参与者"需用 CPS LFPR 辅助 |

**结论：**
- Type A 和 Type B 可完全由 SCE LMS 构造
- Type C 的非就业端需要 CPS 辅助
- **建议第一版先用 reservation_wage × searched 二维交叉分组构造 worker types（2×2=4类→合并为3类）**

### 替代方案建议：

如果论文需要更清晰的3类划分，建议改为：

1. **Active Searcher**：searched=1 且 offer_arrival_belief > median → 积极搜索者
2. **Passive Worker**：searched=0 且 separation_belief < median → 稳定就业者
3. **Marginal Worker**：searched=0 且（separation_belief > median 或 非就业者）→ 边缘劳动力

这三类完全可由 SCE LMS 现有变量构造。

---

## Part 1：变量核验总表

| 模型参数/变量 | SCE原始变量 | 题目原文 | 类型 | 适用样本 | 缺失率 | 直接可用 | 需重编码 | 风险点 | 结论 |
|-------------|-----------|---------|------|---------|--------|---------|---------|--------|------|
| `reservation_wage` | Reservation wage ($) | "lowest wage/salary you would accept" | 连续($) | 全样本 | 🟢低 | ✅ 是 | log变换 | 极端值需winsorize | 🟢 **立即可用** |
| `offer_arrival_belief` | P(offer in 4m) | "expected likelihood of receiving ≥1 offer in next 4 months" | 连续(0-100) | 全样本 | 🟢低 | ✅ 是 | ÷100 | 无 | 🟢 **立即可用** |
| `search_intensity` | Searched past 4 weeks + offer数 | "job search effort and outcomes" | 二分+计数 | 全样本 | 🟢低 | ⚠️ 部分 | 需构造连续指标 | 搜索渠道子问题不确定 | 🟡 **简单版可用，增强版需CPS** |
| `participation_propensity` | P(work beyond 62/67) + 状态转移 | "percent chance of working beyond 62/67" | 连续(0-100) | 全样本 | 🟢低 | ❌ 否 | 需与CPS联合 | 仅覆盖老年端 | 🔴 **必须CPS辅助** |
| `offer_acceptance_threshold` | reservation_wage / expected_offer_wage | 构造变量 | 连续比值 | 条件样本 | 🟡中 | ❌ 否 | 需构造 | expected_offer_wage有条件缺失 | 🟡 **建议用reservation_wage代替** |
| employment_status | Employment status | 就业状态分类 | 分类 | 全样本 | 🟢极低 | ✅ 是 | — | 非就业者仅14% | 🟢 **立即可用** |
| job_transition_belief | P(new employer in 4m) | "expected likelihood of moving to different employer" | 连续(0-100) | 就业者 | 🟢低 | ✅ 是 | — | 仅就业者 | 🟢 **验证指标** |
| separation_belief | P(non-employment in 4m) | "expected likelihood of moving into non-employment" | 连续(0-100) | 就业者 | 🟢低 | ✅ 是 | — | 仅就业者 | 🟢 **验证指标** |
| earnings_expectations | Wage satisfaction + SCE Core | — | 混合 | — | — | ❌ 否 | 需跨数据集 | 需SCE Core整合 | 🔴 **MVP暂不纳入** |

---

## Part 2：参数实现建议表

| 模型参数 | 实现方式 | SCE LMS 单独可完成？ | CPS 辅助？ | MVP 建议 |
|---------|---------|-------------------|-----------|---------|
| `reservation_wage` | 直接使用 SCE LMS 变量，log 变换 | ✅ **完全可以** | 不需要 | ✅ **第一版直接纳入** |
| `offer_arrival_belief` | 直接使用 SCE LMS 变量，÷100 | ✅ **完全可以** | 不需要 | ✅ **第一版直接纳入** |
| `search_intensity` | 简单版：二分类 searched(0/1)；增强版：CPS搜索方法数量归一化 | ⚠️ 简单版可以 | ✅ 增强版需要 | ✅ **第一版用简单版，后期升级** |
| `participation_propensity` | CPS 分组 LFPR 作基准 + SCE LMS P(work beyond 62/67) 微调 | ❌ 不可以 | ✅ **必须** | ⚠️ **第一版做粗分组（3组）** |
| `offer_acceptance_threshold` | 第一版用 reservation_wage 直接代替；后期构造 ratio | ⚠️ 间接 | 不需要 | ✅ **并入 reservation_wage** |

---

## Part 3：Worker Types 实现路径

| Worker Type | 定义 | 构造变量 | 数据来源 | MVP 可行性 |
|-------------|------|---------|---------|-----------|
| **Active Searcher** | 高搜索+高offer预期 | searched=1 且 offer_arrival_belief > median | SCE LMS | ✅ 立即可行 |
| **Passive Worker** | 低搜索+低separation风险 | searched=0 且 separation_belief < median | SCE LMS | ✅ 立即可行 |
| **Marginal Worker** | 低搜索+高退出/非就业 | searched=0 且 (separation_belief > median 或 非就业) | SCE LMS + CPS | 🟡 需CPS辅助非就业端 |

---

## Part 4：最终判断

### 1. SCE LMS 是否足以支撑 MVP 阶段的参数约束？

**✅ 足以支撑，但有边界条件。**

- **2个参数可以立即进入模型**：`reservation_wage` 和 `offer_arrival_belief`
- **1个参数可以用简单版进入**：`search_intensity`（二分类）
- **1个参数必须等CPS**：`participation_propensity`
- **1个参数暂时搁置**：`earnings_expectations`

### 2. 哪两个参数已经可以直接进入模型？

1. **`reservation_wage`** — 最可靠，连续型，全样本覆盖，官方已做过计量回归验证
2. **`offer_arrival_belief`** — 第二可靠，连续概率型，全样本覆盖

### 3. 哪两个参数必须等 CPS 联合后才能稳定实现？

1. **`participation_propensity`** — SCE LMS 仅覆盖老年端(P(work beyond 62/67))，全年龄必须用 CPS 分层 LFPR
2. **`search_intensity`（稳健版）** — SCE LMS 只有二分类，CPS 有搜索方法数量可构造连续指标

### 4. 第一版 Worker Types 是否已经可以开始设计？

**✅ 可以开始。** 使用 reservation_wage × searched × offer_arrival_belief 三个 SCE LMS 直接变量即可构造 3 类 Worker Types。非就业者的"边缘参与者"需后续用 CPS 增强。

### 5. 下一步最应该去接 CPS、JOLTS、还是 CES？为什么？

**➡️ CPS 最优先。** 理由：

1. CPS 提供 `participation_propensity` 的唯一来源（分组 LFPR）— **解决当前 4 个参数中唯一不能由 SCE LMS 独立完成的那个**
2. CPS 微观文件可构造月度状态转移矩阵（E→U, U→E, E→N, N→E）— 这是 ABM 最核心的校准目标
3. CPS 的失业者搜索方法变量可增强 `search_intensity` 的连续化构造
4. CPS 提供失业率、劳参率、EPOP 三大宏观校准目标
5. CPS 与 SCE LMS 在人口特征维度上可以对齐（都有 age, education, gender）

**JOLTS 和 CES 在 CPS 之后接入。** 它们只提供宏观时间序列（空缺率/招聘率/工资/工时），数据获取极简单（BLS API），不需要微观数据处理，优先级低于 CPS。

---

## 附：下一步具体行动项

| 优先级 | 行动 | 目的 | 预计耗时 |
|--------|------|------|---------|
| **P0** | 下载 SCE LMS Complete Microdata 并打开 | 确认变量名、搜索子问题结构、缺失率 | 1天 |
| **P0** | 下载 SCE LMS Questionnaire PDF | 确认题目原文和跳转逻辑 | 0.5天 |
| **P1** | 下载 CPS 月度汇总表（BLS API） | 获取失业率、劳参率、EPOP 时间序列 | 0.5天 |
| **P1** | 下载 CPS PUMD（选定月份） | 测试状态转移矩阵构造 + 搜索方法变量 | 2天 |
| **P2** | 下载 JOLTS 时间序列（BLS API） | 获取空缺、招聘、辞职、解雇月度序列 | 0.5天 |
| **P2** | 下载 CES 时间序列（BLS API） | 获取非农就业、平均时薪、平均周工时 | 0.5天 |

---

> **本报告结论：SCE LMS 变量层面足以支撑 MVP 阶段。reservation_wage 和 offer_arrival_belief 可立即落地。search_intensity 和 participation_propensity 需 CPS 补充。下一步应优先接 CPS。**
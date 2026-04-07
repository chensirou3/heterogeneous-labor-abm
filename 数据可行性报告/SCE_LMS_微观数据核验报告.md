# SCE Labor Market Survey 微观数据核验报告

> 核验日期：2026-04-06
> 目标：确认 SCE LMS 的关键变量能否支撑 MVP 阶段异质性参数构造

---

## 一、官方数据入口确认

| 项目 | 确认状态 | 官方位置 |
|------|---------|---------|
| **数据主页** | ✅ 已确认 | https://www.newyorkfed.org/microeconomics/sce/labor |
| **Complete Microdata** | ✅ 免费下载，无需注册 | Data Bank → SCE Labor Market Survey → Complete Microdata |
| **Questionnaire** | ✅ 可下载 PDF | 数据主页 Downloads → Questionnaire |
| **Chart Guide** | ✅ 可下载（相当于 codebook/变量说明） | 数据主页 Downloads → Chart Guide |
| **Chart Data** | ✅ 汇总图表数据可下载 | 数据主页 Downloads → Chart Data |
| **Data Bank 入口** | ✅ | https://www.newyorkfed.org/microeconomics/databank |

**关键信息：**
- 调查频率：每4个月一次（3月/7月/11月）
- 起始时间：2014年3月
- 微观数据公开滞后：约 18 个月
- 最新可用微观数据：约到 2024年底（2025年7月 wave 的摘要指标已在线发布）
- 样本量：约 1,300 人（旋转面板，每位受访者参与约12个月）
- 母调查：Survey of Consumer Expectations (SCE)，全国代表性互联网面板

---

## 二、关键变量逐项核验

### 变量 1：Reservation Wage（保留工资）

| 字段 | 内容 |
|------|------|
| **存在性** | ✅ 确认存在 |
| **题目原文** | "Suppose someone offered you a job today in a line of work that you would consider. **What is the lowest wage or salary you would accept** (BEFORE taxes and other deductions) for this job?" |
| **数据类型** | 连续型，美元金额（年薪） |
| **询问对象** | **所有受访者**（就业者、失业者、非劳动力均被问到） |
| **取值范围** | 连续正实数。2025年7月平均值 $82,472；标准差约 $44,614（从回归分析推算） |
| **时间覆盖** | 2014年3月至今 |
| **缺失率** | 官方报告中未提及系统性缺失；因为是直接问所有人，预计缺失率低 |
| **来源确认** | Liberty Street Economics 2024-08-19 博客文章明确引用此问题原文；NY Fed 新闻稿反复报告此指标 |

**核验结论：** 🟢 **最可靠的变量**。直接对应模型参数 `reservation_wage`。无需重编码，直接可用。

---

### 变量 2：Current Employment Status（当前就业状态）

| 字段 | 内容 |
|------|------|
| **存在性** | ✅ 确认存在 |
| **题目含义** | 受访者当前劳动力状态：就业(Employed) / 失业(Unemployed) / 非劳动力(Out of Labor Force) |
| **数据类型** | 分类型（至少3类） |
| **询问对象** | 所有受访者 |
| **取值范围** | 至少 Employed / Unemployed / Out of Labor Force |
| **时间覆盖** | 2014年3月至今 |
| **缺失率** | 极低（基础人口学变量） |
| **来源确认** | 官方报告按 employment status 分组报告 reservation wage、transition rates 等 |

**核验结论：** 🟢 **可靠**。用于分层分析和条件参数构造。

---

### 变量 3：Search Behavior in Past Four Weeks（过去4周搜索行为）

| 字段 | 内容 |
|------|------|
| **存在性** | ✅ 确认存在 |
| **题目含义** | 过去4周是否搜索工作；搜索努力和结果（job search effort and outcomes） |
| **数据类型** | 二分类（是/否）+ 可能的搜索渠道/方法细分 |
| **询问对象** | 所有受访者（从官方摘要看，报告的是总体中搜索者的比例） |
| **取值范围** | 2025年11月：23.8% 的受访者报告过去4周搜索过工作 |
| **时间覆盖** | 2014年3月至今 |
| **缺失率** | 预计低 |
| **来源确认** | 2017年介绍性博客明确提到 "job search effort and outcomes"；官方摘要每期报告此比例 |

**核验结论：** 🟡 **可用但需构造**。二分类变量（searched / not searched）可作为 `search_intensity` 的代理。但不是连续的"搜索强度"量度——需要从搜索渠道数、搜索频率等构造连续指标，或直接用搜索概率。

---

### 变量 4：Offer Arrival Belief（工作机会到达信念）

| 字段 | 内容 |
|------|------|
| **存在性** | ✅ 确认存在 |
| **题目含义** | "未来4个月收到至少一份工作机会的预期概率" (expected likelihood of receiving at least one job offer in the next four months) |
| **数据类型** | 连续型，概率 0-100% |
| **询问对象** | 所有受访者 |
| **取值范围** | 0-100。2025年11月平均 18.3%；2025年7月平均 18.8% |
| **时间覆盖** | 2014年3月至今 |
| **缺失率** | 预计低（概率引出问题是 SCE 的核心方法论） |
| **来源确认** | 每期官方摘要报告此指标；2017年介绍博客明确描述 |

**核验结论：** 🟢 **最可靠的变量之一**。直接对应模型参数 `offer_arrival_belief`。概率形式，无需重编码。

---

### 变量 5：Offer Wage / Expected Offer Wage（工作机会工资）

| 字段 | 内容 |
|------|------|
| **存在性** | ✅ 确认存在（包括实际 offer wage 和 expected offer wage） |
| **题目含义** | (a) 过去4个月实际收到的 offer 工资；(b) 未来4个月预期 offer 工资 |
| **数据类型** | 连续型，美元金额 |
| **询问对象** | (a) 仅收到 offer 的受访者；(b) 所有受访者（条件预期） |
| **取值范围** | 2018年11月平均全职 offer wage $58,035；2024年有所上升 |
| **时间覆盖** | 2014年3月至今 |
| **缺失率** | 实际 offer wage 缺失率较高（仅~19%的人收到过offer）；expected offer wage 缺失率低 |
| **来源确认** | 2017年博客 "expected wages for these offers"；官方新闻稿 "expected wage offer (conditional on receiving one)" |

**核验结论：** 🟡 **可用但有条件**。Expected offer wage 可用于构造 `offer_acceptance_threshold`（与 reservation wage 的差异）。实际 offer wage 有较高缺失率（仅收到 offer 的子样本）。

---

### 变量 6：Job Transition Belief（工作转换信念）

| 字段 | 内容 |
|------|------|
| **存在性** | ✅ 确认存在 |
| **题目含义** | 就业者在未来4个月：(a) 换到不同雇主的预期概率；(b) 仍在同一雇主的预期概率 |
| **数据类型** | 连续型，概率 0-100% |
| **询问对象** | 就业者 |
| **取值范围** | 换雇主概率平均约 8.17%（从回归表中获得） |
| **时间覆盖** | 2014年3月至今 |
| **缺失率** | 对就业者预计低；非就业者不适用 |
| **来源确认** | 2024年博客回归表 "Probability of Moving to a New Job" Dep. Var. Mean = 8.172 |

**核验结论：** 🟢 **可靠**。直接可用。官方回归分析已使用此变量。

---

### 变量 7：Job Separation Belief（失业/离职信念）

| 字段 | 内容 |
|------|------|
| **存在性** | ✅ 确认存在 |
| **题目含义** | 就业者在未来4个月进入非就业状态（失业或退出劳动力）的预期概率 |
| **数据类型** | 连续型，概率 0-100% |
| **询问对象** | 就业者 |
| **取值范围** | 进入非就业概率平均约 3.14%（从回归表中获得） |
| **时间覆盖** | 2014年3月至今 |
| **缺失率** | 对就业者预计低 |
| **来源确认** | 2024年博客回归表 "Probability of Moving into Non-Employment" Dep. Var. Mean = 3.143 |

**核验结论：** 🟢 **可靠**。直接可用。

---

### 变量 8：Earnings Expectations（收入预期）

| 字段 | 内容 |
|------|------|
| **存在性** | 🟡 部分存在（LMS + SCE Core 联合） |
| **题目含义** | SCE LMS: 工资/福利满意度；SCE Core: 未来一年收入增长预期概率分布 |
| **数据类型** | LMS: 满意度量表；Core: 连续概率分布 |
| **询问对象** | 就业者（LMS 满意度）；所有人（Core 收入预期） |
| **取值范围** | Core 中有 expected earnings growth (%); 2017博客提到 "earnings" 相关问题 |
| **时间覆盖** | Core: 2013年至今(月度)；LMS: 2014年至今 |
| **缺失率** | 需要合并 Core + LMS 数据 |

**核验结论：** 🟡 **可用但需跨数据集构造**。LMS 中有工资满意度和实际工资变化信息。完整的收入增长预期概率分布在 SCE Core 中，二者通过受访者 ID 可链接。

---

## 三、变量 → 模型参数映射表

| 模型参数 | 对应 SCE 原始变量 | 题目含义 | 直接可用？ | 需重编码？ | 缺失率评估 | 风险点 |
|---------|-----------------|---------|-----------|-----------|-----------|--------|
| **`reservation_wage`** | Reservation wage (年薪 $) | "你愿意接受的最低工资/薪水" | ✅ **直接可用** | 否 | 🟢 低（问所有人） | 无重大风险。自我报告可能有偏，但有充足学术先例（Krueger & Mueller 2016, Kosar et al. 2024） |
| **`search_intensity`** | Job search (past 4 weeks) + 搜索渠道数 | 过去4周是否搜索 + 搜索方法 | ⚠️ 部分直接 | 是：二分类→需构造连续指标 | 🟢 低 | 搜索者仅占~24%样本；搜索渠道细分需验证微观数据中具体的子问题数量。**可用 CPS 失业者搜索方法变量做外部校验** |
| **`participation_propensity`** | (a) 工作到62/67岁以上的概率 (b) 非就业→就业的转移概率预期 | "你在62/67岁后仍工作的概率" | ⚠️ 间接 | 是：需与就业状态结合构造 | 🟢 低 | 62/67岁工作概率仅反映老年端参与意愿。全年龄的劳参倾向需结合就业状态和就业转移概率推断。**建议用 CPS 劳参率做分层锚定** |
| **`offer_acceptance_threshold`** | Reservation wage ÷ Expected offer wage | 保留工资与预期offer工资的比值 | ⚠️ 需构造 | 是：两变量之比 | 🟡 中（expected offer wage 有条件缺失） | 需用 reservation wage 和 expected offer wage 构造。Expected offer wage 的条件是"如果收到 offer"，非所有人都有预期 offer wage。**但 reservation wage 本身已是 acceptance threshold 的直接度量** |
| **`offer_arrival_belief`** | Expected probability of receiving ≥1 offer in next 4 months | "未来4个月收到至少一份offer的概率" | ✅ **直接可用** | 否 | 🟢 低 | 无重大风险。概率引出方式是 SCE 的核心方法论，有丰富校验文献 |

### 补充映射：LMS 中存在但非核心5参数的变量

| 变量 | 对应 SCE 原始变量 | 在模型中的用途 |
|------|-----------------|--------------|
| `job_transition_belief` | P(换雇主 in next 4m) | 就业者工作-工作转移概率。可用于校准模型中的 job-to-job flow |
| `separation_belief` | P(进入非就业 in next 4m) | 就业者失业/退出预期。可用于校准 separation rate |
| `earnings_expectations` | SCE Core: 收入增长预期分布；LMS: 工资满意度 | 用于校准 wage dynamics。需合并 Core + LMS |
| 实际 offer 数量 | # of job offers received in past 4m | 校验 `offer_arrival_belief` 的实际实现率 |
| 实际 offer 工资 | Offer wage received | 校验预期 offer 与实际 offer 的关系 |
| 工资满意度 | Satisfaction with wage/benefits | 间接支持 `offer_acceptance_threshold` |

---

## 四、最终判断

### 1. SCE LMS 是否足以支撑 MVP 阶段的异质性参数约束？

**结论：✅ 足以支撑，但有一个需注意的限制。**

**可以直接支撑的参数（无障碍）：**
- `reservation_wage` — 直接可得，连续型，全样本覆盖，最可靠的变量
- `offer_arrival_belief` — 直接可得，概率型，全样本覆盖

**可以间接构造的参数（需一定数据处理，但有可行路径）：**
- `search_intensity` — 从搜索行为二分类 + 搜索渠道数构造
- `offer_acceptance_threshold` — 从 reservation_wage / expected_offer_wage 构造，或直接用 reservation_wage 作为 acceptance threshold 的度量
- `participation_propensity` — 从 P(工作到62/67) + P(非就业→就业) + CPS 分层劳参率联合构造

**核心风险：**
- `search_intensity` 的连续化构造取决于微观数据中搜索渠道子问题的具体结构——**需要打开实际微观数据文件验证**
- `participation_propensity` 的全年龄构造需要 CPS 辅助——SCE LMS 单独不足以覆盖

### 2. 哪些变量最可靠？

按可靠性排序：

1. 🟢 **Reservation wage** — 最可靠。直接问卷题目，连续型，全样本，有大量学术先例
2. 🟢 **Offer arrival belief** — 最可靠。概率引出，全样本
3. 🟢 **Job transition belief** — 可靠。概率引出，就业者子样本
4. 🟢 **Separation belief** — 可靠。概率引出，就业者子样本
5. 🟡 **Search behavior** — 可用但粗糙。需构造连续指标
6. 🟡 **Expected offer wage** — 可用但有条件缺失
7. 🟡 **Earnings expectations** — 需跨数据集（Core + LMS）构造

### 3. 哪些变量有样本量或缺失问题？

| 问题 | 影响变量 | 严重程度 | 应对方案 |
|------|---------|---------|---------|
| **总样本量约1300** | 所有变量 | 🟡 中等 | 合并多波次数据（36+波次 × 1300 ≈ 最多 ~47,000 人次观测）；使用加权统计 |
| **非就业者子样本小** | 非就业者→就业转移概率 | 🔴 较高 | 非就业者约占样本~30-40%（~400-500人/波），非就业者子样本的精细分组将受限 |
| **实际 offer 收到者子样本小** | 实际 offer wage | 🔴 较高 | 仅~19%受访者收到过 offer（~250人/波）。Expected offer wage 覆盖更广 |
| **精细交叉分组** | 按教育×年龄×性别 | 🔴 较高 | 1300人做3×3×2=18组，每组约72人。需合并波次或使用贝叶斯分层模型 |
| **面板轮换** | 长期追踪 | 🟡 中等 | 每人参与~12个月（3波），不适合做长面板分析，但足够做分布估计 |

### 4. 下一步最应该接 CPS、JOLTS、还是 CES？

**建议顺序：CPS → JOLTS → CES**

理由：

| 优先级 | 数据源 | 理由 |
|--------|--------|------|
| **第一** | **CPS** | (1) CPS 提供失业率、劳参率、EPOP 三大宏观校准目标；(2) CPS 微观文件可构造状态转移矩阵（E→U、U→E、E→N等），是 ABM 最核心的校准对象；(3) CPS 的搜索方法变量可补充 SCE LMS 中 `search_intensity` 的构造；(4) CPS 按人口特征分层的劳参率可锚定 `participation_propensity`。**CPS 是 SCE LMS 最重要的互补数据源。** |
| **第二** | **JOLTS** | (1) 空缺率、招聘率、辞职率、解雇率是搜索匹配模型的核心流量变量；(2) Beveridge 曲线（空缺率 vs 失业率）是模型校准的标志性矩；(3) 数据获取极简单（BLS API，直接时间序列） |
| **第三** | **CES** | (1) 非农就业变化、平均时薪、平均周工时；(2) 获取最简单（BLS API）；(3) 但 CES 的信息与 CPS 有较大重叠（就业变化），独立增量相对小 |

---

## 五、关键行动项

### 立即行动（本周）

1. **下载 SCE LMS Complete Microdata** → 打开实际数据文件，确认：
   - 变量名列表与上述核验是否一致
   - reservation_wage 的实际分布、缺失率
   - search behavior 的子问题结构（是否有搜索渠道/方法数量）
   - offer_arrival_belief 的实际分布
   - 按 employment status 分组后的样本量

2. **下载 Questionnaire PDF** → 逐题确认题目原文和跳转逻辑

3. **下载 CPS 月度汇总表** → 通过 BLS API 获取失业率、劳参率、EPOP 时间序列

### 第二周

4. **下载 JOLTS 时间序列** → 通过 BLS API 获取空缺、招聘、辞职、解雇月度序列

5. **下载 CPS PUMD 微观文件（选定月份）** → 测试状态转移矩阵的构造流程

### 汇总判断

> **SCE LMS 在数据变量层面足以支撑 MVP 阶段的异质性参数约束。**
> 核心参数 `reservation_wage` 和 `offer_arrival_belief` 直接可用且可靠。
> `search_intensity` 和 `participation_propensity` 需配合 CPS 构造。
> 最大的不确定性是搜索行为子问题的精细度——需打开实际微观数据确认。
> **数据层面无致命障碍，项目可以继续推进。**



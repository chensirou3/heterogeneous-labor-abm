# JOLTS 接入与匹配流量指标审查报告

> 审查日期：2026-04-06
> 目标：确认 JOLTS 能否稳定承担劳动市场 ABM 中的 vacancy / hiring / separation 层
> 方法：基于 BLS 官方 JOLTS 主页、数据定义页、Series ID 格式文档、下载目录、API 文档及最新新闻稿

---

## Part 1：JOLTS 数据总表

### 1.1 数据概况

| 参数 | 值 |
|------|---|
| **官方名称** | Job Openings and Labor Turnover Survey (JOLTS) |
| **主管机构** | U.S. Bureau of Labor Statistics (BLS) |
| **官方主页** | https://www.bls.gov/jlt/ |
| **数据定义页** | https://www.bls.gov/jlt/jltdef.htm |
| **免费获取** | ✅ 完全免费 |
| **API 支持** | ✅ BLS Public Data API（v1无需注册；v2需API key，50 series/次，500次/天） |
| **下载目录** | https://download.bls.gov/pub/time.series/jt/ （文本文件直接下载） |
| **数据频率** | **月度** |
| **时间覆盖** | **2000年12月至今**（约25年月度数据） |
| **覆盖范围** | 全国 + 50州及DC（州级仅 total nonfarm） |
| **行业分层** | ✅ 有（total nonfarm / total private / government / 主要行业） |
| **季调版本** | ✅ 同时提供季调(S)和非季调(U)版本 |
| **最新数据** | 2026年2月（preliminary），2026年3月31日发布 |
| **发布滞后** | 约1个月（比月后约5周发布） |
| **调查方式** | 企业调查（establishment survey），样本约21,000个非农事业单位 |

### 1.2 Series ID 格式（已从官方文档确认）

```
JT  S  000000  00  00000  00  JO  R
│   │  │       │   │      │   │   │
│   │  │       │   │      │   │   └─ Rate/Level: R=Rate, L=Level
│   │  │       │   │      │   └──── Data Element: JO/HI/TS/QU/LD/OS
│   │  │       │   │      └──────── Size Class (00=all)
│   │  │       │   └─────────────── Area Code (00000=national)
│   │  │       └─────────────────── State Code (00=national)
│   │  └─────────────────────────── Industry Code (000000=total nonfarm)
│   └────────────────────────────── Seasonal: S=adjusted, U=unadjusted
└────────────────────────────────── Prefix: JT
```

**Data Element 编码：**

| 代码 | 含义 |
|------|------|
| `JO` | Job Openings |
| `HI` | Hires |
| `TS` | Total Separations |
| `QU` | Quits |
| `LD` | Layoffs and Discharges |
| `OS` | Other Separations |

**Rate/Level 编码：**

| 代码 | 含义 |
|------|------|
| `L` | Level（千人） |
| `R` | Rate（百分比） |

### 1.3 核心 Series ID 速查表

| 指标 | Series ID | 说明 |
|------|-----------|------|
| **Job Openings Level (SA)** | `JTS000000000000000JOL` | 季调，全国，total nonfarm，千人 |
| **Job Openings Rate (SA)** | `JTS000000000000000JOR` | 季调，全国，total nonfarm，% |
| **Hires Level (SA)** | `JTS000000000000000HIL` | 季调，全国，total nonfarm，千人 |
| **Hires Rate (SA)** | `JTS000000000000000HIR` | 季调，全国，total nonfarm，% |
| **Total Separations Level (SA)** | `JTS000000000000000TSL` | 季调，全国，total nonfarm，千人 |
| **Total Separations Rate (SA)** | `JTS000000000000000TSR` | 季调，全国，total nonfarm，% |
| **Quits Level (SA)** | `JTS000000000000000QUL` | 季调，全国，total nonfarm，千人 |
| **Quits Rate (SA)** | `JTS000000000000000QUR` | 季调，全国，total nonfarm，% |
| **Layoffs/Discharges Level (SA)** | `JTS000000000000000LDL` | 季调，全国，total nonfarm，千人 |
| **Layoffs/Discharges Rate (SA)** | `JTS000000000000000LDR` | 季调，全国，total nonfarm，% |
| **Other Separations Level (SA)** | `JTS000000000000000OSL` | 季调，全国，total nonfarm，千人 |
| **Other Separations Rate (SA)** | `JTS000000000000000OSR` | 季调，全国，total nonfarm，% |

**API 调用示例：**
```
GET https://api.bls.gov/publicAPI/v2/timeseries/data/JTS000000000000000JOL?startyear=2014&endyear=2026
```

### 1.4 下载文件结构

BLS 直接提供文本文件下载（`download.bls.gov/pub/time.series/jt/`）：

| 文件 | 内容 |
|------|------|
| `jt.data.0.Current` | 当前发布的所有数据 |
| `jt.data.1.AllItems` | 全部历史数据 |
| `jt.data.2.JobOpenings` | 仅 Job Openings |
| `jt.data.3.Hires` | 仅 Hires |
| `jt.data.4.TotalSeparations` | 仅 Total Separations |
| `jt.data.5.Quits` | 仅 Quits |
| `jt.data.6.LayoffsDischarges` | 仅 Layoffs & Discharges |
| `jt.data.7.OtherSeparations` | 仅 Other Separations |
| `jt.series` | Series 元数据 |
| `jt.industry` | 行业代码映射 |
| `jt.state` | 州代码映射 |

---

### 1.5 官方定义核验

以下定义直接摘自 BLS 官方数据定义页 (`bls.gov/jlt/jltdef.htm`)：

#### Employment（JOLTS 口径）
> 所有在包含每月12日的工资期内工作或领取工资的在册员工。包括全职和兼职、永久和临时、薪金制和时薪制员工。**不包括**企业主/合伙人、无薪家庭工人、罢工员工、临时工派遣机构/外包/咨询公司员工。

**关键：JOLTS 的 employment 是事业单位口径（establishment-based），与 CES 一致，但与 CPS（household-based）不同。**

#### Job Openings
> 在当月最后一个工作日，所有满足以下全部三个条件的未填充职位：
> 1. 存在具体岗位且有工作可做（全/兼职、永久/临时/季节性均可）
> 2. 该岗位可在30天内开始
> 3. 正在从事业单位外部积极招聘（active recruiting）

**关键：Job Openings 是存量（stock）指标，测量的是月末时点的未填充职位数。**

#### Hires
> 当月所有新增到工资册上的人。包括新招和再招、全/兼职、永久/临时/季节性员工、间歇性回岗员工、当月招入又离职的员工、从其他事业单位调入的员工。**不包括**同一事业单位内部的调动/晋升。

**关键：Hires 是流量（flow）指标，测量当月新增人数。**

#### Separations
> 当月所有从工资册上分离的人。分为三个子类：
>
> - **Quits（自愿离职）**：员工自愿离开。退休和跨地点调动归入 Other Separations。
> - **Layoffs & Discharges（解雇/裁员）**：雇主发起的非自愿分离。包括裁员（无意召回）、岗位取消、合并/缩编/关厂、因故解雇、季节性终止、预计超过7天的暂时停薪。
> - **Other Separations**：退休、跨地点调动、死亡、伤残离职。

**关键：Total Separations = Quits + Layoffs/Discharges + Other Separations。分母统一为 employment（事业单位在册就业人数）。**

#### Rate 的分母
> JOLTS 中所有 rate 的分母统一为 **employment**（事业单位在册就业人数）。
>
> Rate = (Level / Employment) × 100

**这意味着 JOLTS rate 的基准是就业人口，不是劳动力或总人口。**

### 1.6 最新数据快照（2026年2月，preliminary）

| 指标 | Level（千人） | Rate（%） |
|------|-------------|-----------|
| **Job Openings** | 6,882 | 4.2 |
| **Hires** | 4,849 | 3.1 |
| **Total Separations** | 4,971 | 3.1 |
| **Quits** | — | 1.9 |
| **Layoffs/Discharges** | — | 1.1 |

### 1.7 维度与分层

| 维度 | 是否支持 | 详情 | 对第一版的必要性 |
|------|---------|------|----------------|
| **National Total** | ✅ 支持 | total nonfarm + total private + government | ✅ **必须** |
| **Industry** | ✅ 支持 | 主要行业（约15-20个大类 NAICS 行业） | ❌ **第一版不需要** |
| **Region** | ✅ 支持 | 4 Census Regions | ❌ 第一版不需要 |
| **State** | ✅ 支持 | 50州+DC（仅 total nonfarm） | ❌ 第一版不需要 |
| **Firm Size** | ✅ 支持 | Size Class 编码 | ❌ 第一版不需要 |
| **Age / Education / Gender** | ❌ **不支持** | JOLTS 是企业调查，不收集员工人口特征 | N/A |

**关键限制：JOLTS 是事业单位调查（establishment survey），不收集个体员工的人口特征（年龄/教育/性别）。因此无法与 CPS 或 SCE LMS 在人口维度上直接对齐。这不影响宏观校准，但影响分群分析。**

---

## Part 2：指标—模型映射表

| JOLTS 指标 | 在 ABM 中的作用 | 推荐角色 | 第一版是否纳入 | 风险点 |
|-----------|---------------|---------|-------------|--------|
| **Job Openings (Level)** | 反映劳动市场中可用职位总量 | 🟢 **外生环境变量 / 匹配模块输入** | ✅ 纳入 | 无 |
| **Job Openings Rate** | 反映职位空缺相对于就业的紧张程度 | 🟢 **Beveridge 曲线校准目标** | ✅ 纳入 | 与 unemployment rate 联合使用 |
| **Hires (Level)** | 反映劳动市场匹配的实际结果 | 🟢 **匹配成功率的校准目标** | ✅ 纳入 | 无 |
| **Hires Rate** | 每月新招占就业的比例 | 🟡 验证指标 | ⚠️ 可选 | 与 Level 信息重复 |
| **Total Separations (Level)** | 反映劳动市场总流出 | 🟡 验证指标 | ⚠️ 可选 | = Quits + L&D + OS，分解后更有用 |
| **Total Separations Rate** | 总分离率 | 🟡 验证指标 | ⚠️ 可选 | 同上 |
| **Quits (Level)** | 反映 worker-side 自愿退出行为 | 🟢 **Worker 搜索/退出行为的验证目标** | ✅ 纳入 | 无 |
| **Quits Rate** | 自愿离职率 | 🟢 **与 reservation_wage / search_intensity 关联验证** | ✅ 纳入 | 无 |
| **Layoffs/Discharges (Level)** | 反映 employer-side 冲击 | 🟡 **Separation block 的外生约束** | ✅ 纳入 | 与经济周期高度相关 |
| **Layoffs/Discharges Rate** | 解雇裁员率 | 🟡 **与 separation_belief 关联验证** | ✅ 纳入 | 同上 |
| Other Separations | 退休/调动/死亡等 | ⚪ 辅助 | ❌ 第一版不需要 | 噪声大，含义混杂 |

### 角色定义说明

| 角色类型 | 含义 | JOLTS 中的代表 |
|---------|------|--------------|
| **外生环境变量** | 模型将其作为给定的外部条件输入，不由模型内生决定 | Job Openings Level → 决定市场中有多少可匹配岗位 |
| **匹配模块校准目标** | 模型的匹配函数输出应接近此值 | Hires Level → 匹配成功数应接近 JOLTS hires |
| **Beveridge 曲线校准目标** | 模型应再现空缺率-失业率的负相关关系 | Job Openings Rate × Unemployment Rate |
| **Worker 行为验证目标** | 验证模型中 worker-side 行为是否合理 | Quits Rate → 模型中自愿搜索换工作的频率应接近 |
| **Separation block 外生约束** | 模型中 exogenous separation shock 的锚定 | Layoffs/Discharges Rate → 外生分离冲击的强度 |

---

## Part 3：JOLTS 与 CPS 的互补性判断

### 3.1 为什么已有 CPS Gross Flows 仍需 JOLTS？

**CPS Gross Flows 和 JOLTS 测量的是劳动市场流量的两个完全不同的维度：**

| 维度 | CPS Gross Flows | JOLTS |
|------|----------------|-------|
| **调查对象** | 住户（household）→ 劳动者 | 事业单位（establishment）→ 雇主 |
| **测量的是什么** | 劳动者在 E/U/N 三状态之间的**人的流动** | 雇主侧的**岗位的开设、填充、分离** |
| **核心变量** | E→U, U→E, E→N, N→E, U→N, N→U | Job openings, Hires, Quits, Layoffs |
| **能回答的问题** | "有多少人从就业变成失业？" | "有多少岗位空着？雇主招了多少人？" |
| **不能回答的问题** | ❌ 市场上有多少空缺岗位 | ❌ 劳动者在 U 和 N 之间的流动 |
| **搜索匹配模型的角色** | Worker-side 状态转移 | Firm-side 空缺与匹配 |

**结论：两者完全互补，不重叠。**

- CPS Gross Flows 提供 **worker-side** 的状态转移（E↔U↔N）
- JOLTS 提供 **firm-side** 的空缺、招聘、分离
- 搜索匹配模型需要同时看到 worker-side（搜索者数量、状态转移）和 firm-side（空缺数量、招聘结果）

### 3.2 JOLTS 提供了 CPS 没有的什么信息？

| 独占信息 | JOLTS 变量 | CPS 完全不覆盖？ | 重要性 |
|---------|-----------|----------------|--------|
| **市场中有多少空缺岗位** | Job Openings | ✅ CPS 完全不覆盖 | 🔴 **核心** — Beveridge 曲线的另一轴 |
| **雇主每月实际招了多少人** | Hires | ✅ CPS 不直接提供（U→E 是劳动者侧近似） | 🟡 重要 — 匹配函数的输出 |
| **自愿离职 vs 被解雇的区分** | Quits vs Layoffs/Discharges | ⚠️ CPS Gross Flows 的 E→U 不区分原因 | 🟢 有用 — 区分 worker-side vs employer-side shock |
| **分离的企业侧视角** | Total Separations | ⚠️ CPS 的 E→U+E→N 是劳动者侧 | 🟡 有用 — 交叉验证 |

### 3.3 哪些指标可能和 CPS 重复？

| JOLTS 指标 | CPS 对应 | 重复程度 | 建议 |
|-----------|---------|---------|------|
| Hires | U→E + N→E（CPS Gross Flows） | 🟡 **部分重叠但口径不同** | 保留两者，用于交叉验证 |
| Total Separations | E→U + E→N（CPS Gross Flows） | 🟡 **部分重叠但口径不同** | JOLTS 分解为 Q/L&D/OS 更有价值 |
| Job Openings | **无对应** | ❌ 完全不重复 | **必须保留** |
| Quits | 无直接对应 | ❌ 完全不重复 | **必须保留** |
| Layoffs/Discharges | 无直接对应 | ❌ 完全不重复 | **必须保留** |

**口径差异说明：**
- JOLTS Hires ≠ CPS (U→E + N→E)：JOLTS 包含 E→E 的跨雇主换工作（job-to-job transitions），CPS Gross Flows 中这部分停留在 E→E 对角线上
- JOLTS Total Separations ≠ CPS (E→U + E→N)：同样因为口径和调查对象不同

### 3.4 如果只保留最必要的 JOLTS 指标，应该留哪些？

**最小必要集（3个）：**
1. **Job Openings Rate** — Beveridge 曲线的 vacancy 轴，CPS 完全没有
2. **Hires Level** — 匹配函数的校准目标
3. **Quits Rate** — Worker-side 自愿搜索行为的验证

**强烈建议（额外2个）：**
4. **Layoffs/Discharges Rate** — Employer-side 外生冲击的锚定
5. **Job Openings Level** — 匹配模块的输入量

---

## Part 4：最终结论

### 1. JOLTS 是否值得作为劳动市场 ABM 的第三个核心数据源接入？

**✅ 绝对值得。JOLTS 是唯一能提供 firm-side vacancy 信息的官方数据源。**

没有 JOLTS，ABM 只能看到 worker-side（CPS + SCE LMS），完全看不到市场上有多少岗位可供匹配。这对于任何包含搜索匹配模块的模型都是致命缺陷。

| 数据源 | 提供的视角 | 不可替代的信息 |
|--------|----------|--------------|
| **SCE LMS** | Worker 信念与行为参数 | reservation_wage, offer_arrival_belief |
| **CPS** | Worker 状态与宏观校准 | E/U/N 分布, 状态转移, LFPR |
| **JOLTS** | Firm 空缺与匹配流量 | 空缺数, 招聘数, 自愿离职 vs 解雇 |

三者共同构成完整的 worker-side + firm-side 劳动市场图景。

### 2. 第一版最少应接入哪几个 JOLTS 指标？

**MVP 优先级：**

| 优先级 | 指标 | Series ID | 角色 |
|--------|------|-----------|------|
| 🔴 **必须接入** | Job Openings Rate (SA) | `JTS000000000000000JOR` | Beveridge 曲线校准 |
| 🔴 **必须接入** | Job Openings Level (SA) | `JTS000000000000000JOL` | 匹配模块输入 |
| 🔴 **必须接入** | Hires Level (SA) | `JTS000000000000000HIL` | 匹配成功校准目标 |
| 🟡 **强烈建议** | Quits Rate (SA) | `JTS000000000000000QUR` | Worker 行为验证 |
| 🟡 **强烈建议** | Layoffs/Discharges Rate (SA) | `JTS000000000000000LDR` | Separation shock 锚定 |
| ⚪ **可选增强** | Hires Rate / Separations Rate | 各对应 ID | 交叉验证 |
| ❌ **第一版不做** | Other Separations | — | 噪声大 |
| ❌ **第一版不做** | 行业分层 | — | 增加复杂度，第一版不需要 |

**一次 API 调用即可获取全部5个必须/强烈建议指标：**
```
POST https://api.bls.gov/publicAPI/v2/timeseries/data/
Body: {
  "seriesid": [
    "JTS000000000000000JOR",
    "JTS000000000000000JOL",
    "JTS000000000000000HIL",
    "JTS000000000000000QUR",
    "JTS000000000000000LDR"
  ],
  "startyear": "2014",
  "endyear": "2026"
}
```

### 3. 第一版是否应只用 national aggregate，而不是做 industry 分层？

**✅ 第一版只用 national aggregate。** 理由：

1. **模型复杂度控制**：第一版 ABM 是单一劳动市场模型，不区分行业
2. **与 CPS/SCE LMS 的对齐**：CPS 的宏观指标和 SCE LMS 的参数都是 national level
3. **样本量充足**：national aggregate 最稳，industry 分层后某些行业波动大
4. **后期可扩展**：行业分层可以在第二版引入，用于异质性分析

### 4. 接完 JOLTS 后，下一步应该优先接 CES 吗？为什么？

**✅ 应该接 CES，但优先级较低，可以延后。** 理由：

| 评估维度 | CES 的价值 |
|---------|-----------|
| **独立增量** | 🟡 中等——非农就业变化 CPS 已有近似；平均时薪/平均工时是独立信息 |
| **对 MVP 的必要性** | 🟡 非核心——MVP 的校准目标已被 CPS(失业率/LFPR) + JOLTS(空缺/招聘) 覆盖 |
| **工资信息** | ✅ CES 的平均时薪(AHE)是唯一月度工资序列，可用于验证 reservation_wage 的合理性 |
| **获取难度** | 🟢 极简单——与 JOLTS 共用 BLS API |

**建议：**
- MVP 阶段可以暂不接 CES
- 如果需要验证 reservation_wage 与市场工资的关系，再接 CES 的平均时薪
- CES 的非农就业人数变化与 CPS 就业水平高度相关，独立增量有限

---

## 附：完成 JOLTS 接入后的完整数据架构

```
┌─────────────────────────────────────────────────────────┐
│              MVP 完整数据架构（三源）                       │
├──────────────┬──────────────────────────────────────────┤
│ 参数层        │                                          │
│ (SCE LMS     │  reservation_wage ← SCE LMS              │
│  + CPS)      │  offer_arrival_belief ← SCE LMS          │
│              │  search_intensity ← SCE LMS + CPS        │
│              │  participation_propensity ← CPS          │
├──────────────┼──────────────────────────────────────────┤
│ 校准目标层    │                                          │
│ Worker-side  │  unemployment_rate ← CPS (BLS API)       │
│ (CPS)        │  LFPR ← CPS (BLS API)                    │
│              │  EPOP ← CPS (BLS API)                    │
│              │  E↔U↔N 转移矩阵 ← CPS Gross Flows       │
│──────────────│──────────────────────────────────────────│
│ Firm-side    │  job_openings_rate ← JOLTS (BLS API)     │
│ (JOLTS)      │  job_openings_level ← JOLTS (BLS API)    │
│              │  hires_level ← JOLTS (BLS API)           │
│              │  quits_rate ← JOLTS (BLS API)            │
│              │  layoffs_rate ← JOLTS (BLS API)          │
├──────────────┼──────────────────────────────────────────┤
│ 验证指标层    │                                          │
│              │  job_transition_belief ← SCE LMS         │
│              │  separation_belief ← SCE LMS             │
│              │  P(move into employment) ← SCE LMS      │
│              │  Beveridge curve ← JOLTS JOR × CPS UR   │
│              │  avg_hourly_earnings ← CES (后期可选)     │
└──────────────┴──────────────────────────────────────────┘
```

### 下一步行动项

| 优先级 | 行动 | 目的 |
|--------|------|------|
| **P0** | 通过 BLS API 获取 JOLTS 5个核心序列（JOR/JOL/HIL/QUR/LDR） | Firm-side 校准目标 |
| **P0** | 验证 JOLTS 与 CPS 的时间对齐（都是月度，2000年12月起） | 确认数据可联合使用 |
| **P1** | 构造 Beveridge 曲线（JOR × UR）作为校准目标 | 匹配模块核心验证 |
| **P2** | 可选：通过 BLS API 获取 CES 平均时薪 | 工资合理性验证 |
| **P2** | 可选：检查 JOLTS 行业分层数据 | 后续异质性分析储备 |

---

> **本报告结论：JOLTS 完全值得作为第三个核心数据源接入。它提供了 CPS 完全不覆盖的 firm-side vacancy/hiring/separation 信息。第一版最少接 5 个 national aggregate 指标（JOR/JOL/HIL/QUR/LDR），一次 API 调用即可获取。与 CPS 完全互补、零重叠。第一版只用 national aggregate，不做行业分层。接完 JOLTS 后，CES 可作为可选增强延后处理。**

---
name: survival-analysis
description: 生存分析完整工作流：Kaplan-Meier 与 log-rank、Cox 比例风险回归（单/多因素）、森林图、时间依赖 ROC 与 C-index、竞争风险、列线图、TCGA 风格表达-生存分析。Python lifelines 与 R survival/survminer/rms 双实现。
whenToUse: 做生存分析、KM 曲线、Cox 回归、预后模型、表达-生存关联时
---

# 生存分析（Survival Analysis）

## 环境
- Python：lifelines 已装（from lifelines import KaplanMeierFitter, CoxPHFitter, logrank_test）
- R：survival / survminer / survivalROC / timeROC / rms / cmprsk / forestplot 已装
- 数据格式：通常为三列——`time`（随访时间）、`event`（1=发生终点事件，0=删失）、协变量列；生存分析前先确认删失编码正确

## 核心方法速查
| 目的 | 方法 | Python (lifelines) | R |
|---|---|---|---|
| 生存曲线 | Kaplan-Meier | `KaplanMeierFitter().fit(t, e)` | `survfit(Surv(t,e)~grp)` |
| 两组比较 | log-rank | `logrank_test(t, grp, e)` | `survdiff(Surv(t,e)~grp)` |
| 多因素回归 | Cox PH | `CoxPHFitter().fit(df, 'time', 'event')` | `coxph(Surv(t,e)~x1+x2)` |
| 预测能力 | 时间依赖 AUC/C-index | `lifelines.utils.concordance_index` | `timeROC` / `survivalROC` |
| 竞争风险 | Fine-Gray | （lifelines 有限） | `cmprsk::crr` |
| 列线图 | 预后可视化 | — | `rms::cph` + `rms::nomogram` |

## 标准流程（TCGA 风格表达-生存分析，组学常用）
1. **分组**：按基因表达切分——常用中位数/三分位；若要优化切点，用 `maxstat`/`surv_cutpoint`（survminer），**必须说明切点选择方法**，避免"试切点直到显著"的 p-hacking
2. **单因素**：每组画 KM 曲线 + log-rank p 值（`ggsurvplot` 标注 p 与风险表 number at risk）
3. **多因素**：`coxph` 纳入临床协变量（年龄/分期/TNM 等），报告每个变量的 HR（95%CI）与 p
4. **森林图**：`survminer::ggforest`（R）或 matplotlib 手绘（Python）
5. **预测评价**：时间依赖 ROC（`timeROC::timeROC`，报告 1/3/5 年 AUC）、C-index；有需要时做 5 折/10 折交叉验证
6. **风险分层**：多因素 Cox 系数构建风险评分（risk score = Σβ·x），按中位数分高低风险组，再画 KM + ROC（lasso-cox 见下）

## Python 关键代码（lifelines）
```python
from lifelines import KaplanMeierFitter, CoxPHFitter, logrank_test
from lifelines.utils import concordance_index

kmf = KaplanMeierFitter()
kmf.fit(df['time'], df['event'], label='Group A')
kmf.plot_survival_function()          # KM 曲线
print(logrank_test(df['time'][df['grp']==1], df['time'][df['grp']==0],
                   df['event'][df['grp']==1], df['event'][df['grp']==0]).p_value)

cph = CoxPHFitter(penalizer=0.01)
cph.fit(df[['time','event','age','stage','gene']], duration_col='time', event_col='event')
cph.print_summary()                    # 含 HR/CI/p
cph.plot()                             # 系数图
```
- LASSO-Cox 特征筛选：用 sklearn `LassoCV` 对标准化协变量先筛，再用 CoxPHFitter 拟合

## R 关键代码
```r
library(survival); library(survminer)
fit <- survfit(Surv(time, event) ~ group, data = df)
ggsurvplot(fit, data = df, pval = TRUE, risk.table = TRUE, conf.int = TRUE)
cox <- coxph(Surv(time, event) ~ age + stage + gene, data = df)
ggforest(cox)                 # 森林图
zph <- cox.zph(cox); print(zph)   # 检验 PH 假设，p<0.05 需处理（分层/时变）
timeROC(T, delta, marker = df$gene, cause = 1, times = c(365, 1095, 1825))
```

## 报告规范
- 报告：中位生存时间（KM）、log-rank p、Cox 的 HR（95%CI）与 p、AUC 值；KM 曲线必须带风险表
- 删失处理：说明删失比例与原因；右删失是默认假设
- **PH 假设检验**（cox.zph）：不满足时改用分层 Cox 或时变系数
- 样本量提示：每组事件数（非样本数）决定检验功效，过少时避免过度解读
- 竞争风险（如死于其他原因 vs 疾病相关死亡）：用 cmprsk，KM 会高估

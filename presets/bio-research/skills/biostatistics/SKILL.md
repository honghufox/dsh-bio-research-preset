---
name: biostatistics
description: 生物科研数据统计分析方法与 Python/R 实现：t 检验、ANOVA、非参数检验、多重比较校正、相关与回归、生存分析、功效分析。需要选择或解释统计检验时使用。
whenToUse: 处理实验数据、选择统计检验、报告 p 值/效应量、做生存分析或功效分析时
---

# 生物统计与数据分析

## 环境
- Python 已装齐：pandas 3.0 / numpy 2.4 / scipy 1.18 / statsmodels 0.14 / seaborn 0.13 / scikit-learn 1.9
- R 4.5 可用（脚本中用 Rscript 显式调用）
- 脚本写入工作区、可重复运行；数据不要硬编码进脚本，从文件读取

## 选择统计检验（决策速查）
| 数据类型 | 两组比较 | 多组比较 |
|---|---|---|
| 正态 + 方差齐 | 独立样本 t 检验 / 配对 t 检验 | one-way ANOVA / 重复测量 ANOVA |
| 非正态或方差不齐 | Mann-Whitney U / Wilcoxon 符号秩 | Kruskal-Wallis / Friedman |
| 分类计数 | 卡方检验 / Fisher 精确检验 | — |

先做正态性检验（scipy.stats.shapiro / normaltest）与方差齐性检验（scipy.stats.levene），再选检验；不要默认 t 检验。

## 常用实现
- t 检验：scipy.stats.ttest_ind / ttest_rel；ANOVA：scipy.stats.f_oneway，或 statsmodels OLS + anova_lm（支持双因素与交互项）
- 非参数：mannwhitneyu / wilcoxon / kruskal / friedmanchisquare
- 多重比较校正：statsmodels.stats.multitest.multipletests（组学用 BH-FDR，少量先验假设用 Bonferroni）
- 回归：statsmodels OLS / GLM（报告系数、SE、置信区间、p 值）
- 生存分析：statsmodels.duration.hazard_regression（Cox）或 R survival 包（Kaplan-Meier + log-rank、coxph）
- 功效分析：statsmodels.stats.power（tt_ind_solve_power 等），实验设计阶段估算样本量

## 报告规范
- 同时报告效应量（Cohen's d、η²、r）与 p 值；p 值给实际数值（如 p=0.003，而非 p<0.05）
- 说明检验假设是否满足；不满足时说明替代方案
- 组学数据（RNA-seq / 蛋白组）默认 FDR 校正，注明阈值（如 padj<0.05 且 |log2FC|>1）
- 每个图标注统计检验方法与显著性标记（* p<0.05, ** p<0.01, *** p<0.001）

## 常见陷阱
- 多重比较不校正；把相关当因果；忽略重复测量相关性；只报告显著结果（p-hacking）
- 数据清洗先行：缺失值处理、异常值用客观方法（Grubbs / MAD）而非主观剔除、单位统一

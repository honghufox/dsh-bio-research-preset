---
name: scientific-plotting
description: 发表级科研绘图：matplotlib/seaborn 规范（尺寸、字体、DPI、色盲友好配色），柱状/箱线/小提琴/散点/火山图/热图/生存曲线等生物学常见图型。
whenToUse: 绘制论文图表、制作 figures、调整图表样式时
---

# 科研绘图（Publication-Quality Figures）

## 基线规范（matplotlib）
- 单栏图宽 3.5 in，双栏 7 in；高度按内容 2.5–5 in；输出 dpi=300（PNG/TIFF），矢量优先存 SVG/PDF
- 字体：Arial / Helvetica 或 Times；字号 7–9 pt（多数期刊要求 6–10 pt）；数学符号用 mathtext
- 去图表垃圾：默认关闭 top/right 边框（ax.spines），网格浅色虚线可选
- 颜色：色盲友好（Okabe-Ito 或 seaborn colorblind 调色板）；不用红绿对比表达关键差异

## rcParams 推荐模板（写在脚本开头）
```python
import matplotlib as mpl
mpl.rcParams.update({
    'figure.dpi': 300, 'savefig.dpi': 300,
    'font.family': 'sans-serif', 'font.sans-serif': ['Arial'],
    'font.size': 8, 'axes.labelsize': 8, 'axes.titlesize': 9,
    'xtick.labelsize': 7, 'ytick.labelsize': 7,
    'axes.linewidth': 0.8, 'lines.linewidth': 1.2,
    'legend.fontsize': 7, 'svg.fonttype': 'none',
})
```

## 生物学常见图型
- 柱状图 + 误差棒：seaborn.barplot + errorbar（注明 SEM 或 SD）；叠加散点（swarm/strip）优于纯柱状
- 箱线 / 小提琴：seaborn.boxplot / violinplot，配合显著性标注
- 散点 + 回归：seaborn.regplot；报告 Pearson/Spearman r 与 p
- 火山图：log2FC vs -log10(padj)，阈值线 + 按阈值着色高亮显著基因（matplotlib scatter）
- 热图：seaborn.clustermap（带层次聚类）或 heatmap + 行列注释（基因/样本）；Z-score 标准化需注明
- 生存曲线：R survival + survminer（ggsurvplot）或 Python lifelines；标注 log-rank p 与中位生存时间
- 多面板：plt.subplots / GridSpec；统一图例、轴范围与配色
- 序列相关：序列 logo 用 R ggseqlogo 或 Python logomaker；比对图见 bioinformatics 技能

## 中文支持
- matplotlib 默认无中文字体：设 rcParams['font.sans-serif']=['Microsoft YaHei','SimHei']，并设 axes.unicode_minus=False
- 投稿期刊大多要求英文标签：图中文字一律英文，中文只用于说明文字

## 输出与交付
- 存到工作区 figures/ 目录；同时交付可复现脚本
- 交付时说明：图类型、统计方法、样本量、误差棒含义、软件与版本

---
name: variant-analysis
description: VCF 变异数据处理、过滤、注释与可视化：vcfpy/vcfR 读写、变异过滤规范（QUAL/DP/VAF/gnomAD）、biomaRt 注释、染色体分布/类型统计/样本比较等图表。
whenToUse: 处理 VCF 文件（变异调用结果）、变异过滤、注释、比较样本、绘制变异分布图时
---

# VCF 变异数据分析与可视化

## 环境
- Python：vcfpy 0.14 已装（from vcfpy import Reader, Writer, Header）
- R：vcfR 已装（read.vcfR / chromoR / vcfR 可视化族）
- 注释查询：R biomaRt（Ensembl，需网络；DSH 沙箱内联网受限时用 web 工具或让用户终端执行）
- 说明：本机不处理 BAM/FASTQ 原始数据（samtools/pysam 未装）；VCF 是"处理完成"的变异结果文件，以下流程都从 VCF 开始

## VCF 字段速记
- `#CHROM POS ID REF ALT`：位置与等位基因；`QUAL` 质量分；`FILTER` 过滤标记（PASS 表示通过）
- `INFO` 信息字段：`DP`（深度）、`AF`（等位频率）、`AC/AN`（等位计数/总数）、`SVTYPE`（结构变异）
- `FORMAT` + 样本列：`GT`（基因型 0/1、1/1）、`AD`（各等位 reads 数）、`DP`（样本深度）、`GQ`（基因型质量）
- 变异类型：SNV（单碱基替换）、MNV、InDel（插入/缺失）、SV（结构变异）

## 读取与基本统计
```python
from vcfpy import Reader
r = Reader.from_path('input.vcf')
for rec in r:                      # 每条记录
    chrom, pos, ref, alt = rec.CHROM, rec.POS, rec.REF, rec.ALT[0].value
    qual = rec.QUAL
    dp = rec.INFO.get('DP')
r.close()
```
```r
library(vcfR)
vcf <- read.vcfR('input.vcf')
vcf@meta; vcf@fix; vcf@gt          # 元信息 / 变异表 / 基因型
getFIX(vcf)                        # CHROM POS REF ALT 等
```

## 过滤规范（写论文必须交代）
常用过滤组合（按研究需要取用，报告时说明阈值）：
- 质量：`QUAL >= 30` 且 `FILTER == PASS`
- 深度：`DP >= 10`（低深度易假阳性）
- 等位频率：`VAF/AF >= 0.2`（体细胞）或 0.3–0.4（胚系杂合）；纯合要求 VAF 接近 1
- 种群频率（胚系）：gnomAD 频率 < 0.01（罕见变异）或 < 0.05（根据研究目的）；用 biomaRt 或 gnomAD 网页查询
- 过滤前后都要报告变异数量（"从 N 个过滤到 M 个，条件为..."）

## 注释（把变异变成生物学意义）
- R biomaRt：按 rsID/位置查 Ensembl 基因、变异效应（同义/非同义/剪接位点）、ClinVar 致病性
```r
library(biomaRt)
snp <- useEnsembl(biomart = "snps", dataset = "hsapiens_snp")
getBM(attributes = c("refsnp_id","chrom_start","clinical_significance","consequence_type_tv"),
      filters = "snp_filter", values = rs_ids, mart = snp)
```
- 概念：`consequence_type`（missense/nonsense/splice/frameshift）、`sift/polyphen` 功能预测、`clinvar_clnsig`（致病性分级）
- 批量注释重型需求（VEP/ANNOVAR）建议在 Linux 服务器跑，本机不装

## 可视化（本机重点）
```r
# 染色体变异分布图（全基因组鸟瞰）
chromoR(chrom, pos, dp = depth)          # vcfR::chromoR 基础版
chromoqc(vcf)                            # 变异质量/深度 QC 图
# 变异类型统计（SNV/InDel 比例）— 提取 REF/ALT 长度差分类后用 ggplot2 柱状图
# 转换/颠换（Ti/Tv）比例 — 常见质控指标，~2.0（人类 WGS）
```
- Python/matplotlib：染色体分布散点/直方图、每样本变异数柱状图、VAF 分布直方图、`UpSet/Venn` 比较样本共有变异（matplotlib-venn 未装时用 R `VennDiagram`/`eulerr`）
- 多样本比较：按样本 GT 分组统计（0/0、0/1、1/1）堆叠条形图；共享/特有变异 UpSet 图

## 常见分析任务模板
1. 给定 VCF + 样本表 → 过滤 → 每个样本的变异总数/类型分布 → 组间比较（卡方/Fisher，见 biostatistics 技能）
2. 已知基因列表 → 从 VCF 提取这些基因区域的变异（按 CHROM+POS 与基因坐标匹配）→ 注释 → 表格交付
3. 变异与表型关联 → 携带/不携带变异两组 → 组间统计或生存分析（见 survival-analysis 技能）

## 可复现规范
- 交付时写明：VCF 来源与版本、参考基因组（hg19/hg38）、过滤阈值与过滤前后数量、注释工具与数据库版本、软件版本（sessionInfo）
- 结果表格：chr:pos | rsID | gene | consequence | VAF | gnomAD_AF | ClinVar | 样本基因型

---
name: bioinformatics
description: 常用生信分析流程：序列获取与检索（NCBI/UniProt）、BLAST、多序列比对、系统发育树、ORF 预测、GC 含量、蛋白特性分析、RNA 二级结构；本地 Biopython 与 R Bioconductor 用法。
whenToUse: 做序列分析、比对、BLAST、系统发育、差异表达等生信任务时
---

# 生信分析

## 环境
- Python Biopython 1.88 已装（from Bio import SeqIO, Entrez, Align, Phylo）
- R 4.5 可用；Bioconductor 包按需安装（BiocManager::install）
- biotools MCP 提供 37 个现成工具（`mcp__biotools__` 前缀），优先复用

## 常用流程

### 1. 序列获取与检索
- 蛋白：`mcp__biotools__search_uniprot(query)` / `get_protein_entry(accession)` / `get_protein_sequence`
- 核酸：`mcp__biotools__get_nucleotide_sequence`（GenBank/RefSeq）
- 基因/基因组：NCBI Datasets 相关工具；批量检索用 Biopython Entrez（必须先设 `Entrez.email="user@example.com"`）

### 2. 基础序列分析
- GC 含量/组成：`mcp__biotools__analyze_gc_content`
- 限制酶切位点：`mcp__biotools__find_restriction_sites`
- ORF 预测：`mcp__biotools__predict_orfs`；或 Biopython：`Seq("...").translate()`
- 蛋白特性（分子量/等电点/疏水性）：`mcp__biotools__predict_protein_properties`；跨膜区 `predict_transmembrane_regions`；基序 `scan_protein_motifs`

### 3. 比对与 BLAST
- BLAST：`mcp__biotools__blast_search`
- 多序列比对：`mcp__biotools__multiple_sequence_alignment`；保守区 `highlight_conserved_regions`；序列 logo `generate_sequence_logo`
- 双序列比对：`align_sequences_global` / `align_sequences_local`

### 4. 系统发育
- 构建树：`mcp__biotools__build_phylogenetic_tree(sequences, method="neighbor-joining", bootstrap_replicates)`
- 比较树：`mcp__biotools__compare_phylogenetic_trees`
- 本地：Biopython Phylo + 外部软件（MEGA/RAxML 需另行安装，先与用户确认）

### 5. RNA 与结构
- RNA 二级结构预测：`mcp__biotools__predict_rna_secondary_structure`；RNA 基序 `scan_rna_motifs`
- 蛋白结构：`mcp__biotools__get_protein_structure`（PDB）
- 通路：`mcp__biotools__get_pathway_data`（KEGG/Reactome）

### 6. 组学（转录组）流程参考
- 定量：Salmon / STAR（需安装）；差异表达：R DESeq2 / edgeR（Bioconductor）
- 流水线：QC（fastqc/multiQC）→ 比对 → 定量 → 差异 → 富集（clusterProfiler，GO/KEGG）
- 本机未装这些工具时，先与用户确认是否安装或改用公共服务器

## 可复现规范
- 记录软件版本（R `sessionInfo()` 或 `pip freeze` 子集）
- 保存：输入序列文件、参数、脚本、输出；每个分析给一句话方法与版本说明
- 引用：NCBI 数据用 accession；软件引用官方文献；MCP 工具结果标注来源数据库

---
name: literature-review
description: 文献检索与综述：PubMed 检索策略（MeSH/布尔/字段标签）、biotools MCP 检索工具使用、去重筛选、证据表整理、系统综述流程。
whenToUse: 检索文献、查证引用、整理综述、做系统综述时
---

# 文献检索与综述

## 检索工具（按优先级）
1. biotools MCP（本预设已挂载，工具名前缀 `mcp__biotools__`）：
   - `mcp__biotools__search_pubmed(term, max_results)` — PubMed 检索
   - `mcp__biotools__get_publication_details(pmid)` — 完整元数据（标题/作者/期刊/年份/DOI/摘要）
   - `mcp__biotools__get_publication_abstract(pmid)` — 摘要
2. web_search 兜底：Google Scholar 线索、预印本 bioRxiv、机构页面
3. 需要批量/高级检索（MeSH、日期范围）时用 NCBI E-utilities：
   `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=<URL编码检索式>`
   （通过 web 工具或 node fetch 调用，注意遵守 NCBI 限速并附 email）

## 检索策略
- 拆解主题为 PICO 或概念组：每个概念收集同义词（如 "CRISPR" AND ("gene editing" OR "genome editing")）
- 用字段标签提高精度：[tiab]（标题/摘要）、[au]（作者）、[pt]（文献类型）、[dp]（日期）
- MeSH 词（PubMed "MeSH Terms" 过滤）提高召回；配合布尔 AND / OR / NOT
- 记录检索式与检索日期（可复现综述必需）；常见问题：同义词不全导致漏检、检索式过宽导致噪音

## 筛选与整理
- 去重：按 PMID/DOI；跨库检索（PubMed + Web of Science）时注意
- 两级筛选：标题/摘要初筛 → 全文复筛；记录排除原因（PRISMA 风格流程图）
- 证据表字段建议：作者年份 | 研究类型 | 样本/模型 | 主要结果 | 结论 | 局限 | PMID
- 引用核实：任何写进论文的文献，用 PMID 回查确认作者、年份、卷期页码正确

## 综述写作
- 按主题而非时间组织；每个主题段：已确立结论 → 争议 → 缺口
- 引用密度适中、避免堆砌；直接引用数据时注明页码/图表
- 配图：研究进展时间线、机制示意图（draw.io 或 matplotlib 示意）

---
name: literature-review
description: 文献检索与综述：PubMed 检索策略（MeSH/布尔/字段标签）、biotools MCP 检索工具使用、去重筛选、证据表整理、系统综述流程。
whenToUse: 检索文献、查证引用、整理综述、做系统综述时
---

# 文献检索与综述

## 检索工具（按优先级）
1. biotools MCP（工具名前缀 `mcp__biotools__`）：`search_pubmed` / `get_publication_details` / `get_publication_abstract`
2. pubmed MCP（`mcp__pubmed__`，12 工具）：`pubmed_search_articles` 检索、`pubmed_fetch_fulltext` 取全文（PMC→Europe PMC→Unpaywall）、`pubmed_format_citations` 出 APA/MLA/BibTeX/RIS/Vancouver、`pubmed_fetch_articles` 的 notices 查撤稿/更正、`pubmed_convert_ids` 换 ID、`pubmed_lookup_mesh` 查主题词
3. web_search 兜底：预印本 bioRxiv、机构页面、中文库（CNKI/万方需人工登录）
4. 批量/高级检索（MeSH、日期范围）：NCBI E-utilities `esearch.fcgi` / `esummary.fcgi`（ncbi MCP 已封装），遵守限速并附 email

## 检索策略
- 拆解主题为 PICO 或概念组：每个概念收集同义词（如 "CRISPR" AND ("gene editing" OR "genome editing")）
- 用字段标签提高精度：[tiab]（标题/摘要）、[au]（作者）、[pt]（文献类型）、[dp]（日期）
- MeSH 词（PubMed "MeSH Terms" 过滤）提高召回；配合布尔 AND / OR / NOT
- 记录检索式与检索日期（可复现综述必需）；常见问题：同义词不全导致漏检、检索式过宽导致噪音

## 筛选与整理
- 去重：按 PMID/DOI；跨库检索（PubMed + Web of Science）时注意
- 两级筛选：标题/摘要初筛 → 全文复筛；记录排除原因（PRISMA 风格流程图）
- 证据表字段建议：作者年份 | 研究类型 | 样本/模型 | 主要结果 | 结论 | 局限 | PMID
- 引用核实：任何写进论文的文献，用 PMID 回查确认作者、年份、卷期页码正确；定稿前跑 `reference-integrity` 的 `verify_refs.py`（存在性 + 撤稿/勘误），再人工确认"文献结论支持这句话"（审稿人最常查的就是这条）
- 中文文献（GB/T 7714、无 DOI）Crossref 覆盖不全：`NOT_FOUND` 不等于造假，需人工在 CNKI/万方/期刊官网复核，报告里要区分"无法自动核验"与"确认不存在"

## 综述写作
- 按主题而非时间组织；每个主题段：已确立结论 → 争议 → 缺口
- 引用密度适中、避免堆砌；直接引用数据时注明页码/图表
- 配图：研究进展时间线、机制示意图（draw.io 或 matplotlib 示意）

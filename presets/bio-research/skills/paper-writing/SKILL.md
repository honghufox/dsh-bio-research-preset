---
name: paper-writing
description: 科研论文写作与投稿全流程：写作 brief 与期刊选择、IMRaD 逐节写法、标题/摘要/highlights、学术英语润色、统计与图表报告规范（ARRIVE/CONSORT/STROBE/PRISMA/MIQE）、参考文献真实性、数据与代码可得性、CRediT 与 AI 使用声明、cover letter 与返修回复。起草、改写、润色、投稿论文时使用。
whenToUse: 写或改论文任一部分、写摘要/标题/cover letter/返修信、按期刊要求体检稿件时
---

# 论文撰写

> 多人/多 agent 并行写整篇（分节起草 + 独立审稿 + 裁决）时，先读 `writing-team` 技能；这里只管"一篇稿子该怎么写对"。
> 审别人的稿、模拟审稿、写 decision letter 用 `manuscript-review`。

## 0. 动笔前先定 6 件事（写不出来通常是这里没定）

先产出 `manuscript-brief.md`（半页即可），再写正文：

| 项 | 要求 | 反例 |
| --- | --- | --- |
| 一句话研究问题 | ≤ 25 字，含对象+变量+结局 | "研究基因表达" |
| 主结论（primary claim） | 一句可被证据证伪的话 | "结果具有重要意义" |
| 证据链 | claim → 图/表 → 统计量 → n | 只有图，说不出效应量 |
| 目标期刊 | 具体到刊名 + article type | "投个一区" |
| 报告规范 | EQUATOR 里对应的那条 | 动物实验不写 ARRIVE |
| 作者与贡献 | CRediT 分工 + 通讯作者 | 投稿前才吵署名 |

**主结论只能有一个。** 第二个结论要么降级为次要发现（Results 里一句），要么另写一篇。

## 1. 期刊选择：先 scope 后指标

按顺序筛，别反过来：

1. **Scope 匹配**：近 24 个月该刊发过 ≥2 篇同主题文章（用 PubMed `"<journal>"[journal] AND <topic>` 验证）。
2. **Article type 与硬限制**：正文词数、图/表数、参考文献上限、摘要是否结构化、是否需要 highlights/graphical abstract。
3. **政策**：OA/APC、预印本是否允许、数据与代码必须存哪个库、图像完整性审查、AI 使用披露方式、reporting guideline 强制项。
4. **流程**：平均审稿周期、是否 transfer 机制、是否接受 registered report。
5. **风险**：掠夺性期刊特征（假影响因子、几天接收、邮件约稿、无编委名单）。查 DOAJ / 期刊官网编委会。

把以上写成 `target-journal.md`（1 页），投稿前逐条打勾。

## 2. 标题与摘要

**标题**：`<关键发现/机制> + <对象/体系> + <方法或角度>`，10–15 词。
- 用具体名词和动词，不用 "Study on / Investigation of"。
- 不用 "Novel / First / Significantly" 自我评价。
- 避免疑问句标题（除 Perspective 类）。
- 缩写只在标题里必须时使用。

**摘要**（250–300 词，除非期刊另有限制）：
1. 背景 1–2 句（只写与本文结论直接相关的 gap）
2. 方法 1–2 句（体系、n、关键手段）
3. 结果 2–4 句，**每句带数值**（效应量 + 方向 + 显著性 + n）
4. 结论 1 句（可推广边界写清楚，不要超设计）

摘要里出现但与正文对不上的数字，是最常见的退稿理由之一：摘要定稿后**从正文重新核对每个数字**。

**Highlights / Graphical abstract**：3–5 条，每条 ≤ 85 字符，动词开头，写"发现了什么"而不是"我们研究了什么"。

## 3. IMRaD 逐节写法

### Introduction（4 段，约 500–700 词）
1. 领域共识（只引用权威综述/关键原始文献）
2. 具体 gap（前人做到哪、缺什么，必须有引用支撑）
3. 本研究做了什么（一句假设 + 一句策略）
4. 主要发现预告（1–2 句，可与摘要结论呼应但不复制）

反例：从教科书第一句讲起；gap 靠"尚未见报道"而不是引证；Introduction 里出现 Results 的细节。

### Methods（可复现优先，8 项自检）
- 材料/试剂/细胞系/品系：来源、货号、**RRID**、批号、培养条件
- 实验设计：分组、样本量及其依据（功效分析或先验经验）、重复定义（生物学重复 vs 技术重复）
- 随机化与盲法：怎么随机、谁盲、盲到什么程度
- 仪器与软件：厂商型号 + 软件版本 + 关键参数
- 统计：检验名、双侧/单侧、显著性阈值、多重比较校正方法、缺失值处理、软件版本
- 伦理：批号/批准号、知情同意、动物福利
- 数据与代码：库名 + 登录号 + DOI
- 任何"按说明书操作"都补一句关键偏离

### Results（图先行，一段一图）
- 每段 = 一个小结论 + 支撑它的数据 + 必要的对照说明；**不解释机制**（留给 Discussion）。
- 段落标题就写结论（"X 缺失导致 Y 下降"），不写"X 的表达分析"。
- 先报效应量与 CI，再报 p；p 只写精确值（P = 0.013，不写 P = 0.000）。
- 阴性结果照写，并给功效说明，不要藏。
- 正文数字与图/表必须一一对应；写完后用 `scripts/` 或手工做一遍数字核对。

### Discussion（6 段）
1. 用一句话重述主要发现（不复制 Results）
2. 与前人结果的一致/冲突（给解释，不回避冲突文献）
3. 机制解释（明确标注是推测）
4. 意义与适用范围
5. 局限（3–5 条，具体到设计层面，不写"样本量有限"这种万能句）
6. 结论与下一步（1 段，不引入新数据、新引用堆砌）

## 4. 学术英语：可执行的规则

**时态**：Methods/Results 用过去时；公认事实与图表指代用现在时；Discussion 里"本研究显示"用过去时、"一般性推论"用现在时。

**语态**：Methods 允许被动（was measured）；Results 用主动更清楚（X increased by 32%）；避免一句里三个被动。

**Hedging 阶梯**（按证据强度选，不要一律用 may）：
`demonstrates > shows > indicates > suggests > is consistent with > may reflect`

**中式表达对照**（左→右）：

| 不要写 | 改写 |
| --- | --- |
| The expression of X was significantly increased | X expression increased by 2.1-fold (P = 0.004) |
| plays an important role in | is required for / contributes to / regulates |
| in order to explore | to test whether |
| has become a hot topic | (删掉，直接写 gap) |
| There are many studies reported that | Previous work showed that (给引用) |
| obviously / significantly (非统计意义) | markedly / substantially |
| we can see from Figure 1 | Figure 1 shows |
| due to the reason that | because |
| more and more | increasingly |
| It is well known that | (删掉或给引用) |

**数字与单位**：SI + 期刊约定；`µM`（不是 uM）、`10⁶ cells/mL`、温度 `37 °C`（带空格）、`h/min/s` 统一；数字与单位间空格；句子开头不用阿拉伯数字。

**术语一致**：建 `style-guide.md` 记：基因/蛋白大小写与斜体规则（人 *GENE* 斜体大写、小鼠 *Gene* 首字母大写斜体、蛋白正体）、缩写全称（首次出现给全称，之后统一用缩写）、同一概念只用一个词（不要 donor/patient/subject 混用）。

## 5. 统计与报告（审稿人最先看这里）

必须报告的：n（并说明是什么重复）、中心趋势与离散度（均值±SD 或中位数[IQR]，说明选了哪个）、效应量 + 95% CI、精确 p、多重比较方法与校正后 p、统计软件与版本、缺失数据量。

常见错误：SD/SEM 混用不说明；只报 p 不报效应量；把技术重复当生物学重复（伪重复）；多组两两 t 检验不做校正；非正态数据用 t 检验；生存分析不检验比例风险假设、不处理竞争风险；相关性当因果；图上的误差棒不写定义。

**n < 3 不画误差棒**；小样本（n ≤ 5）建议同时给个体数据点（dot plot）。

## 6. 报告规范门控（EQUATOR）

按研究类型选，不按学科习惯选：

| 研究类型 | 规范 | 最低要写清 |
| --- | --- | --- |
| 动物实验 | ARRIVE 2.0 | 样本量依据、随机化、盲法、纳入排除、福利与伦理号 |
| 随机对照试验 | CONSORT（最新版） | 流程图、分配隐藏、盲法、主要结局预注册 |
| 观察性研究 | STROBE | 设计、偏倚、样本量、亚组、缺失 |
| 系统综述/Meta | PRISMA 2020 | 检索式与日期、筛选流程图、偏倚评估、异质性 |
| qPCR | MIQE | 引物效率、参考基因、重复、扩增特异性 |
| 测序/组学 | 对应领域规范 | 建库、批次、质控阈值、数据登录号、代码 |

不确定时：EQUATOR Network 网站按"研究类型 + 关键词"查；找不到就按同类高被引论文的 Methods 结构对齐，并在 cover letter 说明。

## 7. 图与表

- 图与绘图脚本、数据放同一目录（`figures/`），脚本可重跑；产物 PNG 300 dpi + 矢量 PDF/SVG。
- 版面：单栏 85 mm、双栏 170 mm 以内；最小字号 ≥ 7 pt（缩放后仍可读）；色盲友好配色（避开红绿对立）。
- 每个 panel 有字母编号 (a)(b)，legend 里逐 panel 说明；误差棒定义、统计标注、n 全部写进 legend。
- legend 模板：`(a) 代表性 Western blot（n = 3 次独立实验）。X 敲低效率以 Y 归一化。(b) 定量结果，均值 ± SD，双因素方差分析 + Tukey 校正；*P < 0.05, **P < 0.01。`
- 表格：不用截图；三线表；单位写进表头；脚注给缩写与统计方法。

## 8. 参考文献：先保真，再谈格式

1. 只引用**读过且真实存在**的文献；写之前先用 `reference-integrity` 技能的 `scripts/verify_refs.py` 验一遍 DOI/PMID（会查 Crossref / PubMed / Europe PMC，并标出撤稿与勘误）。
2. 引用要"支持这句话"：审稿人常查的是引用与 claim 对不对得上，而不是格式。每段的关键断言逐条回看原文结论。
3. 优先引原始研究 + 权威综述；避免引预印本支撑核心结论（必须引时明确标注 preprint）。
4. 撤稿文献：不得作为正面证据引用；若必须讨论，注明 "retracted"。
5. 格式：Vancouver（生物医学常用，序号按出现顺序）、APA、Nature 风格按目标刊；用 Zotero + Better BibTeX 导出时固定 citation key 规则，避免返修期重排。
6. 自引 ≤ 合理比例；同一结论不要堆 5 篇同组文章。

## 9. 数据、代码、材料与声明

- **数据**：GEO（表达谱/芯片/测序）、SRA/ENA（原始 reads）、PRIDE/ProteomeXchange（蛋白）、MetaboLights（代谢）、Figshare/Zenodo（其他与代码）；给登录号，审稿期给匿名访问链接。
- **代码**：仓库 + release tag + Zenodo DOI；附 `README`（环境、一行运行命令、输入输出）；不只给"可索取"。
- **材料**：质粒/菌株/细胞系给来源与 RRID；有 MTA 限制就明说。
- **声明**：基金号、利益冲突、伦理批准号、知情同意、作者贡献（CRediT 14 类：Conceptualization, Data curation, Formal analysis, Funding acquisition, Investigation, Methodology, Project administration, Resources, Software, Supervision, Validation, Visualization, Writing – original draft, Writing – review & editing）。
- **AI 使用声明**：按目标刊政策写（ICMJE §V：AI 不得署名、参与处理稿件可能违反保密、须披露；Elsevier：投稿时须声明，且不允许把审稿稿件上传到 AI 工具；Springer Nature 用绿/琥珀/红分级，"把评审委托给 LLM"属红色禁止）。通常放 Methods 或 Acknowledgements，说明工具名/版本/用途（语言润色、代码辅助、文献整理）+ "作者对全文内容负责"；AI 不能列为作者；不得把未公开稿件/审稿内容上传到无授权服务。**不要生成式 AI 造图**（多数期刊禁止或要求声明原始数据来源）。

## 10. 投稿包（一次备齐，避免被退回）

- [ ] 正文（含图 legends、表）
- [ ] 图（按刊要求的分辨率与格式，单独文件 + 合成图）
- [ ] Cover letter（1 页：研究问题与主要发现 3 句、为何适合该刊 2 句、声明未一稿多投/全体作者同意/无利益冲突）
- [ ] Highlights / graphical abstract（若要求）
- [ ] 推荐审稿人 3–5 位（避开近 5 年合作者与同机构）
- [ ] 报告规范 checklist（ARRIVE/CONSORT/…）
- [ ] 数据与代码可得性声明 + 登录号
- [ ] 作者贡献、COI、基金、伦理
- [ ] 文字相似度自查（综述段落尤其）
- [ ] 投稿系统里所有作者信息、ORCID、顺序与通讯作者一致

## 11. 返修（Response to Reviewers）

结构：`总述（感谢 + 主要改动摘要）→ 逐条回复`。每条：

```
Reviewer #1, Comment 3:
"作者声称 X，但 Figure 2 缺少对照。"

Response: 我们同意。已在 Figure 2c 增加 Y 对照（n = 3 独立实验），
结果为 ...。相应修改见正文第 2 页第 3 段与 Figure 2 图注。
```

规则：
- 每条都回，**编号与原文一致**；引用改后稿件的位置（页码/行号/图号）。
- 不同意时：先复述审稿人的关切，再给证据（新数据、文献、方法限制），语气不对抗；不要用"审稿人误解了"。
- 改动必须落到稿子里，不能只在回复信里解释。
- 返修稿用高亮或 tracked changes 标出改动（按刊要求）。
- 回复信本身也要过一遍：数字与正文一致、没有新引入未验证的引用。

## 12. 本机交付链路（已实测）

- Markdown → Word/PDF：`pandoc`（在 PATH 上）。中文 PDF 需 `-V CJKmainfont="Microsoft YaHei"`。
- LaTeX：TinyTeX（在 PATH 上，含 ctex/xeCJK），需要模板时用 `latex-compile` 技能。
- 文档交付：`document-output` 技能（docx/pptx 规范与校验）。
- 图：`scientific-plotting` 技能；Tavotto MCP 做出版前版式微调与矢量导出。
- 不要引用不存在的盘符/路径；R 未加入 PATH（用全路径 `C:\Program Files\R\R-4.6.0\bin\Rscript.exe`）。

## 13. 交稿前终检（12 项，全过再投）

1. 摘要与正文每个数字一致（跑 `writing-team/scripts/lint_manuscript.py` 做机械核对） 2. 主结论只出现一次且被证据链支撑 3. 每个图在正文被引用且顺序正确 4. 每个缩写首次出现有全称 5. 术语/基因命名全文统一 6. 统计报告含 n、效应量、CI、校正、软件版本 7. 报告规范清单逐项有落点 8. 参考文献全部真实且支持对应 claim（跑过 verify_refs） 9. 数据/代码登录号可访问 10. 声明齐（伦理、COI、基金、CRediT、AI） 11. 图分辨率/尺寸/字号符合刊规 12. 作者信息与投稿系统一致

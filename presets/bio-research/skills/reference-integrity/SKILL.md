---
name: reference-integrity
description: 参考文献真实性校验：批量核查 DOI/PMID 是否真实存在、是否被撤稿或勘误，输出 TSV/JSON 报告并给出需人工复核的条目。
whenToUse: 定稿前核实引用、审稿怀疑引用造假、投稿前做引用体检、被编辑质疑引用不实时
---

# 参考文献真实性与撤稿校验

引用"看起来像真的"和"真的存在"是两件事。本技能用一个只依赖 Python 标准库的脚本，把稿子里所有
DOI/PMID 过一遍 Crossref、PubMed、Europe PMC，一次性回答：**存在吗？被撤稿了吗？有勘误/关注声明吗？**
"引用内容与 claim 是否一致"留给人工复核（见下文）。

## 何时用
- **定稿前**：`refs.bib` 整体跑一遍，先筛掉"查无此文"的引用（多为作者凭记忆手写 DOI）
- **审稿**：怀疑堆砌/编造引文时先做存在性筛查，再抽查关键引用的数值与结论方向
- **投稿前**：确认没有引用已撤稿文献（尤其是方法学引用、安全性结论引用）
- **被质询时**：逐条给出 DOI 解析结果与元数据作为举证材料（报告可直接贴进回复）

## 快速开始

```powershell
cd "<bundle>\presets\bio-research\skills\reference-integrity"   # <bundle> = 本预设 bundle 的安装目录

python scripts\verify_refs.py --input refs.bib --out ref_report.tsv --json ref_report.json  # 整份 bib
python scripts\verify_refs.py --input refs.txt --out ref_report.tsv                        # 纯文本/CSV
python scripts\verify_refs.py --doi 10.1038/s41586-020-2649-2 --pmid 32075877              # 临时核对（可重复）
python scripts\verify_refs.py --text "见 10.1038/s41586-020-2649-2 与 PMID: 32075877"       # 段落内嵌
```

> **PowerShell 陷阱**：`--doi 10.1016/S0140-6736(97)11096-0` 不加引号会被拆成三段并报
> `unrecognized arguments`。含括号的 DOI 必须用单引号（从文件读入没有这个问题）。

常用选项：`--json` 额外产出机器可读报告；`--no-europepmc` 只查 Crossref+PubMed（更快）；
`--skip-unidentified` 跳过 .bib 里无 DOI/PMID 的条目；`--interval`/`--timeout`/`--retries`
控制节流重试；`--use-proxy` 见代理一节；`--limit N` 只查前 N 条。

## 没有 DOI/PMID 的引用：`--bibliographic`

GB/T 7714、中文期刊、书籍章节、报告常常**只有作者-题目-期刊-年份，没有 DOI/PMID**。加
`--bibliographic` 后脚本会：从每行解析出题目/期刊/年份 → **先按题目精确检索**
（Crossref `query.title`，取前 5 条）→ 若最佳候选置信度不足 0.80，再退化为
`query.bibliographic`（题目+期刊+年份）合并候选 → 用题目相似度（difflib + 词级 Jaccard，
含"候选题目被完整包含"加分）与年份差判定。

```powershell
python scripts\verify_refs.py --input "_used_in_review.md" --bibliographic --out ref_report.tsv
python scripts\verify_refs.py --input refs.md --bibliographic --limit 30 --out spot_check.tsv  # 先抽查 30 条
```

判定规则与新增列：

| 判定 | 条件 | 含义与动作 |
| --- | --- | --- |
| `MATCHED` | 相似度 ≥ 0.80 且年份差 ≤ 1 | 视为同一篇，`resolved_doi` 可直接用；仍需人工核内容 |
| `AMBIGUOUS` | 相似度 0.60–0.80 | 疑似同一篇，必须人工确认（可能标题被改/年份错/评论文章） |
| `NOT_FOUND` | 相似度 < 0.60 或 Crossref 无候选 | **不等于造假**，先按「人工核验路径」处理 |

新增 4 列：`match_confidence`（0–1，年份不符会扣分）、`matched_title`、`matched_journal`、
`matched_year`。原有列语义不变：`title`/`journal`/`year` 放**引用里解析出的**值，
`matched_*` 放 Crossref 候选的值，两列对照即可发现"引用元数据写错"。
`flags` 里的 `journal-mismatch:ref=...,matched=...` 就是题目一致但期刊不同（常见于译文/再发表版）。

> 注意：书目检索一次请求一条，比 DOI 精确校验慢；165 条约 5 分钟。先用 `--limit 30` 抽查。

## 报告怎么读

`--out` 默认写 `ref_report.tsv`（UTF-8 BOM，Excel 直接打开不乱码），列固定为：

| 列 | 含义 / 取值 |
| --- | --- |
| `input` | 原始输入（DOI、PMID、bib 条目键或整条引用文本） |
| `kind` | `doi` / `pmid` / `bibliographic` / `bib-no-id` / `invalid` |
| `resolved_doi` | 解析到的规范 DOI（Crossref 的大小写可能与输入不同；PMID 条目会自动补 DOI） |
| `pmid` | 解析到的 PMID（DOI 条目会自动补 PMID） |
| `title`/`journal`/`year`/`first_author` | 元数据；`--bibliographic` 下是**从引用里解析出的**值 |
| `exists` | `yes` / `MATCHED` / `AMBIGUOUS` / `NOT_FOUND` / `ERROR:<reason>` |
| `retracted` | `yes` / `no` / `unknown`（unknown = 所有来源都没查成） |
| `corrected` | `yes` / `no` / `unknown`（勘误、更正、再发表） |
| `flags` | `;` 分隔的证据链 |
| `match_confidence`/`matched_title`/`matched_journal`/`matched_year` | 仅 `--bibliographic` 有值：候选的置信度与元数据 |

**必须先看的四种行**：`exists=NOT_FOUND`（查无此文）、`retracted=yes`（已撤稿）、
`exists=ERROR:*`（没查成，不能当成"没问题"）、`flags` 含 `pmid-mismatch`（bib 里的 PMID 与 DOI 对不上）。
`flags` 常见取值：

- 撤稿证据：`retracted:crossref(Retraction@2010)`、`retracted:europepmc(pubtype=Retracted Publication)`、
  `retracted:europepmc(retraction in)`、`retracted:crossref-title-prefix` + `title-prefixed-RETRACTED`
- 勘误/关注：`corrected:crossref(Correction@2004)`、`eoc:europepmc(expression of concern in)`
- `this-doi-is-retraction-notice:<原文DOI>`：这条记录本身是撤稿声明，不是被撤稿的原文
- `pmid-mismatch:bib=...,resolved=...`；`duplicate-input`（同一文献重复引用）
- `no-doi-or-pmid-in-bib-entry`：无法自动校验，必须人工补标识
- 书目匹配：`cjk-reference`、`crossref-coverage-limited`（中文文献 Crossref 覆盖不足）、
  `possibly-unindexed`（Crossref 完全无候选）、`low-similarity:0.34`（有候选但都不像）、
  `manual-check-required`（AMBIGUOUS）、`year-offset:2`、`journal-mismatch:ref=...,matched=...`
- `crossref-miss;epmc-resolved`：Crossref 无但 Europe PMC 有（非 Crossref 注册机构常见）
- `crossref-error:timeout` / `europepmc-error:http-503`：来源侧失败，不是文献不存在

## 退出码（可做投稿门禁）

- `0`：所有条目 `exists=yes` 或 `MATCHED`，且无 `retracted=yes` —— 体检通过，可在投稿脚本里放行
- `1`：出现 `NOT_FOUND`、`AMBIGUOUS`、`ERROR:*`、`retracted=yes` 或无可识别标识 —— 门禁拦截，需人工处理

## Windows 代理陷阱（本预设已多次踩到）

本机注册表代理（`HKCU\...\Internet Settings`）会把 `https://` 请求导向一个 **HTTP 代理端口**，
表现为全量超时或 `SSL: WRONG_VERSION_NUMBER`。脚本默认**强制直连**：进程内设 `no_proxy=*`/
`NO_PROXY=*`、清掉 `http(s)_proxy`、给 urllib 用空 `ProxyHandler({})` 的 opener，绕开注册表代理；
需要走代理时加 `--use-proxy` 恢复系统/环境代理行为。

已实测：`https_proxy` 指向死端口 `127.0.0.1:9` 时默认模式仍成功；加 `--use-proxy` 才失败，
并在报告里写 `ERROR:connection-refused`（脚本不崩、退出码 1）。

## 人工复核：引用内容与 claim 是否一致

脚本只能证明"这篇文献存在且没被撤稿"，**不能证明作者没曲解它**。对关键位置逐条人工过：

1. **打开原文**（用报告里的 `resolved_doi`/`pmid` 进出版社或 PubMed），读摘要+结论段，确认方向、
   效应量、研究类型（RCT？动物？体外？综述？）与稿中表述一致
2. **核对数字**：稿中"降低 30%"之类必须能在原文结果里找到同一个数字，而不是二手转述
3. **核对引用类型**：综述/评论/撤稿声明不能当"原始研究证据"引用；看到
   `this-doi-is-retraction-notice` 尤其要当心
4. **核对版本**：预印本（bioRxiv/medRxiv `10.1101/...`）与正式版是两条记录，结论可能已改；
   `corrected=yes` 的必须用勘误后的版本

经验：`exists=yes` 但"结论被夸大"的比例往往比"查无此文"更高，第 1 步不能省。

## 人工核验路径（GB/T 7714 / 中文文献）

**`NOT_FOUND` 不等于造假。** 中文期刊大量没有 DOI、未注册 Crossref，脚本没有可查的入口。
报告里用三处区分"无法自动核验"和"确实查不到"：

| 报告信号 | 含义 | 该怎么做 |
| --- | --- | --- |
| `flags=cjk-reference;crossref-coverage-limited` 或 `possibly-unindexed` | **无法自动核验**（Crossref 没有这条中文文献） | 走下面的中文库核验，不要报"造假" |
| `flags=low-similarity:0.34`（有候选但都不像） | 有相近文献但**元数据对不上**，可能是题目/年份/期刊写错 | 核对原刊页面，改正后重跑 |
| 精确 DOI/PMID 查询 `flags=not-found-in:crossref+epmc` | 标识符本身不存在（可能是编造或抄错） | 优先怀疑引用造假或 DOI 抄错 |
| 汇总行 `未找到 N 条 = 无法自动核验 a + 有候选但元数据不符 b + 确认不存在 c` | 直接给出三类分布 | 按分布分配人工工作量 |

中文文献人工核验顺序（每条约 1–2 分钟）：

1. **CNKI / 万方**：按"作者 + 题目 + 年份"检索，能检索到且卷期页码一致 → 记录 CNKI 链接作为举证
2. **期刊官网/知网空间**：核对卷期页码与引用是否一致（中文期刊常见"年,卷:页"格式错误）
3. **万方/维普英文版或 PubMed**：少数中文期刊被 MEDLINE 收录，可用 `--pmid` 复核
4. **书/报告**：ISBN 或出版社官网核对（如"中国居民营养与慢性病状况报告（2020年）"）
5. 三步都查不到 → 才按"疑似不实引用"处理，并把检索日期与截图留档

## 常见陷阱

- **DOI 大小写与尾部标点**：正文里 `10.xxx/yyy.` 带句号或全角句号会查不到；脚本会自动 trim 尾部标点并
  从中文文本中截断，但仍建议从 bib/PDF 复制完整 DOI
- **预印本 vs 正式版**：两个 DOI，引用预印本必须在文中标注
- **撤稿/勘误/关注声明**：撤稿后原文页面仍能打开，Crossref 只在 `updated-by` 里挂声明，
  必须看 `retracted`/`corrected` 而不是"能不能打开"
- **PMID 张冠李戴**：作者常把 PMID 写成同主题另一篇；脚本对 bib 里同时给了 DOI+PMID 的条目做交叉校验
- ** predatory 期刊**：能解析 DOI 不代表期刊可信，`journal` 列需配合 JCR/DOAJ 人工判断
- **中文期刊无 DOI**：Crossref 覆盖不足，`NOT_FOUND` 多为"未收录"，按上一节人工核验；
  不要因为脚本没查到就判定作者造假
- **译文/再发表**：同一题目可能先发中文期刊、再发英文刊，`journal-mismatch` 标记提示这种情况
- **重复引用/非文献标识**：换键重复会标 `duplicate-input`；试剂货号、基金号可能被误判，
  用 `--doi/--pmid` 显式指定更稳

## 与检索类 MCP 的分工

| 任务 | 用谁 |
| --- | --- |
| 找文献、读摘要全文、MeSH 高级检索 | `mcp__biotools__search_pubmed` / `get_publication_details` / `get_publication_abstract` |
| 批量核对存在性/撤稿、出机器可读报告 | 本技能 `scripts\verify_refs.py` |
| 单条疑难（`ERROR:*` 或元数据可疑） | 用 biotools MCP 按 PMID 拉详情交叉确认 |
| 网络受限只剩代理 | 脚本 `--use-proxy`；仍不通则改 MCP 逐条查 |

脚本负责"广度+门禁"，MCP 负责"深度+兜底"。

## 实测

> 2026-11-06，Windows 10 + Python 3.10.2（未安装任何第三方包），真实联网。

```powershell
python scripts\verify_refs.py --doi 10.1038/s41586-020-2649-2 --doi 10.1126/science.abb2507 `
  --doi '10.1016/S0140-6736(97)11096-0' --out ref_report.tsv --json ref_report.json
```

| input | resolved_doi | pmid | journal | year | first_author | exists | retracted | corrected |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10.1038/s41586-020-2649-2 | 10.1038/s41586-020-2649-2 | 32939066 | Nature | 2020 | Harris | yes | no | no |
| 10.1126/science.abb2507 | 10.1126/science.abb2507 | 32075877 | Science | 2020 | Wrapp | yes | no | no |
| 10.1016/S0140-6736(97)11096-0 | 10.1016/s0140-6736(97)11096-0 | 9500320 | The Lancet | 1998 | Wakefield | yes | **yes** | **yes** |

Wakefield 那行的 flags（撤稿判定证据链，三源互相印证）：

```text
title-prefixed-RETRACTED;corrected:crossref(Correction@2004);
eoc:europepmc(expression of concern in);retracted:crossref(Retraction@2010);
retracted:crossref-title-prefix;retracted:europepmc(pubtype=Retracted Publication);
retracted:europepmc(retraction in)
```

汇总行 `条目 3 | 存在 3 | 未找到 0 | 错误 0 | 撤稿 1 | 勘误 1`，退出码 `1`（有撤稿 → 门禁不通过）；
标题原样保留 `RETRACTED: Ileal-lymphoid-nodular...`，正确暴露撤稿状态。

同一轮还验证了（均可复现）：

- `.bib` 四条目（DOI、`https://doi.org/` URL、仅 PMID、无标识）→ 3 存在 + 1 `NOT_FOUND`；
  写错的 PMID 被抓出 `pmid-mismatch:bib=1234567,resolved=32939066`
- `.txt` / `.csv` / `--text` 混排抽取：中文全角标点后不粘连，版式年份 2020 不被误判成 PMID
- 编造 DOI `10.9999/j.fake.2024.1`、不存在 PMID `99999999` → `NOT_FOUND`，退出码 1
- 撤稿声明 DOI `10.1016/S0140-6736(10)60175-4` → `exists=yes, retracted=no`，flags 标
  `this-doi-is-retraction-notice:10.1016/s0140-6736(97)11096-0`（不把声明本身误判为被撤稿）
- 死代理 `https_proxy=http://127.0.0.1:9`：默认直连仍成功（0）；`--use-proxy` 写
  `ERROR:connection-refused`（1，不崩溃）；`--no-europepmc` 单靠 Crossref 也能判 Wakefield 撤稿

### 真实综述初稿（GB/T 7714，无 DOI/PMID）

用户稿件 `E:\2026\毕业论文综述部分撰写\refs\_used_in_review.md`：165 条，**0 条带 DOI/PMID**
（17 条中文 + 148 条英文）。前 30 条实测：

```powershell
python scripts\verify_refs.py --input "E:\2026\毕业论文综述部分撰写\refs\_used_in_review.md" `
  --bibliographic --limit 30 --out ref_report.tsv --json ref_report.json
```

**分布：MATCHED 13 | AMBIGUOUS 0 | NOT_FOUND 17**，耗时约 130 秒（每条约 1–2 次 Crossref 请求）。
13 条英文文献**全部 MATCHED**；17 条 NOT_FOUND 全是中文文献
（`cjk-reference;crossref-coverage-limited`，Crossref 未收录这些中文刊），**没有一条能判定为"造假"**。

5 条示例（含置信度）：

| 引用（截断） | 判定 | confidence | 关键信息 |
| --- | --- | --- | --- |
| Aune D, … Whole grain consumption and risk of cardiovascular disease… BMJ, 2016, 353:i2716 | MATCHED | 1.000 | 命中 `10.1136/bmj.i2716`，期刊/年份一致 |
| Bisset ES, Howlett SE. The biology of frailty… Aging Med (Milton), 2019, 2:27-34 | MATCHED | 1.000 | 顺带检出 `corrected:crossref(Erratum@2019)` |
| Alberts DS, … Lack of effect of a high-fiber cereal supplement… N Engl J Med, 2000, 342:1156-1162 | MATCHED | 0.900 | 题目带机构附注，靠"包含关系"兜底加分 |
| Alberti KGMM, … Harmonizing the metabolic syndrome… Circulation, 2009, 120:1640-1645 | MATCHED | 0.997 | 命中译文版并标 `journal-mismatch:ref=Circulation,matched=Obesity and metabolism`，需核对原刊 |
| 陈起萱，凌文华，…．黑米和红米对兔主动脉脂质斑块面积和血脂的影响．卫生研究，2000，29:170-172 | NOT_FOUND | 0.150 | `cjk-reference;crossref-coverage-limited`（未收录）→ 走 CNKI 核验 |

## 限制

- 只判断"记录存在/撤稿/勘误"，**不能判断内容是否被曲解**（见人工复核）
- 依赖三家公共 API：Crossref 无记录且 Europe PMC 未索引者会误报 `NOT_FOUND`（部分图书章节、
  内部报告、CNKI/万方中文文献）
- `--bibliographic` 的准确率取决于引用里的题目质量：题目被大幅改写、只有中文且期刊未注册 Crossref
  时会落到 NOT_FOUND；书籍/标准/报告基本只能人工核验
- Crossref 撤稿线索主要来自 Retraction Watch 同步，个别撤稿可能滞后；已用 Europe PMC 交叉验证
- DOI 正则只接受 ASCII 合法字符，含非 ASCII 的罕见 DOI 需 `--doi` 显式传入
- 每条 2 次请求、约 1–2 秒/条（可 `--interval 0.4` 固定节流）；不校验期刊掠夺性，`exists=yes` 不代表文章可信

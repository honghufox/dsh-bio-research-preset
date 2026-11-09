# Claims Ledger（稿件唯一的事实来源，Lead 独占维护）

> 规则：正文里每一句"结论性断言"都必须能映射到一行；写手只能引用已有 `claim_id`。
> 门控 G1 就是拿整篇稿子逐句对这张表。

| claim_id | 断言（一句话，可证伪） | 证据（图/表/统计量/原始数据路径） | 引用（DOI/PMID） | 状态 | 出现位置 |
| --- | --- | --- | --- | --- | --- |
| C1 | 例：X 缺失使 Y 表达下降约 2 倍 | Fig.2b；t 检验 P=0.004，n=3 独立实验；raw: data/qpcr.csv | — | supported | Abstract, Results ¶2, Discussion ¶1 |
| C2 | 例：X 与 Z 的关联独立于年龄 | Fig.3c；Cox 多因素 HR=1.8 (1.2–2.7) | 10.xxxx/xxxxx | supported | Results ¶4 |
| C3 | 例：机制可能经由 W 通路 | — | 10.yyyy/yyyyy, 10.zzzz/zzzzz | speculative | Discussion ¶3 |
| C4 | 例：在 A 队列中未观察到差异 | Supp. Table 1；n=18，功效 0.42 | — | negative | Results ¶5, Limitation ¶2 |

状态枚举：
- `planned` 还没证据 → 不许进正文
- `supported` 有直接证据
- `speculative` 允许出现在 Discussion，必须带 hedging（suggest / may / consistent with）
- `negative` 阴性结果，必须在 Results + Limitation 各出现一次
- `removed` 已删除（保留行以便追溯，不要删行）

## 数字台账（防止摘要/正文/图注打架）

| 指标 | 值 | 出处（脚本/输出文件） | 摘要 | 正文 | 图注 | 表格 |
| --- | --- | --- | --- | --- | --- | --- |
| 例：Y 相对表达 | 0.46 ± 0.09 | analysis/qpcr_stats.txt | ✔ | ✔ | ✔ | — |
| 例：HR (95% CI) | 1.8 (1.2–2.7) | analysis/cox_model.Rout | — | ✔ | ✔ | ✔ |

超出设计的因果断言（如"导致/驱动/causes"）：设计不支持的，一律降级为关联表述，并在 Limitation 写明。

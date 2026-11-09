# Response to reviewers 模板（含审稿人侧的验收标准）

## A. 整体格式（作者视角的正确做法 / 审稿人视角的验收点）

```markdown
# Response to Reviewers — <稿件编号>

We thank the reviewers and the editor for their careful evaluation. Below we reproduce each
comment verbatim (grey/italic), followed by our response and the exact location of changes.
All changes are highlighted in the revised manuscript.

---
## Reviewer 1

### Comment 1.1
> <审稿人原文，逐字照抄>

**Response:** We agree that <复述核心质疑，证明理解正确>.
<为解决该问题，我们做了什么：新实验/新分析/新数据；给出结果数值>
We have revised <具体位置>: <Fig 3E (new), Results L412–425, Methods L180–195>.

<若不同意：>
**Response:** We respectfully disagree on this point for the following reason(s).
<理由 1，附文献> <理由 2，附本稿数据>
To address the underlying concern, we have <妥协方案：降级表述 / 补充分析 / 明确局限>.
<位置>

---
```

## B. 审稿人侧的验收表（逐条打标签）

| 标签 | 判定证据 | 后续动作 |
|---|---|---|
| ✅ 已解决 | 有新数据/新分析 + 可定位位置 + 数值与结论一致 | 关闭该 concern |
| 🟡 部分解决 | 有新数据但不足以支撑原 claim；或只改了一部分 | 二轮写明「剩余差距是什么」，要求降级或补做 |
| 🔵 文字绕开 | 只在 Discussion 加解释段，无新证据；把问题重述为「limitation」 | 保留原 concern，二轮明确指出「未回应证据层面的要求」 |
| ⚪ 未回应 | 无说明、无修改 | 关键项 → 升级 must-fix，未解决则 reject |
| 🔴 新问题 | 新增数据引入新的统计/对照缺陷 | 作为新 major 提出（不追责，只审证据） |

## C. 常见绕开手法识别表

| 作者写法 | 潜台词 | 审稿人应核 | 标准回复句 |
|---|---|---|---|
| 「We have added a paragraph discussing this limitation.」 | 没做实验 | 摘要/结论是否同步降级 | 「讨论局限不等同于修正结论；请将摘要中的因果表述改为相关性表述，或补充 <实验>。」 |
| 「We have revised the wording accordingly.」 | 只改形容词 | 全文动词是否一致（标题/摘要/结论/图注） | 「修改未覆盖摘要结论句（L38）与 Fig 5 图注，仍为因果表述。」 |
| 「Due to sample limitations, this experiment cannot be performed.」 | 拒绝补数据 | 是否可降低 claim 强度 | 「若无法补充，请将结论限定为 <安全表述> 并在标题中体现研究对象与体系。」 |
| 只回 6/12 条 | 回避最重的几条 | 逐条对号，统计覆盖率 | 「Comments 1.3、1.4、2.1 未见回应。」 |
| 新增一个次要分析来回答质疑 | 转移焦点 | 新分析是否真的回答了原问题 | 「新增的 <分析> 未涉及原问题（X 与 Y 的因果方向），请直接回应。」 |
| 「As suggested by Reviewer 2, we now cite <文献>」 | 引用替代实验 | 引用是否支持所述结论 | 「所引文献为体外数据，不能支持本文的人体结论。」 |

## D. 二轮报告模板

```markdown
## Review of revised manuscript <编号>（Round 2）
本轮仅评估 response 与修订稿差异，未重新评审全文。

### 已解决
- R1.2（伪重复统计）：已补 3 个独立生物学重复，改用线性混合模型（新 Fig 2D；Methods L188–196）。确认解决。
- R2.1（数据可得性）：已提供 GEO 私有 token 与代码仓库。确认解决。

### 未解决 / 部分解决
- R1.4（因果表述）：摘要 L38 已改为「is associated with」，但结论段 L470 与 Fig 5 图注仍为「drives」。**请统一。**
- R2.3（生存分析 PH 假设）：作者仅补充 log-rank，未提供 PH 检验。**请提供 Schoenfeld 残差检验，或在 Cox 结果处说明 PH 不满足并改用时间依赖模型。**

### 新增问题
- 新增 Fig 3E 的 n=2，且未说明是否为独立实验；新增数据目前无法支持该句结论。

### 结论
Recommendation: <Minor revision（仅 R1.4 与 R2.3 两处）>  Confidence: <4>
```

## E. 审稿人自检（写返修意见时）
- [ ] 每条都引用了作者原文，无「作者似乎认为」式转述。
- [ ] 明确说了「这条已解决」，不让作者反复猜。
- [ ] 未解决项写了具体缺口，不是「仍不充分」。
- [ ] 新增问题只针对新增证据，不重新开题。
- [ ] 二轮不再要求与首轮无关的新实验（除非新数据自己引出）。

# 编辑决定信模板（Decision letter）

## A. 通用骨架

```markdown
Dear Dr. <通讯作者>,

Thank you for submitting your manuscript "<标题>" (ID: <编号>) to <期刊>. It has been
evaluated by <n> reviewers and by the handling editor.

Decision: <Accept / Minor revision / Major revision / Reject>

<1–2 句：稿件价值。必须具体，不能写 "interesting work"。>
例：The study addresses an important gap in <领域> and the <模型/队列> is well suited to it.

<若 Reject，直接说明不可修复的原因，2–3 句，不列可改项。>
例：The central claim requires an intervention that the current design does not permit, and
this cannot be addressed through revision of the text.

<若返修，列必须解决的问题，已归并审稿人意见、按优先级编号。>
We ask you to address the following points, which we consider essential:

1. <设计/证据层问题>（来源：Reviewer 1 第 2 条、Reviewer 2 第 1 条）
   - 需要：<具体可执行要求>
   - 可接受替代：<降级 claim / 补分析 / 明确标注局限>
2. …

The following points should also be addressed but are not gating:
3. …

<返修要求>
- 请提交 point-by-point response，标明每处修改的页码/行号。
- 修改处请在稿件中用 <高亮/修订模式> 标出。
- 期限：<n> 周（<日期>）。如需延长请提前说明。
- 数据与代码：请在返修时提供 <accession / 仓库链接>。
- 报告规范：请按 <ARRIVE 2.0 / CONSORT / STROBE> 清单逐项核对并附 checklist。

<编辑判断说明（重要）>
Where the reviewers disagreed on <问题>, the editor has reviewed <Fig X> and considers
<采信哪一方及理由>。请据此回应，不必同时满足两种互斥要求。

Sincerely,
<编辑姓名>，<期刊>，on behalf of the reviewers
```

## B. 冲突意见的裁决写法

| 情形 | 写法 |
|---|---|
| 一方要补实验、一方说足够 | 「编辑已核对 Fig 3，认为现有证据只能支持相关性表述；请将摘要与结论相应下调，无需补做 <实验>。」 |
| 一方质疑新颖性、一方认可 | 「新颖性争议集中在与 <文献> 的重合度；请在 Introduction 明确列出本文相对该工作的三点增量。」 |
| 审稿人明显超出专业范围 | 「Reviewer 2 关于 <统计> 的意见编辑不予采信，理由：<…>；无需回应。」 |

## C. 各档位必写内容 / 禁写内容

| 档位 | 必写 | 禁写 |
|---|---|---|
| Reject | 不可修复的根因（设计层/伦理/不端） | 一长串可改项（会暗示可返修） |
| Major | 3–6 条 gating 项 + 可接受替代路径 + 期限 | 「请按审稿人意见修改」式空指令 |
| Minor | 具体条目（图注、统计描述、措辞、引用）+ 校对要求 | 引入新的科学要求（超出 minor 语义） |
| Accept | 版权/校对/数据存档提醒 | 新的修改要求 |

## D. 质量检查
- [ ] 决定句在第一段出现，作者不用猜。
- [ ] 每条要求都能被作者执行（有动词、有对象、有判据）。
- [ ] 已归并重复意见，未把 3 位审稿人的 30 条原样转给作者。
- [ ] 明确说了哪些**不需要**做（减少无效工作量）。
- [ ] 冲突意见已裁决，未把矛盾丢给作者。
- [ ] 涉及图像/数据疑虑时，措辞为事实陈述 + 材料请求，不含指控定性。

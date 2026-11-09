# Team 模式编排手册（有 `spawn_teammate` / `team_task_*` / `wait_agent` 时用）

适用于：整篇论文、跨小时、需要中断/resume、需要多人并行且要能看到"谁在写哪节"。

## 0. 判断与准备

```
有 spawn_teammate 且有 team_task_create  → 走本手册
只有 workflow                            → 走 scripts/manuscript-workflow.js
只有 subagent                            → 串行两三步，自己当 reviewer
```

准备（Lead 自己做，不进 Team）：

1. `manuscript/` 目录与 `00-brief.md`、`01-outline.md`、`claims-ledger.md`、`style-guide.md` 四件套写完（用 `templates/`）。
2. 记录**绝对路径** `MANUSCRIPT_ROOT`：teammate 的 cwd 可能与你不同，prompt 里一律给绝对路径。
3. 确认无人正在写同一批文件；Team 里用 `writeScopes` 把冲突变成可见警告。

## 1. 建任务（先后顺序 = 依赖）

每个写一节一个任务；审稿任务 `blocked_by` 所有起草任务；裁决任务 `blocked_by` 所有审稿任务。

```
team_task_create({
  subject: "起草 Introduction",
  description: "只写 manuscript/sections/intro.md：按 00-brief.md 的 gap 与主结论，引用 claims-ledger 的 C1/C3；不新增 claim；跑完自检数字",
  write_scopes: ["manuscript/sections/intro.md"]
})
team_task_create({
  subject: "独立审稿（统计 lens）",
  description: "评审 manuscript/manuscript.md，按 manuscript-review 的结构化格式写到 manuscript/review/round-1/r2.md",
  write_scopes: ["manuscript/review/round-1/r2.md"],
  blocked_by: ["task-<起草A>", "task-<起草B>", "..."]
})
```

## 2. 派队友（`context: "fresh"`，不要 fork）

审稿人**必须 fresh**：fork 会继承你的写作上下文，等于自己审自己。

```
spawn_teammate({
  name: "writer-intro",
  context: "fresh",
  description: "写 Introduction",
  prompt: "<见 §3 模板>"
})
```

命名：`writer-<sec>`、`reviewer-<lens>`、`editor`。名字永久不可复用。

## 3. 写手 prompt 模板（复制改路径）

```
你是论文写手，只负责 Introduction 一节。

工作目录：<ABS_ROOT>/manuscript
必读：00-brief.md、01-outline.md（你这一行）、claims-ledger.md、style-guide.md
目标期刊：<journal>

任务：task-<id>（先 team_task_get 读全文，再 team_task_update claim）
产出：只写 <ABS_ROOT>/manuscript/sections/intro.md

规则：
- 只能引用 claims-ledger 里的 claim_id；需要新 claim 就 send_message 给 lead，不要自己加
- 不写其他节；不做机制大推测（留给 Discussion）；不编造引用
- 数字不确定就标注 TODO(needs-data)，不要猜
- 完成后 team_task_update complete，并 send_message 给 lead：文件路径 + 字数 + 用到的 claim_id + 缺什么
```

## 4. 审稿人 prompt 模板

```
你是审稿人，lens：统计与实验设计。独立评审，不要参考其他审稿人意见，也不要假设作者在场。

稿件：<ABS_ROOT>/manuscript/manuscript.md
图表：<ABS_ROOT>/manuscript/figures/
规范参考：技能 manuscript-review（结构化审稿报告格式）

任务：task-<id>（claim 后开始）
产出：只写 <ABS_ROOT>/manuscript/review/round-1/r2.md

每条 major concern 必须包含：
- location：图/表/节 + 引用原句
- evidence：稿件里的原文或数据
- whyItMatters：为什么这是问题（设计/统计/结论强度）
- requiredFix：具体改法（加什么对照、补什么统计、改哪句措辞）
禁止"建议进一步研究""建议补充文献"这类无落点意见；不确定就写 confidence 低。

完成后 team_task_update complete，并 send_message 给 lead：recommendation + major 条数 + 最致命的一条。
```

## 5. 盯盘与纠偏

- `wait_agent({timeout_ms: 300000})`；醒来先 `team_task_list({status:"in_progress"})` 看谁在动，再 `list_agents` 看状态。
- 队友 `inactive` ≠ 完成；只有任务 `completed` 或收到消息才算。
- 跑偏（写了别的节、加了新 claim、开始编引用）：`interrupt_agent` 停掉当前轮，`send_message` 给纠正 + 缩小任务范围后重开；不要让它"接着改"。
- 不要同时等 >5 个活跃队友；合并成本会吃掉并行收益。

## 6. 评审独立性检查（P4 必做）

1. 所有 reviewer 都是 P3 整合完成后才创建（`blocked_by` 已经保证任务不可 claim）。
2. reviewer 之间**不转发**彼此意见；`send_message` 只发给 lead。
3. 若两份 review 的 major 几乎逐条雷同，判为"未独立"，重跑而不是采信。

## 7. 裁决与收尾

- `editor`（fresh）只拿稿件 + 全部 review 文件，逐条 `accept|partial|reject`；驳回必须给证据。
- Lead 按裁决改 `manuscript.md` + 写 `revision-log.md`（每条意见 → 改在哪）。
- 收尾：确认所有任务 `completed`、所有队友 `inactive`，再跑 §6 门控（见 SKILL.md），最后向用户交付。
- 中断恢复：会话重启后用 `team_task_list` + `list_agents` 重建状态，不要凭记忆补进度。

## 8. 成本控制

| 角色 | 模型选择 | 理由 |
| --- | --- | --- |
| 分节写手 | 快/便宜 | 有 ledger 与 brief 约束，任务窄 |
| 审稿人 | 最强 | 评审质量决定稿件上限 |
| 裁决 | 最强、温度低 | 需要一致、可解释 |
| 一致性终检 | 中等 | 机械核对为主，可脚本化 |

一节一篇 = 1 个写手；不要把 4 节塞给 1 个写手（会串味）。同理，一个 reviewer 不能兼任两个 lens。

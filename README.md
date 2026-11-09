# 生物科研模式（含 LSF 集群执行）（DSH Agent 预设）

DeepSeek Harness 的 **生物科研模式（含 LSF 集群执行）** 预设，打包为可移植的 desktop bundle：克隆到本机后即可在 DSH 桌面版 / Web 版里选用。

- 预设 id：`bio-research`
- bundle 名：`bio-research-preset`
- 自带资源：`presets/bio-research/`（技能与工具源码）
- 版本兼容：composition 已对齐 **DSH 0.2.2-rc.1**（2026-11-06）：新增 `time-context` / `tool-schedule` / `command-goal` 行、`tool-fs.applyPatch: false`、子代理改用 `modelSelection` + `modelDiscovery`（旧的 `modelSelectionSettings` / `backgroundMode` 在新版已删除）、plan-mode 文案对齐内置预设、`tool-web` 开启 fetch；**删除 `tool-subagent-control/list-agents` 行**——0.2.2 移除了该子路径导出，`list_agents` 改由 `tool-subagent-control` 主插件一并注册。

## 写作与审稿能力（v1.1 新增）

预设的写作能力从"能写"升级为"能按投稿标准写、能被独立审、引用可验证"：

| 技能 | 作用 | 关键资源 |
| --- | --- | --- |
| `paper-writing` | 写作 brief、期刊选择、IMRaD 逐节写法、学术英语、统计与图表报告、报告规范门控、投稿包、返修信 | — |
| `manuscript-review` | 同行评审：结构化审稿报告、严谨性 11 条、分学科门控（ARRIVE/CONSORT/STROBE/PRISMA/MIQE）、decision letter、投稿前 red team | `templates/`、`references/review-rubric.md`、`references/reporting-guidelines.md` |
| `writing-team` | 多 agent 协作编排：P0–P8 阶段、claims ledger 与引文池、3 路异质盲评 + 裁决（不平均分）、证据一致性阻断门、一致性终检、反模式 | `scripts/manuscript-workflow.js`（喂给 workflow 工具）、`scripts/lint_manuscript.py`（离线体检）、`references/team-playbook.md`（喂给 spawn_teammate）、`references/multi-agent-evidence.md`（设计依据与政策来源） |
| `reference-integrity` | 引用真实性校验：Crossref + PubMed + Europe PMC，标出不存在/撤稿/勘误 | `scripts/verify_refs.py`（支持 DOI/PMID/bib 批量） |

多 agent 的两条落地路径：

1. **有 Agent Teams 工具**（`spawn_teammate` / `team_task_*` / `wait_agent`）→ 按 `writing-team/references/team-playbook.md`：每节一个 fresh 写手、写作用 `writeScopes` 隔离、审稿人是 P3 整合后才创建的独立 fresh 队友、裁决者只见稿件与意见。
2. **只有 `workflow` 工具** → 把 `writing-team/scripts/manuscript-workflow.js` 交给 workflow 工具，`args` 给 `outDir` / `sections` / `reviewers` / `journal`；脚本内置结构化 schema 与门控字段。

共同铁律：写手不得新增 claim（只引用 `claims-ledger.md`）；审稿人不得改稿；评审最多 2 轮；任何新引用进稿前先跑 `verify_refs.py`。

## 这个 bundle 为什么可移植

预设的 `agent.cordis.yml` 用 `new URL('skills/', baseUrl)` 定位自带资源。DSH 的 `Include` 会把 `baseUrl` 设为**组合文件所在目录**，因此把 composition 内联进 bundle 的 `cordis.patch.yml` 之后，同一个表达式会指向 bundle 目录。生成时已把每处引用重写为 `new URL('presets/bio-research/…', baseUrl)`，资源也随 bundle 一起分发。

于是整个 bundle 放在**任意路径、任意机器**上都自解析，无需安装期改写绝对路径。

## 安装

```powershell
# 1) 克隆到 desktop profile 的 local-bundles（目录名即 bundle 名）
git clone <本仓库地址> "$env:USERPROFILE\.dsh\profiles\desktop\local-bundles\bio-research-preset"

# 2) 重建依赖并写入 profile 清单
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\.dsh\profiles\desktop\local-bundles\bio-research-preset\setup.ps1"
```

改完重启 DSH（桌面版退出重开，Web 版重启 `dsh web`），新建会话时即可在预设列表里选到「生物科研模式（含 LSF 集群执行）」。

## 依赖产物说明

仓库**刻意不提交** `node_modules`：它们是平台专属、重装即可得的产物，提交进 Git 会让仓库膨胀且不可移植。

需要在以下目录执行 `npm install`（`setup.ps1` 已自动处理，并会校验真正的构建产物）：

- `presets/bio-research/tools/biotools` — `npm install --omit=dev`，产物 `node_modules/bach-biotools-server/build/index.js`
- `presets/bio-research/tools/zotero` — `npm install --omit=dev`，产物 `node_modules/mcp-zotero/build/server.js`
- `presets/bio-research/tools/pubmed` — `npm install --omit=dev`，产物 `node_modules/@cyanheads/pubmed-mcp-server/dist/index.js`（PubMed 全文/引用格式化/撤稿通告，12 工具；需 Node ≥ 24）

另外两个 MCP 服务器依赖 **Python 侧**环境，同样由 `setup.ps1` 处理（`-SkipPythonTools` 可跳过）：

- `presets/bio-research/tools/ncbi` — `python -m pip install --user ncbi-mcp "mcp>=1.0,<2"`
  （mcp SDK 2.x 移除了 FastMCP API，必须锁 1.x）
- `presets/bio-research/tools/tavotto` — `python mcp/server.py --provision`
  （在 `%APPDATA%\Tavotto\mcp-runtime\venv` 下建插件自管环境；预设行的 `command` 会优先挑它）

> **DSH 0.2 起 `package.json` 里的 `dsh.install` 不再被读取**（0.2 只读 `dsh.bundle.patch`
> 与 `dsh.profile.bundles`）。所以上面这些步骤**只能**由 `setup.ps1` 承担 —— 漏装时预设
> 仍会挂载成功（`failOnStartupError: false`），只是对应的 `mcp__*` 工具会缺失。

## 手工安装（不使用 setup.ps1）

```powershell
$bundle = "$env:USERPROFILE\.dsh\profiles\desktop\local-bundles\bio-research-preset"

# 重建 node 侧依赖
Push-Location "$bundle\presets\bio-research\tools\biotools"; npm install --omit=dev; Pop-Location
Push-Location "$bundle\presets\bio-research\tools\zotero"; npm install --omit=dev; Pop-Location
Push-Location "$bundle\presets\bio-research\tools\pubmed"; npm install --omit=dev; Pop-Location

# 重建 python 侧依赖
python -m pip install --user ncbi-mcp "mcp>=1.0,<2"
python "$bundle\presets\bio-research\tools\tavotto\mcp\server.py" --provision

# 编辑 $env:USERPROFILE\.dsh\profiles\desktop\package.json：
#   dependencies 里加  "bio-research-preset": "link:./local-bundles/bio-research-preset"
#   dsh.profile.bundles 里加  "bio-research-preset"
```

## 目录结构

```
bio-research-preset/
├── cordis.patch.yml     # 预设声明（一行 @deepseek-ai/dsh-agent-preset，内联 composition）
├── package.json         # dsh.bundle.patch 指向上面的 patch（dsh.install 是 0.1.x 遗留字段，0.2 不读）
├── lib/index.js         # bundle 入口（空模块，仅满足包约定）
├── setup.ps1            # node + python 依赖重建、profile 清单写入
└── presets/bio-research/       # 预设自带资源：skills/、tools/ 等
```

## 许可

MIT。第三方技能与工具的版权归各自作者所有，详见各目录内说明。

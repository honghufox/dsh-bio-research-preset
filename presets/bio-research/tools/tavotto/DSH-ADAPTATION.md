# DSH 适配说明（Tavotto Codex 插件 → `bio-research` 预设）

这份目录是上游 Tavotto 的 **Codex 插件发行包**整包 vendor 进来的副本，外加下面
列出的 DSH 适配补丁。它由 `bio-research` 预设的 `mcp-tavotto` 行加载。

## 来源

| | |
| --- | --- |
| 仓库 | <https://github.com/Tavotto/Tavotto> |
| 分支 | `plugin-stable`（发行分支；仓库根 `.agents/plugins/marketplace.json` 的 `git-subdir` 来源就是它） |
| 提交 | `53a8f2fbf220806539f6fbe49f399836c672a180`（2026-09-19） |
| 插件版本 | `0.15.0`（见 `.codex-plugin/plugin.json`、`plugin-build.json`） |
| vendor 日期 | 2026-09-20 |
| 许可证 | AGPL-3.0-only（见 `LICENSE`） |

重取命令：

```sh
git clone --filter=blob:none --no-checkout --depth 1 https://github.com/Tavotto/Tavotto.git <tmp>
git -C <tmp> fetch --depth 1 origin plugin-stable
git -C <tmp> checkout -f FETCH_HEAD -- codex-plugin
```

覆盖本目录时**不要**把 `codex-plugin/` 这一层目录名带进来：把它的**内容**直接
放在 `tools/tavotto/` 下，`mcp/server.py` 才能按 `../skills/tavotto-figure/scripts`
找到它的 `handoff.py`。覆盖之后必须重放下面第 5 节的文本补丁。

## 上游包长什么样

| 路径 | 作用 |
| --- | --- |
| `mcp/server.py` | 启动器：先找一个能 `import tavotto.engine` 的解释器再交棒；找不到就起降级 server（纯标准库） |
| `mcp/tavotto_mcp/` | 协议 + 引擎桥：`rpc.py` / `server.py` / `bridge.py` / `roots.py` / `widget.py` |
| `mcp/widget/canvas.html` | 内嵌画布构建产物（本 host 用不到，见 2.） |
| `skills/tavotto-figure/` | 技能本体 + `references/` + `scripts/`（handoff / prefs / update_check） |
| `.mcp.json`、`.codex-plugin/`、`.agents/plugins/` | Codex 侧清单，保留只为溯源，DSH 不读 |

九个 MCP 工具：`tavotto_health`、`tavotto_open_figure`、`tavotto_apply_overrides`、
`tavotto_normalize_figure`、`tavotto_preflight`、`tavotto_export`、
`tavotto_verify_replay`、`tavotto_refresh_project`、`tavotto_close_session`。
在 DSH 里它们的公开名是 `mcp__tavotto__<上表原名>`。

## DSH 与 Codex 的差异，以及本副本怎么处理

### 1. 启动器的 `os.execv` 交棒会让 DSH 挂载卡死（最要命的一条）

`mcp/server.py` 是两层：当前解释器能 `import tavotto.engine` 就直接跑；否则按固定
优先级找一个能 import 的解释器，再用 `os.execv` **把当前进程的映像换掉**——上游
注释的理由是「同一个进程 = stdio 原样继承」。

**这条在 DSH 上不成立。** `dsh-mcp-client` 经 Node 的 `child_process` 管道起子
进程，换成别的映像之后那对 stdin/stdout 不再接得上：server 侧一切正常（stderr 上
还能看到「交棒」那一行），`initialize` 却永远没有回应。实测（同一台机器、同一份
插件、DSH 自己钉的 SDK 1.30.0、空 `capabilities`）：

| 行里的 `command` | 结果 |
| --- | --- |
| `python`（当前解释器没有引擎 ⇒ **会交棒**） | 150 s 后仍未连上 |
| `G:\...\mcp-runtime\venv\Scripts\python.exe`（有引擎 ⇒ **不交棒**） | **160 ms 连上，9 个工具齐全** |

这不只是「慢」：DSH 的 standing mount 会一直等 `dsh-mcp-client.apply`（它 `await`
连接 + 工具发现），而 MCP SDK 的 `client.connect()` 不理会取消信号——于是预设
挂不上、会话起不来，页面上的停止按钮也停不下来（只能重启 dsh）。

**两道处置，预设里都做了：**

1. `command` 直接挑一个**已经装着引擎**的解释器，永远不会走到交棒那一步：
   `TAVOTTO_MCP_PYTHON` → `TAVOTTO_WORKER_PYTHON` → 插件自管 venv
   （`%APPDATA%\Tavotto\mcp-runtime\venv\Scripts\python.exe`，`--provision` 建的那个）
   → 兜底 `python`。
2. `env.TAVOTTO_MCP_EXECED: '1'`——启动器读这个变量，`== "1"` 就**整条跳过**
   resolve + `os.execv`（上游拿它当防 exec 死循环的护栏）。有了它，兜底到没有引擎的
   `python` 也只会得到一个**降级 server**：握手正常、`tools/list` 只列
   `tavotto_health`，绝不卡死。

只做第 1 条不够（引擎装在 pipx 之类别处时兜底仍会交棒），只做第 2 条也不够
（那样永远拿不到引擎）。两条一起才是「要么满血、要么诚实降级，两个都不卡」。

### 2. 只桥接 tools —— 没有内嵌画布

`@deepseek-ai/dsh-mcp-client` 的 README 写明「Resources and Prompts have no
harness consumer mechanism and are deferred」，而内嵌画布正是
`ui://tavotto/canvas/v1.html` 这一个 MCP resource。所以：

* 画布**不会**出现在 DSH 会话里。**这是设计，不是故障**——不要把它报成错误，
  也不要拿「打开浏览器」冒充它（上游自己也禁止这一点）。
* 九个工具本身照常可用。Tavotto 的文档写明「没有 UI 的 host 里这九个工具就能走
  完整条流程」——打开 → 改 → 预检 → 导出。改图走 `tavotto_apply_overrides`。
* `mcp/widget/canvas.html` 仍随包保留（1.3 MB）。工具会检查它在不在位并在
  `canvas_ui` 里如实报告；删掉它不会让工具变好，只会多一条 `widget_missing` 诊断。

### 3. 工作区授权只有 `TAVOTTO_MCP_ROOTS` 一条路

Tavotto 的 `RootAuthority` 优先级是：`TAVOTTO_MCP_ROOTS` → host 的 `roots/list`
→ 用户经 `elicitation/create` 批准的精确目录 → 宿主工作区变量
（`TAVOTTO_MCP_WORKSPACE` / `CODEX_*`）→ 安全 cwd（且不能在插件目录里）。

DSH 的 mcp-client 在 `initialize` 里声明的是**空 capabilities**（`lib/index.js`：
`{ capabilities: {} }`），所以中间那几档全都到不了；预设给 MCP server 的 `cwd`
又正是插件目录（Tavotto 明确不拿它当边界）。结论：**必须显式给根**。

预设里那一行钉的是**用户主目录** `C:\Users\<你的用户名>`（本预设的默认放图位置）：

```yaml
env:
  TAVOTTO_MCP_ROOTS: !!js "process.env.TAVOTTO_MCP_ROOTS ?? process.getBuiltinModule('node:path').join('C:', 'Users', 'wangh')"
```

写成 `path.join` 而不是字面量，是为了绕开 YAML 双引号里的反斜杠转义：`!!js` 标量
先过 YAML 解码再 `eval`（`cordis-plugin-loader` 的
`new Function('ctx', 'expr', 'with (ctx) { return eval(expr) }')`），字面量要写四个
反斜杠才等于一个，很容易数错——而拼错的症状是「每个 open 都回
`path_out_of_scope`」。

要换、要加，就在**启动 dsh 之前**设这个环境变量（多个根用 `os.pathsep` 分隔，
Windows 上是 `;`，例如 `C:\Users\<你的用户名>;G:\dsh`）。可信根之外的路径每个 open 都会回
`path_out_of_scope`，一个根都没有则回 `no_workspace_root`——`project_path` 只是
候选，不能自证权限。

### 4. `command` 不写上游清单里的 `python3`

Windows 上 `python3` 常是微软商店的 App Execution Alias（命令存在、退出码 9009、
零输出），上游为此专门有 `tavotto codex install` 那一跳把已装副本里的命令钉死。
DSH 这边按第 1 条的候选链自动挑一个存在的解释器。

### 5. 技能文本做的 DSH 适配

`skills/tavotto-figure/` 下只改了**宿主相关**的表述，没有动契约、工具语义或判据：

| 文件 | 改动 |
| --- | --- |
| `SKILL.md` | 顶部加「DSH 适配说明」块；「在 Codex 里」→「在 DSH 会话里」；会话入口第 4/5/6 步换成 DSH 的恢复路径（没有插件市场）；`python3` → `python`；提问工具写成 `ask_user_question`；「画布里拖」改成用工具改 |
| `references/first-run-and-recovery.md` | 「工具列表里没有 tavotto_health」与「插件有新版本」两节重写为 DSH 版本；引擎恢复命令改成 `python <预设目录>/tools/tavotto/mcp/server.py --provision`；工作区授权一节写明 DSH 只有 `TAVOTTO_MCP_ROOTS`；新开一节写「挂载卡死」的排查 |
| `references/compatibility.md` | 「三条入口」→ 两条（去掉内嵌画布）；错误码表补 `no_workspace_root` / `desktop_only`，`tavotto_missing` 的恢复改成 provision |
| `references/desktop-handoff.md` | 去掉「内嵌画布」并列；`python3` → `python` |
| `references/issue-reporting.md` | `python3` → `python` |
| `skills/tavotto-figure/agents/openai.yaml` | **未改**（Codex 技能元数据，DSH 不读，保留只为溯源） |

`references/figure-contract.md`、`references/publication-style.md` 与
`scripts/*.py` 是纯内容（绘图契约、出版规范、偏好与交接脚本），**一个字没动**。

## 实测：一条完整的交互回路（2026-09-20）

`G:\dsh\_adapter\tavotto_roundtrip.py` 用**空 capabilities** 的 MCP client 直接从
stdio 驱动 `mcp/server.py`（`TAVOTTO_MCP_ROOTS=C:\Users\<你的用户名>`、
`TAVOTTO_MCP_EXECED=1`），在 `C:\Users\<你的用户名>\tavotto-probe\figures` 上把整条流程跑
通了：

| 步骤 | 结果 |
| --- | --- |
| `initialize` | `serverInfo` = tavotto 0.15.0 |
| `tools/list` | 9 个工具 |
| `tavotto_health` | `ok: true`、`mode: engine`、`roots: ["C:\Users\<你的用户名>"]`、`source: explicit_env` |
| `tavotto_open_figure` | 会话 `s-…`、80.0×60.0 mm、**20 个可编辑元素**，manifest 带完整 `editable` 属性表（gid + prop + 枚举/范围） |
| `tavotto_apply_overrides` | 一次发 6 条全量 patch（`legend.frameon=false`、`legend.fontsize=8.5`、`xticks/yticks.direction=in`、`xlabel/ylabel.weight=bold`），全部 applied |
| `tavotto_preflight` | 改完 `error: 0`、`warn: 2`、`suggestion: 1`（改之前是 `warn: 5`，`tick-direction` / `legend-frame` / `legend-font-size` 三条被 override 消掉） |
| `tavotto_export` | 出真矢量 `Fig_demo_0920_115700.pdf` + 300 dpi `.png` + `_proof.json`，落在 `<项目>/tavottofile/export/` |
| `tavotto_close_session` | 正常关闭 |

**两次「预检挡住导出」都是真的，不是摆设**，正好演示了分工：

1. 先是图幅 80×60 mm 下 y 轴标签越界 6.16 mm → `element-outside-figure`（error）。
   这类几何问题按契约**归代码**，回脚本加 `layout="constrained"` 后消失。
2. 再把图例字号改成 8 pt → 规范报「最终有效字号必须**大于** 8 pt」（8.00 不大于
   8）→ error。改成 8.5 pt 才过。

留了两条不挡导出的 warning，也都是如实报告、不假装通过：机器上没装 Times New
Roman（Tavotto 不拿相近字体冒充达标），以及图例压住数据（挪到图外属于结构性改动，
归代码）。项目本身就是一份可复现的样例，留在 `C:\Users\<你的用户名>\tavotto-probe\`。

## 技能是怎么被 DSH 发现的

预设 `agent.cordis.yml` 的 `skill-filesystem` 行把**两个**目录当 skill root：

```yaml
customSkillDirs:
  - <预设目录>/skills/
  - <预设目录>/tools/tavotto/skills/
```

第二项就是这里。之所以不把 `tavotto-figure/` 复制一份到 `<预设目录>/skills/`，
是因为 `mcp/server.py` 按 `../skills/tavotto-figure/scripts` 找它的 `handoff.py`：
复制品会和这里的 `scripts/` 悄悄漂开，而两边的 `scripts/handoff.py` 正是
「图能不能被接手」的判据所在。

## 装引擎

引擎是 PyPI 的 `tavotto`（`requires-python >=3.10,<3.15`）。不装时工具列表里只有
`tavotto_health`；装法二选一：

```sh
python <预设目录>/tools/tavotto/mcp/server.py --provision   # Tavotto 配置目录下的自管 venv
pipx install "tavotto[worker]"                              # 或装 pip 形态的引擎
```

**装完必须重启 dsh**：`command` 与 `TAVOTTO_MCP_EXECED` 都是*挂载时*读的，已经建好
的 standing mount 不会重来（改了预设文件也一样——实测编辑 `agent.cordis.yml` 不会
重挂）。

## 定位这个 bug 用过的两个探针

`G:\dsh\_adapter` 下的两个脚本（已随本次调试留在工作区）不是插件的一部分：

* `probe_node_mcp.mjs` —— 用 DSH 自己钉的 `@modelcontextprotocol/sdk` 按同样的
  `command`/`args`/`cwd`/scrub 过的 env 起一遍 `initialize` + `tools/list`，打印
  耗时与工具名。改 `command` 之后可以用它把「连不上」和「连上但只有 1 个工具」
  区分开。
* `probe_resolve_command.mjs` —— 直接从 `agent.cordis.yml` 抠出
  `command: !!js "…"` 求值，确认它落到哪个解释器、那个文件存不存在。

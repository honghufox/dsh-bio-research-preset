# 首次使用与恢复（只在会话入口判到异常时读）

本文件展开 SKILL.md「会话入口」各状态的恢复动作。**健康会话一个字都不用读。**

## 工具列表里没有 `mcp__tavotto__tavotto_health`

说明 `bio-research` 预设里 `mcp-tavotto` 那一行没有在本会话起来。**这不是
「插件没装」**：Tavotto 是预设自带的 vendor 副本（`<预设目录>/tools/tavotto/`，
取自上游发行分支 `plugin-stable`，v0.15.0）。DSH 没有插件市场，也没有
`codex plugin …` 那套命令可跑——**不要给用户两条安装命令，也不要让他去 clone
仓库**。

按顺序对号：

```sh
# 预设目录里的启动器：直接问它看到了什么（纯标准库，没有引擎也能跑）
python <预设目录>/tools/tavotto/mcp/server.py --health
```

* **输出一行 JSON，`ok: false, mode: degraded`**（`code: tavotto_missing` 或
  `desktop_only`）：server 起来了，缺的只是引擎——这时会话里的工具列表应当只有
  一个 `tavotto_health`。走下面「引擎不可用」那一节。
* **这条命令自己就报错、或没有 JSON**：是 DSH 起 MCP server 的那一跳没起来。
  按顺序查：
  1. `agent.cordis.yml` 里 `mcp-tavotto` 的 `command`。预设写的是 `python`；
     Windows 上这个名字有时是微软商店的 App Execution Alias——命令**存在**、
     启动起来只有退出码 9009 且什么都不打印。遇到这种就把 `command` 钉成解释器
     绝对路径（`python -c "import sys;print(sys.executable)"` 会打印它）。
  2. `args` / `cwd` 指向的 `tools/tavotto/mcp/server.py` 是否还在——vendor 目录被
     动过就有这一档。
  3. 预设改动之后**必须新开一个 DSH 会话**：已经开着的会话不会重新加载 MCP 工具。
* **`--health` 正常，会话里连 `tavotto_health` 都没有**：同样先新开会话；新开
  还是没有，就把 `--health` 的完整输出交给用户。那是 DSH 侧 mcp-client 的连接或
  发现失败，不是 Tavotto 的问题，**本技能不猜**。

**不要在旧会话里继续假装工具可用**，也不要重装预设。

## 会话起不来 / 一直转圈、连停止都点不动 —— 挂载卡死

症状：新开 dsh 会话（或任何触发预设挂载的动作）之后永不返回，页面上的停止按钮
也点不动，只有重启 dsh 能收场。**根因不是引擎没装，是上游启动器的 `os.execv`
交棒**：DSH 经 Node 的管道起子进程，换成别的映像之后那对 stdio 接不上，
`initialize` 永远没有回应，而 `dsh-mcp-client` 的 apply 会一直等它。

自查（在 shell 里跑，不需要先挂载）：

```sh
python <预设目录>/tools/tavotto/mcp/server.py --health
```

看 `tried` 那一列：只要存在一个**不是 `current` 但 `importable: true`** 的解释器，
而 `mcp-tavotto` 的 `command` 又指向 `current`（例如兜底的 `python`），启动器就一定
会去交棒 → 卡死。

正确配置必须**同时**满足两条（预设里已经这么写了，改坏了才需要看这一节）：

1. `mcp-tavotto` 的 `command` 指向**已经装着引擎**的那个解释器；
2. 它的 `env` 里有 `TAVOTTO_MCP_EXECED: '1'`——启动器读到它就整条跳过 resolve +
   `os.execv`。有了这条，哪怕 `command` 兜底到没有引擎的 `python`，最坏也只是拿到
   一个只列 `tavotto_health` 的降级 server，**不会卡死**。

改完预设必须**重启 dsh**：`command` 与 `env` 都是挂载时读的，已经建好的 standing
mount 不会重来（编辑 `agent.cordis.yml` 也不会触发重挂）。

## 工具在、引擎不可用（`tavotto_health` 回 `ok: false`）

按返回的 `code` 只做**对应的一条**恢复动作，不做全套重装：

* `desktop_only` —— 用户装了 Tavotto 桌面版，**不要说「没有安装 Tavotto」**。
  桌面交接（`scripts/handoff.py`）此刻就能用。只有用户明确要 MCP 工具本身时，
  才给这两条里的一条（不是都给）：

  ```sh
  python <预设目录>/tools/tavotto/mcp/server.py --provision   # 启动器建自管 venv
  pipx install "tavotto[worker]"                              # 或者装 pip 形态的引擎
  ```

  装完**新开一个 dsh 会话**才拿得到工具。
* `tavotto_missing` —— 机器上确实没有 Tavotto。按用户的需求引导：只要桌面收尾
  就装桌面版（<https://github.com/Tavotto/Tavotto/releases>），要 MCP 工具就
  `python <预设目录>/tools/tavotto/mcp/server.py --provision`（在 Tavotto 用户
  配置目录下建一个专属 venv，不碰系统 Python / Conda，删掉那个目录即卸载），
  或 `pipx install "tavotto[worker]"`。
* `engine_unavailable`（`TAVOTTO_MCP_PYTHON` 指错了）—— 指名道姓地把它报给
  用户，让用户改环境变量或去掉；不要悄悄换别的解释器。
* 其它 code —— 把 `code` + health 输出里的 `recovery` 步骤原样转达。

**引擎缺失只修引擎**：不要因为引擎不可用去动预设或 `agent.cordis.yml`。

> `--provision` 会往 Tavotto 用户配置目录写东西（Windows 上是
> `%APPDATA%\Tavotto\mcp-runtime`）。dsh 若以受限文件权限运行，这条命令可能被
> 沙箱拒绝——那就请用户在自己的终端里跑一次，或在 dsh 里批准一次更宽的文件权限。

## Tavotto 有新版本

当前任务照常做完。收尾时提醒**一次**：本预设里的 Tavotto 是 vendored 副本
（v0.15.0，取自上游 `plugin-stable` 分支），DSH 没有 `marketplace upgrade`。

```sh
# 重新取一遍发行分支（需要 git）
git clone --filter=blob:none --no-checkout --depth 1 https://github.com/Tavotto/Tavotto.git <临时目录>
git -C <临时目录> fetch --depth 1 origin plugin-stable
git -C <临时目录> checkout -f FETCH_HEAD -- codex-plugin
# 用它覆盖 <预设目录>/tools/tavotto/，再按 DSH-ADAPTATION.md 重放适配补丁
```

**只提醒，不下载、不安装、不擅自覆盖**：vendor 目录里的技能文本带着 DSH 适配
（工具名前缀、没有内嵌画布、DSH 侧的恢复路径），直接覆盖会把适配冲掉。升级要
重放补丁，步骤在 `<预设目录>/tools/tavotto/DSH-ADAPTATION.md`。

`update` 里若还有 `tavotto` 字段，那是说本机**引擎**版本低于新插件的要求——
跟插件是两码事，别混着说。

## 离线 / 网络失败

`--provision`、`pip install`、vendor 升级都是尽力而为：失败就报一句，**不循环
重试，不退回 clone 源码或本地构建**。已经画好的图和脚本都在磁盘上，联网恢复后
重跑同一条命令即可。

## 工作区授权（每个连接第一次 open 时）

**DSH 这一格只有一条路。** DSH 的 MCP client 在 `initialize` 里声明的是空
capabilities：既没有 `roots`，也没有 `elicitation`。于是 Tavotto 的
`RootAuthority` 跳过 host 那两档，落到环境变量 / 安全 cwd 这一档；而预设给 MCP
server 的 `cwd` 正是插件目录，Tavotto 明确不拿它当边界。结果是：
**`TAVOTTO_MCP_ROOTS` 没设，每个 open 都回 `no_workspace_root`**。

配置方式（**启动 dsh 之前**设好；改完必须重启 dsh，MCP 连接不会热更新环境）：

```
TAVOTTO_MCP_ROOTS = 你的图库目录[;另一个目录…]      # Windows 用 ; 分隔（os.pathsep）
```

预设里的值是**用户主目录** `C:\Users\<你的用户名>`——图库放在这一层下面都行。要换、要加，
就在**启动 dsh 之前**设 `TAVOTTO_MCP_ROOTS`（多个根用 `os.pathsep` 分隔，Windows
上是 `;`）；改完必须重启 dsh，MCP 连接不会热更新环境。

看 `tavotto_health` 的 `root_authority`：`roots` 非空才说明授权已落地。授权失败
**分档**，每档一个稳定 `code`、一个 `disposition`（谁该动手）和一句 `recovery`
（下一步）。**把 `recovery` 转达给用户，别把 `code` 念出来**；不要自动重试，
也不要改用 shell 绕过。health 已给出恰好一个可信根时才可以用相对路径。

| `code` | `disposition` | 下一步 |
| --- | --- | --- |
| `no_workspace_root` | `configure_roots` | **DSH 上最常撞见的一档**：让用户按上面设 `TAVOTTO_MCP_ROOTS`，然后重启 dsh |
| `path_out_of_scope` | `narrow_the_path` | 路径越界：改用 `roots` 里列出的目录 |
| `ambiguous_workspace_root` | `send_absolute_path` | 相对路径对不上唯一根：改传绝对路径 |
| `workspace_confirmation_*` / `workspace_roots_*` | `ask_user_again` / `fix_host_wiring` | DSH 声明的是空 capabilities，理论上撞不到这两组；真撞上说明宿主接线变了，按 `recovery` 原样转达，**别自己编** |

## 三条铁律

* 引擎不可用 ≠ 可以拿桌面窗口或浏览器顶替内嵌画布——那是两条路，不许冒充。
  DSH 上本来就没有内嵌画布，更要把「画布没出现」说成设计，而不是故障；
* 预设里的行起来了 ≠ 工具可用：改完预设 / 装完引擎必须**新开会话**；
* 工具回了结构化错误就把 `code` + 恢复步骤转达给用户，绝不自己编一个成功。

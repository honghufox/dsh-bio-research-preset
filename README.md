# 生物科研模式（含 LSF 集群执行）（DSH Agent 预设）

DeepSeek Harness 的 **生物科研模式（含 LSF 集群执行）** 预设，打包为可移植的 desktop bundle：克隆到本机后即可在 DSH 桌面版 / Web 版里选用。

- 预设 id：`bio-research`
- bundle 名：`bio-research-preset`
- 自带资源：`presets/bio-research/`（技能与工具源码）

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

需要在以下目录执行 `npm install`（`setup.ps1` 已自动处理）：

- `presets/bio-research/tools/biotools` — `npm install --omit=dev`
- `presets/bio-research/tools/zotero` — `npm install --omit=dev`

## 手工安装（不使用 setup.ps1）

```powershell
$bundle = "$env:USERPROFILE\.dsh\profiles\desktop\local-bundles\bio-research-preset"

# 重建依赖
Push-Location "$bundle\presets\bio-research\tools\biotools"; npm install --omit=dev; Pop-Location
Push-Location "$bundle\presets\bio-research\tools\zotero"; npm install --omit=dev; Pop-Location

# 编辑 $env:USERPROFILE\.dsh\profiles\desktop\package.json：
#   dependencies 里加  "bio-research-preset": "link:./local-bundles/bio-research-preset"
#   dsh.profile.bundles 里加  "bio-research-preset"
```

## 目录结构

```
bio-research-preset/
├── cordis.patch.yml     # 预设声明（一行 @deepseek-ai/dsh-agent-preset，内联 composition）
├── package.json         # dsh.bundle.patch 指向上面的 patch；dsh.install 列出待重建依赖
├── lib/index.js         # bundle 入口（空模块，仅满足包约定）
├── setup.ps1            # 依赖重建 + profile 清单写入
└── presets/bio-research/       # 预设自带资源：skills/、tools/ 等
```

## 许可

MIT。第三方技能与工具的版权归各自作者所有，详见各目录内说明。

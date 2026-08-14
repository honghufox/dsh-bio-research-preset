# DSH 生物科研 Agent 预设（bio-research）

一个面向基础生物学科研的 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) Agent 预设：
**基因组学（VCF 变异分析）+ 生存分析**方向，覆盖文献检索、数据分析、发表级绘图、论文撰写与文档产出全流程。

## 内容

### 技能（9 个，SKILL.md 标准格式，可被 Claude Code / Codex 等兼容 Agent 读取）

| 技能 | 用途 |
|---|---|
| `literature-review` | PubMed 检索策略、MeSH/布尔、证据表、系统综述 |
| `biostatistics` | 统计检验选择、多重比较校正、功效分析 |
| `survival-analysis` | KM/log-rank、Cox 回归、时间依赖 ROC、竞争风险、列线图、表达-生存分析 |
| `variant-analysis` | VCF 变异过滤/注释/可视化（vcfpy + R vcfR + biomaRt） |
| `scientific-plotting` | matplotlib/seaborn 发表级图表规范 |
| `paper-writing` | IMRaD 结构、学术英语润色、参考文献格式 |
| `bioinformatics` | 序列分析、BLAST、比对、系统发育 |
| `latex-compile` | TinyTeX 编译 LaTeX PDF（含中文支持） |
| `document-output` | pandoc 转 Word/PDF、python-docx |

### MCP 服务器（`tools/`，用 `dsh-mcp-client` 行挂载）

| 服务器 | 工具 | 安装 | 说明 |
|---|---|---|---|
| biotools | `mcp__biotools__*`（37 个：PubMed/UniProt/GenBank/KEGG/PDB/BLAST/建树） | `cd tools/biotools && npm install --ignore-scripts` | 默认启用 |
| ncbi | `mcp__ncbi__*`（E-utilities：EInfo/ESearch/ESummary/EFetch） | `pip install --user ncbi-mcp "mcp>=1.0,<2"` + 填 `NCBI_EMAIL` | 默认启用 |
| zotero | `mcp__zotero__*` | `cd tools/zotero && npm install --ignore-scripts` + 填 API Key/User ID | 默认禁用（需凭证） |

## 安装

1. 把整个目录复制到 `${DSH_HOME}/.agent-presets/bio-research/`（Windows 默认 `%USERPROFILE%\.dsh\.agent-presets\`，macOS/Linux 为 `~/.dsh/.agent-presets/`）
2. 重启 DSH Web，在预设选择器中选择「生物科研模式」
3. 按需启用 MCP（见上表）：
   - biotools：`cd tools/biotools && npm install --ignore-scripts`
   - ncbi：`pip install --user ncbi-mcp "mcp>=1.0,<2"`，并把 `agent.cordis.yml` 中 `NCBI_EMAIL` 的 `your_email@example.com` 换成你的邮箱（NCBI E-utilities 要求真实邮箱）
   - zotero：`cd tools/zotero && npm install --ignore-scripts`，在 zotero.org/settings/keys 创建 API Key，填入 `agent.cordis.yml` 的 `ZOTERO_API_KEY` / `ZOTERO_USER_ID` 并删除 `disabled: true`
4. 可选科学栈：`pip install --user pandas numpy scipy statsmodels seaborn scikit-learn biopython lifelines vcfpy python-docx`；R 建议装 `survival survminer rms vcfR biomaRt`

## 从零部署新电脑

完整手动指南见 [`docs/新机器部署指南.md`](docs/新机器部署指南.md)，或直接在新电脑的普通 PowerShell 运行一键脚本：

```powershell
.\docs\setup-dsh-new-machine.ps1   # 自动完成 DSH 安装、预设克隆、Python 包、MCP 依赖
```

## Windows 一键启动器（可选）

[`docs/launcher/`](docs/launcher/) 提供「生物科研模式一键启动」桌面工具源码（C#，无需额外运行时）：
临时切换默认预设 → 启动 dsh web → 打开浏览器 → 退出时自动恢复。编译方法见其 README。

## 目录结构

```
bio-research/
├── preset.yml              # 预设元数据
├── agent.cordis.yml        # Cordis 组合文件（persona、技能、MCP 行）
├── skills/<name>/SKILL.md  # 9 个科研技能
└── tools/                  # MCP 服务器运行清单（node_modules 见 .gitignore）
```

## 许可

MIT。上游组件许可：DeepSeek Harness（MIT）、[biotools-mcp-server](https://github.com/BACH-AI-Tools/biotools-mcp-server)（MIT）、[ncbi-mcp](https://github.com/noahzeidenberg/ncbi-mcp)（Apache-2.0）、[mcp-zotero](https://github.com/kaliaboi/mcp-zotero)。

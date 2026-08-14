<#
.SYNOPSIS
  新电脑一键部署 DeepSeek Harness + 生物科研预设（bio-research）
.DESCRIPTION
  在普通 PowerShell 终端运行（不要在 DSH 沙箱内运行）。覆盖：Node 检查、DSH 安装、
  克隆并安装 bio-research 预设、Python 科研包、MCP 服务器依赖。
  需要手动完成的：DeepSeek API Key 配置、R 包安装、TinyTeX/pandoc、个人凭证。
.EXAMPLE
  .\setup-dsh-new-machine.ps1
  .\setup-dsh-new-machine.ps1 -Proxy "http://127.0.0.1:7897" -UseTsinghuaMirror
.PARAMETER Proxy
  GitHub 代理地址，默认 http://127.0.0.1:7897（你的 Clash 端口）
.PARAMETER SkipDshInstall
  跳过 npm 全局安装 dsh（已装过时使用）
.PARAMETER SkipPythonPackages
  跳过 Python 包安装
.PARAMETER UseTsinghuaMirror
  pip 使用清华镜像（国内加速）
#>
param(
    [string]$Proxy = "http://127.0.0.1:7897",
    [switch]$SkipDshInstall,
    [switch]$SkipPythonPackages,
    [switch]$UseTsinghuaMirror
)

$ErrorActionPreference = 'Continue'
$Repo = "https://github.com/honghufox/dsh-bio-research-preset"
$PresetDir = "$env:USERPROFILE\.dsh\.agent-presets\bio-research"
$CloneDir  = "$env:USERPROFILE\Desktop\dsh-bio-research-preset"

function Step($title) { Write-Host "`n==== $title ====" -ForegroundColor Cyan }
function Ok($msg)     { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Warn($msg)   { Write-Host "  [!!] $msg" -ForegroundColor Yellow }

Step "0/6 环境检查"
$node = node -v 2>$null
$npm  = npm -v  2>$null
if ($node -and $npm) { Ok "Node $node / npm $npm" }
else { Warn "未检测到 Node.js，请先到 https://nodejs.org 安装 LTS 版（勾选 Add to PATH）后重试"; exit 1 }

Step "1/6 安装 DSH（全局）"
if (-not $SkipDshInstall) {
    npm install -g @deepseek-ai/dsh 2>&1 | Out-Host
    $dsh = (Get-Command dsh -ErrorAction SilentlyContinue)
    if ($dsh) { Ok "dsh 已安装" } else { Warn "dsh 安装可能未完成，请检查 npm 输出" }
} else { Ok "已跳过（-SkipDshInstall）" }

Step "2/6 克隆 bio-research 预设仓库"
$env:HTTPS_PROXY = $Proxy; $env:HTTP_PROXY = $Proxy
if (Test-Path $CloneDir) { Remove-Item $CloneDir -Recurse -Force }
git clone $Repo $CloneDir 2>&1 | Out-Host
if (Test-Path "$CloneDir\agent.cordis.yml") { Ok "克隆成功：$CloneDir" } else { Warn "克隆失败，请确认代理 $Proxy 可用（或改用 -Proxy 参数）" }

Step "3/6 安装预设到 DSH"
if (Test-Path "$CloneDir\agent.cordis.yml") {
    New-Item -ItemType Directory -Force "$env:USERPROFILE\.dsh\.agent-presets" | Out-Null
    if (Test-Path $PresetDir) { Remove-Item $PresetDir -Recurse -Force }
    Copy-Item $CloneDir $PresetDir -Recurse
    Ok "已复制到 $PresetDir（重启 dsh web 后生效）"
} else { Warn "跳过：预设未克隆成功" }

Step "4/6 Python 科研包"
if (-not $SkipPythonPackages) {
    $env:NO_PROXY = '*'; $env:no_proxy = '*'
    $pipArgs = @('install','--user','pandas','numpy','scipy','statsmodels','seaborn','scikit-learn','biopython','lifelines','vcfpy','pyfaidx','python-docx','requests','ncbi-mcp','mcp>=1.0,<2')
    if ($UseTsinghuaMirror) { $pipArgs += '-i'; $pipArgs += 'https://pypi.tuna.tsinghua.edu.cn/simple' }
    python -m pip install @pipArgs 2>&1 | Select-Object -Last 3 | Out-Host
    python -c "import scipy,lifelines,vcfpy; print('  科学包 OK')" 2>&1 | Out-Host
} else { Ok "已跳过（-SkipPythonPackages）" }

Step "5/6 MCP 服务器依赖"
foreach ($mcp in @('biotools','zotero')) {
    $dir = "$PresetDir\tools\$mcp"
    if (Test-Path "$dir\package.json") {
        Write-Host "  安装 $mcp ..."
        Push-Location $dir
        npm install --ignore-scripts --no-audit --no-fund 2>&1 | Select-Object -Last 1 | Out-Host
        Pop-Location
    }
}
$bio = Test-Path "$PresetDir\tools\biotools\node_modules\bach-biotools-server\build\index.js"
$zot = Test-Path "$PresetDir\tools\zotero\node_modules\mcp-zotero\build\server.js"
if ($bio) { Ok "biotools MCP 就绪" } else { Warn "biotools 依赖未装好，请手动在 tools\biotools 下 npm install --ignore-scripts" }
if ($zot) { Ok "zotero MCP 就绪" } else { Warn "zotero 依赖未装好（可稍后启用时再装）" }

Step "6/6 剩余手动步骤"
Write-Host @"

1. 启动 DSH：dsh web  → 打开 http://127.0.0.1:3080
2. Settings → Models → 填入 DeepSeek API Key
3. 新会话选择预设「生物科研模式」
4. R 包（R 控制台）：
     options(repos=c(CRAN='https://mirrors.tuna.tsinghua.edu.cn/CRAN/'))
     install.packages(c('vcfR','survminer','survivalROC','timeROC','rms','cmprsk','forestplot'))
     if(!requireNamespace('BiocManager',quietly=TRUE)) install.packages('BiocManager')
     BiocManager::install('biomaRt')
5. 编辑 $PresetDir\agent.cordis.yml：
     - NCBI_EMAIL 换成你的真实邮箱
     - Zotero：填入 ZOTERO_API_KEY / ZOTERO_USER_ID 并删除该行 disabled: true
6. 可选：TinyTeX（LaTeX）与 pandoc，见《新机器部署指南.md》
7. git 身份：git config --global user.name "honghufox" / user.email "你的邮箱"
"@
Write-Host "完成。遇到问题参考《新机器部署指南.md》常见问题表。" -ForegroundColor Green

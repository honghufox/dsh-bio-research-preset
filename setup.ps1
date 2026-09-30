<#
  生物科研模式（含 LSF 集群执行） 预设的安装脚本。

  1) 重建随 bundle 分发但未提交的依赖产物（node_modules），并校验真正的构建产物；
  2) 检查并按需安装 Python 侧的 MCP 依赖（ncbi-mcp、Tavotto 引擎）；
  3) 把本 bundle 写进 desktop profile 的 dependencies 与 dsh.profile.bundles。

  为什么有第 2 步：DSH 0.2 不再读取 package.json 里的 dsh.install（0.1.x 的
  「安装后自动重建」机制已移除），所以这些依赖只能在这里固化，否则换机重装时
  预设仍会挂载成功、但对应 MCP 服务器起不来。

  用法：
    powershell -ExecutionPolicy Bypass -File setup.ps1 [-ProfileDir <路径>] [-SkipPythonTools]
#>
[CmdletBinding()]
param(
  [string]$ProfileDir,
  [switch]$SkipPythonTools
)

$ErrorActionPreference = 'Stop'
$bundleName = 'bio-research-preset'
$bundleDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not $ProfileDir) {
  $ProfileDir = Join-Path $env:USERPROFILE '.dsh\profiles\desktop'
}
if (-not (Test-Path $ProfileDir)) {
  throw "找不到 profile 目录：$ProfileDir（DSH 桌面版至少启动过一次才会有）"
}

Write-Host "bundle  : $bundleDir"
Write-Host "profile : $ProfileDir"

# ---- 1) 重建依赖 ----
# `artifact` 是预设行真正会 spawn 的文件：node_modules 存在不等于装好了，
# 少一次构建就会让 mcp-client 起不来，所以这里单独校验。
$rebuilds = @(
  @{ dir = 'presets/bio-research/tools/biotools'; artifact = 'node_modules/bach-biotools-server/build/index.js' },
  @{ dir = 'presets/bio-research/tools/zotero';   artifact = 'node_modules/mcp-zotero/build/server.js' }
)
foreach ($item in $rebuilds) {
  $relative = $item.dir
  $target = Join-Path $bundleDir ($relative -replace '/', '\')
  if (-not (Test-Path (Join-Path $target 'package.json'))) {
    Write-Warning "跳过（无 package.json）：$target"
    continue
  }
  if (Test-Path (Join-Path $target $item.artifact)) {
    Write-Host "已就绪  : $relative"
    continue
  }
  Write-Host "安装中  : $relative"
  Push-Location $target
  try { & npm install --omit=dev } finally { Pop-Location }
  if (Test-Path (Join-Path $target $item.artifact)) {
    Write-Host "已构建  : $($item.artifact)"
  } else {
    Write-Warning "缺构建产物：$relative\$($item.artifact)（MCP 服务器会起不来，请手动检查该包的 build 脚本）"
  }
}

# ---- 2) Python 侧依赖 ----
# 判据取「预设行真正需要的那一步」，不是笼统的 import：
#   ncbi  —— run-ncbi-mcp.py 直接 `from ncbi_mcp.server import main`，且需要 mcp SDK 1.x；
#   tavotto —— 启动器按 TAVOTTO_MCP_PYTHON → TAVOTTO_WORKER_PYTHON → 插件自管 venv → python
#              的顺序挑解释器，所以把自管 venv 建好就等于给预设行一个可用 command。
function Test-PythonImport {
  param([string]$Python, [string]$Statement)
  $previous = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try {
    & $Python -c $Statement *> $null
    return ($LASTEXITCODE -eq 0)
  } catch {
    return $false
  } finally {
    $ErrorActionPreference = $previous
  }
}

if ($SkipPythonTools) {
  Write-Host 'Python  : 已跳过（-SkipPythonTools）'
} else {
  $python = (Get-Command python -ErrorAction SilentlyContinue).Source
  if (-not $python) {
    Write-Warning '找不到 python；ncbi 与 tavotto 两个 MCP 服务器会起不来（预设仍可挂载，failOnStartupError=false）'
  } else {
    # ncbi-mcp（PyPI）+ mcp SDK 1.x（2.x 移除了 FastMCP API）
    if (Test-PythonImport -Python $python -Statement 'from ncbi_mcp.server import main') {
      Write-Host '已就绪  : ncbi-mcp'
    } else {
      Write-Host "安装中  : ncbi-mcp（$python -m pip install --user ncbi-mcp 'mcp>=1.0,<2'）"
      & $python -m pip install --user ncbi-mcp 'mcp>=1.0,<2'
      if (Test-PythonImport -Python $python -Statement 'from ncbi_mcp.server import main') {
        Write-Host '已就绪  : ncbi-mcp'
      } else {
        Write-Warning 'ncbi-mcp 安装后仍无法导入；mcp__ncbi__* 工具会缺失'
      }
    }

    # Tavotto 引擎：优先用插件自管 venv（预设行的 command 会挑到它）
    $tavottoServer = Join-Path $bundleDir 'presets\bio-research\tools\tavotto\mcp\server.py'
    $managed = Join-Path $env:APPDATA 'Tavotto\mcp-runtime\venv\Scripts\python.exe'
    $engineReady = (Test-Path $managed) -and (Test-PythonImport -Python $managed -Statement 'import tavotto.engine')
    if ($engineReady) {
      Write-Host '已就绪  : Tavotto 引擎（自管 venv）'
    } elseif (Test-Path $tavottoServer) {
      Write-Host '安装中  : Tavotto 引擎（python mcp/server.py --provision）'
      & $python $tavottoServer --provision
      if ((Test-Path $managed) -and (Test-PythonImport -Python $managed -Statement 'import tavotto.engine')) {
        Write-Host '已就绪  : Tavotto 引擎（自管 venv）'
      } else {
        Write-Warning 'Tavotto 引擎未就绪；预设仍可挂载，但工具列表里只会有 tavotto_health（改完需重启 dsh）'
      }
    } else {
      Write-Warning "找不到 $tavottoServer"
    }
  }
}

# ---- 3) 安装随 bundle 分发的宿主插件 ----
# 预设声明里的插件行按包名解析，所以插件必须进 profile 的 node_modules。
$pluginRoot = Join-Path $bundleDir 'presets\bio-research\plugins'
$plugins = @()
if (Test-Path $pluginRoot) {
  $plugins = Get-ChildItem -Directory $pluginRoot | Where-Object { Test-Path (Join-Path $_.FullName 'package.json') }
}
if ($plugins.Count -eq 0) {
  Write-Host '插件    : 无需安装'
} else {
  foreach ($plugin in $plugins) {
    Write-Host "插件    : $($plugin.Name) -> $($plugin.FullName)"
  }
}

# ---- 4) 写入 profile 清单 ----
$manifestPath = Join-Path $ProfileDir 'package.json'
if (-not (Test-Path $manifestPath)) { throw "找不到 profile 清单：$manifestPath" }
Copy-Item $manifestPath "$manifestPath.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')" -Force

$manifest = Get-Content $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $manifest.dependencies) {
  $manifest | Add-Member -NotePropertyName dependencies -NotePropertyValue ([pscustomobject]@{}) -Force
}
$manifest.dependencies | Add-Member -NotePropertyName $bundleName -NotePropertyValue "link:./local-bundles/$bundleName" -Force
foreach ($plugin in $plugins) {
  $uri = 'file:' + ($plugin.FullName -replace '\\', '/')
  $manifest.dependencies | Add-Member -NotePropertyName $plugin.Name -NotePropertyValue $uri -Force
}

if (-not $manifest.dsh) { $manifest | Add-Member -NotePropertyName dsh -NotePropertyValue ([pscustomobject]@{}) -Force }
if (-not $manifest.dsh.profile) { $manifest.dsh | Add-Member -NotePropertyName profile -NotePropertyValue ([pscustomobject]@{}) -Force }
$bundles = @()
if ($manifest.dsh.profile.bundles) { $bundles = @($manifest.dsh.profile.bundles) }
if ($bundles -notcontains $bundleName) { $bundles += $bundleName }
$manifest.dsh.profile | Add-Member -NotePropertyName bundles -NotePropertyValue $bundles -Force

$manifest | ConvertTo-Json -Depth 100 | Set-Content $manifestPath -Encoding UTF8
Write-Host "清单已写入: $manifestPath"

# ---- 5) 让 profile 的 node_modules 生效 ----
if ($plugins.Count -gt 0) {
  Write-Host ''
  Write-Host '正在安装插件依赖（在 profile 目录执行 pnpm install）…'
  Push-Location $ProfileDir
  try {
    & pnpm install
    if ($LASTEXITCODE -ne 0) {
      Write-Warning "pnpm install 返回 $LASTEXITCODE；请在 $ProfileDir 手动执行 pnpm install"
    }
  } catch {
    Write-Warning "pnpm 不可用（$_）；请在 $ProfileDir 手动执行 pnpm install"
  } finally { Pop-Location }
}

Write-Host ''
Write-Host '完成。重启 DSH 后，新建会话即可选择该预设。'

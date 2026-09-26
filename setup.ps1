<#
  生物科研模式（含 LSF 集群执行） 预设的安装脚本。

  1) 重建随 bundle 分发但未提交的依赖产物（node_modules）；
  2) 把本 bundle 写进 desktop profile 的 dependencies 与 dsh.profile.bundles。

  用法：powershell -ExecutionPolicy Bypass -File setup.ps1 [-ProfileDir <路径>]
#>
[CmdletBinding()]
param(
  [string]$ProfileDir
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
$rebuilds = @('presets/bio-research/tools/biotools', 'presets/bio-research/tools/zotero')
if ($rebuilds.Count -eq 0) {
  Write-Host '依赖    : 无需重建'
} else {
  foreach ($relative in $rebuilds) {
    $target = Join-Path $bundleDir ($relative -replace '/', '\')
    if (-not (Test-Path (Join-Path $target 'package.json'))) {
      Write-Warning "跳过（无 package.json）：$target"
      continue
    }
    if (Test-Path (Join-Path $target 'node_modules')) {
      Write-Host "已就绪  : $relative"
      continue
    }
    Write-Host "安装中  : $relative"
    Push-Location $target
    try { & npm install --omit=dev } finally { Pop-Location }
  }
}

# ---- 2) 安装随 bundle 分发的宿主插件 ----
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

# ---- 3) 写入 profile 清单 ----
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

# ---- 4) 让 profile 的 node_modules 生效 ----
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

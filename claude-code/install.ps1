$ErrorActionPreference = 'Stop'

$ScriptDir = $PSScriptRoot
$Target = $env:AUTOMIX_LIGHT_MARKETPLACE_DIR
if (-not $Target) {
  $Target = Join-Path $HOME '.claude-marketplaces\automix-light-en'
}

Write-Output 'automix-light-en installer'
Write-Output '-------------------------------------------------'
Write-Output "From: $ScriptDir"
Write-Output "To:   $Target"
Write-Output ''

$Marketplace = Join-Path $ScriptDir '.claude-plugin\marketplace.json'
if (-not (Test-Path -LiteralPath $Marketplace -PathType Leaf)) {
  [Console]::Error.WriteLine("Error: $Marketplace not found.")
  [Console]::Error.WriteLine('       Run claude-code\install.ps1 from the repository (for example, powershell -ExecutionPolicy Bypass -File claude-code\install.ps1).')
  exit 1
}

foreach ($pair in @(
    @($Marketplace, 'marketplace.json'),
    @((Join-Path $ScriptDir 'aml\.claude-plugin\plugin.json'), 'plugin.json'))) {
  try {
    Get-Content -LiteralPath $pair[0] -Raw -Encoding UTF8 | ConvertFrom-Json | Out-Null
  } catch {
    [Console]::Error.WriteLine("Error: $($pair[1]) is not valid JSON.")
    exit 1
  }
}

$Parent = Split-Path -Parent $Target
if ($Parent) { New-Item -ItemType Directory -Force -Path $Parent | Out-Null }
if (Test-Path -LiteralPath $Target -PathType Container) {
  $Backup = "$Target.bak"
  Write-Output "Backing up the existing install to $Backup"
  if (Test-Path -LiteralPath $Backup) { Remove-Item -LiteralPath $Backup -Recurse -Force }
  Move-Item -LiteralPath $Target -Destination $Backup
}
New-Item -ItemType Directory -Force -Path $Target | Out-Null
Copy-Item -LiteralPath (Join-Path $ScriptDir '.claude-plugin') -Destination $Target -Recurse
Copy-Item -LiteralPath (Join-Path $ScriptDir 'aml') -Destination $Target -Recurse

$ShowTarget = (Resolve-Path -LiteralPath $Target).ProviderPath -replace '\\', '/'
Write-Output @"
Copied: $ShowTarget

Next, run these inside Claude Code:

  1. Add the marketplace:
     /plugin marketplace add $ShowTarget

  2. Install the plugin:
     /plugin install aml@automix-light-en

  3. Check:
     /help                  # look for /aml:new, /aml:go, /aml:review, /aml:next

"@

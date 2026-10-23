<#
  一键重新生成头图
  用法：在终端里执行  .\build.ps1  （或用「使用 PowerShell 运行」）
  前置：装有 Chrome 或 Edge，Windows 自带 Edge 就够
#>
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$html = Join-Path $here 'hero.html'
$out  = Join-Path (Split-Path -Parent $here) 'hero.png'

if (-not (Test-Path $html)) { throw '找不到 hero.html' }

$browser = @(
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
  "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $browser) { throw '没找到 Chrome / Edge，请先安装其中一个' }

$tmp = Join-Path $env:TEMP ('hero_' + [guid]::NewGuid().ToString('N') + '.png')
$uri = 'file:///' + ($html -replace '\\', '/')

Write-Host ('正在用 ' + (Split-Path -Leaf $browser) + ' 渲染 ...')
$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $browser --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 --default-background-color=00000000 --window-size=1280,360 --screenshot="$tmp" $uri 2>&1 | Out-Null
$ErrorActionPreference = $prevEap

for ($i = 0; $i -lt 40 -and -not (Test-Path $tmp); $i++) { Start-Sleep -Milliseconds 250 }
if (-not (Test-Path $tmp)) { throw '浏览器没有生成截图，可能被杀毒软件拦了' }

Copy-Item $tmp $out -Force
Remove-Item $tmp -Force
$size = (Get-Item $out).Length / 1KB
Write-Host ('完成 -> ' + $out + '  (' + [math]::Round($size) + ' KB, 2560x720)')
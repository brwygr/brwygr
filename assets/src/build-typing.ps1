<#
  重新生成粒子辉光动画
  用法：在 assets/src 里右键 build-typing.ps1 → 使用 PowerShell 运行
  改文字/颜色/速度：编辑同目录的 typing.json
#>
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$json = Join-Path $here 'typing.json'
$gen  = Join-Path $here 'gen_typing.py'
$out  = Join-Path (Split-Path -Parent $here) 'typing.svg'

$py = 'C:\Users\Y9000P\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
if (-not (Test-Path $py)) {
  $cmd = Get-Command python -ErrorAction SilentlyContinue
  if (-not $cmd) { throw '没找到 Python，请先安装并加入 PATH' }
  $py = $cmd.Source
}

& $py -c "import fontTools" 2>$null
if ($LASTEXITCODE -ne 0) { throw '缺少 fontTools，请先运行：python -m pip install fonttools' }

Write-Host '正在生成 ...'
& $py $gen --config $json --out $out
if ($LASTEXITCODE -ne 0) { throw '生成失败，检查 typing.json 的格式' }
Write-Host ('完成 -> ' + $out)
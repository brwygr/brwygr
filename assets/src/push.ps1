<#
  一键：重建粒子动画 → 提交 → 推送
  用法（在 assets\src 目录下，整行复制）：
    .\push.ps1 "update typing"
  不写说明也可以：
    .\push.ps1
#>
param([string]$Msg = "update")

$src  = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent (Split-Path -Parent $src)

Write-Host "1/3 重建粒子动画 ..." -ForegroundColor Cyan
& (Join-Path $src "build-typing.ps1")

Write-Host "2/3 提交 ..." -ForegroundColor Cyan
Set-Location $root
git add -A
git commit -m $Msg
if ($LASTEXITCODE -ne 0) {
  Write-Host "没有可提交的改动（typing.svg 也没变），继续执行推送。" -ForegroundColor Yellow
}

Write-Host "3/3 推送 ..." -ForegroundColor Cyan
git push
if ($LASTEXITCODE -eq 0) {
  Write-Host "完成：已推到 GitHub。页面最多 5 分钟后刷新，急的话 Ctrl + F5。" -ForegroundColor Green
} else {
  Write-Host "推送失败，看上面的英文报错；常见原因是网络或需要先 git pull。" -ForegroundColor Red
}
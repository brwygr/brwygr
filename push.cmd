@echo off
setlocal
chcp 65001 >nul
set "ROOT=%~dp0"
set "MSG=%~1"
if "%MSG%"=="" set "MSG=update"

echo.
echo [1/3] rebuilding typing.svg ...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%assets\src\build-typing.ps1"
if errorlevel 1 goto :fail

echo.
echo [2/3] commit ...
cd /d "%ROOT%"
git add -A
git commit -m "%MSG%"
if errorlevel 1 echo   (nothing to commit, continue)

echo.
echo [3/3] push ...
git push
if errorlevel 1 goto :fail

echo.
echo DONE - pushed to GitHub. The page refreshes within 5 minutes.
echo.
pause
exit /b 0

:fail
echo.
echo FAILED - read the message above.
echo.
pause
exit /b 1
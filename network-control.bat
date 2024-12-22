@echo off
title Network Control Panel

REM Check admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Error: Administrator rights required!
    echo Please run this script as administrator.
    pause
    exit /b 1
)

:menu
cls
echo Current port forwarding status:
netsh interface portproxy show all
echo.
echo Select operation:
echo 1. Enable port forwarding and firewall rule
echo 2. Disable port forwarding and firewall rule
echo 3. Show current status
echo 4. Exit
set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" goto enable
if "%choice%"=="2" goto disable
if "%choice%"=="3" goto status
if "%choice%"=="4" goto end
goto menu

:enable
echo.
echo Enabling port forwarding and firewall rule...
netsh interface portproxy reset
netsh interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress=172.26.8.203
netsh advfirewall firewall delete rule name="Allow Port 8000" >nul 2>&1
netsh advfirewall firewall add rule name="Allow Port 8000" dir=in action=allow protocol=TCP localport=8000
echo.
echo Current status:
netsh interface portproxy show all
pause
goto menu

:disable
echo.
echo Disabling port forwarding and firewall rule...
netsh interface portproxy reset
netsh advfirewall firewall delete rule name="Allow Port 8000" >nul 2>&1
echo.
echo Current status:
netsh interface portproxy show all
pause
goto menu

:status
echo.
echo Port forwarding status:
netsh interface portproxy show all
echo.
echo Firewall rule status:
netsh advfirewall firewall show rule name="Allow Port 8000"
pause
goto menu

:end
exit /b 0

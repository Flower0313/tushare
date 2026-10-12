@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Tushare 数据平台启动器

set "PROJECT_ROOT=C:\Users\flowe\Documents\ChatGPT\tushare"
set "BACKEND_DIR=%PROJECT_ROOT%\backend"
set "FRONTEND_DIR=%PROJECT_ROOT%\frontend"
set "ENV_FILE=%PROJECT_ROOT%\.env"

if not exist "%PROJECT_ROOT%" (
    echo [错误] 找不到项目目录：%PROJECT_ROOT%
    pause
    exit /b 1
)

if not exist "%ENV_FILE%" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PROJECT_ROOT%\scripts\initialize-env.ps1" -ProjectRoot "%PROJECT_ROOT%"
    if errorlevel 1 (
        echo [错误] 环境配置失败，平台未启动。
        pause
        exit /b 1
    )
)

if not exist "%BACKEND_DIR%\.venv\Scripts\uvicorn.exe" (
    echo [错误] 后端虚拟环境不存在：%BACKEND_DIR%\.venv
    echo 请先按照 README 安装后端依赖。
    pause
    exit /b 1
)

if not exist "%FRONTEND_DIR%\node_modules" (
    echo [错误] 前端依赖尚未安装：%FRONTEND_DIR%\node_modules
    echo 请先在 frontend 目录运行 npm install。
    pause
    exit /b 1
)

echo 正在启动 Tushare 数据平台...

powershell.exe -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
if errorlevel 1 (
    start "Tushare Backend" /D "%BACKEND_DIR%" cmd.exe /k "set RUN_EMBEDDED_WORKER=false&& .venv\Scripts\alembic.exe upgrade head && .venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8000"
) else (
    echo 后端端口 8000 已在监听，跳过重复启动。
)

tasklist /FI "WINDOWTITLE eq Tushare Worker" | find /I "cmd.exe" >nul
if errorlevel 1 (
    start "Tushare Worker" /D "%BACKEND_DIR%" cmd.exe /k ".venv\Scripts\python.exe -m app.worker"
) else (
    echo Worker 已在运行，跳过重复启动。
)

tasklist /FI "WINDOWTITLE eq Tushare Scheduler" | find /I "cmd.exe" >nul
if errorlevel 1 (
    start "Tushare Scheduler" /D "%BACKEND_DIR%" cmd.exe /k ".venv\Scripts\python.exe -m app.scheduler"
) else (
    echo Scheduler 已在运行，跳过重复启动。
)

tasklist /FI "WINDOWTITLE eq Tushare Maintenance" | find /I "cmd.exe" >nul
if errorlevel 1 (
    start "Tushare Maintenance" /D "%BACKEND_DIR%" cmd.exe /k ".venv\Scripts\python.exe -m app.maintenance"
) else (
    echo Maintenance 已在运行，跳过重复启动。
)

powershell.exe -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
if errorlevel 1 (
    start "Tushare Frontend" /D "%FRONTEND_DIR%" cmd.exe /k "npm run dev"
) else (
    echo 前端端口 5173 已在监听，跳过重复启动。
)

start "" powershell.exe -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 4; Start-Process 'http://localhost:5173/apis'"

echo 启动命令已发送，浏览器将在几秒后打开。
timeout /t 2 /nobreak >nul
exit /b 0

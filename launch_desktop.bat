@echo off
rem =====================================================================
rem MAK - Autonomous Cognitive Core (Unified One-Click Launcher)
rem Starts FastAPI Backend + Vite Dev Server + Electron Native Desktop App
rem =====================================================================
title MAK // Autonomous Cognitive Core Launcher
color 0B

echo =====================================================================
echo                MAK // AUTONOMOUS COGNITIVE CORE
echo       Starting Headless FastAPI Backend ^& Electron Desktop App
echo =====================================================================
echo.

if exist "%~dp0.venv\Scripts\activate.bat" (
    echo [Launcher] Activating Python virtual environment...
    call "%~dp0.venv\Scripts\activate.bat"
)

cd /d "%~dp0desktop_client"

if not exist "node_modules" (
    echo [Launcher] Installing desktop client dependencies...
    call npm install
)

echo [Launcher] Initializing FastAPI Server ^& MAK Desktop OS...
call npm run electron:dev


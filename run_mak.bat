@echo off
rem =====================================================================
rem MAK Enterprise OS - One-Click Streamlit Dashboard Launcher
rem =====================================================================

rem Change to the project root directory where this script resides
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" goto use_venv
if exist ".venv\Scripts\streamlit.exe" goto use_venv_streamlit
goto use_system

:use_venv
call .venv\Scripts\activate.bat
".venv\Scripts\python.exe" -m streamlit run app.py
goto end

:use_venv_streamlit
".venv\Scripts\streamlit.exe" run app.py
goto end

:use_system
python -m streamlit run app.py
goto end

:end

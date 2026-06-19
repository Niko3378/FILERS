@echo off
chcp 65001 >nul
cd /d "%~dp0filers"
python main.py
pause

@echo off
python installer.py
if errorlevel 1 (
    echo.
    echo Python introuvable. Telechargez-le sur https://www.python.org/downloads/
    echo Cochez "Add Python to PATH" lors de l'installation.
    pause
)

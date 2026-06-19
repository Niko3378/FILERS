@echo off
chcp 65001 >nul
echo.
echo ================================================
echo   FILERS - Diagnostic et reparation
echo ================================================
echo.

:: --- Python ---
echo [1] Verification de Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo     ERREUR : Python introuvable dans le PATH.
    echo     Telechargez Python sur https://www.python.org
    goto :fin
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo     OK : %%v
for /f "tokens=*" %%p in ('python -c "import sys; print(sys.executable)"') do set PYEXE=%%p
echo     Executable : %PYEXE%
echo.

:: --- Chercher FILERS ---
echo [2] Recherche de l'installation FILERS...
set FOUND=
set FILERS_DIR=

for %%D in (
    "%LOCALAPPDATA%\FILERS"
    "%USERPROFILE%\FILERS"
    "C:\FILERS"
    "C:\Program Files\FILERS"
    "C:\Program Files (x86)\FILERS"
    "%USERPROFILE%\Desktop\FILERS"
    "%USERPROFILE%\Documents\FILERS"
) do (
    if exist "%%~D\filers\main.py" (
        set FILERS_DIR=%%~D
        set FOUND=1
        echo     Trouve : %%~D
    )
)

if not defined FOUND (
    echo     Non trouve dans les emplacements standards.
    echo.
    echo     Entrez le chemin d'installation complet :
    set /p FILERS_DIR="     > "
    if not exist "%FILERS_DIR%\filers\main.py" (
        echo.
        echo     ERREUR : main.py introuvable dans %FILERS_DIR%\filers\
        echo     Relancez install.exe pour reinstaller.
        goto :fin
    )
)
echo.

:: --- Verifier les dependances ---
echo [3] Verification des dependances Python...
set MISSING=

python -c "import PyQt6" >nul 2>&1
if errorlevel 1 ( echo     MANQUANT : PyQt6 & set MISSING=%MISSING% PyQt6 ) else ( echo     OK : PyQt6 )

python -c "import paramiko" >nul 2>&1
if errorlevel 1 ( echo     MANQUANT : paramiko & set MISSING=%MISSING% paramiko ) else ( echo     OK : paramiko )

python -c "import smb" >nul 2>&1
if errorlevel 1 ( echo     MANQUANT : pysmb & set MISSING=%MISSING% pysmb ) else ( echo     OK : pysmb )

python -c "import chardet" >nul 2>&1
if errorlevel 1 ( echo     MANQUANT : chardet & set MISSING=%MISSING% chardet ) else ( echo     OK : chardet )

python -c "import fitz" >nul 2>&1
if errorlevel 1 ( echo     MANQUANT : PyMuPDF & set MISSING=%MISSING% PyMuPDF ) else ( echo     OK : PyMuPDF )

echo.

:: --- Installer les manquants ---
if defined MISSING (
    echo [4] Installation des paquets manquants :%MISSING%
    pip install %MISSING%
    echo.
) else (
    echo [4] Toutes les dependances sont presentes.
    echo.
)

:: --- Creer / corriger le lanceur ---
echo [5] Creation du lanceur FILERS.bat...
(
    echo @echo off
    echo cd /d "%FILERS_DIR%\filers"
    echo start "" "%PYEXE%" main.py
) > "%FILERS_DIR%\FILERS.bat"
echo     Cree : %FILERS_DIR%\FILERS.bat
echo.

:: --- Test de lancement ---
echo [6] Test de lancement...
echo     Demarrage de FILERS dans 3 secondes...
timeout /t 3 /nobreak >nul
start "" "%PYEXE%" "%FILERS_DIR%\filers\main.py"
echo.
echo     Si FILERS ne s'ouvre pas, lancez le test en mode debug :
echo     python "%FILERS_DIR%\filers\main.py"
echo.

:fin
echo ================================================
pause

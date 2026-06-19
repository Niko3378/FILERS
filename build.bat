@echo off
echo.
echo ================================================
echo   Files Manager - Compilation (2 etapes)
echo ================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python introuvable.
    pause
    exit /b 1
)

echo Installation de PyInstaller...
pip install pyinstaller --quiet
echo [OK] PyInstaller disponible.
echo.

:: ---- Etape 1 : FILERS.exe (application) ----
echo [1/2] Compilation de Files Manager.exe...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "Files Manager" ^
    --icon "filers\icon.ico" ^
    --add-data "filers\icon.ico;." ^
    --paths "filers" ^
    --hidden-import "smb.SMBConnection" ^
    --hidden-import "nmb.NetBIOS" ^
    --collect-all "pysmb" ^
    --hidden-import "win32security" ^
    --hidden-import "win32api" ^
    --hidden-import "win32con" ^
    --hidden-import "ntsecuritycon" ^
    --hidden-import "pywintypes" ^
    "filers\main.py"

if errorlevel 1 (
    echo.
    echo [ERREUR] Compilation de Files Manager.exe echouee.
    pause
    exit /b 1
)
echo [OK] dist\Files Manager.exe
echo.

:: ---- Etape 2 : install.exe (installateur) ----
echo [2/2] Compilation de install.exe...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "install" ^
    --add-binary "dist\Files Manager.exe;." ^
    --hidden-import "tkinter" ^
    --hidden-import "tkinter.ttk" ^
    --hidden-import "tkinter.filedialog" ^
    --hidden-import "tkinter.messagebox" ^
    installer.py

if errorlevel 1 (
    echo.
    echo [ERREUR] Compilation de install.exe echouee.
    pause
    exit /b 1
)

echo.
echo ================================================
echo   Compilation terminee !
echo   Distribuer uniquement : dist\install.exe
echo ================================================
echo.
if exist dist\install.exe (
    for %%F in ("dist\Files Manager.exe") do echo   Files Manager.exe : %%~zF octets
    for %%F in (dist\install.exe) do echo   install.exe : %%~zF octets
)
echo.
pause

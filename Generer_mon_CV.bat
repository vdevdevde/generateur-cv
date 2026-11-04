@echo off
rem ==========================================================================
rem  Double-cliquez sur ce fichier pour créer votre CV en PDF.
rem  (Vous pouvez aussi glisser un autre fichier .yaml sur ce fichier.)
rem ==========================================================================
chcp 65001 >nul
cd /d "%~dp0"

rem --- Trouver Python ---------------------------------------------------------
set "PYTHON="
where py >nul 2>nul && set "PYTHON=py"
if not defined PYTHON (
    where python >nul 2>nul && set "PYTHON=python"
)
if not defined PYTHON (
    echo Python n'est pas installe sur cet ordinateur.
    echo Installez-le depuis https://www.python.org/downloads/ puis relancez.
    pause
    exit /b 1
)

rem --- Premiere utilisation : preparation (une seule fois) --------------------
if not exist ".venv\Scripts\python.exe" (
    echo Premiere utilisation : installation des outils necessaires...
    echo Cela prend une minute, une seule fois.
    %PYTHON% -m venv .venv || goto erreur
    ".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r requirements.txt || goto erreur
    echo.
)

rem --- Generation du CV -------------------------------------------------------
".venv\Scripts\python.exe" generer_cv.py %1
echo.
pause
exit /b 0

:erreur
echo.
echo L'installation a echoue. Verifiez votre connexion Internet puis relancez.
rem En cas de nouvel essai, on repart de zero.
rmdir /s /q .venv 2>nul
pause
exit /b 1

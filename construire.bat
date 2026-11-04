@echo off
rem ================================================================
rem  Fabrique l'application Windows : dist\GenerateurCV\GenerateurCV.exe
rem  Double-clique sur ce fichier pour reconstruire apres une modification.
rem ================================================================
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Preparation des outils, une seule fois : quelques minutes...
    py -m venv .venv || goto erreur
    ".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r requirements.txt || goto erreur
)

echo [1/3] Creation de l'icone...
.venv\Scripts\python.exe outils\creer_icone.py || goto erreur

echo [2/3] Fabrication de l'application (1 a 3 minutes)...
.venv\Scripts\pyinstaller.exe --noconfirm --clean --windowed ^
  --name GenerateurCV ^
  --icon ressources\icone.ico ^
  --add-data "ressources;ressources" ^
  --add-data "modeles;modeles" ^
  --add-data "mon_cv.yaml;." ^
  --exclude-module tkinter ^
  lancer.py || goto erreur

echo [3/3] Allegement...
.venv\Scripts\python.exe outils\alleger.py || goto erreur

echo.
echo Termine ! L'application est dans : dist\GenerateurCV\GenerateurCV.exe
pause
exit /b 0

:erreur
echo.
echo Une erreur est survenue pendant la fabrication.
pause
exit /b 1

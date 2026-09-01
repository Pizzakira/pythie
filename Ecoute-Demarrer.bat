@echo off
chcp 65001 >nul
title Pythie - ecoute de controle

set "PYTHIE=%~dp0"
set "KMP_DUPLICATE_LIB_OK=TRUE"
cd /d "%PYTHIE%"

echo.
echo   PYTHIE - ecoute de controle
echo   La page s'ouvre dans le navigateur ; chaque geste est enregistre
echo   dans data\empreintes\ecoute.json et confirmation.yaml est regenere.
echo   Laissez cette fenetre ouverte pendant l'ecoute. Ctrl+C pour arreter.
echo   ---------------------------------------------------------------
echo.

if not exist "data\ecoute_de_controle.html" (
    echo   Page absente : fabrication...
    python scripts\confirmation_page.py
)

python scripts\ecoute_serveur.py
pause

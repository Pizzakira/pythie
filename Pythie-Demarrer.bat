@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title Pythie - lanceur

set "PYTHIE=%~dp0"
set "LLAMA_BAT=D:\LLM\llama-b10452\Qwen3.8UnslothQ4XL.bat"
set "ENDPOINT=http://127.0.0.1:1234/v1/models"
set "TRANSCRIPT=data\laref2026.json"
set "PLATEAU=data\laref2026.plateau.yaml"

cd /d "%PYTHIE%"

echo.
echo   PYTHIE
echo   Compare une valeur enoncee a une source primaire.
echo   ---------------------------------------------------------------
echo.

:: --- verification des dependances ---------------------------------------
python -c "import pydantic, yaml, numpy" 2>nul
if errorlevel 1 (
    echo   [!] Dependances manquantes. Installation...
    python -m pip install -q -r requirements.txt
    if errorlevel 1 (
        echo   [X] Echec de l'installation. Verifiez votre Python.
        pause
        exit /b 1
    )
)

if not exist "%TRANSCRIPT%" (
    echo   [!] Transcription absente : %TRANSCRIPT%
    echo       Lancez d'abord :
    echo       python scripts\fetch_transcript.py "URL" --sortie %TRANSCRIPT%
    echo.
)

:: --- le serveur modele ---------------------------------------------------
call :check_server
if "%SERVER_UP%"=="1" (
    echo   [ok] llama-server deja en marche sur le port 1234
    goto :menu
)

echo   [.] llama-server eteint.
echo.
choice /c ON /n /m "   Le demarrer maintenant ? [O/N] "
if errorlevel 2 goto :menu

if not exist "%LLAMA_BAT%" (
    echo   [X] Introuvable : %LLAMA_BAT%
    echo       Modifiez LLAMA_BAT en tete de ce fichier.
    pause
    goto :menu
)

echo   [.] Lancement dans une fenetre separee ^(elle reste visible^)...
start "llama-server - Qwen3.8-27B" cmd /k "%LLAMA_BAT%"

echo   [.] Chargement du modele ^(~20 Go, comptez une minute^)...
set /a TRIES=0
:wait
timeout /t 5 /nobreak >nul
set /a TRIES+=1
call :check_server
if "%SERVER_UP%"=="1" (
    echo   [ok] Serveur pret apres !TRIES! tentative^(s^).
    goto :menu
)
if !TRIES! lss 36 (
    echo       ... !TRIES!/36
    goto :wait
)
echo   [X] Le serveur ne repond toujours pas. Regardez sa fenetre.

:: --- menu ----------------------------------------------------------------
:menu
echo.
echo   ---------------------------------------------------------------
echo    1  Chaine SANS modele        instantane, declencheurs seuls
echo    2  Chaine AVEC modele        echantillon de 10 affirmations
echo    3  Chaine AVEC modele        tout ^(173 affirmations, ~2 h^)
echo    4  Ouvrir les resultats      degre 1 et degre 2
echo    5  Etat des dossiers candidats
echo    6  Banc ASR noms propres     necessite l'audio
echo    0  Quitter ^(laisse le serveur tourner^)
echo   ---------------------------------------------------------------
echo.
set "CHOIX="
set /p "CHOIX=   Votre choix : "

if "%CHOIX%"=="1" goto :sans_modele
if "%CHOIX%"=="2" goto :avec_modele_court
if "%CHOIX%"=="3" goto :avec_modele_tout
if "%CHOIX%"=="4" goto :ouvrir
if "%CHOIX%"=="5" goto :dossiers
if "%CHOIX%"=="6" goto :banc
if "%CHOIX%"=="0" exit /b 0
echo   Choix inconnu.
goto :menu

:sans_modele
echo.
python scripts\run_chain.py "%TRANSCRIPT%" --plateau "%PLATEAU%" --out data\chaine --no-model
goto :fin_action

:avec_modele_court
call :check_server
if not "%SERVER_UP%"=="1" (
    echo   [X] Le serveur est eteint. Relancez ce script.
    goto :fin_action
)
echo.
echo   ~40 s par affirmation. Patientez.
python scripts\run_chain.py "%TRANSCRIPT%" --plateau "%PLATEAU%" --out data\chaine --limit 10
goto :fin_action

:avec_modele_tout
call :check_server
if not "%SERVER_UP%"=="1" (
    echo   [X] Le serveur est eteint. Relancez ce script.
    goto :fin_action
)
echo.
echo   173 affirmations a ~40 s = environ deux heures.
choice /c ON /n /m "   Confirmer ? [O/N] "
if errorlevel 2 goto :menu
python scripts\run_chain.py "%TRANSCRIPT%" --plateau "%PLATEAU%" --out data\chaine
goto :fin_action

:ouvrir
if exist "data\chaine_degre1.html" (
    start "" "data\chaine_degre1.html"
    start "" "data\chaine_degre2.html"
    echo   [ok] Ouverts dans le navigateur.
    echo.
    echo   Note : tant que le corpus n'a qu'un domaine, la quasi-totalite
    echo   des passages reste en gris "non verifie". C'est le comportement
    echo   correct - le systeme avoue qu'il ne sait pas - mais la page est
    echo   presque vide.
) else (
    echo   [X] Aucun resultat. Lancez d'abord l'option 1 ou 2.
)
goto :fin_action

:dossiers
echo.
python scripts\coverage_report.py
goto :fin_action

:banc
if not exist "data\audio" (
    echo   [X] Audio absent. Telechargez-le avec :
    echo       rip\yt-dlp-nightly.exe -f bestaudio -o "data\audio\laref2026.%%^(ext^)s" URL
    goto :fin_action
)
echo.
python ETUDES\banc_noms.py
goto :fin_action

:fin_action
echo.
pause
goto :menu

:: --- sous-routine --------------------------------------------------------
:check_server
set "SERVER_UP=0"
powershell -NoProfile -Command ^
  "try { $r = Invoke-WebRequest -Uri '%ENDPOINT%' -TimeoutSec 3 -UseBasicParsing; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 set "SERVER_UP=1"
exit /b 0

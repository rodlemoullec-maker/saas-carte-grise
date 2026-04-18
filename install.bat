@echo off
REM ============================================================
REM  Imatra - Script d'installation Windows
REM
REM  Usage : double-cliquez sur ce fichier
REM  ou dans une invite de commandes : install.bat
REM ============================================================

setlocal enabledelayedexpansion

echo.
echo ================================================================
echo   Imatra - Installation
echo ================================================================
echo.

REM ----- Verifier Docker --------------------------------------------------
echo [1/5] Verification de Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERREUR : Docker n'est pas installe ou n'est pas dans le PATH.
    echo.
    echo Telechargez Docker Desktop ici :
    echo   https://www.docker.com/products/docker-desktop/
    echo.
    pause
    exit /b 1
)
docker info >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERREUR : Docker est installe mais n'est pas demarre.
    echo.
    echo Lancez Docker Desktop puis relancez ce script.
    echo.
    pause
    exit /b 1
)
echo   OK - Docker est installe et demarre

REM ----- Verifier Docker Compose ------------------------------------------
echo [2/5] Verification de Docker Compose...
docker compose version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERREUR : Docker Compose v2 n'est pas disponible.
    echo Mettez a jour Docker Desktop vers la derniere version.
    echo.
    pause
    exit /b 1
)
echo   OK - Docker Compose est disponible

REM ----- Verifier les fichiers nécessaires --------------------------------
echo [3/5] Verification des fichiers...
if not exist "Dockerfile" (
    echo ERREUR : Dockerfile manquant
    pause
    exit /b 1
)
if not exist "docker-compose.yml" (
    echo ERREUR : docker-compose.yml manquant
    pause
    exit /b 1
)
if not exist "requirements.txt" (
    echo ERREUR : requirements.txt manquant
    pause
    exit /b 1
)
echo   OK - Tous les fichiers sont presents

REM ----- Creer le dossier data --------------------------------------------
echo [4/5] Preparation du dossier data...
if not exist "data" (
    mkdir data
    echo   OK - Dossier data\ cree
) else (
    echo   OK - Dossier data\ deja present
)

REM ----- Build et demarrage -----------------------------------------------
echo [5/5] Build et demarrage du conteneur...
echo Cette etape peut prendre entre 5 et 15 minutes au premier lancement.
echo.
docker compose up -d --build
if errorlevel 1 (
    echo.
    echo ERREUR pendant le build ou le demarrage.
    echo Verifiez les logs : docker compose logs imatra
    echo.
    pause
    exit /b 1
)

echo.
echo ================================================================
echo   Imatra est demarre
echo ================================================================
echo.
echo   Ouvrez votre navigateur web et allez a :
echo.
echo      http://localhost:8001
echo.
echo   Commandes utiles :
echo.
echo     docker compose logs -f imatra    : voir les logs
echo     docker compose stop                   : arreter
echo     docker compose start                  : redemarrer
echo     docker compose down                   : arreter et supprimer
echo.
echo   Vos donnees sont stockees dans : .\data\
echo   (a sauvegarder regulierement)
echo.

pause

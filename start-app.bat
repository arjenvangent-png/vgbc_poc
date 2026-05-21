@echo off
REM ============================================================
REM start-app.bat - VGBC POC handmatig of automatisch starten
REM ============================================================
REM Dubbelklik dit bestand om de Streamlit-app te starten.
REM Het PowerShell-venster dat opent moet open blijven zolang
REM de app draait (sluiten = app stopt).
REM
REM Browser opent automatisch op http://localhost:8501
REM ============================================================

cd /d "C:\projects\VGBC\Van Gent BI Consulting\01-dev-poc"

echo.
echo === VGBC POC starten ===
echo Werkmap: %CD%
echo.

REM PostgreSQL-pad toevoegen voor schema-checks vanuit Python
set "PATH=%PATH%;C:\Program Files\PostgreSQL\16\bin"

REM Streamlit-app starten via make.ps1 (zelfde commando als handmatig)
powershell -NoExit -ExecutionPolicy Bypass -Command ".\make.ps1 app"

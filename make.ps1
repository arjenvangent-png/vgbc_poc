# make.ps1 — Windows-equivalent van een Makefile voor de VGBC POC
# Gebruik: .\make.ps1 <target>
# Targets: db-up, db-down, schema, load, seed, app, test

param(
    [Parameter(Mandatory=$true)]
    [string]$Target
)

$ErrorActionPreference = "Stop"

# Laad .env als die bestaat
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]+)=(.*)$") {
            $key   = $Matches[1].Trim()
            $value = $Matches[2].Trim()
            [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

function Require-Env($name) {
    if (-not [System.Environment]::GetEnvironmentVariable($name)) {
        Write-Error "Omgevingsvariabele '$name' niet gevonden. Kopieer .env.example naar .env en vul in."
    }
}

switch ($Target) {

    "db-up" {
        Write-Host "PostgreSQL-container starten (Docker)..."
        docker compose up -d
        Write-Host "Wacht tot database gereed is..."
        $max = 30; $i = 0
        do {
            Start-Sleep 2; $i++
            $ready = docker compose exec postgres pg_isready -U vgbc_user -d vgbc_poc 2>$null
        } while ($LASTEXITCODE -ne 0 -and $i -lt $max)
        if ($LASTEXITCODE -ne 0) { Write-Error "Database niet bereikbaar na $($max*2) seconden." }
        Write-Host "Database gereed."
    }

    "db-down" {
        Write-Host "PostgreSQL-container stoppen..."
        docker compose down
    }

    "schema" {
        Require-Env "DATABASE_URL"
        Write-Host "Schema aanmaken..."
        psql -d "$env:DATABASE_URL" -v ON_ERROR_STOP=1 -f "db/ddl/001_schema.sql"
        if ($LASTEXITCODE -ne 0) { Write-Error "psql failure bij 001_schema.sql (exit $LASTEXITCODE)" }
        psql -d "$env:DATABASE_URL" -v ON_ERROR_STOP=1 -f "db/views/views.sql"
        if ($LASTEXITCODE -ne 0) { Write-Error "psql failure bij views.sql (exit $LASTEXITCODE)" }
        psql -d "$env:DATABASE_URL" -v ON_ERROR_STOP=1 -f "db/ddl/002_roles.sql"
        if ($LASTEXITCODE -ne 0) { Write-Error "psql failure bij 002_roles.sql (exit $LASTEXITCODE)" }
        Write-Host "Schema klaar."
    }

    "load" {
        Require-Env "DATABASE_URL"
        Write-Host "CSV-data laden..."
        python "db/load/load_csv.py"
    }

    "seed" {
        Write-Host "=== seed: genereren + schema + laden ==="
        Write-Host "1/3 Data genereren..."
        python "sample-data/generate_data.py"
        Write-Host "2/3 Schema aanmaken..."
        & $PSCommandPath "schema"
        Write-Host "3/3 Data laden..."
        & $PSCommandPath "load"
        Write-Host "=== seed klaar ==="
    }

    "app" {
        Require-Env "ANTHROPIC_API_KEY"
        Write-Host "Streamlit-app starten op http://localhost:8501 ..."
        python -m streamlit run "app/main.py"
    }

    "test" {
        Write-Host "Tests uitvoeren..."
        python -m pytest tests/ -v
    }

    default {
        Write-Host @"
Gebruik: .\make.ps1 <target>

Beschikbare targets:
  db-up    Start de PostgreSQL-container via Docker Compose
  db-down  Stop de container
  schema   Voer DDL + views + roles uit op de database
  load     Laad CSV-bestanden in de database
  seed     Genereer data + schema + laden (alles in één keer)
  app      Start de Streamlit-chatbot op localhost:8501
  test     Voer de pytest-testsuite uit
"@
    }
}

#requires -Version 5.1
<#
.SYNOPSIS
    Native Windows setup for Northstar — no containers required.

.DESCRIPTION
    Installs PostgreSQL via winget, creates a Python virtualenv, installs
    frontend dependencies via Bun (falling back to npm), and bootstraps
    backend\.env.

    Redis has no officially supported native Windows build. This script does
    not attempt to install it — the app does not depend on Redis today (it's
    provisioned on macOS/Linux purely for future use). If you need a
    Redis-compatible service on Windows, use WSL2 (recommended) or Memurai;
    see README.md's Troubleshooting section.
#>

[CmdletBinding()]
param(
    [string]$DbName = "northstar",
    [string]$DbUser = "northstar",
    [string]$DbPassword = "northstar"
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RootDir "backend"
$CodeDir = Join-Path $RootDir "code"

function Write-Step($Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-WarningStep($Message) {
    Write-Warning $Message
}

function Test-CommandExists($Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

if (-not (Test-CommandExists "winget")) {
    throw "winget not found. Install 'App Installer' from the Microsoft Store, then re-run this script."
}

Write-Step "Installing PostgreSQL (winget)"
$pgInstalled = winget list --id PostgreSQL.PostgreSQL.16 2>$null | Select-String "PostgreSQL"
if (-not $pgInstalled) {
    winget install --id PostgreSQL.PostgreSQL.16 --silent --accept-package-agreements --accept-source-agreements
} else {
    Write-Host "PostgreSQL already installed."
}

# winget's PostgreSQL installer registers a Windows service and adds `psql`
# to a version-specific bin directory that isn't always on PATH yet in the
# current session.
$PgBinCandidates = Get-ChildItem "C:\Program Files\PostgreSQL" -Directory -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending
if ($PgBinCandidates) {
    $env:PATH = "$($PgBinCandidates[0].FullName)\bin;$env:PATH"
}

if (-not (Test-CommandExists "psql")) {
    throw "psql not found on PATH after install. Open a new terminal (so PATH updates apply) and re-run this script."
}

Write-Step "Starting the PostgreSQL service"
$svc = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($svc -and $svc.Status -ne "Running") {
    Start-Service $svc.Name
}

Write-Step "Waiting for PostgreSQL to accept connections"
$env:PGPASSWORD = "postgres"
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    & pg_isready -q 2>$null
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    Start-Sleep -Seconds 1
}
if (-not $ready) {
    throw "PostgreSQL did not report ready after 30s. Check the 'postgresql-x64-16' service in services.msc."
}

Write-Step "Creating database role and database (idempotent)"
$roleExists = & psql -U postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname = '$DbUser'"
if ($roleExists -ne "1") {
    & psql -U postgres -c "CREATE ROLE $DbUser WITH LOGIN PASSWORD '$DbPassword' CREATEDB;"
}
$dbExists = & psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$DbName'"
if ($dbExists -ne "1") {
    & psql -U postgres -c "CREATE DATABASE $DbName OWNER $DbUser;"
}
Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue

Write-Step "Setting up backend\.env"
$envPath = Join-Path $BackendDir ".env"
$envExamplePath = Join-Path $BackendDir ".env.example"
if (-not (Test-Path $envPath)) {
    Copy-Item $envExamplePath $envPath

    Add-Type -AssemblyName System.Web -ErrorAction SilentlyContinue
    $jwtSecret = -join ((1..64) | ForEach-Object { "{0:x2}" -f (Get-Random -Maximum 256) })

    $content = Get-Content $envPath
    $content = $content -replace '^JWT_SECRET_KEY=.*', "JWT_SECRET_KEY=$jwtSecret"
    $content = $content -replace '^DEBUG=.*', 'DEBUG=true'
    $content = $content -replace '^ENVIRONMENT=.*', 'ENVIRONMENT=development'
    $content = $content -replace '^DATABASE_URL=.*', "DATABASE_URL=postgresql+asyncpg://${DbUser}:${DbPassword}@localhost:5432/${DbName}"
    Set-Content -Path $envPath -Value $content

    Write-Step "Generated backend\.env with a fresh JWT secret (DEBUG=true for local dev)"
} else {
    Write-Step "backend\.env already exists — leaving it untouched"
}

Write-Step "Creating Python virtual environment"
$pythonBin = if (Test-CommandExists "python3.12") { "python3.12" }
             elseif (Test-CommandExists "python") { "python" }
             else { throw "Python not found. Install Python 3.12+ from https://python.org or via winget (Python.Python.3.12), then re-run." }

$venvDir = Join-Path $BackendDir ".venv"
if (-not (Test-Path $venvDir)) {
    & $pythonBin -m venv $venvDir
}

$venvPython = Join-Path $venvDir "Scripts\python.exe"
& $venvPython -m pip install --upgrade pip | Out-Null
& $venvPython -m pip install -r (Join-Path $BackendDir "requirements-dev.txt")

Write-Step "Running database migrations"
Push-Location $BackendDir
try {
    & $venvPython -m alembic upgrade head
} finally {
    Pop-Location
}

Write-Step "Installing frontend dependencies"
if (Test-CommandExists "bun") {
    Push-Location $CodeDir
    try { & bun install } finally { Pop-Location }
} elseif (Test-CommandExists "npm") {
    Write-WarningStep "Bun not found — falling back to npm (https://bun.sh is the primary supported tool)"
    Push-Location $CodeDir
    try { & npm install } finally { Pop-Location }
} else {
    throw "Neither Bun nor npm found. Install Bun (https://bun.sh) or Node.js/npm, then re-run."
}

$envLocalPath = Join-Path $CodeDir ".env.local"
if (-not (Test-Path $envLocalPath)) {
    Set-Content -Path $envLocalPath -Value "VITE_API_BASE_URL=http://localhost:8000/api/v1"
    Write-Step "Created code\.env.local pointing at the local backend"
}

Write-Step "Setup complete."
Write-Host @"

Next steps:
  bash scripts/dev.sh        start backend + frontend together (Git Bash/WSL)
  bash scripts/test.sh       run backend + frontend test/verify suites
  make help                  list all available commands (requires 'make' — see README)

Redis note: not installed by this script (no native Windows build). Use
WSL2 if you need it locally — see README.md's Troubleshooting section.
"@

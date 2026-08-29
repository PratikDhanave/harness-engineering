# Set up this repo on Windows. Safe to re-run.
#   .\scripts\install.ps1
# Then, once, if you want the on-device model ready before you need it:
#   uv run python scripts\prefetch_model.py     (~2-3 GB, one time)
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'install git first' }

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host 'installing uv...'
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

Write-Host 'installing dependencies (uv brings its own Python)...'
uv sync --extra dev
if ($LASTEXITCODE) { throw 'uv sync failed' }

Write-Host 'verifying...'
uv run --extra dev pytest -q
if ($LASTEXITCODE) { throw 'tests failed' }
uv run python scripts\af_tour.py *> $null
if ($LASTEXITCODE) { throw 'lesson tour failed' }
Write-Host 'all seven lessons ran'

Write-Host ''
Write-Host 'ready:'
Write-Host '  uv run --extra dev pytest            the suite'
Write-Host '  uv run python scripts\af_tour.py     all seven lessons'
Write-Host '  uv run uvicorn harness.app:app --reload                  API on :8000'
Write-Host '  uv run uvicorn harness.app:app --reload --env-file .env  /chat on-device'

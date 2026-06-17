[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$schemaFile = Join-Path $scriptDir "schema.sql"

if (-not (Test-Path $schemaFile)) {
    throw "Schema file not found: $schemaFile"
}

Push-Location $repoRoot
try {
    Write-Host "Applying schema from $schemaFile to PostgreSQL service 'postgres'..."
    Get-Content -Raw $schemaFile |
        docker compose -p solar-ai-support-agent exec -T postgres psql -U solar -d solar_ai_support

    if ($LASTEXITCODE -ne 0) {
        throw "Failed to apply schema. Ensure 'docker compose -p solar-ai-support-agent up -d' is running."
    }

    Write-Host "Schema applied successfully."
}
finally {
    Pop-Location
}

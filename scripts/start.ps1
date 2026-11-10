$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot

docker compose --project-directory "$ProjectDir" -f "$ProjectDir/compose.yaml" up --build --detach --wait --wait-timeout 60
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Output "Kanban Studio is running at http://localhost:8000"

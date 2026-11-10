$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot

docker compose --project-directory "$ProjectDir" -f "$ProjectDir/compose.yaml" down
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Output "Kanban Studio stopped. Saved data is preserved."

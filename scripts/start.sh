#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
docker compose --project-directory "$project_dir" -f "$project_dir/compose.yaml" up --build --detach --wait --wait-timeout 60
printf '%s\n' 'Kanban Studio is running at http://localhost:8000'

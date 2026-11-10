#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
docker compose --project-directory "$project_dir" -f "$project_dir/compose.yaml" down
printf '%s\n' 'Kanban Studio stopped. Saved data is preserved.'

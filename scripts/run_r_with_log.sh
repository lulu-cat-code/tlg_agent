#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "Usage: bash scripts/run_r_with_log.sh <script.R> [log_path]" >&2
  exit 1
fi

script_path="$1"
log_path="${2:-run.log}"

{
  printf 'Generated at: %s\n\n' "$(date +"%Y-%m-%d %H:%M:%S")"
  Rscript "$script_path"
} 2>&1 | tee "$log_path"

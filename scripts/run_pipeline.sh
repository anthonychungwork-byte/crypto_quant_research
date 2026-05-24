#!/usr/bin/env bash
# Execute every notebook in order. Used after a fresh clone or after a
# methodology change to regenerate all narratives, figures, and tables.
#
# Usage: bash scripts/run_pipeline.sh
#
# Stage 5 (06_holdout.ipynb) is RUN-ONCE by methodology — re-running this
# script after Stage 5 has fired technically violates the SOP unless you
# are intentionally invalidating prior holdout claims.

set -euo pipefail

cd "$(dirname "$0")/.."

NOTEBOOKS=(
    "02_data_quality.ipynb"
    "03_is_optimization.ipynb"
    "04_oos_validation.ipynb"
    "05_walkforward.ipynb"
    "06_holdout.ipynb"
    "07_multicoin.ipynb"
    "08_postmortem.ipynb"
)

for nb in "${NOTEBOOKS[@]}"; do
    printf '\n=== Executing notebooks/%s ===\n' "$nb"
    uv run jupyter nbconvert \
        --to notebook \
        --execute \
        --inplace \
        --ExecutePreprocessor.timeout=3600 \
        "notebooks/$nb"
done

printf '\nAll stages executed. See results/ for figures and tables.\n'

#!/usr/bin/env bash
# Enforce docs/requirements/CLAUDE.md's hard rule:
# every FR-xxx in the FRD must appear in the traceability matrix,
# and every FR-xxx in the matrix must exist in the FRD.
set -uo pipefail

FRD="docs/requirements/FRD.md"
MATRIX="docs/requirements/traceability-matrix.md"
fail=0

# The matrix may express a contiguous block as a range row, e.g. "FR-QUAL-001..009".
# Expand those so individual IDs count as covered.
matrix_ids=$(
  {
    grep -oE 'FR-[A-Z]+-[0-9]{3}' "$MATRIX"
    grep -oE 'FR-[A-Z]+-[0-9]{3}\.\.[0-9]{3}' "$MATRIX" | while read -r range; do
      prefix=${range%-*}; prefix=${prefix%.*}
      base=$(echo "$range" | grep -oE '^FR-[A-Z]+')
      start=$(echo "$range" | sed -E 's/^FR-[A-Z]+-([0-9]{3})\.\.[0-9]{3}$/\1/')
      end=$(echo "$range" | sed -E 's/^FR-[A-Z]+-[0-9]{3}\.\.([0-9]{3})$/\1/')
      for n in $(seq "$((10#$start))" "$((10#$end))"); do
        printf '%s-%03d\n' "$base" "$n"
      done
    done
  } | sort -u
)

for fr in $(grep -oE '^### (FR-[A-Z]+-[0-9]{3})' "$FRD" | awk '{print $2}' | sort -u); do
  if ! echo "$matrix_ids" | grep -qx "$fr"; then
    echo "BROKEN: $fr defined in FRD.md but has no row in traceability-matrix.md"
    fail=1
  fi
done

if [ "$fail" -eq 0 ]; then
  echo "OK: every FR in FRD.md is traced."
fi
exit $fail

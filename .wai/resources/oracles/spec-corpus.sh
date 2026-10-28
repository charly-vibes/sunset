#!/usr/bin/env bash
# Purpose: Gate DSC pipeline shipment on the repository's executable corpus checks.
# Responsibilities: Run just spec-check in the selected workspace and propagate
#   failures from strict specs, lint, tests and frozen 0.2 descriptor fixtures.
# Rationale: sunset-0y1 replaces the Cargo-specific release gate with actual DSC
#   validation; the optional artifact argument is not treated as test evidence.
set -euo pipefail
exec env OMP_THREAD_LIMIT="${OMP_THREAD_LIMIT:-1}" \
    npm_config_cache="${npm_config_cache:-/tmp/sunset-spec-check-npm-cache}" \
    just spec-check

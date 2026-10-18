#!/usr/bin/env bash
# Atajo para Linux/macOS: toda la lógica está en demo.py (también corre en Windows).
exec python3 "$(dirname "$0")/demo.py" "$@"

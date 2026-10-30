#!/usr/bin/env bash
# Demo de la exposición (Linux/macOS): prepara lo que falte y delega en demo.py (que también corre en Windows).
#
#   ./demo.sh               deja todo listo y dice qué falta (.venv, node_modules, gh)
#   ./demo.sh lanzar        al empezar la exposición: dispara el pipeline en parte-2 y abre el run (~7 min)
#   ./demo.sh mostrar       en el slide de la demo: espera el run y abre Pages, Allure web y la matriz
#   ./demo.sh web           plan B local: Qolqe + E2E con Chrome visible + Allure (act repite desde la caché;
#                           GRABAR=1 deja que el modelo regrabe con la clave de tests/e2e/.env)
#   ./demo.sh <orden>       cualquier orden de demo.py: ensayo, demo, schemathesis, reporte, plan-b...
set -euo pipefail
cd "$(dirname "$0")"
PY=.venv/bin/python

preparar() {
  echo "Preparando la demo:"
  if [[ ! -x $PY ]] || ! $PY -c 'import pytest_bdd, schemathesis, uvicorn' 2>/dev/null; then
    python3 demo.py preparar
  fi
  echo "  ✓ Python (.venv)"
  if command -v npm >/dev/null; then
    [[ -d tests/e2e/node_modules ]] || (cd tests/e2e && npm ci)
    echo "  ✓ Node (tests/e2e)"
  else
    echo "  ✗ Node: sin npm no corre el plan B web"
  fi
  if command -v gh >/dev/null && gh auth status >/dev/null 2>&1; then
    echo "  ✓ gh autenticado"
  else
    echo "  ✗ gh sin sesión (gh auth login): 'mostrar' abrirá lo último publicado"
  fi
}

case "${1:-}" in
  "" | preparar) preparar ;;
  lanzar)  preparar; exec "$PY" demo.py ci lanzar ;;
  mostrar) preparar; exec "$PY" demo.py ci ;;
  web)
    preparar
    cd tests/e2e
    # ponytail: vacía la clave para no gastar tokens en vivo; loadEnvFile no pisa variables ya definidas
    [[ ${GRABAR:-} == 1 ]] || export ANTHROPIC_API_KEY=
    exec npm run demo ;;
  *) preparar; exec "$PY" demo.py "$@" ;;
esac

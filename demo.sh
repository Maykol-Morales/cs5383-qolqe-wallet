#!/usr/bin/env bash
# Alista y ejecuta la demo de la presentación.
#   ./demo.sh preparar        crea .venv e instala dependencias (una vez)
#   ./demo.sh ensayo          corre todos los pasos seguidos y mide el tiempo
#   ./demo.sh demo            igual, pero espera Enter entre pasos (para el vivo)
#   ./demo.sh schemathesis    CLI de Schemathesis contra un servidor temporal; abre el reporte HTML
#   ./demo.sh schemathesis todos   ídem con todos los checks (44 hallazgos, ver informe §3)
set -euo pipefail
cd "$(dirname "$0")"
PUERTO="${PUERTO:-8765}"
VENV="${VENV:-.venv}"

activar() { [ -d "$VENV" ] || { echo "Falta $VENV: ejecuta ./demo.sh preparar"; exit 1; }; source "$VENV/bin/activate"; }

paso() {  # paso "título" comando...
  local titulo="$1"; shift
  echo; echo "=== $titulo"; echo "\$ $*"
  [ "${PAUSA:-0}" = 1 ] && read -rp "(Enter para ejecutar) " _
  local t=$SECONDS
  "$@" || true   # los xfail/fallos esperados no deben cortar la demo
  echo "--- ${titulo}: $((SECONDS - t)) s"
}

pasos() {
  activar
  paso "1. Escenarios de la historia HU-G3-01" pytest tests/api -m "HU-G3-01" -v
  paso "2. Todos los escenarios" pytest -rx
  paso "3. Un defecto a la vista (DEF-07)" env MOSTRAR_DEFECTOS=1 pytest tests/api -m "DEF-07"
  paso "4. Contrato OpenAPI (Schemathesis dentro de pytest)" pytest tests/api/test_contrato.py -v
}

schemathesis_cli() {
  activar
  local checks="not_a_server_error,status_code_conformance,content_type_conformance,response_headers_conformance,response_schema_conformance"
  [ "${1:-}" = todos ] && checks=all
  tmp=$(mktemp -d)  # globales: el trap EXIT corre fuera de la función
  QOLQE_BD="$tmp/q.db" QOLQE_MODO_PRUEBA=1 uvicorn qolqe.main:app --port "$PUERTO" --log-level warning &
  pid=$!
  trap 'kill $pid 2>/dev/null; rm -rf "$tmp"' EXIT
  for _ in $(seq 40); do curl -sf "localhost:$PUERTO/api/salud" >/dev/null && break; sleep 0.5; done
  echo "Contrato: http://localhost:$PUERTO/docs  (Swagger)  ·  http://localhost:$PUERTO/openapi.json"
  local token
  token=$(curl -s -X POST "localhost:$PUERTO/api/auth/login" -H "Content-Type: application/json" \
    -d '{"celular":"987654321","pin":"4826"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
  # Se excluyen operaciones que invalidan la sesión o el reloj compartidos
  schemathesis run "http://localhost:$PUERTO/openapi.json" -H "Authorization: Bearer $token" \
    --max-examples 30 --checks "$checks" \
    --exclude-path-regex '/api/auth/logout|/api/seguridad/sesiones|/api/pruebas/reloj|/api/pruebas/reiniciar|/api/cuentas/me/cierre' \
    --report html --report-dir reporte-schemathesis || true
  local html; html=$(find reporte-schemathesis -name 'index.html' 2>/dev/null | head -1)
  [ -n "$html" ] && { echo "Reporte: $html"; xdg-open "$html" >/dev/null 2>&1 || true; }
}

case "${1:-}" in
  preparar)
    [ -d "$VENV" ] || python3 -m venv "$VENV"
    source "$VENV/bin/activate"
    pip install -q -r requirements-dev.txt
    command -v schemathesis >/dev/null && echo "Listo: pytest y schemathesis instalados." ;;
  ensayo) pasos ;;
  demo) PAUSA=1 pasos ;;
  schemathesis) schemathesis_cli "${2:-}" ;;
  *) sed -n '2,8p' "$0" ;;
esac

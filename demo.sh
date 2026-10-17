#!/usr/bin/env bash
# Alista y ejecuta la demo de la presentación.
#   ./demo.sh preparar        crea .venv e instala dependencias (una vez)
#   ./demo.sh ensayo          corre todos los pasos seguidos y mide el tiempo
#   ./demo.sh demo            igual, pero espera Enter entre pasos (para el vivo)
#   ./demo.sh schemathesis    CLI de Schemathesis contra un servidor temporal; abre el reporte HTML
#   ./demo.sh schemathesis todos   ídem con todos los checks (44 hallazgos, ver informe §2)
#   ./demo.sh schemathesis g3      solo endpoints de G3 (movimientos y categorías); combinable: g3 todos
#   ./demo.sh plan-b          pytest -rx guardando la salida en reportes/ensayo.txt (pregrabada)
# El paso 4 (contrato) repite lo que ya corre en el paso 2: es opcional, SIN_CONTRATO=1 lo omite.
set -euo pipefail
cd "$(dirname "$0")"
PUERTO="${PUERTO:-8765}"
VENV="${VENV:-.venv}"

activar() { [ -d "$VENV" ] || { echo "Falta $VENV: ejecuta ./demo.sh preparar"; exit 1; }; source "$VENV/bin/activate"; }

paso() {  # paso "título" comando...
  local titulo="$1"; shift
  echo; echo "=== $titulo"; echo "\$ $*"
  if [ "${PAUSA:-0}" = 1 ]; then read -rp "(Enter para ejecutar) " _ || true; fi
  local t=$SECONDS
  RC=0; "$@" || RC=$?   # los xfail/fallos esperados no deben cortar la demo
  echo "--- ${titulo}: $((SECONDS - t)) s (rc=$RC)"
}

pasos() {
  activar
  paso "1. Escenarios de la historia HU-G3-01" pytest tests/api -m "HU-G3-01" -v
  paso "2. Todos los escenarios" pytest -rx
  paso "3. Un defecto a la vista (DEF-07)" env MOSTRAR_DEFECTOS=1 pytest tests/api -m "DEF-07"
  [ "$RC" = 0 ] || echo "(esperado: los defectos fallan a la vista)"
  if [ "${SIN_CONTRATO:-0}" != 1 ]; then
    paso "4. Contrato OpenAPI (Schemathesis dentro de pytest)" pytest tests/api/test_contrato.py -v
  fi
}

schemathesis_cli() {
  activar
  local checks="not_a_server_error,status_code_conformance,content_type_conformance,response_headers_conformance,response_schema_conformance"
  local incluir=()
  for a in "$@"; do
    case "$a" in
      todos) checks=all ;;
      g3) incluir=(--include-path-regex '^/api/(movimientos|categorias)') ;;
    esac
  done
  command -v curl >/dev/null || { echo "Falta curl"; exit 1; }
  if (exec 3<>"/dev/tcp/localhost/$PUERTO") 2>/dev/null; then
    echo "Puerto $PUERTO ocupado: usa otro con PUERTO=nnnn ./demo.sh schemathesis"; exit 1
  fi
  tmp=$(mktemp -d)  # globales: el trap EXIT corre fuera de la función
  QOLQE_BD="$tmp/q.db" QOLQE_MODO_PRUEBA=1 uvicorn qolqe.main:app --port "$PUERTO" --log-level warning &
  pid=$!
  trap 'kill $pid 2>/dev/null; rm -rf "$tmp"' EXIT
  local ok=0
  for _ in $(seq 40); do
    curl -sf "localhost:$PUERTO/api/salud" >/dev/null && { ok=1; break; }
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.5
  done
  if [ "$ok" != 1 ] || ! kill -0 "$pid" 2>/dev/null; then
    echo "uvicorn no arrancó (¿puerto $PUERTO ocupado?)"; exit 1
  fi
  echo "Contrato: http://localhost:$PUERTO/docs  (Swagger)  ·  http://localhost:$PUERTO/openapi.json"
  local token
  token=$(curl -s -X POST "localhost:$PUERTO/api/auth/login" -H "Content-Type: application/json" \
    -d '{"celular":"987654321","pin":"4826"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
  # Se excluyen operaciones que invalidan la sesión o el reloj compartidos
  schemathesis run "http://localhost:$PUERTO/openapi.json" -H "Authorization: Bearer $token" \
    --seed 1 --max-examples 30 --checks "$checks" "${incluir[@]}" \
    --exclude-path-regex '/api/auth/logout|/api/seguridad/sesiones|/api/pruebas/reloj|/api/pruebas/reiniciar|/api/cuentas/me/cierre' \
    --report html --report-dir reporte-schemathesis || true
  local html; html=$(ls -t reporte-schemathesis/*/index.html 2>/dev/null | head -1 || true)
  if [ -n "$html" ]; then
    echo "Reporte: $html"
    command -v xdg-open >/dev/null && xdg-open "$html" >/dev/null 2>&1 || { command -v open >/dev/null && open "$html"; } || true
  fi
}

case "${1:-}" in
  preparar)
    [ -d "$VENV" ] || python3 -m venv "$VENV"
    source "$VENV/bin/activate"
    pip install -q -r requirements-dev.txt
    if command -v schemathesis >/dev/null; then echo "Listo: pytest y schemathesis instalados."
    else echo "Aviso: schemathesis no quedó instalado (revisa requirements-dev.txt)"; exit 1; fi ;;
  ensayo) pasos ;;
  demo) PAUSA=1 pasos ;;
  schemathesis) shift; schemathesis_cli "$@" ;;
  plan-b) activar; mkdir -p reportes; pytest -rx 2>&1 | tee reportes/ensayo.txt || true ;;
  *) sed -n '2,/^set /{/^set /!p}' "$0" ;;
esac

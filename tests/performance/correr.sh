#!/usr/bin/env bash
# Corre una prueba en el mismo equipo de Qolqe: prepara datos, mide recursos, k6, integridad y gráficos.
# Uso (desde la raíz, con Qolqe en QOLQE_URL): tests/performance/correr.sh humo|carga|pico|estres
# Variables: USUARIOS (1000), DURACION, PESOS, TOPE, PASO (pasan a k6), ETIQUETA (sufijo del directorio),
#            PERFIL=1 graba un flamegraph con py-spy (pide sudo), QOLQE_PID si el puerto no basta.
# Sale con el código de k6 (≠ 0 si se incumple un umbral).
set -euo pipefail
cd "$(dirname "$0")/../.."
PRUEBA=${1:-humo}
DIR=tests/performance/resultados/$PRUEBA-$(date +%Y%m%d-%H%M)${ETIQUETA:+-$ETIQUETA}
PY=.venv/bin/python
export USUARIOS=${USUARIOS:-1000}
export QOLQE_URL=${QOLQE_URL:-http://localhost:8000}

$PY tests/performance/datos.py preparar "$DIR" "$USUARIOS"
QOLQE=${QOLQE_PID:-$(lsof -ti "tcp:${QOLQE_URL##*:}" -sTCP:LISTEN)}
$PY tests/performance/monitor.py "$QOLQE" "$DIR/recursos-qolqe.csv" & MONITORES=$!
[ "${PERFIL:-}" = 1 ] && sudo .venv/bin/py-spy record --pid "$QOLQE" -o "$DIR/flamegraph.svg" --nonblocking &

echo "inicio $(date +%T)" > "$DIR/horario.txt"
K6_WEB_DASHBOARD=true K6_WEB_DASHBOARD_EXPORT="$DIR/dashboard.html" \
  k6 run -e PRUEBA="$PRUEBA" --out json="$DIR/k6.json.gz" --summary-export="$DIR/summary.json" \
  tests/performance/qolqe.js > "$DIR/k6.txt" 2>&1 & CORRIDA=$!
$PY tests/performance/monitor.py "$CORRIDA" "$DIR/recursos-k6.csv" & MONITORES="$MONITORES $!"
tail -f --pid=$CORRIDA "$DIR/k6.txt" &
RC=0; wait $CORRIDA || RC=$?
echo "fin $(date +%T)" >> "$DIR/horario.txt"
kill $MONITORES 2>/dev/null || true
[ "${PERFIL:-}" = 1 ] && sudo pkill -INT -f "py-spy record" || true

$PY tests/performance/datos.py verificar "$DIR" || true
$PY tests/performance/graficos.py "$DIR"
echo "Resultados en $DIR (k6 salió con $RC)"
exit $RC

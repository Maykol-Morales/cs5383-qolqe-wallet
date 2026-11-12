#!/usr/bin/env bash
# Corre saldo.js (k6) y locustfile.py (Locust) contra el mismo Qolqe y mide el CPU de cada generador.
# Uso (desde la raíz, con QOLQE_URL y QOLQE_BD como en ../correr.sh): tests/performance/comparativa/correr.sh
set -euo pipefail
cd "$(dirname "$0")/../../.."
PY=.venv/bin/python
DIR=tests/performance/resultados/comparativa-$(date +%Y%m%d-%H%M)
mkdir -p "$DIR"

$PY tests/performance/datos.py preparar "$DIR" 100
k6 run -e QOLQE_URL="$QOLQE_URL" --summary-export="$DIR/k6-summary.json" tests/performance/comparativa/saldo.js > "$DIR/k6.txt" 2>&1 & G=$!
$PY tests/performance/monitor.py $G "$DIR/cpu-k6.csv" & M=$!
wait $G; kill $M 2>/dev/null || true

$PY tests/performance/datos.py preparar "$DIR" 100
.venv/bin/locust -f tests/performance/comparativa/locustfile.py --headless -u 100 -r 2 -t 170s --host "$QOLQE_URL" \
  --csv "$DIR/locust" > "$DIR/locust.txt" 2>&1 & G=$!
$PY tests/performance/monitor.py $G "$DIR/cpu-locust.csv" & M=$!
wait $G || true; kill $M 2>/dev/null || true

$PY - "$DIR" <<'EOF'
import csv, json, sys
d = sys.argv[1]
def cpu(f):  # promedio con los 100 usuarios ya dentro (desde el segundo 55)
    c = [float(r["cpu_%"]) for r in csv.DictReader(open(f"{d}/{f}"))][55:]
    return sum(c) / len(c)
k6 = json.load(open(f"{d}/k6-summary.json"))["metrics"]["http_reqs"]
lo = next(r for r in csv.DictReader(open(f"{d}/locust_stats.csv")) if r["Name"] == "Aggregated")
p95 = json.load(open(f"{d}/k6-summary.json"))["metrics"]["http_req_duration"]["p(95)"]
for nombre, c, n, p in [("k6", cpu("cpu-k6.csv"), k6["count"], p95),
                        ("Locust", cpu("cpu-locust.csv"), int(lo["Request Count"]), float(lo["95%"]))]:
    print(f"{nombre}: {n} peticiones, p95 {p:.0f} ms, CPU del generador {c:.1f} % en la meseta")
EOF

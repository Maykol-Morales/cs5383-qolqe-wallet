#!/usr/bin/env bash
# Uso (desde tests/e2e, con Qolqe en QOLQE_URL): benchmark/correr.sh A|B|C <n>
#   A = browser.act en frío (borra benchmark/__act__/ y graba con el modelo)
#   B = browser.act desde la caché que dejó A (locked, sin modelo)
#   C = Page Objects clásicos (features/clasificar.feature)
# Cada corrida deja benchmark/crudo/<modo>-<i>.ndjson: registros de act/llm + una línea final {tipo:"corrida"}.
set -u
modo=$1; n=${2:-3}; dir=benchmark/crudo; mkdir -p "$dir"
for i in $(seq "${INICIO:-1}" "$n"); do
    out="$dir/$modo-$i.ndjson"; : > "$out"
    case $modo in
        A) rm -rf benchmark/__act__; export BENCH_CACHE=write BENCH_SPEC=../features/clasificar-ia.feature ;;
        B) export BENCH_CACHE=locked BENCH_SPEC=../features/clasificar-ia.feature ;;
        C) export BENCH_CACHE=locked BENCH_SPEC=../features/clasificar.feature ;;
    esac
    t0=$(date +%s%3N)
    BENCH_OUT="$PWD/$out" npx wdio run benchmark/wdio.bench.conf.js > "$dir/$modo-$i.log" 2>&1; rc=$?
    echo "{\"tipo\":\"corrida\",\"modo\":\"$modo\",\"i\":$i,\"ms\":$(( $(date +%s%3N) - t0 )),\"rc\":$rc}" >> "$out"
    tail -1 "$out"
done

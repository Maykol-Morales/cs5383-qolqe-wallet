#!/usr/bin/env bash
# Sesión exploratoria con el MCP de WebdriverIO: Claude Code explora la interfaz de Qolqe buscando comportamientos que
# contradigan las reglas de negocio (benchmark/mcp/explorar-prompt.md), sin saber cuáles son los defectos conocidos.
# Uso, desde tests/e2e:   QOLQE_URL=http://localhost:8002 benchmark/mcp/explorar.sh [n]
# Deja crudo/X-<n>.{traza.ndjson,json,meta.json,err}; el arreglo JSON de hallazgos va en el campo `result` de X-<n>.json.
# Mismo aislamiento y modelo que correr.sh (directorio vacío, sin ajustes de usuario, solo el MCP, tope de gasto).
set -u
n=${1:-1}
url=${QOLQE_URL:-http://localhost:8002}
e2e=$PWD; aqui=$e2e/benchmark/mcp; dir=$aqui/crudo; mkdir -p "$dir"
modelo=${MODELO:-claude-sonnet-5-5}; tope=${TOPE_USD:-1.50}
base=$(mktemp -d)/wdio-explora; mkdir -p "$base"; tag=X-$n
prompt=$(sed "s|{{URL}}|$url|g" "$aqui/explorar-prompt.md")

curl -sf -X DELETE "$url/api/pruebas/reloj" >/dev/null && curl -sf -X POST "$url/api/pruebas/reiniciar" >/dev/null || { echo "Qolqe no responde en $url"; exit 1; }
cd "$base" || exit 1
inicio=$(date +%s)
timeout "${LIMITE_S:-1500}" claude -p "$prompt" --model "$modelo" --output-format stream-json --verbose \
    --permission-mode acceptEdits --no-session-persistence --disable-slash-commands --setting-sources project \
    --max-budget-usd "$tope" --tools "" --allowedTools "mcp__wdio-mcp" --mcp-config "$aqui/mcp.json" --strict-mcp-config \
    > "$dir/$tag.traza.ndjson" 2> "$dir/$tag.err"
rc=$?
echo "{\"rc\": $rc, \"s\": $(( $(date +%s) - inicio ))}" > "$dir/$tag.meta.json"
tail -1 "$dir/$tag.traza.ndjson" > "$dir/$tag.json"
echo "$tag: rc=$rc $(cat "$dir/$tag.meta.json")"

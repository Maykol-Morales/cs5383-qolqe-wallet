#!/usr/bin/env bash
# Sesión exploratoria con el MCP de WebdriverIO: Claude Code explora la interfaz de Qolqe buscando comportamientos que
# contradigan las reglas de negocio (benchmark/mcp/explorar-prompt.md), sin saber cuáles son los defectos conocidos.
# Uso, desde tests/e2e:   QOLQE_URL=http://localhost:8002 benchmark/mcp/explorar.sh [n]
#   CONOCIDOS=1   le pasa la lista de defectos conocidos (docs/defectos.md) y que marque cuáles reconoce (job del CI)
#   MCP_CONFIG=   configuración del servidor MCP (por defecto mcp.json, con `cmd /c npx` de Windows; en Linux, .mcp.json)
# Deja crudo/X-<n>.{traza.ndjson,json,meta.json,err}; el arreglo JSON de hallazgos va en el campo `result` de X-<n>.json.
# Mismo aislamiento y modelo que correr.sh (directorio vacío, sin ajustes de usuario, solo el MCP, tope de gasto).
set -u
n=${1:-1}
url=${QOLQE_URL:-http://localhost:8002}
e2e=$PWD; aqui=$e2e/benchmark/mcp; dir=$aqui/crudo; mkdir -p "$dir"
modelo=${MODELO:-claude-sonnet-5-5}; tope=${TOPE_USD:-1.50}
base=$(mktemp -d)/wdio-explora; mkdir -p "$base"; tag=X-$n
prompt=$(sed "s|{{URL}}|$url|g" "$aqui/explorar-prompt.md")
# CONOCIDOS=1 (lo usa el job `exploracion` del CI): se le pasa la lista de defectos ya registrados y reporta todo, marcando en cada
# hallazgo el DEF-nn que coincide (o null si es nuevo). Así el resumen separa lo reconfirmado de lo posiblemente nuevo. Sin esto el agente
# no sabe cuáles son (así se midió cuántos redescubre; ver comparativa-mcp-agentes.md §6).
if [ -n "${CONOCIDOS:-}" ]; then
    lista=$(grep -E '^## DEF-[0-9]+:' "$e2e/../../docs/defectos.md" | sed 's/^## //' | tr -d '\r')
    prompt="$prompt

Defectos YA CONOCIDOS del proyecto (de docs/defectos.md):
$lista

Reporta TODO lo que encuentres, aunque ya sea conocido. Agrega a cada hallazgo el campo \"conocido\": el DEF-nn de esa lista si es el mismo problema, o null si es un comportamiento distinto (un posible defecto nuevo). Marca un DEF-nn solo cuando de verdad coincida."
fi

curl -sf -X DELETE "$url/api/pruebas/reloj" >/dev/null && curl -sf -X POST "$url/api/pruebas/reiniciar" >/dev/null || { echo "Qolqe no responde en $url"; exit 1; }
cd "$base" || exit 1
inicio=$(date +%s)
timeout "${LIMITE_S:-1500}" claude -p "$prompt" --model "$modelo" --output-format stream-json --verbose \
    --permission-mode acceptEdits --no-session-persistence --disable-slash-commands --setting-sources project \
    --max-budget-usd "$tope" --tools "" --allowedTools "mcp__wdio-mcp" --mcp-config "${MCP_CONFIG:-$aqui/mcp.json}" --strict-mcp-config \
    > "$dir/$tag.traza.ndjson" 2> "$dir/$tag.err"
rc=$?
echo "{\"rc\": $rc, \"s\": $(( $(date +%s) - inicio ))}" > "$dir/$tag.meta.json"
tail -1 "$dir/$tag.traza.ndjson" > "$dir/$tag.json"
echo "$tag: rc=$rc $(cat "$dir/$tag.meta.json")"

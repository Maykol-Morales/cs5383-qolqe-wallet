#!/usr/bin/env bash
# Enfoque D: Claude Code (headless) resuelve la tarea por su cuenta. Uso, desde tests/e2e:
#   QOLQE_URL=http://localhost:8002 benchmark/correr-agente.sh <n> <dir-temporal>
# Por corrida: reinicia Qolqe, corre `claude -p` en un directorio vacío y verifica el resultado por la API.
# CIEGO=1: no le dice dónde está el repo (solo enlaza node_modules en el directorio), así no lee los Page Objects.
# MODELO (defecto sonnet). --bare: sin hooks, plugins ni CLAUDE.md del usuario; factura a ANTHROPIC_API_KEY de tests/e2e/.env.
set -u
n=${1:-3}; tmp=$2; url=${QOLQE_URL:-http://localhost:8002}; e2e=$PWD; dir=$e2e/benchmark/crudo; mkdir -p "$dir"
prompt="Qolqe es una billetera web que corre en $url (la interfaz se pinta con JavaScript después del login).
Tarea, a través de la interfaz web en un navegador real: inicia sesión como Ana (celular 987654321, PIN 4826),
ve a la sección Movimientos, crea la categoría 'Viajes' con el color azul #1E88E5, clasifica el movimiento más
reciente de la lista en 'Viajes' con la nota 'Pasaje a Cusco' y verifica que la fila lo muestre.
$( [ -n "${CIEGO:-}" ] && echo "Tienes Chromium en /usr/bin/chromium y WebdriverIO en ./node_modules (Node 22). No instales paquetes." \
   || echo "Tienes Chromium en /usr/bin/chromium y WebdriverIO instalado en $e2e/node_modules (Node 22). No instales paquetes." )
Al terminar responde solo con una línea JSON: {\"exito\": true|false, \"metodo\": \"<cómo lo hiciste>\", \"codigo_operacion\": \"<movimiento clasificado>\"}"
for i in $(seq "${INICIO:-1}" "$n"); do
    curl -sf -X DELETE "$url/api/pruebas/reloj" >/dev/null && curl -sf -X POST "$url/api/pruebas/reiniciar" >/dev/null || exit 1
    tag=D${CIEGO:+c}-$i; w="$tmp/$tag"; rm -rf "$w"; mkdir -p "$w"; [ -n "${CIEGO:-}" ] && ln -s "$e2e/node_modules" "$w/node_modules"
    ( cd "$w" && set -a && . "$e2e/.env" && set +a && claude -p "$prompt" --bare --model "${MODELO:-sonnet}" --output-format stream-json --verbose \
        --allowedTools "Bash,Read,Write,Edit" --permission-mode acceptEdits --no-session-persistence --strict-mcp-config ) \
        > "$dir/$tag.traza.ndjson" 2> "$dir/$tag.err"
    tail -1 "$dir/$tag.traza.ndjson" > "$dir/$tag.json"   # la última línea es el resultado (usage, costo, tiempo)
    # Verificación independiente por la API (con el token de Ana).
    python3 - "$url" > "$dir/$tag.verif.json" <<'EOF'
import json, sys, urllib.request as u
url = sys.argv[1]
def req(p, body=None, tok=None):
    r = u.Request(url + p, data=body and json.dumps(body).encode(), headers={'content-type': 'application/json', **({'Authorization': 'Bearer ' + tok} if tok else {})})
    return json.load(u.urlopen(r))
tok = req('/api/auth/login', {'celular': '987654321', 'pin': '4826'})['access_token']
cats = [c for c in req('/api/categorias', tok=tok) if c['nombre'] == 'Viajes']
# historial de 90 días + recientes: con DEF-07 el historial no muestra los movimientos de hoy
from datetime import date, timedelta as td
h = date.today()
movs = {m['codigo_operacion']: m for m in req(f'/api/movimientos?desde={h - td(90)}&hasta={h}&categoria_id={cats[0]["id"]}', tok=tok)['movimientos'] + req('/api/movimientos/recientes', tok=tok)
        if (m['categoria'] or {}).get('nombre') == 'Viajes'}.values() if cats else []
movs = list(movs)
print(json.dumps({'categoria': cats, 'clasificados': [{k: m[k] for k in ('codigo_operacion', 'tipo', 'fecha', 'nota')} for m in movs],
    'exito': len(cats) == 1 and cats[0]['color'] == '#1E88E5' and len(movs) == 1 and movs[0]['nota'] == 'Pasaje a Cusco'}))
EOF
    python3 -c "import json;d=json.load(open('$dir/$tag.json'));print($i, d.get('total_cost_usd'), d.get('duration_ms'), d.get('num_turns'), str(d.get('result'))[-200:])"
    cat "$dir/$tag.verif.json"; echo
done

#!/usr/bin/env bash
# Compara tres formas de que Claude Code maneje el navegador para la MISMA tarea de UI que benchmark/correr-agente.sh,
# más una corrida «base» sin tarea que mide el costo fijo de cada configuración. Uso, desde tests/e2e:
#   QOLQE_URL=http://localhost:8002 benchmark/mcp/correr.sh <E|F|D|G|base-E|base-F|base-D|base-G> <n>
#
#   E   Claude Code con el servidor MCP de WebdriverIO (@wdio/mcp); sin herramientas integradas.
#   F   Claude Code con `wdio session` en la terminal (la skill que instala `wdio session skill --install`); solo Bash(wdio session) y Read.
#   D   Claude Code escribiendo sus propios scripts con WebdriverIO (Bash, Read, Write, Edit; sin la ruta del repo).
#   G   Claude Code con Claude in Chrome (`--chrome`): maneja el Chrome real del usuario, con capturas de pantalla; sin herramientas integradas.
#   base-*  la misma configuración con un prompt trivial («responde listo»): mide lo fijo (esquemas de herramientas, prompt de sistema).
#
# Aislamiento: directorio de trabajo vacío fuera del repo (no se carga el CLAUDE.md del proyecto), sin ajustes de usuario
# (--setting-sources project), sin skills (--disable-slash-commands) ni otros servidores MCP (--strict-mcp-config), sin guardar
# sesión, mismo modelo y un tope de gasto por corrida. No se usa --bare porque exige ANTHROPIC_API_KEY y aquí se factura la sesión
# iniciada; el costo fijo que quede (CLAUDE.md de usuario, memoria) lo mide la corrida base y es igual en los tres enfoques.
set -u
enfoque=${1:?enfoque: E | F | D | base-E | base-F | base-D}; n=${2:-3}
url=${QOLQE_URL:-http://localhost:8002}
e2e=$PWD; aqui=$e2e/benchmark/mcp; dir=$aqui/crudo; mkdir -p "$dir"
modelo=${MODELO:-claude-sonnet-5-5}; tope=${TOPE_USD:-1.50}
raiz=$(cd "$e2e/../.." && pwd); PY=${PY:-$raiz/.venv/Scripts/python}
base=$(mktemp -d)/wdio-bench-mcp; mkdir -p "$base"

tarea="Qolqe es una billetera web que corre en $url (la interfaz se pinta con JavaScript después del login).
Tarea, a través de la interfaz web en un navegador real (Chrome sin ventana, headless): inicia sesión como Ana (celular 987654321, PIN 4826),
ve a la sección Movimientos, crea la categoría 'Viajes' con el color azul #1E88E5, clasifica el movimiento más
reciente de la lista en 'Viajes' con la nota 'Pasaje a Cusco' y verifica que la fila lo muestre."
cierre="Al terminar responde solo con una línea JSON: {\"exito\": true|false, \"metodo\": \"<cómo lo hiciste>\", \"codigo_operacion\": \"<movimiento clasificado>\"}"
trivial="Responde únicamente con la palabra: listo"

for i in $(seq "${INICIO:-1}" "$n"); do
    tag=$enfoque-$i; w="$base/$tag"; mkdir -p "$w"
    curl -sf -X DELETE "$url/api/pruebas/reloj" >/dev/null && curl -sf -X POST "$url/api/pruebas/reiniciar" >/dev/null || { echo "Qolqe no responde en $url"; exit 1; }
    cd "$w" || exit 1
    case $enfoque in
      E|base-E)
        extra=(--tools "" --allowedTools "mcp__wdio-mcp" --mcp-config "$aqui/mcp.json" --strict-mcp-config)
        metodo="Usa únicamente las herramientas del servidor MCP de WebdriverIO (wdio-mcp). No tienes terminal."
        ;;
      F|base-F)
        export PATH="$e2e/node_modules/.bin:$PATH"
        # `wdio session` mantiene el navegador vivo entre comandos Y entre corridas: sin cerrarla, la corrida siguiente
        # reutiliza el Chrome (y la página ya hecha) de la anterior (pasó con F-2 en la primera tanda).
        wdio session close >/dev/null 2>&1
        [ "$enfoque" = F ] && wdio session skill --install . >/dev/null 2>&1
        extra=(--tools "Bash,Read" --allowedTools "Read" "Bash(wdio session:*)" "Bash(npx wdio session:*)" --strict-mcp-config)
        metodo="Usa únicamente el comando \`wdio session\` en la terminal (hay una guía en .agents/skills/wdio-session/SKILL.md). No escribas scripts."
        ;;
      D|base-D)
        cmd //c mklink //J "$(cygpath -w "$w/node_modules")" "$(cygpath -w "$e2e/node_modules")" >/dev/null 2>&1 || ln -s "$e2e/node_modules" "$w/node_modules"
        extra=(--tools "Bash,Read,Write,Edit" --allowedTools "Bash,Read,Write,Edit" --strict-mcp-config)
        metodo="Escribe y ejecuta tus propios scripts de Node con WebdriverIO (webdriverio ya está en ./node_modules, Node 22). No instales paquetes."
        ;;
      G|base-G)
        # Claude in Chrome: la extensión maneja el Chrome REAL del usuario (capturas de pantalla y lectura de texto); no es headless.
        extra=(--chrome --tools "" --allowedTools "mcp__claude-in-chrome" --strict-mcp-config)
        metodo="Usa únicamente las herramientas de Claude in Chrome. Trabaja en una pestaña nueva (no toques las demás) y ciérrala al terminar."
        ;;
      *) echo "enfoque desconocido: $enfoque"; exit 1 ;;
    esac
    case $enfoque in base-*) prompt=$trivial ;; *) prompt="$tarea
$metodo
$cierre" ;; esac
    [ "${enfoque#base-}" = G ] || [ "$enfoque" = G ] && prompt=${prompt//"Chrome sin ventana, headless"/"el navegador Chrome del usuario"}

    inicio=$(date +%s)
    timeout "${LIMITE_S:-720}" claude -p "$prompt" --model "$modelo" --output-format stream-json --verbose \
        --permission-mode acceptEdits --no-session-persistence --disable-slash-commands --setting-sources project \
        --max-budget-usd "$tope" "${extra[@]}" > "$dir/$tag.traza.ndjson" 2> "$dir/$tag.err"
    rc=$?
    case $enfoque in F|base-F) wdio session close >/dev/null 2>&1 ;; esac
    echo "{\"rc\": $rc, \"s\": $(( $(date +%s) - inicio ))}" > "$dir/$tag.meta.json"
    tail -1 "$dir/$tag.traza.ndjson" > "$dir/$tag.json"
    cd "$e2e" || exit 1
    case $enfoque in base-*) ;; *)
        "$PY" - "$url" > "$dir/$tag.verif.json" <<'EOF'
import json, sys, urllib.request as u
from datetime import date, timedelta as td
url = sys.argv[1]
def req(p, body=None, tok=None):
    r = u.Request(url + p, data=body and json.dumps(body).encode(), headers={'content-type': 'application/json', **({'Authorization': 'Bearer ' + tok} if tok else {})})
    return json.load(u.urlopen(r))
tok = req('/api/auth/login', {'celular': '987654321', 'pin': '4826'})['access_token']
cats = [c for c in req('/api/categorias', tok=tok) if c['nombre'] == 'Viajes']
h = date.today()
movs = {m['codigo_operacion']: m for m in (req(f'/api/movimientos?desde={h - td(90)}&hasta={h}&categoria_id={cats[0]["id"]}', tok=tok)['movimientos'] + req('/api/movimientos/recientes', tok=tok))
        if (m['categoria'] or {}).get('nombre') == 'Viajes'}.values() if cats else []
movs = list(movs)
print(json.dumps({'categoria': cats, 'clasificados': [{k: m[k] for k in ('codigo_operacion', 'tipo', 'fecha', 'nota')} for m in movs],
    'exito': len(cats) == 1 and cats[0]['color'] == '#1E88E5' and len(movs) == 1 and movs[0]['nota'] == 'Pasaje a Cusco'}))
EOF
        ;; esac
    echo "$tag: rc=$rc $(cat "$dir/$tag.meta.json") verif=$(cat "$dir/$tag.verif.json" 2>/dev/null | head -c 60)"
done

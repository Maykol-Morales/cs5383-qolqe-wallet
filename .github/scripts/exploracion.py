"""Resumen en Markdown de una sesión exploratoria con el MCP de WebdriverIO (job `exploracion` del CI).

    python .github/scripts/exploracion.py [ruta/a/X-1.json]  >> "$GITHUB_STEP_SUMMARY"

Lee el último evento de `claude -p --output-format stream-json` que deja tests/e2e/benchmark/mcp/explorar.sh: el campo
`result` trae el arreglo JSON de hallazgos del agente y el resto, el costo de la sesión (tiempo, turnos, tokens y USD a precio
de lista). Con CONOCIDOS=1 el agente marca en cada hallazgo el campo `conocido` (el DEF-nn que reconoce, o null si es distinto):
el resumen separa los posiblemente nuevos de los ya conocidos que reconfirmó. Esa marca la pone el agente y puede equivocarse,
así que hay que reproducir cada hallazgo a mano antes de registrar un defecto. Solo biblioteca estándar. Sale con 0 aunque la
sesión haya fallado: es una exploración, no un criterio del gate.
"""
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
RUTA = RAIZ / "tests/e2e/benchmark/mcp/crudo/X-1.json"
DEF = re.compile(r"DEF-\d+", re.IGNORECASE)


def hallazgos(texto):
    """Arreglo JSON de hallazgos dentro del texto del agente (tolera texto antes o después). None si no hay uno válido."""
    inicio, fin = texto.find("["), texto.rfind("]")
    if inicio < 0 or fin < inicio:
        return None
    try:
        datos = json.loads(texto[inicio:fin + 1])
    except ValueError:
        return None
    return [h for h in datos if isinstance(h, dict)] if isinstance(datos, list) else None


def celda(valor, largo=170):
    texto = re.sub(r"\s+", " ", str(valor or "")).replace("|", "\\|").strip()
    return texto if len(texto) <= largo else texto[:largo - 1] + "…"


def defecto(h):
    """DEF-nn que el agente dice reconocer en el hallazgo, o None si lo marcó como distinto."""
    m = DEF.search(str(h.get("conocido") or ""))
    return m.group(0).upper() if m else None


def main():
    ruta = Path(sys.argv[1]) if len(sys.argv) > 1 else RUTA
    try:
        r = json.loads(ruta.read_text(encoding="utf-8").strip().splitlines()[-1])
    except (OSError, ValueError, IndexError):
        print("### Exploración con IA (MCP de WebdriverIO)\n\nNo hay resultado de la sesión (el agente no llegó a terminar o no dejó salida).\n")
        return
    u = r.get("usage", {})
    contexto = u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0) + u.get("cache_read_input_tokens", 0)
    miles = lambda n: f"{n:,}".replace(",", " ")  # solo en los números: el texto lleva comas propias
    costo = (f"{round(r.get('duration_ms', 0) / 1000)} s, {r.get('num_turns', '?')} turnos, "
             f"{miles(contexto)} tokens de contexto y {miles(u.get('output_tokens', 0))} de salida, "
             f"≈ US$ {r.get('total_cost_usd', 0):.2f} a precio de lista")
    print("### Exploración con IA (MCP de WebdriverIO)\n")
    print("Un agente de Claude Code con solo el MCP de WebdriverIO exploró la interfaz de Qolqe buscando comportamientos que "
          "contradigan las reglas de negocio. Se le pasó la lista de defectos ya conocidos para que marque cuáles reconoce y deje "
          "aparte lo nuevo.\n")
    print(f"Sesión: {costo}.\n")
    if r.get("is_error") or r.get("subtype") not in (None, "success"):
        print(f"La sesión no terminó bien (`{r.get('subtype')}`): puede que haya alcanzado el tope de gasto o de tiempo.\n")
    lista = hallazgos(r.get("result") or "")
    if lista is None:
        print("El agente no devolvió un arreglo JSON de hallazgos válido; su respuesta cruda queda en el artefacto `exploracion`.\n")
        return
    if not lista:
        print("**Sin hallazgos.** El agente no encontró nada raro en esta sesión (ni siquiera defectos ya conocidos).\n")
        return
    nuevos, repetidos = [h for h in lista if not defecto(h)], [h for h in lista if defecto(h)]
    print(f"**{len(lista)} hallazgo(s): {len(nuevos)} posiblemente nuevo(s) y {len(repetidos)} ya conocido(s).** "
          "El agente marca qué defecto reconoce y puede equivocarse: hay que reproducir cada uno antes de registrarlo.\n")
    if nuevos:
        print("#### Posiblemente nuevos\n")
        print("| Pantalla | Qué hizo | Esperado | Observado | Severidad |\n|---|---|---|---|---|")
        for h in nuevos:
            print(f"| {celda(h.get('pagina'), 40)} | {celda(h.get('pasos'))} | {celda(h.get('esperado'))} | {celda(h.get('observado'))} "
                  f"| {celda(h.get('seguridad'), 12)} |")
        print()
    else:
        print("**Ninguno nuevo.** Todo lo que el agente vio ya estaba registrado.\n")
    if repetidos:
        print("#### Ya conocidos, reconfirmados en esta sesión\n")
        print("| Defecto | Pantalla | Qué observó |\n|---|---|---|")
        for h in repetidos:
            print(f"| {defecto(h)} | {celda(h.get('pagina'), 40)} | {celda(h.get('observado'))} |")
        print()


if __name__ == "__main__":
    main()

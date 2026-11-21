"""Resume benchmark/mcp/crudo/*.json en benchmark/mcp/resultados.json y una tabla Markdown.

    python resumir.py            (desde tests/e2e/benchmark/mcp)

Por corrida lee, del último evento de `claude -p --output-format stream-json` (<tag>.json): tokens, costo (total_cost_usd, a precio de
lista), turnos y tiempo; de la traza (<tag>.traza.ndjson): cuántas llamadas a herramientas hizo y cuáles; de <tag>.verif.json: si la
tarea quedó bien según la API. Las corridas «base-*» (prompt trivial) miden lo fijo de cada configuración y se restan aparte.
"""
import json
import statistics
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).resolve().parent
CRUDO = AQUI / "crudo"
NOMBRES = {"G": "G · Claude in Chrome (--chrome)", "E": "E · MCP de WebdriverIO (@wdio/mcp)", "F": "F · `wdio session` en la terminal", "D": "D · scripts propios del agente"}


def corrida(tag):
    r = json.loads((CRUDO / f"{tag}.json").read_text(encoding="utf-8"))
    u = r.get("usage", {})
    nuevo, escr, lect, sal = (u.get(k, 0) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens"))
    herramientas = Counter()
    for linea in (CRUDO / f"{tag}.traza.ndjson").read_text(encoding="utf-8").splitlines():
        try:
            o = json.loads(linea)
        except ValueError:
            continue
        if o.get("type") == "assistant":
            for b in o.get("message", {}).get("content", []):
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    herramientas[b["name"].replace("mcp__wdio-mcp__", "mcp:")] += 1
    verif = CRUDO / f"{tag}.verif.json"
    exito = json.loads(verif.read_text(encoding="utf-8")).get("exito") if verif.exists() and verif.stat().st_size else None
    meta = json.loads((CRUDO / f"{tag}.meta.json").read_text(encoding="utf-8"))
    return {"tag": tag, "exito": exito, "error": r.get("is_error"), "subtipo": r.get("subtype"), "rc": meta["rc"],
            "s": round(r.get("duration_ms", 0) / 1000, 1), "turnos": r.get("num_turns"),
            "tokens_entrada_nuevos": nuevo, "tokens_cache_escritura": escr, "tokens_cache_lectura": lect, "tokens_salida": sal,
            "tokens_contexto_total": nuevo + escr + lect, "usd": round(r.get("total_cost_usd", 0), 4),
            "llamadas_herramientas": sum(herramientas.values()), "herramientas": dict(herramientas)}


def med(xs):
    xs = [x for x in xs if x is not None]
    return (statistics.median(xs), min(xs), max(xs)) if xs else (None, None, None)


def celda(xs, fmt="{:,.0f}"):
    m, a, b = med(xs)
    if m is None:
        return "—"
    f = lambda v: fmt.format(v).replace(",", " ")
    return f"**{f(m)}** [{f(a)}–{f(b)}]"


def main():
    por = {}
    for tag in sorted(p.name[:-5] for p in CRUDO.glob("*.json") if not p.name.endswith((".verif.json", ".meta.json"))):
        por.setdefault(tag.rsplit("-", 1)[0], []).append(corrida(tag))
    salida = {"enfoques": por}
    fijo = {k[5:]: v[0] for k, v in por.items() if k.startswith("base-")}
    salida["base"] = {k: {x: v[x] for x in ("tokens_contexto_total", "usd")} for k, v in fijo.items()}
    (AQUI / "resultados.json").write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")

    print("| Enfoque | n | Éxito | Tiempo (s) | Turnos | Llamadas a herramientas | Contexto total (tokens) | Salida (tokens) | USD por corrida |")
    print("|---|---|---|---|---|---|---|---|---|")
    for k in ("E", "F", "D", "G"):
        c = por.get(k)
        if not c:
            continue
        ok = sum(1 for x in c if x["exito"])
        print(f"| {NOMBRES[k]} | {len(c)} | {ok}/{len(c)} | {celda([x['s'] for x in c])} | {celda([x['turnos'] for x in c])} | "
              f"{celda([x['llamadas_herramientas'] for x in c])} | {celda([x['tokens_contexto_total'] for x in c])} | "
              f"{celda([x['tokens_salida'] for x in c])} | {celda([x['usd'] for x in c], '{:,.3f}')} |")
    print("\nCosto fijo (corrida base, prompt trivial):", {k: f"{v['tokens_contexto_total']} tokens, US$ {v['usd']}" for k, v in salida["base"].items()})
    for k in ("E", "F", "D", "G"):
        for x in por.get(k, []):
            print(f"  {x['tag']}: éxito={x['exito']} rc={x['rc']} {x['s']} s, {x['turnos']} turnos, {x['tokens_contexto_total']} tokens, "
                  f"US$ {x['usd']}, herramientas={x['herramientas']}")


if __name__ == "__main__":
    main()

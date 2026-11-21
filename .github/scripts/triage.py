"""Triage con IA de un run de CI (asesor: nunca forma parte del quality gate).

    python .github/scripts/triage.py [destino]     (destino por defecto: sitio/)

Si el run tuvo fallas inesperadas, le pasa a Claude lo que el pipeline ya sabe (los JUnit, los defectos conocidos de
docs/defectos.md y lo que pasó con la misma prueba en las otras corridas del run) y escribe `triage.md` y `triage.html`
con la clasificación de cada falla (defecto conocido / intermitente / nueva) y el siguiente paso. Imprime el Markdown
por stdout (para $GITHUB_STEP_SUMMARY).

No llama al modelo, y sale con 0, cuando: no hay fallas (un run verde cuesta 0), falta ANTHROPIC_API_KEY (forks, PR,
repos sin el secreto) o la API falla. Solo biblioteca estándar, como reportes.py.

    ANTHROPIC_API_KEY   clave de la API (en el CI, secreto del repositorio)
    TRIAGE_MODELO       modelo (por defecto claude-sonnet-5-5)
    TRIAGE_BACKEND      api (por defecto) | cli: usa `claude -p` con la sesión iniciada, solo para probar en local
    ANTHROPIC_BASE_URL  para apuntar a un servidor de pruebas
"""
import glob
import html
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reportes as R  # noqa: E402  (mismo directorio)

MODELO = os.environ.get("TRIAGE_MODELO", "claude-sonnet-5-5")
URL = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/") + "/v1/messages"
USD_POR_MTOK = (2.0, 10.0)  # entrada y salida de Sonnet 5.x a precio de lista, solo para informar el costo

SISTEMA = (
    "Eres un ingeniero de QA que hace el triage de un run de CI de un proyecto académico (Qolqe Wallet, pruebas de API y web). "
    "Solo puedes usar los datos que se te dan; si algo no alcanza para concluir, dilo. No inventes nombres de pruebas, defectos ni causas. "
    "Clasifica cada falla en una sola categoría: DEFECTO CONOCIDO (cita su DEF-nn solo si el mensaje o el escenario lo respalda), "
    "INTERMITENTE (la misma prueba pasó en otra corrida del mismo run, o el mensaje apunta a una condición de carrera) o NUEVA (no coincide "
    "con ningún defecto conocido ni parece intermitente). Para cada falla escribe: la clasificación, la evidencia en una frase y el siguiente "
    "paso concreto. Termina con un veredicto de dos líneas: si el run se puede dar por bueno y qué haría falta. Responde en español, en "
    "Markdown, con un máximo de 300 palabras, sin tablas y sin título (ya lo pone la página). Las pruebas web ya usan esperas explícitas con "
    "reintento; no recomiendes esperas fijas (sleep)."
)


def casos_de_prueba():
    """[(origen, nombre, estado, mensaje)] de todos los testcases de los JUnit del run (API, contrato y web)."""
    archivos = [R.RAIZ / "reportes/junit-api.xml", R.CONTRATO]
    archivos += sorted(Path(p) for p in glob.glob(str(R.RAIZ / "tests/e2e/reportes/junit*/*.xml")))
    salida = []
    for a in archivos:
        if a.parent.name == "junit-def14":  # DEF-14 debe fallar: el pipeline lo invierte, no es una falla inesperada
            continue
        for tc in R.pruebas(a):
            est, msg = R.estado(tc), ""
            if est in ("falla", "xpass"):
                h = next(h for h in tc if h.tag in ("failure", "error"))
                msg = " ".join(((h.get("message") or "") + " " + (h.text or "")).split())[:600]
            origen = a.parent.name if a.parent.name.startswith("junit") else a.stem
            salida.append((origen, tc.get("name") or "", est, msg))
    return salida


def defectos_conocidos():
    texto = (R.RAIZ / "docs/defectos.md").read_text(encoding="utf-8")
    return [f"{d}: {t.strip()}" for d, t in re.findall(r"^## (DEF-\d+): (.+)$", texto, re.M)]


def gate_texto(casos):
    """La tabla del quality gate como texto: gate_md la imprime (y devuelve cuántos criterios fallan), así que se captura."""
    import contextlib
    import io
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        R.gate_md(R.criterios(casos))
    return buffer.getvalue().strip()


def contexto(run, casos, pruebas):
    fallas = [p for p in pruebas if p[2] in ("falla", "xpass")]
    por_nombre = {}
    for origen, nombre, est, _ in pruebas:
        por_nombre.setdefault(nombre, []).append(f"{origen}: {est}")
    bloques = []
    for origen, nombre, est, msg in fallas:
        bloques.append(f"- Prueba: {nombre}\n  Origen: {origen} · estado: {est}\n  Mensaje: {msg or '(sin mensaje)'}\n"
                       f"  Esa misma prueba en este run: {'; '.join(por_nombre[nombre])}")
    return (f"Run #{run['numero']} · commit {run['corto']} · rama {run['rama'] or '—'}\n\n"
            f"Quality gate:\n{gate_texto(casos)}\n\n"
            f"Fallas inesperadas ({len(fallas)}):\n" + "\n".join(bloques[:12]) + "\n\n"
            "Defectos conocidos del proyecto (un escenario marcado @DEF-nn falla a propósito y aparece como xfail, no aquí):\n"
            + "\n".join(f"- {d}" for d in defectos_conocidos()) + "\n\n"
            "Nota: DEF-15 (la API responde antes de guardar) hace que lecturas inmediatas vean el estado viejo; es la causa más "
            "frecuente de fallas intermitentes en las pruebas web.")


def llamar_api(usuario):
    cuerpo = json.dumps({"model": MODELO, "max_tokens": 1200, "system": SISTEMA,
                         "messages": [{"role": "user", "content": usuario}]}).encode()
    req = urllib.request.Request(URL, data=cuerpo, headers={"content-type": "application/json", "anthropic-version": "2023-06-01",
                                                            "x-api-key": os.environ["ANTHROPIC_API_KEY"]})
    with urllib.request.urlopen(req, timeout=90) as r:
        d = json.load(r)
    texto = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
    uso = d.get("usage", {})
    return texto.strip(), uso.get("input_tokens", 0), uso.get("output_tokens", 0)


def llamar_cli(usuario):
    """Solo para probar en local con la sesión iniciada de Claude Code (no hay clave de API en esta máquina)."""
    p = subprocess.run(["claude", "-p", usuario, "--model", MODELO, "--output-format", "json", "--system-prompt", SISTEMA,
                        "--tools", "", "--no-session-persistence", "--disable-slash-commands", "--setting-sources", "project",
                        "--strict-mcp-config"], capture_output=True, text=True, timeout=180, encoding="utf-8")
    d = json.loads(p.stdout.strip().splitlines()[-1])
    u = d.get("usage", {})
    entrada = u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0) + u.get("cache_read_input_tokens", 0)
    return (d.get("result") or "").strip(), entrada, u.get("output_tokens", 0)


def markdown_a_html(md):
    """Conversión mínima (títulos, listas, negrita y código) del texto del modelo; todo escapado antes."""
    salida, en_lista = [], False
    for linea in md.splitlines():
        t = html.escape(linea.rstrip())
        t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
        t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
        item = re.match(r"^\s*[-*] (.*)", t)
        if item and not en_lista:
            salida.append("<ul>")
        if not item and en_lista:
            salida.append("</ul>")
        en_lista = bool(item)
        if item:
            salida.append(f"<li>{item.group(1)}</li>")
        elif re.match(r"^#{1,4} ", t):
            salida.append(f"<h3>{re.sub(r'^#+ ', '', t)}</h3>")
        elif t.strip():
            salida.append(f"<p>{t}</p>")
    return "\n".join(salida) + ("</ul>" if en_lista else "")


def main():
    destino = R.RAIZ / (sys.argv[1] if len(sys.argv) > 1 else "sitio")
    run, casos, pruebas = R.datos_run(), R.casos_con_resultados(), casos_de_prueba()
    fallas = [p for p in pruebas if p[2] in ("falla", "xpass")]
    if not fallas:
        print("### Triage con IA\n\nSin fallas inesperadas en este run: no hace falta triage (y no se llamó al modelo).\n")
        return
    backend = os.environ.get("TRIAGE_BACKEND", "api")
    if backend == "api" and not os.environ.get("ANTHROPIC_API_KEY"):
        print(f"### Triage con IA\n\nOmitido: hay {len(fallas)} falla(s) pero falta el secreto `ANTHROPIC_API_KEY` del repositorio.\n")
        return
    try:
        texto, entrada, salida = (llamar_cli if backend == "cli" else llamar_api)(contexto(run, casos, pruebas))
    except (urllib.error.URLError, OSError, ValueError, KeyError, subprocess.SubprocessError) as e:
        R.aviso(f"Triage con IA: la llamada al modelo falló ({type(e).__name__}); el run sigue sin él")
        print(f"### Triage con IA\n\nLa llamada al modelo falló ({type(e).__name__}); el run sigue sin triage.\n")
        return
    if not texto:
        R.aviso("Triage con IA: el modelo no devolvió texto")
        return
    usd = (entrada * USD_POR_MTOK[0] + salida * USD_POR_MTOK[1]) / 1e6
    miles = lambda n: f"{n:,}".replace(",", " ")
    pie = (f"_Generado por IA ({MODELO}) con el JUnit, `docs/defectos.md` y las demás corridas del run. Es un asesor: puede equivocarse "
           f"y no forma parte del quality gate. {miles(entrada)} tokens de entrada, {miles(salida)} de salida, ≈ US$ {usd:.3f} a precio de lista._")
    md = f"### Triage con IA · run #{run['numero']} ({len(fallas)} falla(s))\n\n{texto}\n\n{pie}\n"
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "triage.md").write_text(md, encoding="utf-8")
    cuerpo = (R.cabecera("Triage con IA", run) + '<p class="sec" style="margin-top:.75rem">Diagnóstico automático de las fallas de este run. '
              'Es un asesor: no forma parte del quality gate y puede equivocarse.</p>'
              f'<section><div class="cab"><h2>Fallas inesperadas <span class="crit">{len(fallas)}</span></h2></div>'
              f'{markdown_a_html(texto)}<p class="mudo">{html.escape(pie.strip("_"))}</p></section>')
    (destino / "triage.html").write_text(R.pagina("Qolqe · Triage con IA", cuerpo), encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()

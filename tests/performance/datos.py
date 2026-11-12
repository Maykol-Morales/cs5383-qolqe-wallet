"""Datos de prueba e integridad para las pruebas de rendimiento.

Corre en la máquina de Qolqe (lee y escribe QOLQE_BD), desde la raíz del repo:
  python tests/performance/datos.py preparar <dir> [usuarios]   reinicia, completa usuarios y guarda la foto
  python tests/performance/datos.py verificar <dir>             compara la BD con la foto y con k6.json.gz
"""
import gzip
import json
import os
import sqlite3
import sys
import urllib.request
from collections import Counter
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from qolqe import config, reloj  # noqa: E402
from qolqe.semilla import USUARIOS_BASE, USUARIOS_DE_CARGA  # noqa: E402

URL = os.getenv("QOLQE_URL", "http://localhost:8000")
TABLAS = ("movimientos", "transferencias", "recargas", "pagos_servicio")
DEUDAS_POR_USUARIO = 30


def uid(n: int) -> int:
    """Id del usuario de carga n (celular 9{n:08d})."""
    return len(USUARIOS_BASE) + n


def suministro(n: int) -> str:
    return f"5{n:08d}"


def preparar(directorio: Path, usuarios: int) -> None:
    urllib.request.urlopen(urllib.request.Request(f"{URL}/api/pruebas/reiniciar", method="POST"), timeout=300)
    bd = sqlite3.connect(config.RUTA_BD, timeout=30)
    with bd:
        # Usuarios 201..N: copias de los de carga (mismo PIN, saldo, límite e historial).
        for n in range(USUARIOS_DE_CARGA + 1, usuarios + 1):
            nuevo, origen = uid(n), uid((n - 1) % USUARIOS_DE_CARGA + 1)
            bd.execute("""INSERT INTO usuarios (id, dni, nombres, celular, pin_hash, creado_en)
                          SELECT ?, ?, ?, ?, pin_hash, creado_en FROM usuarios WHERE id = ?""",
                       (nuevo, f"7{n:07d}", f"Usuario Carga {n:03d}", f"9{n:08d}", origen))
            for tabla in ("cuentas", "limites"):
                columnas = [c[1] for c in bd.execute(f"PRAGMA table_info({tabla})")][1:]
                bd.execute(f"INSERT INTO {tabla} (usuario_id, {', '.join(columnas)}) "
                           f"SELECT ?, {', '.join(columnas)} FROM {tabla} WHERE usuario_id = ?", (nuevo, origen))
            bd.execute("INSERT INTO historial_pin (usuario_id, pin_hash, creado_en) "
                       "SELECT ?, pin_hash, creado_en FROM historial_pin WHERE usuario_id = ?", (nuevo, origen))
            bd.execute("""INSERT INTO movimientos (usuario_id, codigo_operacion, tipo, descripcion, contraparte,
                                                   monto_cent, comision_cent, importe_cent, fecha)
                          SELECT ?, codigo_operacion, tipo, descripcion, contraparte, monto_cent, comision_cent,
                                 importe_cent, fecha FROM movimientos WHERE usuario_id = ?""", (nuevo, origen))
        # Todos: 5 contactos y un suministro propio con deudas pendientes (no hay API para crear deudas).
        ahora, vence = reloj.a_texto(reloj.ahora()), reloj.hoy() + timedelta(days=20)
        bd.executemany("INSERT INTO contactos (usuario_id, contacto_usuario_id, alias, favorito, creado_en) "
                       "VALUES (?, ?, ?, 0, ?)",
                       [(uid(n), uid((n + k - 1) % usuarios + 1), f"Contacto {k}", ahora)
                        for n in range(1, usuarios + 1) for k in range(1, 6)])
        bd.executemany("INSERT INTO deudas (empresa, suministro, titular, periodo, monto_cent, vencimiento) "
                       "VALUES ('ELECTRO', ?, ?, ?, 1000, ?)",
                       [(suministro(n), f"Usuario Carga {n:03d}", f"{vence:%Y-%m}", vence.isoformat())
                        for n in range(1, usuarios + 1) for _ in range(DEUDAS_POR_USUARIO)])
    foto = {"max_id": {t: bd.execute(f"SELECT COALESCE(MAX(id), 0) FROM {t}").fetchone()[0] for t in TABLAS},
            "saldos": dict(bd.execute("SELECT usuario_id, saldo_cent FROM cuentas"))}
    bd.close()
    directorio.mkdir(parents=True, exist_ok=True)
    (directorio / "foto.json").write_text(json.dumps(foto))
    print(f"{usuarios} usuarios listos; foto en {directorio / 'foto.json'}")


def refs_de_k6(ruta: Path) -> dict[str, set[str]]:
    """Referencias de las peticiones de dinero que k6 envió, por resultado (ok = 2xx)."""
    refs = {"ok": set(), "error": set()}
    with gzip.open(ruta, "rt") as f:
        for linea in f:
            if '"http_reqs"' not in linea or '"ref"' not in linea:
                continue
            tags = json.loads(linea)["data"]["tags"]
            refs["ok" if tags.get("status", "").startswith("2") else "error"].add(tags["ref"])
    return refs


def verificar(directorio: Path) -> int:
    foto = json.loads((directorio / "foto.json").read_text())
    desde = foto["max_id"]
    bd = sqlite3.connect(config.RUTA_BD)
    fallos, avisos = [], []

    # 1. Por usuario: lo que cambió el saldo = suma de sus movimientos nuevos.
    importes = dict(bd.execute("SELECT usuario_id, SUM(importe_cent) FROM movimientos WHERE id > ? GROUP BY usuario_id",
                               (desde["movimientos"],)))
    for usuario, saldo in bd.execute("SELECT usuario_id, saldo_cent FROM cuentas"):
        delta = saldo - foto["saldos"].get(str(usuario), 0)
        if delta != importes.get(usuario, 0):
            fallos.append(f"usuario {usuario}: saldo cambió {delta} y sus movimientos suman {importes.get(usuario, 0)}")
        if saldo < 0:
            fallos.append(f"usuario {usuario}: saldo negativo {saldo}")

    # 2. Cada operación con sus movimientos: transferencia QOLQE = 2, recarga = 1, pago = 1.
    nuevos = lambda tabla, extra="": bd.execute(f"SELECT COUNT(*) FROM {tabla} WHERE id > ? {extra}",  # noqa: E731
                                                (desde[tabla],)).fetchone()[0]
    movs = dict(bd.execute("SELECT tipo, COUNT(*) FROM movimientos WHERE id > ? GROUP BY tipo", (desde["movimientos"],)))
    esperado = {"TRANSFERENCIA_ENVIADA": nuevos("transferencias"),
                "TRANSFERENCIA_RECIBIDA": nuevos("transferencias", "AND tipo = 'QOLQE'"),
                "RECARGA": nuevos("recargas"), "PAGO_SERVICIO": nuevos("pagos_servicio")}
    for tipo, cantidad in esperado.items():
        if movs.get(tipo, 0) != cantidad:
            fallos.append(f"{tipo}: {movs.get(tipo, 0)} movimientos para {cantidad} operaciones")
    for deuda, pagos in bd.execute("SELECT deuda_id, COUNT(*) FROM pagos_servicio GROUP BY deuda_id HAVING COUNT(*) > 1"):
        fallos.append(f"deuda {deuda} pagada {pagos} veces")

    # 3. Cruce 1:1 con k6 por referencia propia de cada petición.
    en_bd = [f"T-{d}" for (d,) in bd.execute("SELECT descripcion FROM transferencias WHERE id > ?", (desde["transferencias"],))]
    en_bd += [f"R-{c}" for (c,) in bd.execute("SELECT celular FROM recargas WHERE id > ?", (desde["recargas"],))]
    en_bd += [f"P-{d}" for (d,) in bd.execute("SELECT deuda_id FROM pagos_servicio WHERE id > ?", (desde["pagos_servicio"],))]
    bd.close()
    duplicadas = [r for r, veces in Counter(en_bd).items() if veces > 1]
    k6 = refs_de_k6(directorio / "k6.json.gz")
    perdidas = k6["ok"] - set(en_bd)
    aplicadas_con_error = k6["error"] & set(en_bd)
    if duplicadas:
        fallos.append(f"{len(duplicadas)} operaciones aplicadas dos veces: {sorted(duplicadas)[:5]}")
    if perdidas:
        fallos.append(f"{len(perdidas)} operaciones confirmadas a k6 sin fila en la BD: {sorted(perdidas)[:5]}")
    if aplicadas_con_error:
        avisos.append(f"{len(aplicadas_con_error)} operaciones aplicadas aunque k6 recibió error o timeout")

    informe = [f"Operaciones de dinero confirmadas a k6: {len(k6['ok'])}; filas nuevas: {len(en_bd)}",
               *(f"FALLO {f}" for f in fallos), *(f"AVISO {a}" for a in avisos),
               "INTEGRIDAD OK" if not fallos else f"INTEGRIDAD CON {len(fallos)} FALLOS"]
    (directorio / "integridad.txt").write_text("\n".join(informe) + "\n")
    print("\n".join(informe))
    return 1 if fallos else 0


if __name__ == "__main__":
    accion, directorio = sys.argv[1], Path(sys.argv[2])
    if accion == "preparar":
        preparar(directorio, int(sys.argv[3]) if len(sys.argv) > 3 else 1000)
    else:
        sys.exit(verificar(directorio))

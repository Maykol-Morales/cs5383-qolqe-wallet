"""Junta benchmark/crudo/* en benchmark/resultados.json. Uso, desde tests/e2e: python3 benchmark/resumir.py"""
import glob, json, re, statistics as st

# Precios de lista, USD por millón de tokens (Claude Sonnet 5 / 5.5: $2 entrada, $10 salida;
# escritura de caché 5 min = 1.25x entrada, lectura = 0.1x). D usa el total_cost_usd que informa Claude Code.
P_IN, P_OUT, P_CW, P_CR = 2.0, 10.0, 2.5, 0.2
crudo = 'benchmark/crudo'


def wdio(modo):
    corridas = []
    for f in sorted(glob.glob(f'{crudo}/{modo}-*.ndjson'), key=lambda p: int(re.search(r'-(\d+)\.', p)[1])):
        regs = [json.loads(l) for l in open(f)]
        fin = next(r for r in regs if r['tipo'] == 'corrida')
        llm = [r['usage'] for r in regs if r['tipo'] == 'llm']
        cr = sum(u['input_token_details']['cache_read'] for u in llm)
        cw = sum(u['input_token_details']['cache_creation'] for u in llm)
        tin = sum(u['input_tokens'] for u in llm) - cr - cw  # LangChain suma la caché dentro de input_tokens
        tout = sum(u['output_tokens'] for u in llm)
        log = open(f.replace('.ndjson', '.log')).read()
        corridas.append({
            'corrida': fin['i'], 'exito': fin['rc'] == 0, 'ms_total': fin['ms'],
            'ms_escenario': round(float(re.search(r'passing \(([\d.]+)s\)', log)[1]) * 1000) if 'passing (' in log else None,
            'llamadas_modelo': len(llm), 'tokens_entrada': tin, 'tokens_salida': tout,
            'tokens_cache_lectura': cr, 'tokens_cache_escritura': cw,
            'costo_usd': round((tin * P_IN + tout * P_OUT + cw * P_CW + cr * P_CR) / 1e6, 6),
            'acts': [{k: r.get(k) for k in ('instruction', 'source', 'durationMs', 'usage', 'error')} for r in regs if r['tipo'] == 'act'],
        })
    return corridas


def herramientas(traza):
    usos = []
    for l in open(traza):
        d = json.loads(l)
        if d.get('type') == 'assistant':
            usos += [json.dumps(b['input']) for b in d['message']['content'] if b['type'] == 'tool_use']
    return usos


def agente(patron):
    corridas = []
    for f in sorted([p for p in glob.glob(f'{crudo}/{patron}.json') if not p.endswith('.verif.json')], key=lambda p: int(re.search(r'-(\d+)\.json', p)[1])):
        d, v = json.load(open(f)), json.load(open(f.replace('.json', '.verif.json')))
        u = d['usage']
        c = {'corrida': f.split('/')[-1][:-5], 'modelo': list(d['modelUsage'])[0], 'exito_verificado_api': v['exito'],
             'exito_declarado': '"exito": true' in d['result'], 'clasificado': v['clasificados'],
             'ms_total': d['duration_ms'], 'turnos': d['num_turns'], 'tokens_entrada': u['input_tokens'],
             'tokens_salida': u['output_tokens'], 'tokens_cache_lectura': u['cache_read_input_tokens'],
             'tokens_cache_escritura': u['cache_creation_input_tokens'], 'costo_usd': d['total_cost_usd'],
             'metodo_declarado': d['result'][-600:]}
        try:
            t = herramientas(f.replace('.json', '.traza.ndjson'))
            c['traza'] = {
                'herramientas': len(t),
                'leyo_el_repo': any('pages/' in x and 'cat' in x for x in t),
                'leyo_.env_con_la_clave': any('.env' in x and 'cat' in x for x in t),
                'llamo_api_pruebas_reiniciar': any('/api/pruebas/reiniciar' in x for x in t),
                'corrio_la_suite_existente': any('wdio run' in x for x in t),
                'script_webdriverio_propio': any('remote(' in x for x in t),
                'escribio_archivos_en_el_repo': any(re.search(r'> ?/home/[^ ]*cs5383-qolqe-wallet/tests/e2e/[\w-]+\.mjs|cp [^ ]+ /home/[^ ]*tests/e2e/', x) for x in t),
            }
        except FileNotFoundError:
            c['traza'] = None  # D-1..3: corridas con --output-format json, sin traza de herramientas
        corridas.append(c)
    return corridas


def resumen(corridas, campos=('ms_total', 'tokens_entrada', 'tokens_salida', 'costo_usd')):
    r = {'n': len(corridas), 'exitos': sum(c.get('exito', c.get('exito_verificado_api')) for c in corridas)}
    for k in campos:
        xs = [c[k] for c in corridas if c.get(k) is not None]
        r[k] = {'mediana': st.median(xs), 'min': min(xs), 'max': max(xs)} if xs else None
    return r


datos = {
    'tarea': "Login de Ana, Movimientos, crear 'Viajes' #1E88E5, clasificar el más reciente con nota 'Pasaje a Cusco', verificar la fila",
    'precios_usd_por_mtok': {'entrada': P_IN, 'salida': P_OUT, 'cache_escritura_5m': P_CW, 'cache_lectura': P_CR},
    'A_act_en_frio': wdio('A'), 'B_act_desde_cache': wdio('B'), 'C_page_objects': wdio('C'),
    'D_agente_sonnet_5_5': agente('D-[1237]'), 'D_agente_sonnet_5': agente('D-[456]'), 'D_agente_sonnet_5_sin_ruta_repo': agente('Dc-*'),
}
datos['resumen'] = {k: resumen(v) for k, v in datos.items() if k[1:2] == '_' and isinstance(v, list)}
json.dump(datos, open('benchmark/resultados.json', 'w'), ensure_ascii=False, indent=2)
print(json.dumps(datos['resumen'], indent=1))

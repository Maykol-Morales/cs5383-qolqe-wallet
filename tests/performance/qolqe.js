// Prueba de rendimiento de Qolqe: requerimiento "Quincena Qolqe" (pdfs/P2_Parte3_Enunciado.pdf §4).
// PRUEBA=humo|carga|pico|estres. Resistencia = carga con DURACION=60m. Modelo y trazabilidad: docs/plan-rendimiento.md
import http from 'k6/http';
import { sleep } from 'k6';
import exec from 'k6/execution';
import { Counter } from 'k6/metrics';

const URL = __ENV.QOLQE_URL || 'http://localhost:8000';
const PRUEBA = __ENV.PRUEBA || 'humo';
const USUARIOS = Number(__ENV.USUARIOS || 1000); // preparados con datos.py; uno por VU
const DURACION = __ENV.DURACION || '15m';
// Pesos de la tabla del requerimiento: saldo+perfil, movimientos, transferencia, contactos,
// recarga, consultar deuda, pagar deuda, otras. PESOS permite el experimento sin historial.
const PESOS = (__ENV.PESOS || '30,15,15,10,10,6,4,10').split(',').map(Number);

// Escalones del estrés: desde el pico (300) hasta TOPE, 1 min de subida + 3 min estable.
// El primero sube en 5 min como el pico: con 0 → 300 en 1 min Qolqe colapsa por "database is locked"
// (resultados/estres-20261111-2048-docker-rampa-1min) y no se mide la capacidad.
const escalones = [];
if (PRUEBA === 'estres' && Number(__ENV.TOPE || 1000) > USUARIOS) throw new Error('TOPE > USUARIOS: los VUs sobrantes no tienen usuario');
for (let v = 300; v <= Number(__ENV.TOPE || 1000); v += Number(__ENV.PASO || 100)) {
  escalones.push({ target: v, duration: v === 300 ? '5m' : '1m' }, { target: v, duration: '3m' });
}

const ESCENARIOS = {
  humo: { executor: 'per-vu-iterations', vus: 1, iterations: 3 },
  // 3 000 sesiones/h = 50/min; Little: 50/min × 2 min = 100 VUs. maxVUs acotado para que el atraso se vea.
  carga: {
    executor: 'ramping-arrival-rate', startRate: 0, timeUnit: '1m', preAllocatedVUs: 100, maxVUs: 120,
    stages: [{ target: 50, duration: '2m' }, { target: 50, duration: DURACION }],
  },
  // Triple de usuarios simultáneos (300); todos entran en los primeros 5 de los 15 min.
  pico: { executor: 'ramping-vus', startVUs: 0, stages: [{ target: 300, duration: '5m' }, { target: 300, duration: '10m' }] },
  estres: { executor: 'ramping-vus', startVUs: 0, stages: escalones },
};

// Pico: "degradación razonable" = 2× el umbral y 5 % de fallas (supuesto del plan).
const [CONSULTA_MS, DINERO_MS, FALLAS] = PRUEBA === 'pico' ? [1600, 3000, 0.05] : [800, 1500, 0.01];
const umbrales = {
  'http_req_duration{tipo:consulta}': [`p(95)<${CONSULTA_MS}`],
  'http_req_duration{tipo:dinero}': [`p(95)<${DINERO_MS}`],
  http_req_failed: [`rate<${FALLAS}`],
  errores_negocio: ['count<1'],
};
if (PRUEBA === 'carga') {
  umbrales.dropped_iterations = ['count<1']; // "sin acumular retrasos"
  umbrales.iteration_duration = ['p(95)<130000']; // sesión ≈ 2 min; 6 pausas dan p95 ≈ 120 s
}
if (PRUEBA === 'estres') {
  umbrales.http_req_failed = [{ threshold: 'rate<0.10', abortOnFail: true, delayAbortEval: '1m' }];
}

export const options = {
  scenarios: { [PRUEBA]: ESCENARIOS[PRUEBA] },
  thresholds: umbrales,
  summaryTrendStats: ['avg', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

// Solo 5xx y errores de red son fallas técnicas; los 4xx son reglas de negocio (datos), se cuentan aparte.
http.setResponseCallback(http.expectedStatuses({ min: 200, max: 499 }));
const erroresNegocio = new Counter('errores_negocio');
const operaciones = new Counter('operaciones');

function pedir(metodo, ruta, cuerpo, tipo, extra = {}) {
  const params = {
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    tags: { name: `${metodo} ${ruta.split('?')[0]}`, tipo, ...extra },
  };
  const r = http.request(metodo, `${URL}${ruta}`, cuerpo && JSON.stringify(cuerpo), params);
  if (r.status >= 400 && r.status < 500) {
    let codigo = 'sin_codigo';
    try { codigo = r.json('codigo') || codigo; } catch (_) { /* cuerpo no JSON */ }
    erroresNegocio.add(1, { codigo, name: params.tags.name });
  }
  return r;
}

// Pausa de 10 a 25 s con media 18 s: triangular(10, 19, 25).
function pausa() {
  const u = Math.random();
  sleep(u < 0.6 ? 10 + Math.sqrt(u * 15 * 9) : 25 - Math.sqrt((1 - u) * 15 * 6));
}

let token = null;
const uno = (lista) => lista[Math.floor(Math.random() * lista.length)];

const OPERACIONES = [
  function saldoYPerfil() {
    pedir('GET', '/api/cuentas/me/saldo', null, 'consulta');
    pedir('GET', '/api/cuentas/me', null, 'consulta');
  },
  function movimientos() { pedir('GET', '/api/movimientos', null, 'consulta'); },
  function transferir(ref) {
    const destino = `9${String(exec.vu.idInTest % USUARIOS + 1).padStart(8, '0')}`;
    pedir('POST', '/api/transferencias',
      { tipo: 'QOLQE', celular_destino: destino, monto: `${1 + Math.floor(Math.random() * 20)}.00`, descripcion: ref },
      'dinero', { ref: `T-${ref}` });
  },
  function contactos() {
    pedir('GET', '/api/contactos', null, 'consulta');
    pedir('GET', '/api/contactos?buscar=contacto', null, 'consulta');
  },
  function recargar(ref, n) {
    // Celular destino único por recarga (máx. 5 al día por número) y sirve de referencia.
    const celular = `9${String((exec.vu.idInTest * 100000 + n) % 1e8).padStart(8, '0')}`;
    pedir('POST', '/api/recargas', { celular, monto: uno(['5', '10', '20']) }, 'dinero', { ref: `R-${celular}` });
  },
  function consultarDeuda() { pedir('GET', `/api/servicios/deudas?empresa=ELECTRO&suministro=${suministro()}`, null, 'consulta'); },
  function pagarDeuda() {
    const r = pedir('GET', `/api/servicios/deudas?empresa=ELECTRO&suministro=${suministro()}`, null, 'consulta');
    if (r.status !== 200) return;
    const id = r.json('0.id');
    pedir('POST', '/api/servicios/pagos', { deuda_id: id }, 'dinero', { ref: `P-${id}` });
  },
  function otras() {
    pedir('GET', uno(['/api/limites', '/api/limites/alertas', '/api/solicitudes',
      '/api/seguridad/dispositivos', '/api/seguridad/sesiones']), null, 'consulta');
  },
];
const suministro = () => `5${String(exec.vu.idInTest).padStart(8, '0')}`;
const TOTAL = PESOS.reduce((a, b) => a + b, 0);

function sortear() {
  let x = Math.random() * TOTAL;
  return OPERACIONES.find((_, i) => (x -= PESOS[i]) < 0);
}

// Una iteración = una sesión: login + 6 operaciones, con una pausa antes de cada una.
export default function () {
  token = null;
  const celular = `9${String(exec.vu.idInTest).padStart(8, '0')}`;
  const r = pedir('POST', '/api/auth/login', { celular, pin: '2580' }, 'consulta');
  if (r.status !== 200) return;
  token = r.json('access_token');
  for (let i = 0; i < 6; i++) {
    pausa();
    const n = exec.vu.iterationInInstance * 6 + i;
    sortear()(`k6-${exec.vu.idInTest}-${n}`, n);
    operaciones.add(1);
  }
}

// Comparativa del generador (docs/comparativa-rendimiento.md §4): el mismo escenario que locustfile.py.
// 100 usuarios que entran en 50 s (2/s, por debajo de los 40 logins simultáneos de DEF-16), login una vez
// y luego saldo cada 1 s durante 2 min.
import http from 'k6/http';
import { sleep } from 'k6';
import exec from 'k6/execution';

const URL = __ENV.QOLQE_URL || 'http://localhost:8001';
export const options = {
  scenarios: { saldo: { executor: 'ramping-vus', stages: [{ target: 100, duration: '50s' }, { target: 100, duration: '2m' }] } },
};
let token;

export default function () {
  if (!token) {
    const celular = `9${String(exec.vu.idInTest).padStart(8, '0')}`;
    const r = http.post(`${URL}/api/auth/login`, JSON.stringify({ celular, pin: '2580' }), { headers: { 'Content-Type': 'application/json' } });
    token = r.json('access_token');
  }
  http.get(`${URL}/api/cuentas/me/saldo`, { headers: { Authorization: `Bearer ${token}` } });
  sleep(1);
}

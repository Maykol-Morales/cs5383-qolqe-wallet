// Guion de la demo en vivo (Windows, Linux y macOS). Uso: npm run demo
// Cada paso espera Enter. Levanta Qolqe si no está corriendo y lo apaga al final.
// Termina generando y abriendo el reporte Allure de las corridas de la demo.
import { spawn, spawnSync } from 'node:child_process'
import { existsSync, readFileSync, writeFileSync, readdirSync, rmSync, mkdirSync, openSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { createInterface } from 'node:readline/promises'

try { process.loadEnvFile() } catch {} // ANTHROPIC_API_KEY desde .env, si existe
const URL = 'http://localhost:8000'
const RAIZ = resolve('../..') // raíz del repo: qolqe/ y .venv/ están allí
const SPEC = 'features/clasificar.feature'
const SPEC_IA = 'features/clasificar-ia.feature'
const CACHE_IA = 'features/__act__/clasificar-ia.feature.json'
const original = readFileSync(SPEC, 'utf8')
const rl = createInterface({ input: process.stdin, output: process.stdout })

// Si la entrada se cierra (stdin redirigido o CI), la demo sigue sin esperar.
const paso = (titulo) => rl.question(`\n\x1b[1;31m▸ ${titulo}\x1b[0m\n  [Enter] `).catch(() => {})
// Un solo string con shell: npx es npx.cmd en Windows.
const wdio = (spec, env = {}, flags = '') => spawnSync(`npx wdio run wdio.conf.js --spec ${spec} ${flags}`,
    { stdio: 'inherit', shell: true, env: { ...process.env, ...env } })
const npx = (comando) => spawnSync(`npx ${comando}`, { stdio: 'inherit', shell: true })
const abrir = { win32: 'start ""', darwin: 'open' }[process.platform] ?? 'xdg-open'
const qolqeVivo = () => fetch(`${URL}/api/salud`).then((r) => r.ok, () => false)

let qolqe
function terminar() {
    writeFileSync(SPEC, original) // deja el escenario como estaba, aun con Ctrl+C
    qolqe?.kill()
    rl.close()
}
process.on('SIGINT', () => { terminar(); process.exit(130) })

// 0. SUT: reusar Qolqe si ya corre; si no, levantarlo con una BD aparte.
if (!await qolqeVivo()) {
    const python = ['.venv/Scripts/python.exe', '.venv/bin/python'].map((p) => join(RAIZ, p)).find(existsSync) ?? 'python'
    console.log('Levantando Qolqe en :8000...')
    mkdirSync('reportes', { recursive: true })
    const log = openSync('reportes/qolqe.log', 'w') // peticiones al servidor, para diagnosticar fallas
    qolqe = spawn(python, ['-m', 'uvicorn', 'qolqe.main:app', '--port', '8000'],
        { cwd: RAIZ, env: { ...process.env, QOLQE_BD: join(tmpdir(), 'qolqe-demo.db') }, stdio: ['ignore', log, log] })
    for (let i = 0; i < 60 && !await qolqeVivo(); i++) await new Promise((r) => setTimeout(r, 500))
    if (!await qolqeVivo()) { console.error('Qolqe no arrancó. ¿Corriste python demo.py preparar en la raíz?'); terminar(); process.exit(1) }
}
console.log('Qolqe OK en', URL)
rmSync('reportes/allure-results', { recursive: true, force: true }) // el reporte muestra solo esta demo
rmSync('evidencia', { recursive: true, force: true })

await paso('IA: browser.act() escribe los pasos en lenguaje natural')
console.log(readFileSync(SPEC_IA, 'utf8').split('\n').slice(8).join('\n'))
console.log(readFileSync('steps/ia.steps.js', 'utf8').split('\n').slice(13, 19).join('\n'))
if (process.env.ANTHROPIC_API_KEY) {
    // -s (--updateSnapshots) obliga a grabar de nuevo aunque haya caché: ~45 s y ~140k tokens.
    await paso('IA en vivo: el modelo maneja Chrome y graba los pasos en features/__act__/')
    if (wdio(SPEC_IA, { HEADED: '1' }, '-s').status !== 0) {
        console.log('  La grabación falló: se restaura la caché del repositorio.')
        spawnSync(`git checkout -- ${CACHE_IA}`, { stdio: 'inherit', shell: true })
    }
}
if (existsSync(CACHE_IA)) {
    await paso('La caché: lo que eligió el modelo, con selectores estables')
    for (const { instruction, steps } of Object.values(JSON.parse(readFileSync(CACHE_IA, 'utf8')).entries)) {
        console.log(`\n  \x1b[1m${instruction}\x1b[0m`)
        for (const { code } of steps) console.log(`    ${code}`)
    }
    await paso('Repetir desde la caché: sin modelo, sin clave y sin tokens')
    wdio(SPEC_IA, { HEADED: '1', ANTHROPIC_API_KEY: '' })
} else {
    console.log('\n  Sin ANTHROPIC_API_KEY ni caché: el escenario @ia se marca como skipped.')
    wdio(SPEC_IA) // queda como "skipped" en el reporte
}

await paso('BDD: el escenario en Gherkin es la especificación')
console.log(readFileSync(SPEC, 'utf8'))

await paso('Demo del flujo: escenario → pasos → Page Objects → Chrome')
const flujo = wdio(SPEC, { HEADED: '1' })

await paso("¿Detecta fallos? Cambiamos el escenario a 'cuenta 2 movimientos'")
writeFileSync(SPEC, original.replace('cuenta 1 movimientos', 'cuenta 2 movimientos'))
wdio(SPEC)
writeFileSync(SPEC, original)
console.log(existsSync('evidencia') ? readdirSync('evidencia').map((f) => `  evidencia/${f}`).join('\n') : '  (sin capturas)')

await paso('Reporte Allure: escenarios, pasos, historias y la captura de la falla')
npx('allure generate --clean reportes/allure-results')
const reporte = join(process.cwd(), 'reportes', 'allure', 'index.html')
if (!process.env.CI) spawnSync(`${abrir} "${reporte}"`, { shell: true })
console.log(`  ${reporte}`)

terminar()
console.log('Escenario restaurado. Fin de la demo.')
process.exitCode = flujo.status // la demo falla si el flujo (no la mutación) falló

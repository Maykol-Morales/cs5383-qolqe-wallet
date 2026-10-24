import { spawn } from 'node:child_process'
import { existsSync, mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'

const RAIZ_REPO = resolve(import.meta.dirname, '../../..')
const URL_BASE = process.env.QOLQE_URL ?? 'http://127.0.0.1:8000'
const HEADLESS = process.env.HEADLESS === '1'

let servidor

async function servidorActivo() {
    try {
        return (await fetch(`${URL_BASE}/login`)).ok
    } catch {
        return false
    }
}

function pythonDelRepo() {
    const candidatos = [join(RAIZ_REPO, '.venv', 'Scripts', 'python.exe'), join(RAIZ_REPO, '.venv', 'bin', 'python')]
    return candidatos.find(existsSync) ?? 'python'
}

export const config = {
    runner: 'local',
    specs: ['./features/**/*.feature'],
    maxInstances: 1,

    capabilities: [{
        browserName: 'chrome',
        'goog:chromeOptions': {
            args: HEADLESS ? ['--headless=new', '--window-size=1280,900'] : ['--window-size=1280,900']
        }
    }],

    baseUrl: URL_BASE,
    logLevel: 'warn',
    waitforTimeout: 5000,
    connectionRetryCount: 2,

    framework: 'cucumber',
    cucumberOpts: {
        require: ['./features/step-definitions/*.js'],
        timeout: 30000
    },
    reporters: ['spec'],

    // Levanta el SUT en un proceso aparte si no hay uno corriendo (un solo proceso: el reloj va en memoria).
    async onPrepare() {
        if (await servidorActivo()) return
        const puerto = new URL(URL_BASE).port || '8000'
        // BD y plantilla de carga en una carpeta nueva: en Windows el SUT falla al reemplazar datos/plantilla_carga.db.
        const carpetaBd = mkdtempSync(join(tmpdir(), 'qolqe-wdio-'))
        servidor = spawn(pythonDelRepo(), ['-m', 'uvicorn', 'qolqe.main:app', '--port', puerto, '--log-level', 'warning'], {
            cwd: RAIZ_REPO,
            stdio: 'inherit',
            env: { ...process.env, QOLQE_MODO_PRUEBA: '1', QOLQE_BD: join(carpetaBd, 'qolqe.db'), QOLQE_BD_PLANTILLA: join(carpetaBd, 'plantilla.db') }
        })
        for (let i = 0; i < 120 && !(await servidorActivo()); i++) await new Promise(r => setTimeout(r, 500))
        if (!(await servidorActivo())) throw new Error(`El SUT no respondió en ${URL_BASE}`)
    },

    onComplete() {
        servidor?.kill()
    }
}

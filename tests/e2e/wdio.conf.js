import { mkdirSync } from 'node:fs'
import { resolve } from 'node:path'

// ANTHROPIC_API_KEY (para browser.act) puede venir de tests/e2e/.env, ignorado por git.
try { process.loadEnvFile() } catch {}

export const baseUrl = process.env.QOLQE_URL ?? 'http://localhost:8000'
export const descargas = resolve('reportes/descargas') // CSV de HU-G3-08

export const config = {
    runner: 'local',
    specs: ['./features/**/*.feature'],
    maxInstances: 1,
    capabilities: [{
        browserName: 'chrome',
        webSocketUrl: true, // WebDriver BiDi, lo usa @wdio/ai-service
        'goog:chromeOptions': {
            binary: process.env.CHROME_BIN,
            args: process.env.HEADED ? [] : ['--headless=new', '--window-size=1280,900'],
            prefs: { 'download.default_directory': descargas, 'download.prompt_for_download': false },
        },
    }],
    baseUrl,
    waitforTimeout: 5000,

    // BDD: escenarios Gherkin en features/, pasos en steps/, Page Objects en pages/.
    framework: 'cucumber',
    cucumberOpts: { require: ['./steps/*.js'], timeout: 60000 },

    // Reportería: consola + Allure (npm run reporte genera reportes/allure/index.html) + JUnit para la CI.
    reporters: ['spec', ['allure', {
        outputDir: 'reportes/allure-results',
        useCucumberStepReporter: true,     // los pasos Given/When/Then son los pasos del reporte
        disableWebdriverStepsReporting: true,
    }], ['junit', { outputDir: 'reportes/junit', outputFileFormat: ({ cid }) => `e2e-${cid}.xml` }]],

    // IA: browser.act() pide los pasos al modelo una vez y los repite desde features/__act__/
    // Sonnet 5 rechaza temperature distinta de 1; @wdio/ai-service manda otra por defecto.
    services: [['ai', { model: process.env.WDIO_AI_MODEL ?? { provider: 'anthropic', model: 'claude-sonnet-5', temperature: 1 } }]],
    logLevel: 'warn',

    // Fixture: cada escenario parte de los datos semilla de Qolqe (ver README del SUT), con su reloj
    // en la hora real (antes de reiniciar: la semilla usa ese reloj) y el navegador en hora de Lima. Qolqe valida las fechas en hora de Lima, pero la UI
    // arma desde/hasta con la hora del navegador: en un runner UTC, de noche en Lima, el historial sale
    // vacío (DEF-14, features/historial-zona-horaria.feature).
    beforeScenario: async () => {
        for (const [ruta, method] of [['reloj', 'DELETE'], ['reiniciar', 'POST']]) {
            const res = await fetch(`${baseUrl}/api/pruebas/${ruta}`, { method })
            if (!res.ok) throw new Error(`No se pudo preparar Qolqe (${ruta}): HTTP ${res.status}`)
        }
        await browser.emulationSetTimezoneOverride({ timezone: 'America/Lima', userContexts: ['default'] })
    },
    // Evidencia: captura del paso que falló, en evidencia/ y adjunta en el reporte Allure.
    afterStep: async (step, scenario, { error }) => {
        if (!error) return
        mkdirSync('evidencia', { recursive: true })
        await browser.saveScreenshot(`./evidencia/${scenario.name.replace(/\W+/g, '_')}.png`)
    },
}

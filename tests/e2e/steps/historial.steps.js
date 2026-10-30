// Pasos de /historial: DEF-14, filtros y paginación (HU-G3-01) y exportar CSV (HU-G3-08).
import { mkdirSync, readdirSync, readFileSync, rmSync } from 'node:fs'
import { join } from 'node:path'
import { Given, When, Then } from '@wdio/cucumber-framework'
import { baseUrl, descargas } from '../wdio.conf.js'
import HistorialPage from '../pages/historial.page.js'

// DEF-14: la UI arma el rango del historial con la fecha del celular, no con la de Lima.
// Fija el mismo instante en Qolqe (API de soporte) y en el navegador (solo Date, los timers siguen reales).
// A las 23:00 de Lima ya es el día siguiente en UTC: el escenario no depende de la hora en que corre.
Given('en Lima son las {int}:00 y mi celular está en hora UTC', async (hora) => {
    const hoyLima = new Date(Date.now() - 5 * 3600000).toISOString().slice(0, 10)
    const ahora = `${hoyLima}T${String(hora).padStart(2, '0')}:00:00`
    const res = await fetch(`${baseUrl}/api/pruebas/reloj`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ahora }),
    })
    if (!res.ok) throw new Error(`No se pudo fijar el reloj de Qolqe: HTTP ${res.status}`)
    await browser.emulationSetTimezoneOverride({ timezone: 'UTC', userContexts: ['default'] })
    await browser.emulate('clock', { now: new Date(`${ahora}-05:00`), toFake: ['Date'], shouldAdvanceTime: true })
})

When('abro la sección Movimientos', async () => {
    await $('aria/Movimientos').click()
    await expect(browser).toHaveUrl(expect.stringContaining('/historial'))
})

Then('veo mis movimientos de los últimos 30 días sin errores', async () => {
    await expect(HistorialPage.filas).toBeElementsArrayOfSize({ gte: 1 })
    await expect($('[data-testid=historial-error]')).not.toBeDisplayed()
})

// HU-G3-01 (filtros y paginación) y HU-G3-08 (exportar CSV).
When('filtro mis movimientos por el tipo {string}', async (tipo) => {
    await HistorialPage.filtrar({ tipo })
})

Then('todas las filas son de tipo {string}', async (nombre) => {
    await expect(HistorialPage.filas).toBeElementsArrayOfSize({ gte: 1 })
    for (const fila of await HistorialPage.filas) await expect(fila.$('td:nth-child(2)')).toHaveText(nombre)
})

When('busco mis movimientos desde hace {int} días', async (dias) => {
    await HistorialPage.filtrar({ diasAtras: dias })
})

Then('veo {int} movimientos y el indicador {string}', async (cantidad, texto) => {
    await expect(HistorialPage.filas).toBeElementsArrayOfSize(cantidad)
    await expect(HistorialPage.indicador).toHaveText(expect.stringContaining(texto))
})

When('paso a la página siguiente', async function () {
    this.anteriores = await HistorialPage.filas.map((f) => f.getAttribute('data-codigo'))
    await HistorialPage.cambiarA('boton-siguiente')
})

When('vuelvo a la página anterior', async () => {
    await HistorialPage.cambiarA('boton-anterior')
})

Then('las filas son otras que las de la página anterior', async function () {
    const actuales = await HistorialPage.filas.map((f) => f.getAttribute('data-codigo'))
    expect(actuales.filter((c) => this.anteriores.includes(c))).toEqual([])
})

Then('no puedo avanzar más', async () => {
    await expect(HistorialPage.siguiente).toBeDisabled()
})

// La UI descarga con fetch + blob + <a download>: Chrome lo guarda en la carpeta de wdio.conf.js.
When('exporto el historial a CSV', async function () {
    rmSync(descargas, { recursive: true, force: true })
    mkdirSync(descargas, { recursive: true })
    await $('[data-testid=boton-exportar]').click()
    await browser.waitUntil(() => readdirSync(descargas).some((f) => f.endsWith('.csv')),
        { timeoutMsg: 'No se descargó ningún CSV' })
    const archivo = readdirSync(descargas).find((f) => f.endsWith('.csv'))
    this.csv = readFileSync(join(descargas, archivo), 'utf8').trim().split(/\r?\n/)
})

Then('el CSV tiene el encabezado {string}', function (encabezado) {
    expect(this.csv[0]).toBe(encabezado)
})

Then('el CSV trae los mismos movimientos que la tabla, todos de tipo {string}', async function (tipo) {
    const filas = this.csv.slice(1).map((l) => l.split(';'))
    expect(filas.map((f) => f[2])).toEqual(filas.map(() => tipo))
    expect(filas.map((f) => f[1])).toEqual(await HistorialPage.filas.map((f) => f.getAttribute('data-codigo')))
})

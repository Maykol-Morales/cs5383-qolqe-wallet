import { Before, Given, When, Then } from '@wdio/cucumber-framework'
import { expect } from '@wdio/globals'

import LoginPage from '../../pages/login.page.js'
import HistorialPage from '../../pages/historial.page.js'

const ANA = { celular: '987654321', pin: '4826' }

// Aislamiento: cada escenario parte de los datos semilla y sin sesión previa.
Before(async () => {
    const respuesta = await fetch(new URL('/api/pruebas/reiniciar', browser.options.baseUrl), { method: 'POST' })
    if (!respuesta.ok) throw new Error(`No se pudo reiniciar los datos: ${respuesta.status}`)
    await LoginPage.abrir()
    await browser.execute(() => { localStorage.clear(); sessionStorage.clear() })
})

Given('que inicié sesión como Ana en la web', async () => {
    await LoginPage.abrir()
    await LoginPage.ingresar(ANA.celular, ANA.pin)
    await browser.waitUntil(async () => (await browser.getUrl()).endsWith('/inicio'), { timeoutMsg: 'No se llegó a /inicio tras el login' })
})

Given('estoy en la página de historial', async () => {
    await HistorialPage.abrir()
})

When('creo la categoría {string} de color {string}', async (nombre, color) => {
    await HistorialPage.crearCategoria(nombre, color)
})

Then('veo el aviso {string}', async (texto) => {
    await expect(HistorialPage.aviso).toHaveText(texto)
})

Then('veo el error {string}', async (texto) => {
    await expect(HistorialPage.error).toBeDisplayed()
    await expect(HistorialPage.error).toHaveText(expect.stringContaining(texto))
})

Then('la categoría {string} aparece en mi lista con {int} movimientos', async (nombre, cantidad) => {
    await browser.waitUntil(async () => Boolean(await HistorialPage.categoria(nombre)), { timeoutMsg: `"${nombre}" no aparece en la lista` })
    const item = await HistorialPage.categoria(nombre)
    await expect(item.$('[data-testid=categoria-cantidad]')).toHaveText(`${cantidad} movimientos`)
})

Then('la categoría {string} se muestra con el color {string}', async (nombre, color) => {
    const item = await HistorialPage.categoria(nombre)
    expect(await HistorialPage.colorDe(item)).toBe(color)
})

Then('el contador de categorías muestra {string}', async (texto) => {
    await expect(HistorialPage.contador).toHaveText(texto)
})

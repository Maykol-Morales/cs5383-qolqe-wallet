// DEF-14: la UI arma el rango del historial con la fecha del celular, no con la de Lima.
import { Given, When, Then } from '@wdio/cucumber-framework'
import { baseUrl } from '../wdio.conf.js'
import HistorialPage from '../pages/historial.page.js'

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

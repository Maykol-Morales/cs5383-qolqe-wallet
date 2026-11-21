// DEF-15: Qolqe responde antes de guardar en la BD, así que una lectura inmediata puede ver el estado viejo.
// En vez de un solo refresh + expect, se recarga y se comprueba hasta que el estado guardado aparece (o vence).
// No tapa un defecto real: si el dato nunca se guarda, vence y falla con el mensaje dado.
export async function recargarHasta(comprobar, mensaje, timeout = 20000) {
    let ultimo
    await browser.waitUntil(async () => {
        await browser.refresh()
        try { await comprobar(); return true } catch (e) { ultimo = e; return false }
    }, { timeout, interval: 500, timeoutMsg: `${mensaje}${ultimo ? ` (${ultimo.message.split('\n')[0]})` : ''}` })
}

export const CORTO = { wait: 1500 } // espera de cada intento dentro de recargarHasta

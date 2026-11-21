// Pantalla /historial (G3): movimientos, detalle, clasificación y categorías.
import { recargarHasta, CORTO } from './espera.js'

class HistorialPage {
    get filas() { return $$('[data-testid=fila-movimiento]') }

    fila(codigo) { return $(`[data-testid=fila-movimiento][data-codigo="${codigo}"]`) }
    // Selector, no elemento: expect lo vuelve a buscar en cada reintento aunque Qolqe repinte la lista.
    categoria(nombre) { return $(`//li[@data-testid="categoria"][contains(., "${nombre}")]`) }
    get indicador() { return $('[data-testid=indicador-pagina]') }
    get siguiente() { return $('[data-testid=boton-siguiente]') }

    // Desde/hasta van por JS: lo que se teclea en un <input type=date> depende del idioma del navegador.
    async filtrar({ diasAtras, hastaDias, tipo, categoria }) {
        if (diasAtras) await browser.execute((d) => {
            document.querySelector('[data-testid=input-desde]').value = new Date(Date.now() - d * 86400000).toLocaleDateString('en-CA')
        }, diasAtras)
        if (hastaDias) await browser.execute((d) => {
            document.querySelector('[data-testid=input-hasta]').value = new Date(Date.now() - d * 86400000).toLocaleDateString('en-CA')
        }, hastaDias)
        if (tipo) await $('[data-testid=select-tipo]').selectByVisibleText(tipo)
        if (categoria) await $('[data-testid=select-categoria]').selectByVisibleText(categoria)
        await this.cambiarA('boton-buscar')
    }

    // Buscar, Siguiente o Anterior: la tabla muestra un esqueleto hasta que llega la respuesta.
    async cambiarA(testid) {
        await $(`[data-testid=${testid}]`).click()
        await expect($('[data-testid=tabla-movimientos] .esqueleto')).not.toBeExisting()
    }

    async abrir() {
        await $('aria/Movimientos').click()
        await expect(browser).toHaveUrl(expect.stringContaining('/historial'))
        await expect(this.filas).toBeElementsArrayOfSize({ gte: 1 })
    }

    async crearCategoria(nombre, color) {
        await $('aria/Nombre').setValue(nombre)
        await $(`aria/${color}`).parentElement().click()
        await $('aria/Crear categoría').click()
        // Qolqe responde con un aviso (éxito) o una alerta (error); el paso distingue ambos.
        const error = $('[data-testid=categoria-error]')
        const aviso = $('[data-testid=toast]')
        await browser.waitUntil(async () => await error.isDisplayed() || (await aviso.isDisplayed() && (await aviso.getText()).includes(nombre)),
            { timeoutMsg: `Qolqe no respondió al crear "${nombre}" (ni aviso ni error)` })
        if (await error.isDisplayed()) throw new Error(`Qolqe rechazó la categoría: ${await error.getText()}`)
        // En Windows, a veces Qolqe confirmaba la creación pero la lista (y los selects que usa
        // clasificar) seguían viejos. Se recarga y se verifica el estado guardado.
        await recargarHasta(
            () => expect($('[data-testid=lista-categorias]')).toHaveText(expect.stringContaining(nombre), CORTO),
            `Qolqe confirmó "${nombre}" pero no quedó guardada`)
    }

    get categorias() { return $$('[data-testid=categoria]') }

    // Abre el diálogo «Editar categoría», cambia nombre y color y lo envía; el paso Then mira el aviso o el error del diálogo.
    async editarCategoria(nombre, nuevoNombre, color) {
        await this.categoria(nombre).$('[data-testid=boton-editar-categoria]').click()
        await $('[data-testid=input-editar-nombre]').setValue(nuevoNombre)
        await $('[data-testid=input-editar-color]').selectByAttribute('value', color)
        await $('[data-testid=boton-guardar-dialogo]').click()
    }

    // Envía el formulario sin esperar éxito: el paso Then revisa el error o la lista.
    async intentarCrearCategoria(nombre, color) {
        await $("aria/Nombre").setValue(nombre)
        await $(`aria/${color}`).parentElement().click()
        await $("aria/Crear categoría").click()
    }

    async eliminarCategoria(nombre) {
        await this.categoria(nombre).$("[data-testid=boton-eliminar-categoria]").click()
        await $("[data-testid=boton-confirmar-accion]").click()
    }

    // Abre el movimiento más reciente y devuelve su código de operación.
    async abrirPrimerMovimiento() {
        const fila = this.filas[0]
        const codigo = await fila.getAttribute('data-codigo')
        await fila.click()
        await expect($('[data-testid=detalle-codigo]')).toHaveText(codigo)
        return codigo
    }

    // Espera la respuesta del PUT (vía WebDriver BiDi): el aviso de Qolqe dura milisegundos.
    async clasificar(categoria, nota) {
        const guardado = await browser.mock('**/api/movimientos/*/clasificacion', { method: 'put' })
        await $('[data-testid=select-clasificar-categoria]').selectByVisibleText(categoria)
        await $('[data-testid=input-nota]').setValue(nota)
        await $('aria/Guardar clasificación').click()
        await browser.waitUntil(() => guardado.calls.length > 0, { timeoutMsg: 'Qolqe no respondió al guardar la clasificación' })
        const status = guardado.calls[0].response.status
        await guardado.restore()
        if (status !== 200) throw new Error(`Qolqe rechazó la clasificación: HTTP ${status}`)
    }
}

export default new HistorialPage()

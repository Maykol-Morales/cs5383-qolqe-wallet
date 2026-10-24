class HistorialPage {
    get nombre() { return $('[data-testid=input-categoria-nombre]') }
    get botonCrear() { return $('[data-testid=boton-crear-categoria]') }
    get error() { return $('[data-testid=categoria-error]') }
    get aviso() { return $('[data-testid=toast]') }
    get contador() { return $('[data-testid=contador-categorias]') }
    get categorias() { return $$('[data-testid=categoria]') }

    async abrir() {
        await browser.url('/historial')
        await this.botonCrear.waitForDisplayed()
    }

    // El radio real está oculto detrás de la muestra de color: se hace clic en su etiqueta.
    async elegirColor(color) {
        const radio = await $(`input[name=color-categoria][value="${color}"]`)
        await radio.parentElement().click()
    }

    async crearCategoria(nombre, color) {
        await this.nombre.setValue(nombre)
        if (color) await this.elegirColor(color)
        await this.botonCrear.click()
    }

    // El punto de color lleva el color en el estilo en línea; se devuelve en hexadecimal mayúscula.
    async colorDe(item) {
        return browser.execute((punto) => {
            const [r, g, b] = getComputedStyle(punto).backgroundColor.match(/\d+/g).map(Number)
            return '#' + [r, g, b].map((c) => c.toString(16).padStart(2, '0')).join('').toUpperCase()
        }, await item.$('.punto-color'))
    }

    async categoria(nombre) {
        const items = await this.categorias
        for (const item of items) {
            if ((await item.$('[data-testid=chip-categoria]').getText()) === nombre) return item
        }
        return undefined
    }
}

export default new HistorialPage()

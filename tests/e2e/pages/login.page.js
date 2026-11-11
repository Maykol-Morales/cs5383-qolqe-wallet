class LoginPage {
    get celular() { return $('aria/Celular') }
    get pin() { return $('aria/PIN') }
    get ingresar() { return $('aria/Ingresar') }
    get error() { return $('[data-testid=login-error]') }
    get aviso() { return $('[data-testid=login-aviso]') }

    // browser.url espera la carga completa: app.js ya enganchó el submit (si no, el form se enviaría por GET).
    async enviar(celular, pin) {
        await browser.url('/login')
        await this.celular.setValue(celular)
        await this.pin.setValue(pin)
        await this.ingresar.click()
    }

    // Listo = /inicio con el saldo pintado: prueba que el token ya sirve, no solo que cambió la URL.
    // DEF-15: Qolqe responde al login antes de guardar la sesión; si /inicio pide el saldo antes del commit
    // recibe 401 y app.js rebota a /login?motivo=sesion. Se avisa en la consola y se vuelve a ingresar.
    async ingresarComo(celular, pin) {
        await this.enviar(celular, pin)
        await browser.waitUntil(async () => {
            const url = await browser.getUrl()
            if (url.includes('motivo=sesion')) {
                console.warn(`[DEF-15] el token recién emitido para ${celular} dio 401 (sesión sin confirmar); se reintenta`)
                await this.enviar(celular, pin)
                return false
            }
            return url.includes('/inicio') && (await $('[data-testid=saldo-valor]').getText()).startsWith('S/')
        }, { timeout: 15000, timeoutMsg: `No se pudo ingresar como ${celular}: /inicio no mostró el saldo` })
    }
}

export default new LoginPage()

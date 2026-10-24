class LoginPage {
    get celular() { return $('[data-testid=input-celular]') }
    get pin() { return $('[data-testid=input-pin]') }
    get botonIngresar() { return $('[data-testid=boton-ingresar]') }

    async abrir() {
        await browser.url('/login')
    }

    async ingresar(celular, pin) {
        await this.celular.setValue(celular)
        await this.pin.setValue(pin)
        await this.botonIngresar.click()
    }
}

export default new LoginPage()

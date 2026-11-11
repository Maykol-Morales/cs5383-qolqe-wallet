// Pantalla /registro (HU-N-01).
class RegistroPage {
    get error() { return $('[data-testid=registro-error]') }

    async registrar({ dni, nombres, celular, pin }) {
        await browser.url('/registro')
        await $('[data-testid=input-dni]').setValue(dni)
        await $('[data-testid=input-nombres]').setValue(nombres)
        await $('[data-testid=input-celular]').setValue(celular)
        await $('[data-testid=input-pin]').setValue(pin)
        await $('[data-testid=input-pin-confirmacion]').setValue(pin)
        await $('[data-testid=boton-registrar]').click()
    }
}

export default new RegistroPage()

// Pantalla /transferir (HU-N-07, HU-N-08 y la simulación de comisión de HU-N-09).
class TransferirPage {
    get error() { return $('[data-testid=transferencia-error]') }
    get dialogo() { return $('[data-testid=dialogo-confirmacion]') }
    confirmacion(campo) { return $(`[data-testid=confirmar-${campo}]`) }
    comprobante(campo) { return $(`[data-testid=comprobante-${campo}]`) }

    async abrir() {
        await $('[data-testid=nav-transferir]').click()
        await expect(browser).toHaveUrl(expect.stringContaining('/transferir'))
    }

    // Continuar pide la comisión (GET /api/transferencias/comision): abre la confirmación o muestra un error.
    async continuar({ monto, celular, cci }) {
        if (cci) {
            await $('[data-testid=pestana-interbancaria]').click()
            await $('[data-testid=input-cci]').setValue(cci)
        } else {
            await $('[data-testid=input-celular-destino]').setValue(celular)
        }
        await $('[data-testid=input-monto]').setValue(monto)
        await $('[data-testid=boton-continuar]').click()
        await browser.waitUntil(async () => await this.dialogo.isDisplayed() || await this.error.isDisplayed(),
            { timeoutMsg: 'Qolqe no mostró ni la confirmación ni un error' })
    }

    async confirmar() {
        await $('[data-testid=boton-confirmar]').click()
        await expect($('[data-testid=comprobante]')).toBeDisplayed()
    }
}

export default new TransferirPage()

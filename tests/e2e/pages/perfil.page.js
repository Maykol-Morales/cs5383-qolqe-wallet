// Pantalla /perfil (HU-N-04 CA2 y HU-N-05).
class PerfilPage {
    dato(campo) { return $(`[data-testid=perfil-${campo}]`) }
    get mensaje() { return $('[data-testid=perfil-mensaje]') }

    async abrir() {
        await $('[data-testid=nav-perfil]').click()
        await expect(this.dato('celular')).not.toHaveText('') // se llenó con GET /api/cuentas/me
    }

    async cambiarNombres(nombres) {
        await $('[data-testid=input-nombres]').setValue(nombres)
        await $('[data-testid=boton-guardar-perfil]').click()
    }

    // HU-N-06: el diálogo pide el PIN; si Qolqe rechaza el cierre, el error queda en el diálogo.
    get errorCierre() { return $('[data-testid=dialogo-error]') }

    async cerrarCuenta(pin) {
        await $('[data-testid=boton-cerrar-cuenta]').click()
        await $('[data-testid=input-pin-cierre]').setValue(pin)
        await $('[data-testid=boton-guardar-dialogo]').click()
    }
}

export default new PerfilPage()

// Pantalla /inicio (HU-N-04) y el menú común (cerrar sesión, HU-N-03).
class InicioPage {
    get saludo() { return $('[data-testid=saludo]') }
    get saldo() { return $('[data-testid=saldo-valor]') }
    get usuarioNombre() { return $('[data-testid=usuario-nombre]') } // menú común, en todas las páginas

    async ocultarSaldo() { await $('[data-testid=boton-ocultar-saldo]').click() }

    async cerrarSesion() {
        await $('[data-testid=boton-cerrar-sesion]').click()
        await expect(browser).toHaveUrl(expect.stringContaining('/login?motivo=salida'))
    }
}

export default new InicioPage()

// Pasos del núcleo: registro, sesión, saldo, perfil y transferencias (HU-N-01 a HU-N-09).
import { Given, When, Then } from '@wdio/cucumber-framework'
import LoginPage from '../pages/login.page.js'
import RegistroPage from '../pages/registro.page.js'
import InicioPage from '../pages/inicio.page.js'
import PerfilPage from '../pages/perfil.page.js'
import TransferirPage from '../pages/transferir.page.js'

When('me registro con DNI {string}, nombres {string}, celular {string} y PIN {string}', async (dni, nombres, celular, pin) => {
    await RegistroPage.registrar({ dni, nombres, celular, pin })
})

Then('veo el error de registro {string}', async (mensaje) => {
    await expect(RegistroPage.error).toHaveText(mensaje)
})

Then('veo el aviso de inicio de sesión {string}', async (mensaje) => {
    await expect(LoginPage.aviso).toHaveText(mensaje)
})

When('inicio sesión con el celular {string} y el PIN {string}', async (celular, pin) => {
    await LoginPage.ingresarComo(celular, pin)
})

When('intento ingresar con el celular {string} y el PIN {string}', async (celular, pin) => {
    await LoginPage.enviar(celular, pin)
})

Then('veo el error de inicio de sesión {string}', async (mensaje) => {
    await expect(LoginPage.error).toHaveText(mensaje)
})

Then('sigo en la página {string}', async (ruta) => {
    await expect(browser).toHaveUrl(expect.stringMatching(new RegExp(`${ruta}$`)))
})

Then('sigo en la página {string} con el PIN vacío', async (ruta) => {
    await expect(browser).toHaveUrl(expect.stringMatching(new RegExp(`${ruta}$`)))
    await expect(LoginPage.pin).toHaveValue('')
})

When('cierro sesión', async () => {
    await InicioPage.cerrarSesion()
})

Then('al abrir {string} me lleva a {string}', async (ruta, destino) => {
    await browser.url(ruta)
    await expect(browser).toHaveUrl(expect.stringMatching(new RegExp(`${destino}$`)))
})

Then('veo el saludo {string} y el saldo {string}', async (saludo, saldo) => {
    await expect(InicioPage.saludo).toHaveText(saludo)
    await expect(InicioPage.saldo).toHaveText(saldo)
})

When('oculto mi saldo', async () => {
    await InicioPage.ocultarSaldo()
})

Then('el saldo se muestra como {string}', async (texto) => {
    await expect(InicioPage.saldo).toHaveText(texto)
})

Given('estoy en Mi perfil', async () => {
    await PerfilPage.abrir()
})

Then('mi perfil muestra el DNI {string} y el celular {string}', async (dni, celular) => {
    await expect(PerfilPage.dato('dni')).toHaveText(dni)
    await expect(PerfilPage.dato('celular')).toHaveText(celular)
})

When('cambio mis nombres a {string}', async (nombres) => {
    await PerfilPage.cambiarNombres(nombres)
})

Then('veo el mensaje del perfil {string}', async (mensaje) => {
    await expect(PerfilPage.mensaje).toHaveText(mensaje)
})

// Tras recargar: se verifica lo guardado en Qolqe, no solo lo que quedó en el formulario.
Then('mi perfil muestra los nombres {string}', async (nombres) => {
    await browser.refresh()
    await expect(PerfilPage.dato('nombres')).toHaveText(nombres)
    await expect(InicioPage.usuarioNombre).toHaveText(nombres)
})

Given('estoy en Transferir', async () => {
    await TransferirPage.abrir()
})

When('preparo una transferencia de {string} al celular {string}', async (monto, celular) => {
    await TransferirPage.continuar({ monto, celular })
})

When('preparo una transferencia de {string} al CCI {string}', async (monto, cci) => {
    await TransferirPage.continuar({ monto, cci })
})

Then('la confirmación muestra monto {string}, comisión {string} y total {string}', async (monto, comision, total) => {
    await expect(TransferirPage.dialogo).toBeDisplayed()
    await expect(TransferirPage.confirmacion('monto')).toHaveText(monto)
    await expect(TransferirPage.confirmacion('comision')).toHaveText(comision)
    await expect(TransferirPage.confirmacion('total')).toHaveText(total)
})

When('confirmo la transferencia', async () => {
    await TransferirPage.confirmar()
})

Then('el comprobante muestra destino {string}, total {string} y saldo {string}', async (destino, total, saldo) => {
    await expect(TransferirPage.comprobante('codigo')).toHaveText(/^TRF\d+$/)
    await expect(TransferirPage.comprobante('destino')).toHaveText(destino)
    await expect(TransferirPage.comprobante('total')).toHaveText(total)
    await expect(TransferirPage.comprobante('saldo')).toHaveText(saldo)
})

Then('veo el error de transferencia {string} sin confirmación', async (mensaje) => {
    await expect(TransferirPage.error).toHaveText(mensaje)
    await expect(TransferirPage.dialogo).not.toBeDisplayed()
})

When('cierro mi cuenta con el PIN {string}', async (pin) => {
    await PerfilPage.cerrarCuenta(pin)
})

Then('veo el error de cierre {string}', async (mensaje) => {
    await expect(PerfilPage.errorCierre).toHaveText(mensaje)
})

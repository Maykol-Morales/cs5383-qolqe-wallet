// Traduce cada paso de Gherkin a acciones de los Page Objects. Los pasos no tocan el HTML.
import { Given, When, Then } from '@wdio/cucumber-framework'
import LoginPage from '../pages/login.page.js'
import { recargarHasta, CORTO } from '../pages/espera.js'
import HistorialPage from '../pages/historial.page.js'

// Usuarios semilla de Qolqe (README del SUT, sección 4).
export const USUARIOS = {
    Ana: { celular: '987654321', pin: '4826' },
    Bruno: { celular: '912345678', pin: '7391' },
    Diego: { celular: '998877665', pin: '3604' }, // límite diario S/ 1000, saldo S/ 2500
}

Given('que inicié sesión como {word}', async (nombre) => {
    const { celular, pin } = USUARIOS[nombre]
    await LoginPage.ingresarComo(celular, pin)
})

Given('estoy en la sección Movimientos', async () => {
    await HistorialPage.abrir()
})

When('creo la categoría {string} de color {string}', async (nombre, color) => {
    await HistorialPage.crearCategoria(nombre, color)
})

// `this` es el World de Cucumber: comparte el código del movimiento con los pasos Then.
When('clasifico mi movimiento más reciente en {string} con la nota {string}', async function (categoria, nota) {
    this.codigo = await HistorialPage.abrirPrimerMovimiento()
    await HistorialPage.clasificar(categoria, nota)
})

// "Clasificación guardada" se oculta al repintar el detalle: se verifica el estado guardado.
Then('la fila del movimiento muestra la categoría {string} y la nota {string}', async function (categoria, nota) {
    await recargarHasta(async () => {
        await expect(HistorialPage.fila(this.codigo)).toHaveText(expect.stringContaining(categoria), CORTO)
        await expect(HistorialPage.fila(this.codigo)).toHaveText(expect.stringContaining(nota), CORTO)
    }, 'La clasificación no quedó guardada')
})

// Tras recargar, como el paso anterior: en la CI de Windows la UI a veces no repintaba.
Then('la categoría {string} cuenta {int} movimientos', async (nombre, cantidad) => {
    await expect(HistorialPage.categoria(nombre)).toHaveText(expect.stringContaining(`${cantidad} movimientos`))
})

// --- Entrega final: validaciones y eliminación de categorías (HU-G3-03, HU-G3-06) ---
When('intento crear la categoría {string} de color {string}', async (nombre, color) => {
    await HistorialPage.intentarCrearCategoria(nombre, color)
})

Then('veo el error de categoría {string}', async (mensaje) => {
    await expect($('[data-testid=categoria-error]')).toHaveText(mensaje)
})

// DEF-15: Qolqe responde antes de guardar, así que la lista puede seguir vieja un instante: se recarga hasta que cambie.
Then('la lista de categorías no incluye {string}', async (nombre) => {
    await recargarHasta(() => expect($('[data-testid=lista-categorias]')).not.toHaveText(expect.stringContaining(nombre), CORTO),
        `La lista de categorías todavía incluye "${nombre}"`)
})

When('elimino la categoría {string}', async (nombre) => {
    await HistorialPage.eliminarCategoria(nombre)
})

Then('veo el aviso {string}', async (mensaje) => {
    await expect($('[data-testid=toast]')).toHaveText(expect.stringContaining(mensaje))
})

Then('el contador de categorías muestra {string}', async (texto) => {
    await recargarHasta(() => expect($('[data-testid=contador-categorias]')).toHaveText(texto, CORTO),
        `El contador de categorías no llegó a "${texto}"`)
})

// --- Entrega final (2.ª tanda): editar y ver categorías, notas (HU-G3-04, HU-G3-05, HU-G3-07) ---
When('edito la categoría {string} con el nombre {string} y el color {string}', async (nombre, nuevo, color) => {
    await HistorialPage.editarCategoria(nombre, nuevo, color)
})

Then('veo el error del diálogo {string}', async (mensaje) => {
    await expect($('[data-testid=dialogo-error]')).toHaveText(mensaje)
})

When('cancelo la edición', async () => {
    await $('[data-testid=boton-cancelar-dialogo]').click()
})

Then('la lista de categorías incluye {string}', async (nombre) => {
    await recargarHasta(() => expect($('[data-testid=lista-categorias]')).toHaveText(expect.stringContaining(nombre), CORTO),
        `La lista de categorías no llegó a incluir "${nombre}"`)
})

Then('veo mis categorías en este orden', async (tabla) => {
    const esperado = tabla.hashes()
    await expect(HistorialPage.categorias).toBeElementsArrayOfSize(esperado.length)
    const items = await HistorialPage.categorias
    for (const [i, { nombre, movimientos }] of esperado.entries()) {
        await expect(items[i]).toHaveText(expect.stringContaining(nombre))
        await expect(items[i]).toHaveText(expect.stringContaining(`${movimientos} movimientos`))
    }
})

When('intento clasificar mi movimiento más reciente con una nota de {int} caracteres', async function (n) {
    this.codigo = await HistorialPage.abrirPrimerMovimiento()
    await $('[data-testid=input-nota]').setValue('n'.repeat(n))
    await $('aria/Guardar clasificación').click()
})

Then('veo el error de clasificación {string}', async (mensaje) => {
    await expect($('[data-testid=clasificar-mensaje]')).toHaveText(mensaje)
})

When('clasifico mi movimiento más reciente en {string} con una nota de {int} caracteres', async function (categoria, n) {
    this.codigo = await HistorialPage.abrirPrimerMovimiento()
    await HistorialPage.clasificar(categoria, 'n'.repeat(n))
})

Then('la fila del movimiento conserva una nota de {int} caracteres', async function (n) {
    await recargarHasta(() => expect(HistorialPage.fila(this.codigo)).toHaveText(expect.stringContaining('n'.repeat(n)), CORTO),
        `La nota de ${n} caracteres no quedó guardada`)
})

Then('la fila del movimiento no muestra la categoría {string}', async function (categoria) {
    await recargarHasta(() => expect(HistorialPage.fila(this.codigo)).not.toHaveText(expect.stringContaining(categoria), CORTO),
        `La categoría "${categoria}" sigue en la fila`)
})

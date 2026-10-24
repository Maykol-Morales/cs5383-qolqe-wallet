# Ejemplo WebdriverIO + Cucumber

Ejemplo para la presentación de WebdriverIO: pruebas web de **Historial y categorías (G3)** sobre Qolqe Wallet, escritas en Gherkin y ejecutadas con WebdriverIO 10.

## Requisitos

- Node.js 20 o superior y Chrome instalado (WebdriverIO descarga el driver solo).
- `.venv` del repo creado (`./demo.sh preparar`), para que el runner levante el SUT.

## Ejecutar

```bash
cd tests/e2e/ejemplo-webdriverio
npm install
npm test                # con ventana de Chrome (para la demo)
HEADLESS=1 npm test     # sin ventana (en PowerShell: $env:HEADLESS=1; npm test)
```

Si no hay un SUT en `http://127.0.0.1:8000`, `wdio.conf.js` lo levanta con uvicorn (BD temporal) y lo apaga al terminar. Para usar uno propio: `QOLQE_URL=http://localhost:8000 npm test`.

## Contenido

| Ruta | Qué es |
|---|---|
| `features/categorias.feature` | 4 escenarios (copia reducida de `features/categorias.feature`): crear categoría, verla con el color elegido, nombre de 2 caracteres, nombre duplicado |
| `features/step-definitions/categorias.steps.js` | Pasos de Cucumber; reinicia los datos antes de cada escenario |
| `pages/login.page.js`, `pages/historial.page.js` | Page Objects (selectores por `data-testid`) |
| `wdio.conf.js` | Configuración: Chrome, framework Cucumber, reporter `spec`, arranque del SUT |

## IA: MCP server de WebdriverIO

`.mcp.json` registra `@wdio/mcp` (se baja con `npx`, no requiere instalación). Para la demo:

1. Levantar el SUT: `uvicorn qolqe.main:app` desde la raíz del repo.
2. Abrir Claude Code **desde esta carpeta** (`cd tests/e2e/ejemplo-webdriverio && claude`), aceptar el servidor `wdio-mcp` y comprobar con `/mcp` que está conectado.
3. Pedirle en lenguaje natural que entre como Ana (987654321 / 4826), cree una categoría en `/historial` y escriba el escenario Gherkin con sus pasos.

Verificado: el servidor responde al protocolo MCP (v3.14.0) y expone 17 herramientas por defecto (`start_session`, `navigate`, `click_element`, `set_value`, `snapshot`, `get_screenshot`, `execute_script`, `query_docs`, `enable_tools`, …). La documentación habla de 29; el resto parece activarse con `enable_tools`.

## Nota para Windows

El SUT regenera `datos/plantilla_carga.db` al arrancar y falla si ya existe. Por eso `wdio.conf.js` apunta `QOLQE_BD_PLANTILLA` a una carpeta temporal.

# Formato de tablas: particiones de equivalencia y valores límite

Propuestas de formato. Elige una por técnica (o mezcla) y se construyen desde RN / HU / CA. Los ejemplos usan reglas reales de `requisitos.md`.

---

## A. Particiones de equivalencia

### A1. Una fila por partición (la más simple)

Ejemplo: RN-01 · DNI (HU-N-01 CA2)

| ID | Partición | Tipo | Representante | Resultado esperado |
|---|---|---|---|---|
| EQ-N01-01 | 8 dígitos numéricos | Válida | `45678912` | Cuenta creada |
| EQ-N01-02 | Menos de 8 dígitos | Inválida | `4567891` | `DNI_INVALIDO` |
| EQ-N01-03 | Más de 8 dígitos | Inválida | `456789123` | `DNI_INVALIDO` |
| EQ-N01-04 | Contiene no dígitos | Inválida | `4567891A` | `DNI_INVALIDO` |

### A2. Encabezado de regla + clases (agrupa por HU/CA)

Ejemplo: RN-03 · PIN (HU-N-01 CA4)

**HU-N-01 · CA4 · RN-03** · Variable: `pin` · Error: `PIN_INVALIDO`

| Clase | Descripción | Válida / Inválida | Representante |
|---|---|---|---|
| C1 | 4 dígitos sin patrón | V | `4826` |
| C2 | Longitud ≠ 4 | I | `482` |
| C3 | No numérico | I | `48A6` |
| C4 | Todos iguales | I | `1111` |
| C5 | Secuencia ascendente | I | `1234` |
| C6 | Secuencia descendente | I | `4321` |

### A3. Matriz con trazabilidad (HU, CA, RN en columnas)

| HU | CA | RN | Variable | Clase | V/I | Representante | Esperado |
|---|---|---|---|---|---|---|---|
| HU-N-07 | CA2 | RN-07 | destino | Celular de otro usuario activo | V | `912345678` | 201 |
| HU-N-07 | CA2 | RN-07 | destino | Uno mismo | I | `987654321` | `TRANSFERENCIA_A_SI_MISMO` |
| HU-N-07 | CA2 | RN-07 | destino | No registrado | I | `999999999` | `DESTINO_NO_REGISTRADO` |
| HU-N-07 | CA2 | RN-07 | destino | Cuenta cerrada | I | `934567812` | `DESTINO_INACTIVO` |

### A4. Tabla de decisión (cuando varias condiciones se combinan)

Ejemplo: HU-N-06 · cerrar cuenta (CA1–CA3)

| Condición / Regla | R1 | R2 | R3 | R4 |
|---|---|---|---|---|
| PIN correcto | No | Sí | Sí | Sí |
| Saldo = 0.00 | – | No | Sí | Sí |
| Solicitudes pendientes | – | – | Sí | No |
| **Resultado** | `PIN_INCORRECTO` | `SALDO_PENDIENTE` | `SOLICITUDES_PENDIENTES` | 204 cerrada |

---

## B. Valores límite

### B1. Una fila por frontera (mín−1 / mín / máx / máx+1)

Ejemplo: RN-05 · monto de transferencia (0.00 < monto ≤ 500.00)

| ID | Variable | Frontera | Valor | Lado | Esperado |
|---|---|---|---|---|---|
| VL-N07-01 | monto | inferior (exclusivo) | `0.00` | Fuera | `MONTO_INVALIDO` |
| VL-N07-02 | monto | inferior | `0.01` | Dentro | 201 |
| VL-N07-03 | monto | superior | `500.00` | Dentro | 201 |
| VL-N07-04 | monto | superior | `500.01` | Fuera | `MONTO_INVALIDO` |

### B2. Una fila por variable, valores en columnas

| Variable | Regla | Rango válido | mín−1 | mín | mín+1 | máx−1 | máx | máx+1 |
|---|---|---|---|---|---|---|---|---|
| Nombres (largo) | HU-N-01 CA1 | 2–80 | 1 | 2 | 3 | 79 | 80 | 81 |
| Nota (largo) | R-G3-04 | 0–100 | – | 0 | 1 | 99 | 100 | 101 |
| Nombre categoría | R-G3-03 | 3–20 | 2 | 3 | 4 | 19 | 20 | 21 |
| Categorías por usuario | R-G3-03 | ≤10 | – | – | – | 9 | 10 | 11 |

### B3. Con trazabilidad y tipo de límite

| HU | CA | Regla | Variable | Límite | Valor | Válido | Esperado |
|---|---|---|---|---|---|---|---|
| HU-N-02 | CA4 | RN-04 | minutos desde bloqueo | 15 min | `14` | No | `CUENTA_BLOQUEADA` |
| HU-N-02 | CA4 | RN-04 | minutos desde bloqueo | 15 min | `15` | Sí | token |
| HU-G3-01 | CA1 | R-G3-01 | días del rango | 90 días | `90` | Sí | 200 |
| HU-G3-01 | CA1 | R-G3-01 | días del rango | 90 días | `91` | No | `FILTRO_INVALIDO` |

---

## C. Combinada (una técnica elegida por regla, en una sola tabla)

| ID | HU / CA | Regla | Variable | Técnica | Clase o frontera | Valor | V/I | Esperado |
|---|---|---|---|---|---|---|---|---|
| T-001 | HU-N-01 CA2 | RN-01 | dni | EQ | Menos de 8 dígitos | `4567891` | I | `DNI_INVALIDO` |
| T-002 | HU-N-07 CA2 | RN-05 | monto | VL | máx+1 | `500.01` | I | `MONTO_INVALIDO` |
| T-003 | HU-G3-01 CA3 | R-G3-02 | total movimientos | VL | 10 → 1 pág., 11 → 2 pág. | `10`, `11` | V | 1 / 2 páginas |

---

**Cómo decidir** (sugerencia): numéricos y longitudes con rango → **valores límite** (B); categorías sin orden (tipos, estados, formatos, patrones, propiedad de datos) → **equivalencia** (A); combinación de condiciones → **A4**. Si quieres, te paso la lista de RN/CA con la técnica sugerida para que corrijas.

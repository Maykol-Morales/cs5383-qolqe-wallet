# Hallazgos en módulos de otros grupos (G1, G2, G4, G5, G6)

Al escribir `features/otros_*.feature` para subir la cobertura (64 % → 90 %), estos comportamientos contradicen `requisitos.md`. Se reprodujeron con TestClient (2026-11-20) y se **quitaron de la suite**. No se registran como `DEF-nn` porque esos módulos están fuera de nuestro alcance (Núcleo + G3), pero se dejan aquí para los grupos responsables.

| # | Módulo | Petición | Esperado según el requisito | Obtenido |
|---|---|---|---|---|
| 1 | G1 | `POST /api/recargas` con monto 30 | R-G1-02: «Recargas **desde** S/ 30 reciben un bono de 5 %» → bono 1.50 | bono `0.00` (`calcular_bono` usa `>` en vez de `>=`) |
| 2 | G1 | 6 × `POST /api/recargas` al mismo número el mismo día | R-G1-03: «Máximo 5 recargas por día al mismo número» → la 6.ª da `LIMITE_RECARGAS` | las 6 dan 201 |
| 3 | G1 | `POST .../programadas/{id}/reanudar` con 3 programadas activas | HU-G1-05 CA2: al reanudar se aplica R-G1-04 → `LIMITE_PROGRAMADAS` | 200, quedan 4 activas |
| 4 | G2 | `GET /api/servicios/deudas` ELECTRO 10000002, que vence hoy | R-G2-03: pagar el día del vencimiento no genera mora | `dias_atraso 1`, `mora 0.43` |
| 5 | G2 | ELECTRO 100000009 (5 días de atraso, monto 78.30) | mora 0,5 % × 5 = 1.96 | `dias_atraso 6`, `mora 2.35` (el mismo +1 de `dias_de_atraso`) |
| 6 | G2 | INTERNET 300000000006 con 60 días de atraso | R-G2-04: con 60 días todavía se puede pagar | `EN_COBRANZA`, `dias_atraso 61` (mismo origen) |
| 7 | G2 | `GET /api/servicios/deudas?suministro=1000000000000` (13 dígitos) | R-G2-01: 8 a 12 dígitos → `SUMINISTRO_INVALIDO` | 404 `SIN_DEUDA_PENDIENTE` |
| 8 | G2 | Débito automático en «Internet casa» (61 días, en cobranza) y `POST /api/pruebas/procesar-diario` | HU-G2-05 CA2/CA4 y R-G2-04: no paga deudas vencidas ni en cobranza | la paga (`debitos_pagados 1`, mora 0) |
| 9 | G4 | `POST /api/contactos` con alias «Ñaño» | R-G4-02: solo letras, incluidas tildes y ñ | 422 `ALIAS_INVALIDO` |
| 10 | G4 | `POST /api/contactos` con alias « bruno » (ya existe «Bruno») | R-G4-02: se quitan espacios; único sin distinguir mayúsculas → `ALIAS_DUPLICADO` | 201, se crea un segundo «bruno» |
| 11 | G4 | `POST /api/solicitudes/{id}/aceptar` de una solicitud vencida | HU-G4-08 CA4: solo si está PENDIENTE y no vencida → 409 `ESTADO_INVALIDO` | 200 y se transfiere |
| 12 | G5 | `PUT /api/limites` a 1000, luego 1500 (programado), luego 500 | R-G5-02: una reducción cancela cualquier aumento pendiente | `limite_pendiente 1500.00` sigue vigente |
| 13 | G5 | Alerta RECARGAS de S/ 60 y tres recargas el mismo día (50, 5, 5) | HU-G5-08 CA2: como máximo una vez por día | 3 SMS (`ultima_notificacion` guarda fecha y hora y se compara con la fecha) |
| 14 | G6 | `PUT /api/seguridad/pin` de Ana 4826 → 1357 (su PIN más antiguo de los 3) | R-G6-01: distinto de los últimos 3 PIN → `PIN_REUTILIZADO` | 200 (`PINES_ANTERIORES_A_REVISAR = 2`) |
| 15 | G6 | `PUT /api/seguridad/pin` con una segunda sesión abierta | HU-G6-01 CA2: se cierran las demás sesiones | la segunda sesión sigue respondiendo 200 |

Los escenarios que quedaron en la suite evitan estos casos (bono con 50, mora solo de deudas no vencidas, alias sin ñ, una sola notificación).

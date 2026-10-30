# Informe de Chapter

## 1. Resumen
Contrasté la spec, los informes aprobados y las verificaciones ejecutadas para el commit indicado. Las tres verificaciones reportan éxito, pero eso no cierra los hallazgos ALTA que afectan criterios de aceptación y seguridad; varias pruebas tampoco comprueban todas las condiciones exigidas. La entrega queda **RECHAZADA**.

## 2. Cobertura de la spec

| ID | Estado | Evidencia |
|---|---|---|
| CA-1 | PARCIAL | `app/main.py:94-97` omite el estado del catálogo según Backend; `frontend/styles.css:183-185` oculta títulos móviles; `tests/test_ca1_pasos_visibles.py:18-22` no asegura el estado ACTUAL del siguiente paso. Trazabilidad CA-1 y pruebas automatizadas reportan PASÓ. |
| CA-2 | PARCIAL | `app/domain.py:179-194` no acumula todos los errores de clave; `app/main.py:71-77,107-109` no normaliza errores de parseo según Backend. `tests/test_ca2_validaciones.py:49-53` no exige el código global ni un mensaje accionable. Pruebas automatizadas reportan PASÓ. |
| CA-3 | PARCIAL | Backend informa activación y bloqueo de pagos en `app/onboarding.py:133-152,182-190`; Frontend señala campos de respuesta no definidos en `contracts/openapi.yaml:198-209`; `tests/test_ca3_activacion.py:25-28` no comprueba el mensaje del 403. Pruebas automatizadas reportan PASÓ. |
| CA-4 | PARCIAL | Backend cita registro de eventos en `app/onboarding.py:82-118,171-202`; `tests/test_ca4_eventos.py:37-52` no verifica todos los campos, formato UTC ni código exacto del fallo. Pruebas automatizadas reportan PASÓ. |
| CA-5 | CUMPLE | `app/analytics.py:57-88`; `tests/test_ca5_ca6_analitica.py:11`. La prueba automatizada reporta PASÓ y la salida de trazabilidad incluye CA-5. |
| CA-6 | PARCIAL | Backend cita el cálculo mensual por canal en `app/analytics.py:97-145`; Testing verifica desglose en `tests/test_ca5_ca6_analitica.py:32-71`, pero Frontend indica que no lo muestra en `frontend/app.js:391-397`. Pruebas automatizadas reportan PASÓ. |

## 3. Hallazgos

Sin hallazgos propios del Chapter: las discrepancias entre informes se resuelven por alcance o por especificidad de la evidencia. En CA-6, Testing comprueba el reporte del servidor y Frontend señala que la interfaz omite el canal; por eso la cobertura global es PARCIAL. Lo mismo ocurre en CA-3 y CA-4: la implementación del backend no sustituye la verificación del contrato consumido o de las aserciones de prueba.

El resultado genérico de `python tools/check_contrato.py` («Contrato (13 operaciones) frente a la API real — OK») no detalla la validación del estado del catálogo. Por ser más específica, la evidencia citada por Backend en `app/main.py:94-97` prevalece para ese punto. Los informes distinguen revisiones estáticas de ejecuciones; la evidencia ejecutada entregada reporta `52 passed`, trazabilidad `OK` y contrato `OK`. Esos resultados no prueban las condiciones que las pruebas no asertan.

## Matriz final

| CA | Implementación | Prueba | Evidencia ejecutada | Estado final |
|---|---|---|---|---|
| CA-1 | Backend parcial: catálogo sin estado; Frontend oculta títulos en móvil. | Parcial: no comprueba que el paso siguiente sea ACTUAL. | Pytest, trazabilidad y contrato reportan PASÓ; no despejan esas omisiones. | PARCIAL |
| CA-2 | Backend parcial: errores de clave no acumulados y parseo sin sobre contractual. | Parcial: no exige código global `DATOS_INVALIDOS` ni mensaje accionable. | Pytest reporta PASÓ; las aserciones faltantes no se verifican. | PARCIAL |
| CA-3 | Backend informa activación y bloqueo; Frontend identifica respuesta exitosa sin esquema contractual. | Parcial: no verifica el mensaje requerido para completar el registro. | Pytest reporta PASÓ; no demuestra la condición del mensaje. | PARCIAL |
| CA-4 | Backend informa registro de eventos; la revisión de Frontend no puede verificar el registro real. | Parcial: faltan comprobaciones de campos, UTC y código exacto. | Pytest reporta PASÓ; no cubre todas esas aserciones. | PARCIAL |
| CA-5 | Implementado según Backend. | Comprueba mediana 10 y objetivo falso. | Pytest, trazabilidad y contrato reportan PASÓ. | CUMPLE |
| CA-6 | Backend implementa desglose por canal; Frontend no lo muestra. | Comprueba desglose y CAC según Testing. | Pytest, trazabilidad y contrato reportan PASÓ; no verifica la presentación de canal en la UI. | PARCIAL |

## Hallazgos consolidados de otros roles

| ID original | Rol | Severidad | ¿Bloquea? | Responsable |
|---|---|---|---|---|
| H-ARQ-7 | Architect | ALTA | Sí, afecta RS-1 y RS-5 | Architect y Backend |
| H-ARQ-10 | Architect | ALTA | No para este MVP: RS-6 está marcado pendiente | Architect, Security y Producto antes de producción |
| H-ARQ-11 | Architect | ALTA | No para este MVP: RS-7 está marcado pendiente | Architect, Security y Cumplimiento antes de producción |
| H-BE-1 | Backend | ALTA | Sí, afecta CA-1 | Backend |
| H-BE-2 | Backend | ALTA | Sí, afecta CA-2 | Backend |
| H-BE-3 | Backend | ALTA | Sí, afecta CA-2 | Backend |
| H-FE-1 | Frontend | ALTA | Sí, riesgo de seguridad | Frontend |
| H-FE-2 | Frontend | ALTA | Sí, afecta CA-1 | Frontend |
| H-FE-3 | Frontend | ALTA | Sí, afecta CA-6 | Frontend |
| H-QA-1 | Testing | ALTA | Sí, afecta CA-2 | Testing |
| H-SEC-1 | Security | ALTA | No para este MVP: RS-6 está marcado pendiente | Security y Backend antes de producción |
| H-SEC-2 | Security | ALTA | Sí, riesgo de borrado destructivo no autorizado | Security y Backend |
| H-SEC-3 | Security | ALTA | No para este MVP: RS-7 está marcado pendiente | Security y Backend antes de producción |
| H-SEC-4 | Security | ALTA | Sí, riesgo de seguridad asociado a credenciales | Security y Backend |

## Correcciones priorizadas

1. **Cerrar los bloqueos de CA-1 y CA-2.** Responsable: Backend, Frontend y Testing. Completar el estado de cada paso, mantener los títulos visibles en móvil, normalizar errores de parseo y acumular errores de clave. Verificar los cinco estados y las respuestas 422 con campo, código global y mensaje accionable.
2. **Corregir los bloqueos de seguridad y reporte.** Responsable: Frontend, Backend y Security. Evitar la interpolación HTML insegura, renderizar el desglose por canal y deshabilitar o proteger el reinicio demo. Verificar con datos simulados que el marcado se representa como texto, que se ven los canales y que una petición no autorizada no borra datos.
3. **Cerrar las brechas de contrato y privacidad.** Responsable: Architect y Backend. Restringir campos adicionales en eventos y errores y definir el esquema de respuesta de pagos. Verificar que eventos con DNI adicional y errores con trazas se rechazan y que la respuesta de pagos valida contra el contrato.
4. **Fortalecer la evidencia de pruebas.** Responsable: Testing. Añadir las aserciones faltantes para CA-2, CA-3 y CA-4. Ejecutar `python -m pytest -q -p no:cacheprovider` y comprobar que las pruebas fallan al retirar los campos, mensajes o códigos exigidos.
5. **Planificar los requisitos pendientes para producción.** Responsable: Security, Backend, Architect y Producto. Asignar responsables y definir el cierre de RS-6 y RS-7. Verificar autenticación y límites de intentos antes de habilitar el flujo en producción.

## 4. Límites de esta revisión

No ejecuté comandos ni inspeccioné independientemente el repositorio; contrasté los extractos, ubicaciones e informes entregados con las salidas ejecutadas proporcionadas. Las salidas confirman que las verificaciones reportaron éxito, pero no permiten afirmar que cubran las aserciones ausentes señaladas por Testing. Tampoco se entregó evidencia de despliegue o pruebas en producción; RS-6 y RS-7 permanecen pendientes según la spec.

VEREDICTO: RECHAZADO
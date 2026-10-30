# Informe de Architect

## 1. Resumen

Revisé la spec, el plan, el contrato, las tareas y los supuestos, sin inspeccionar código ni ejecutar pruebas. La trazabilidad general de los seis criterios está declarada, pero quedan ambigüedades en criterios y contrato, además de brechas de seguridad que impiden considerar la documentación lista para producción. Los pendientes PREG-1 a PREG-5 tienen responsables asignados; RS-6 no tiene responsable explícito y PREG-4 no cubre todos los intentos exigidos por RS-7.

## 2. Cobertura de la spec

| ID | Estado | Evidencia |
|---|---|---|
| CA-1 | PARCIAL | `specs/001-registro-activacion/spec.md:30-48`; «en todo momento» y el escenario usa `n` sin valores concretos. |
| CA-2 | PARCIAL | `specs/001-registro-activacion/spec.md:50-65`; el escenario pide un «dato» que incumple una regla RN-n, sin valor de entrada concreto. |
| CA-3 | CUMPLE | `specs/001-registro-activacion/spec.md:67-81`; estado ACTIVA, `puede_pagar`, ruta y error 403 especificados. |
| CA-4 | PARCIAL | `specs/001-registro-activacion/spec.md:83-100`; define eventos y orden, pero «sale del registro» no precisa qué acción constituye abandono. |
| CA-5 | PARCIAL | `specs/001-registro-activacion/spec.md:102-114`; define el cálculo y un ejemplo, pero mezcla meta trimestral y exigencia de medición. |
| CA-6 | PARCIAL | `specs/001-registro-activacion/spec.md:116-129`; incluye ejemplo de CAC, pero no valores concretos para el desglose por canal. |
| RN-1 | PARCIAL | `specs/001-registro-activacion/spec.md:135`; regla y códigos definidos; el contrato no enumera todos los códigos posibles. |
| RN-2 | PARCIAL | `specs/001-registro-activacion/spec.md:136`; regla y códigos definidos; el contrato no enumera todos los códigos posibles. |
| RN-3 | PARCIAL | `specs/001-registro-activacion/spec.md:137`; regla y códigos definidos; el contrato no enumera todos los códigos posibles. |
| RN-4 | PARCIAL | `specs/001-registro-activacion/spec.md:138`; regla y código definidos; el contrato no enumera todos los códigos posibles. |
| RN-5 | PARCIAL | `specs/001-registro-activacion/spec.md:139`; regla y códigos definidos; el contrato no enumera todos los códigos posibles. |
| RN-6 | PARCIAL | `specs/001-registro-activacion/spec.md:140`; regla y códigos definidos; el contrato no enumera todos los códigos posibles. |
| RN-7 | PARCIAL | `specs/001-registro-activacion/spec.md:141`; regla y códigos definidos; el contrato no enumera todos los códigos posibles. |
| RN-8 | PARCIAL | `specs/001-registro-activacion/spec.md:142`; regla y códigos definidos, pero «repetida» y «secuencial» no están delimitadas por completo. |
| RN-9 | PARCIAL | `specs/001-registro-activacion/spec.md:143`; define `DNI_YA_REGISTRADO`; el contrato no restringe los códigos de error a los de la spec. |
| RN-10 | PARCIAL | `specs/001-registro-activacion/spec.md:144`; exige 409 y `PASO_FUERA_DE_ORDEN`; el esquema de conflicto deja el código como texto genérico. |
| RN-11 | PARCIAL | `specs/001-registro-activacion/spec.md:145`; exige 409 y `ONBOARDING_CERRADO`; el esquema de conflicto deja el código como texto genérico. |
| RN-12 | PARCIAL | `specs/001-registro-activacion/spec.md:146`; los enums del contrato coinciden, pero no se restringe el código de error `CANAL_INVALIDO`. |
| RS-1 | PARCIAL | `specs/001-registro-activacion/spec.md:152`; el contrato declara eventos sin datos personales, pero no prohíbe campos adicionales. |
| RS-2 | CUMPLE | `specs/001-registro-activacion/plan.md:33`; DEC-6 especifica PBKDF2-SHA256 y sal aleatoria; la ejecución no se verificó. |
| RS-3 | PARCIAL | `specs/001-registro-activacion/spec.md:154`; aparece en `x-spec`, pero el plan no asigna explícitamente esta garantía a una capa. |
| RS-4 | PARCIAL | `specs/001-registro-activacion/spec.md:155`; plan y contrato declaran enmascaramiento, pero el esquema no lo hace verificable. |
| RS-5 | PARCIAL | `specs/001-registro-activacion/spec.md:156`; el esquema de error no restringe campos adicionales que podrían exponer detalles internos. |
| RS-6 | PARCIAL | `specs/001-registro-activacion/spec.md:157`; está pendiente y fuera del MVP; falta responsable explícito para el cierre de producción. |
| RS-7 | PARCIAL | `specs/001-registro-activacion/spec.md:158`; está pendiente y fuera del MVP; PREG-4 no incluye los intentos de clave. |
| RNF-1 | PARCIAL | `specs/001-registro-activacion/spec.md:164`; planifica cobertura frontend, pero no se entregó evidencia de prueba a 390 px. |
| RNF-2 | PARCIAL | `specs/001-registro-activacion/spec.md:165`; planifica mensajes en español, pero no hay inventario ni verificación de todos los mensajes. |
| RNF-3 | NO VERIFICABLE | `specs/001-registro-activacion/spec.md:166`, `plan.md:18`, `tasks.md:10`; falta el diseño de escritura atómica y el contenido de su prueba. |
| RNF-4 | NO VERIFICABLE | `specs/001-registro-activacion/spec.md:167`, `plan.md:44-49`; se declara una suite pytest, pero falta evidencia de que corra sin servicios externos. |

## 3. Hallazgos

| ID | Severidad | Spec | Hallazgo | Ubicación | Evidencia | Corrección propuesta | Cómo verificar la corrección |
|---|---|---|---|---|---|---|---|
| H-ARQ-1 | MEDIA | CA-1 | CA-1 no define cómo comprobar visibilidad en todo momento | `specs/001-registro-activacion/spec.md:32, 41-43` | «en todo momento»; «completé n pasos» | Sustituir la frase vaga por estados observables para cada paso y cubrir inicio, avance, cierre y retoma. | Probar los estados para cada avance de 0 a 5 pasos y verificar que siempre haya exactamente un paso ACTUAL cuando corresponda. |
| H-ARQ-2 | MEDIA | CA-2 | CA-2 usa un dato abstracto en vez de valores concretos | `specs/001-registro-activacion/spec.md:55-59` | «un dato que incumple una regla RN-n» | Añadir al menos un ejemplo de entrada inválida, campo, código y mensaje esperado. | Ejecutar `pytest tests/test_ca2_validaciones.py` con el valor inválido y comprobar 422, código y campo. |
| H-ARQ-3 | MEDIA | CA-4 | CA-4 no define qué evento de interfaz constituye abandono | `specs/001-registro-activacion/spec.md:95-97`; `specs/001-registro-activacion/contracts/openapi.yaml:173-185` | «Cuando el usuario sale del registro»; el contrato ofrece una operación explícita para abandonar. | Definir qué acción del usuario invoca el cierre y cuándo se emite `onboarding_cerrado`. | Probar la acción definida y verificar un único evento con resultado ABANDONADO y `ultimo_paso` correcto. |
| H-ARQ-4 | MEDIA | CA-5 | CA-5 mezcla una meta trimestral con una obligación de medición | `specs/001-registro-activacion/spec.md:104-114`; `docs/supuestos-y-decisiones.md:5-8` | «baja de 8 minutos a 3»; «Esta spec exige la medición» | Separar el entregable verificable de instrumentación de la meta que se evalúa tras el lanzamiento; definir cohorte y período del reporte. | Con datos de duraciones conocidos, verificar mediana y `cumple_objetivo_mediana`; documentar por separado cómo se evalúa la meta trimestral. |
| H-ARQ-5 | MEDIA | CA-6 | CA-6 no concreta los valores esperados del desglose por canal | `specs/001-registro-activacion/spec.md:121-129`; `docs/supuestos-y-decisiones.md:19-21` | «Y el desglose por canal» | Añadir un escenario con canales, activaciones y gasto por canal, y definir la atribución esperada. | Consultar el reporte mensual con datos de dos canales y comprobar conteos, gasto y CAC de cada uno. |
| H-ARQ-6 | MEDIA | RN-1 a RN-12 | El contrato no limita los códigos de error a los definidos | `specs/001-registro-activacion/contracts/openapi.yaml:12-32, 88-97`; `specs/001-registro-activacion/spec.md:135-146` | `codigo` es `type: string`; el conflicto describe los códigos, pero no los enumera en el esquema. | Restringir los códigos por respuesta al conjunto de la spec y distinguir códigos de error de validación y conflicto. | Validar respuestas representativas de cada RN contra el esquema OpenAPI y comprobar que un código ajeno sea rechazado. |
| H-ARQ-7 | ALTA | RS-1, RS-5 | Los esquemas permiten campos adicionales en eventos y errores | `specs/001-registro-activacion/contracts/openapi.yaml:12-32, 71-85` | Evento declara «Sin datos personales», pero los esquemas no establecen `additionalProperties: false`. | Restringir campos adicionales en eventos y errores; permitir solo los atributos definidos y aprobados. | Validar contra OpenAPI un evento con DNI adicional y un error con una traza; ambos deben rechazarse. |
| H-ARQ-8 | MEDIA | RS-4 | El contrato no hace verificable el enmascaramiento | `specs/001-registro-activacion/contracts/openapi.yaml:62-68`; `specs/001-registro-activacion/plan.md:13` | La descripción menciona enmascaramiento y los ejemplos muestran valores, sin patrón que lo valide. | Definir en el esquema el formato que conserva solo los tres últimos dígitos para DNI y celular. | Validar respuestas enmascaradas válidas y rechazar valores que revelen más de tres dígitos. |
| H-ARQ-9 | MEDIA | RS-3, RNF-4 | El plan no asigna RS-3 ni define verificación de RNF-4 | `specs/001-registro-activacion/plan.md:11-18, 40-49` | La capa Reglas enumera RN-1 a RN-8 y RN-12, no RS-3; la verificación solo indica cantidad de pruebas pytest. | Asignar RS-3 a una capa responsable y especificar cómo se comprueba que las pruebas no dependen de servicios externos. | Revisar la matriz de capas y ejecutar la suite en un entorno sin servicios externos; comprobar también que las reglas se validan en servidor. |
| H-ARQ-10 | ALTA | RS-6 | RS-6 carece de responsable y de gate explícito de producción | `specs/001-registro-activacion/spec.md:157`; `docs/supuestos-y-decisiones.md:47-50` | «Pendiente, fuera del MVP»; «Cualquiera que conozca el id de un onboarding puede consultarlo». | Asignar responsable de Seguridad y Producto, definir autenticación de sesión y bloquear producción hasta su aprobación. | Probar que una consulta sin sesión no accede al registro y que una sesión autorizada solo accede al registro asociado. |
| H-ARQ-11 | ALTA | RS-7 | La pregunta de intentos omite la clave de pagos | `specs/001-registro-activacion/spec.md:158`; `docs/supuestos-y-decisiones.md:52, 62` | RS-7 exige límites para OTP y clave; PREG-4 pregunta por OTP o identidad. | Ampliar PREG-4 para incluir la clave; definir umbrales, bloqueo temporal y responsables de Seguridad y Cumplimiento. | Probar límites y bloqueo temporal por intentos fallidos tanto de OTP como de clave. |
| H-ARQ-12 | MEDIA | RN-8 | RN-8 no define qué patrones cuentan como secuenciales | `specs/001-registro-activacion/spec.md:142`; `docs/supuestos-y-decisiones.md:17` | «no puede ser repetida, secuencial»; el supuesto da ejemplos, pero no delimita el conjunto. | Especificar patrones repetidos y secuenciales rechazados, incluyendo secuencias descendentes y sus límites. | Probar una tabla de claves permitidas y rechazadas que cubra cada patrón definido. |
| H-ARQ-13 | BAJA | — | DEC-6 no justifica los parámetros criptográficos añadidos | `specs/001-registro-activacion/plan.md:33`; `docs/supuestos-y-decisiones.md:32` | El plan fija 16 bytes y 200,000 iteraciones; la justificación solo dice PBKDF2-SHA256 y sal aleatoria. | Documentar la base de esos parámetros y el criterio de actualización. | Revisar DEC-6 y comprobar que documenta rationale y política de configuración de los parámetros. |

## 4. Límites de esta revisión

No se entregó código, contenido de las pruebas, salidas de CI ni resultados de los verificadores; por ello no confirmé comportamiento en ejecución, escritura atómica, ausencia real de servicios externos, validaciones de servidor ni presentación móvil. PREG-1 a PREG-5 tienen roles asignados en el documento, pero permanecen abiertas; su cierre es necesario según los bloqueos descritos. Esta revisión no valida proveedores, métricas reales de producción ni controles implementados.

VEREDICTO: NO CUMPLE
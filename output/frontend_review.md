# Informe de Frontend

## 1. Resumen
Revisé la interfaz, sus estilos y las rutas y campos que consume frente a la spec y el contrato. El flujo básico de errores y reanudación está implementado, pero hay incumplimientos en la secuencia móvil, el desglose analítico y el escape de datos insertados en HTML. La conclusión es **NO CUMPLE**.

## 2. Cobertura de la spec

| ID | Estado | Evidencia |
|---|---|---|
| CA-1 | PARCIAL | `frontend/app.js:118-132,286-292`; `frontend/styles.css:183-185`. La pantalla obtiene el progreso del registro y permite retomarlo, pero en anchos de hasta 480 px oculta los títulos de los pasos. |
| CA-2 | CUMPLE | `frontend/app.js:102-115,220-240`. Muestra los mensajes 422 junto al campo y enfoca el primero; deshabilita el botón durante el envío y ofrece recuperación ante 409 o error de red. |
| CA-3 | PARCIAL | `frontend/app.js:252-263,300-323`; `specs/001-registro-activacion/contracts/openapi.yaml:198-209`. La wallet activa enlaza a pagos y el error muestra una salida para completar el registro; la respuesta 200 no define el esquema de los campos que la pantalla renderiza. |
| CA-4 | NO VERIFICABLE | `frontend/app.js:244-249,413-416`; `specs/001-registro-activacion/spec.md:83-100`. El cliente solicita abandonar y muestra eventos, pero no se entregó evidencia para verificar su registro y orden. |
| CA-5 | CUMPLE | `frontend/app.js:342-370`; `specs/001-registro-activacion/contracts/openapi.yaml:211-220`. La pantalla muestra la mediana y el indicador de cumplimiento recibidos de analítica; no se verifica aquí el cálculo del servidor. |
| CA-6 | PARCIAL | `frontend/app.js:389-397`; `specs/001-registro-activacion/contracts/openapi.yaml:222-229`. Muestra conteos, gasto y CAC mensuales, pero la tabla no presenta el desglose por canal exigido. |
| RNF-1 | NO VERIFICABLE | `frontend/styles.css:71-72,183-187`. Hay reglas adaptables a móvil, pero falta una comprobación ejecutada a 390 px que confirme que no existe desplazamiento horizontal. |
| RNF-2 | PARCIAL | `frontend/app.js:73,230-239`. El texto de interfaz está en español, pero el enlace de términos no realiza ninguna acción. |
| RNF-3 | NO VERIFICABLE | `specs/001-registro-activacion/spec.md:166`. No se entregó material de almacenamiento con el que verificar atomicidad; es ajeno a esta revisión de frontend. |
| RNF-4 | NO VERIFICABLE | `specs/001-registro-activacion/spec.md:167`. No se entregaron pruebas automatizadas ni resultados para comprobar su ejecución sin servicios externos. |

## 3. Hallazgos

| ID | Severidad | Spec | Hallazgo | Ubicación | Evidencia | Corrección propuesta | Cómo verificar la corrección |
|---|---|---|---|---|---|---|---|
| H-FE-1 | ALTA | — | Se interpolan datos del servidor sin escape en plantillas HTML | `frontend/app.js:123,126-129,370,406` | `data-estado="${p.estado}"` y `${e.orden}.` se insertan directamente en HTML. | Escapar cada valor dinámico según su contexto o construir el DOM con propiedades de texto; validar además números y enumeraciones. | Con respuestas simuladas que incluyan marcado en esos campos, comprobar que se muestra como texto y no crea elementos HTML. |
| H-FE-2 | ALTA | CA-1 | Los títulos de pasos desaparecen en pantallas móviles | `frontend/styles.css:183-185` | `.pasos li span { display: none; }` | Mantener visibles los nombres de los cinco pasos en móvil, usando una presentación compacta si hace falta. | A 390 px, comprobar en cada pantalla del registro y al retomarlo que aparecen los cinco nombres y el paso actual. |
| H-FE-3 | ALTA | CA-6 | El reporte mensual omite el desglose por canal | `frontend/app.js:391-397`; `specs/001-registro-activacion/contracts/openapi.yaml:222-229` | La tabla muestra mes, nuevos activos, gasto y CAC, pero no canal. | Definir el desglose por canal en el contrato y renderizarlo en el reporte. | Con datos de dos canales para un mes, comprobar que la interfaz muestra el gasto y CAC desglosados por canal. |
| H-FE-4 | MEDIA | CA-3 | La pantalla de pagos consume campos no definidos en el contrato | `frontend/app.js:310-317`; `specs/001-registro-activacion/contracts/openapi.yaml:205` | El cliente lee `estado_wallet`, `titular`, `opciones` y `nota`; la respuesta 200 solo describe opciones simuladas, sin esquema. | Declarar el esquema de respuesta en el contrato y ajustar la pantalla a ese esquema. | Validar una respuesta de ejemplo contra el contrato y comprobar que la pantalla de pagos muestra sus datos. |
| H-FE-5 | MEDIA | — | Los errores de campo no se asocian programáticamente a sus controles | `frontend/app.js:102-115` | Se actualiza `box.textContent`, pero no se asignan `aria-describedby` ni `aria-invalid` al control. | Asociar cada mensaje al control correspondiente y exponer su estado inválido con atributos ARIA. | Enviar un 422 para DNI y comprobar que el control referencia su mensaje y que un lector de pantalla anuncia el error. |
| H-FE-6 | MEDIA | RNF-2 | El enlace a términos no realiza ninguna acción | `frontend/app.js:73` | `href="#" onclick="return false"` | Proporcionar el contenido o destino real de los términos, o presentarlos como texto si no hay acción disponible. | Activar el enlace con teclado y ratón y comprobar que abre el contenido de términos. |

## 4. Límites de esta revisión

No ejecuté la aplicación ni pruebas automatizadas. Por ello, no pude comprobar el desplazamiento real a 390 px, medir contraste en la interfaz renderizada ni verificar el comportamiento con tecnologías de asistencia. Tampoco revisé lógica del servidor: quedan fuera de esta revisión el registro de eventos, los cálculos analíticos y la atomicidad del almacenamiento. El contrato tampoco define el esquema de la respuesta exitosa de pagos.

VEREDICTO: NO CUMPLE
# Informe de Backend

## 1. Resumen
Revisé las 13 operaciones del contrato y la implementación de CA-1 a CA-6 y RN-1 a RN-12. El flujo principal, la activación, los eventos y los cálculos analíticos están implementados, pero hay incumplimientos del contrato de pasos y de los errores de validación, además de reglas que aceptan entradas fuera de la especificación. No ejecuté pruebas.

## 2. Cobertura de la spec

| ID | Estado | Evidencia |
|---|---|---|
| CA-1 | PARCIAL | `app/main.py:94-97` devuelve el catálogo sin `estado`; `app/onboarding.py:234-285` construye estados y `paso_actual` para el registro. |
| CA-2 | PARCIAL | `app/main.py:71-77` da forma al error de dominio; `app/domain.py:82-117` acumula errores personales, pero `app/domain.py:179-194` devuelve el primero para la clave. |
| CA-3 | CUMPLE | `app/onboarding.py:182-190` activa y cierra al completar; `app/onboarding.py:133-152` bloquea pagos si la wallet no está activa. |
| CA-4 | CUMPLE | `app/onboarding.py:82-86`, `app/onboarding.py:99-109`, `app/onboarding.py:171-202` y `app/onboarding.py:111-118` registran inicio, pasos, fallos, activación y cierre. |
| CA-5 | CUMPLE | `app/analytics.py:57-60` calcula duración desde inicio hasta activación; `app/analytics.py:71-88` calcula mediana y cumplimiento. |
| CA-6 | CUMPLE | `app/analytics.py:97-145` cuenta activaciones por mes y canal; `app/analytics.py:121-132` produce CAC y cumplimiento nulos sin gasto. |
| RN-1 | PARCIAL | `app/domain.py:73-75` recorta espacios y convierte valores no textuales en vacíos; `app/domain.py:84-88` valida el DNI. |
| RN-2 | CUMPLE | `app/domain.py:54` y `app/domain.py:90-96` validan longitud y caracteres permitidos, y dan mensajes accionables. |
| RN-3 | PARCIAL | `app/domain.py:98-114` usa `date.fromisoformat` sin exigir primero el formato exacto `AAAA-MM-DD`. |
| RN-4 | PARCIAL | `app/domain.py:126-148` valida el celular, pero usa `CAMPO_OBLIGATORIO` cuando falta, código no listado para RN-4. |
| RN-5 | PARCIAL | `app/domain.py:137-144` valida formato y código OTP; los valores recortados y ausentes tienen casos límite. |
| RN-6 | CUMPLE | `app/domain.py:151-155` exige autorización; `app/onboarding.py:169-174` rechaza y cierra el flujo cuando falla la identidad. |
| RN-7 | CUMPLE | `app/domain.py:158-168` requiere ambas aceptaciones con sus códigos de error especificados. |
| RN-8 | PARCIAL | `app/domain.py:176-195` comprueba formato, seguridad y confirmación; recorta entradas y usa códigos no listados para campos ausentes. |
| RN-9 | PARCIAL | `app/onboarding.py:160-164` comprueba DNI duplicado y activo; `app/store.py:35` solo sincroniza dentro de una instancia. |
| RN-10 | CUMPLE | `app/onboarding.py:88-99` compara el paso enviado con el actual y devuelve `PASO_FUERA_DE_ORDEN`. |
| RN-11 | CUMPLE | `app/onboarding.py:92-95` y `app/onboarding.py:220-223` impiden avanzar en un registro cerrado. |
| RN-12 | PARCIAL | `app/onboarding.py:62-68` limita canales válidos, pero convierte valores vacíos o nulos en `organico`. |

**Inventario de rutas y contrato:** Las rutas y métodos están en `app/main.py:90-121` para salud, catálogo, inicio, consulta, pasos, abandono, eventos y pagos; `app/main.py:133-154` para analítica y gasto; y `app/main.py:158-166` para reinicio demo. Las rutas implementan los códigos principales del contrato: inicio y gasto devuelven 201; las consultas y transiciones exitosas, 200; los errores de dominio usan los manejadores de `app/main.py:71-86` para 422, 409, 403 y 404. Los errores de validación de dominio incluyen `codigo`, `mensaje` y `errores[]`; conflictos y recursos inexistentes usan `codigo` y `mensaje`, como define el contrato. Los parámetros de analítica y demo están en `app/main.py:133-147` y `app/main.py:159-166`. La ruta de catálogo no cumple el schema `Paso`, que requiere `estado`, y el reinicio demo queda habilitado por defecto, aunque el contrato lo limita a `DEMO_ENDPOINTS=true`.

## 3. Hallazgos

| ID | Severidad | Spec | Hallazgo | Ubicación | Evidencia | Corrección propuesta | Cómo verificar la corrección |
|---|---|---|---|---|---|---|---|
| H-BE-1 | ALTA | CA-1 | El catálogo omite el estado obligatorio de cada paso | `app/main.py:96-97` | `return [{"orden": i, "clave": p.clave, "titulo": p.titulo, "descripcion": p.descripcion}` | Devolver un `estado` válido para cada paso, conforme al schema `Paso`. | Consultar `GET /api/onboarding/pasos` y comprobar que los cinco objetos incluyen `estado` y satisfacen el schema del contrato. |
| H-BE-2 | ALTA | CA-2 | La clave informa solo el primer campo inválido | `app/domain.py:179-194` | Las validaciones ejecutan `raise ErrorValidacion(...)` antes de comprobar los campos restantes. | Acumular los errores independientes de clave y confirmación antes de lanzar la excepción. | Enviar una clave inválida con confirmación ausente y verificar que `errores[]` contiene cada campo inválido. |
| H-BE-3 | ALTA | CA-2 | Los errores de parseo no usan el sobre de validación contractual | `app/main.py:71-77`, `app/main.py:107-109` | El manejador cubre `ErrorValidacion`; el cuerpo del paso se declara como `dict` y no hay manejador para errores de validación del framework. | Normalizar los errores de parseo y tipo al mismo formato 422 con `codigo`, `mensaje` y `errores[]`. | Con `TestClient`, enviar un cuerpo de paso que no sea un objeto y verificar estado 422 y la forma contractual completa. |
| H-BE-4 | MEDIA | RN-1, RN-5, RN-8 | El recorte acepta espacios periféricos en datos de longitud exacta | `app/domain.py:73-75`, `app/domain.py:84-88`, `app/domain.py:137-144`, `app/domain.py:176-182` | `_texto` devuelve `valor.strip()`; DNI, OTP y clave validan después de ese recorte. | Validar la entrada original y distinguir vacíos de valores no textuales o con espacios no permitidos. | Probar DNI, OTP y clave con espacios periféricos y con valores numéricos; comprobar que no se aceptan como valores exactos válidos. |
| H-BE-5 | MEDIA | RN-3 | El parser acepta formatos de fecha distintos de AAAA-MM-DD | `app/domain.py:98-107` | Se llama a `date.fromisoformat(texto_fecha)` sin comprobar el patrón exigido. | Comprobar el patrón exacto `AAAA-MM-DD` antes de convertir la fecha. | Enviar fecha con formato compacto y fecha con guiones; solo la segunda debe superar la validación de formato. |
| H-BE-6 | MEDIA | RN-3, RN-4, RN-5, RN-8 | Los campos ausentes usan códigos no declarados por sus reglas | `app/domain.py:100-107`, `app/domain.py:131-141`, `app/domain.py:179-191` | Los casos ausentes devuelven `CAMPO_OBLIGATORIO`, código no incluido en RN-3, RN-4, RN-5 ni RN-8. | Alinear el código de cada campo ausente con los códigos exactos de su RN. | Enviar cada campo ausente y comparar su código con la tabla de RN de la spec. |
| H-BE-7 | MEDIA | RN-12 | Un canal vacío o nulo se convierte silenciosamente en orgánico | `app/onboarding.py:62-68` | `canal = canal or "organico"` precede a la validación de pertenencia a `CANALES`. | Aplicar el valor por defecto solo cuando el campo se omita; rechazar valores suministrados inválidos. | Probar inicio sin canal, con `null`, cadena vacía y canal con mayúsculas; verificar el resultado especificado para cada caso. |
| H-BE-8 | MEDIA | — | El reinicio demo queda habilitado si falta la variable | `app/main.py:158-160` | `_flag("DEMO_ENDPOINTS", True)` usa `True` como valor por defecto. | Deshabilitar la ruta por defecto y habilitarla solo con `DEMO_ENDPOINTS=true`. | Iniciar la app sin la variable y comprobar que la ruta no está registrada; repetir con valor `true`. |
| H-BE-9 | MEDIA | RN-9 | El lock no protege escrituras concurrentes entre procesos | `app/store.py:35`, `app/store.py:64-68` | El almacenamiento usa `threading.RLock()` por instancia y guarda el estado completo en el archivo. | Usar un mecanismo de bloqueo compartido entre procesos o almacenamiento transaccional. | Ejecutar dos instancias con el mismo archivo y crear concurrentemente registros con el mismo DNI; verificar que no se activan dos wallets. |
| H-BE-10 | MEDIA | RNF-3 | Una excepción deja la copia en memoria sin revertir | `app/store.py:7-8`, `app/store.py:64-68` | El docstring declara que la copia en memoria no se revierte si falla el bloque `write()`. | Escribir sobre una copia y publicar el nuevo estado solo tras completar la escritura. | Inyectar una excepción después de modificar el estado y comprobar que memoria y archivo conservan el estado anterior. |
| H-BE-11 | MEDIA | — | Las excepciones no previstas carecen de manejo explícito | `app/main.py:71-86` | Solo se registran manejadores para `ErrorValidacion`, `Conflicto` y `NoEncontrado`. | Añadir manejo general de excepciones con respuesta 500 controlada y sin detalles internos. | Provocar una excepción inesperada en una prueba y comprobar una respuesta 500 estable, sin trazas ni datos internos. |

## 4. Límites de esta revisión

No ejecuté el servidor, pruebas automatizadas ni verificaciones del contrato. Por ello, no observé respuestas reales del framework ante cuerpos malformados ni fallos de escritura; esos casos se señalan a partir del código y requieren las pruebas indicadas. Tampoco se entregó configuración de despliegue para determinar cuántos procesos comparten el archivo.

VEREDICTO: NO CUMPLE
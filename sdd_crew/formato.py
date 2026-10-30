"""Formato común de los informes y lectura de veredictos y hallazgos."""
from __future__ import annotations

import re
from collections import Counter

SEVERIDADES = ("ALTA", "MEDIA", "BAJA")

FORMATO_INFORME = """\
## Formato obligatorio del informe

Devuelve SOLO un documento markdown en español con estas secciones, en este orden:

# Informe de {nombre}

## 1. Resumen
Dos a cuatro frases: qué revisaste y la conclusión.

## 2. Cobertura de la spec
Tabla con una fila por cada ID que te corresponde revisar ({foco}):
| ID | Estado | Evidencia |
- Estado: CUMPLE, PARCIAL, NO CUMPLE o NO VERIFICABLE.
- Evidencia: `archivo:línea` del material entregado, o la verificación ejecutada que lo demuestra.
- Usa NO VERIFICABLE cuando el material entregado no alcance para decidir, y di qué faltaría.

## 3. Hallazgos
Tabla con una fila por hallazgo (si no hay, escribe "Sin hallazgos" y explica por qué):
| ID | Severidad | Spec | Hallazgo | Ubicación | Evidencia | Corrección propuesta | Cómo verificar la corrección |
- ID: H-{prefijo}-1, H-{prefijo}-2, ... Usa este prefijo solo en esta tabla.
- Severidad: ALTA (incumple un CA o un RS, o es un riesgo de seguridad), MEDIA (cumple a medias o es frágil), BAJA (mejora).
- Spec: el ID de la spec afectado (CA-n, RN-n, RS-n, RNF-n) o "—" si es una mejora general.
- Hallazgo: una frase de máximo 12 palabras que describa el problema (se usa como título de la issue).
- No uses el carácter | dentro de las celdas.
- Ubicación: `archivo:línea` exacto del material entregado.
- Evidencia: cita textual breve del código o de la salida que lo demuestra.
- Cómo verificar: la prueba o el comando concreto que demostraría que la corrección funciona.

{secciones_extra}## 4. Límites de esta revisión
Lo que no pudiste comprobar con el material entregado.

{linea_veredicto}

## Reglas
- Revisa SOLO lo que te corresponde como {nombre}; no repitas el trabajo de otros roles.
- La spec es la fuente de verdad: compara el material contra ella, no contra tu preferencia.
- No inventes archivos, líneas, rutas, resultados de pruebas ni ejecuciones. Solo puedes citar lo que está en el material.
- Tú no ejecutas nada. Si una afirmación necesita ejecución, márcala NO VERIFICABLE o apóyate en la evidencia ejecutada que se te entrega.
- Si recibes feedback humano, corrige el informe según ese feedback y explica al inicio del Resumen qué cambiaste.
"""

LINEA_VEREDICTO_ROL = "Termina con una última línea exacta: `VEREDICTO: CUMPLE` o `VEREDICTO: NO CUMPLE` (NO CUMPLE si hay al menos un hallazgo ALTA)."
LINEA_VEREDICTO_CHAPTER = "Termina con una última línea exacta: `VEREDICTO: APROBADO` o `VEREDICTO: RECHAZADO`."

SECCIONES_CHAPTER = """\
## Matriz final
| CA | Implementación | Prueba | Evidencia ejecutada | Estado final |

## Hallazgos consolidados de otros roles
Tabla | ID original | Rol | Severidad | ¿Bloquea? | Responsable |. Usa los IDs originales (por ejemplo H-BE-2)
y NO los repitas en la sección 3: allí van solo los hallazgos propios del Chapter (contradicciones entre
informes, evidencia faltante, criterios sin cubrir).

## Correcciones priorizadas
Lista numerada: corrección, responsable y cómo verificarla.

"""

VEREDICTO_RE = re.compile(r"VEREDICTO:\s*\**\s*(APROBADO|RECHAZADO|NO CUMPLE|CUMPLE)\b", re.IGNORECASE)
HALLAZGO_RE = re.compile(r"^\|\s*H-[A-Z]+-\d+\s*\|\s*\**(ALTA|MEDIA|BAJA)\**\s*\|", re.IGNORECASE | re.MULTILINE)


def veredicto(texto: str) -> str | None:
    """Último veredicto declarado en el informe (None si no hay)."""
    encontrados = VEREDICTO_RE.findall(texto or "")
    return encontrados[-1].upper() if encontrados else None


def seccion_hallazgos(texto: str) -> str:
    """Solo la sección "## 3. Hallazgos": evita contar tablas que citan IDs de otros roles."""
    m = re.search(r"^##\s*3\.\s*Hallazgos.*?$(.*?)(?=^##\s|\Z)", texto or "", re.MULTILINE | re.DOTALL)
    return m.group(1) if m else (texto or "")


def hallazgos_por_severidad(texto: str) -> dict[str, int]:
    conteo = Counter(s.upper() for s in HALLAZGO_RE.findall(seccion_hallazgos(texto)))
    return {s: conteo.get(s, 0) for s in SEVERIDADES}

"""Ejecuta un rol: un mini-Crew de un agente y una tarea, o un informe simulado."""
from __future__ import annotations

import os

from sdd_crew import llm
from sdd_crew.roles.base import Rol, ids_en_foco

os.environ.setdefault("CREWAI_TELEMETRY_OPT_OUT", "true")
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")


def ejecutar_con_crewai(rol: Rol, prompt: str) -> str:
    from crewai import Agent, Crew, Process, Task

    agente = Agent(role=rol.rol_agente, goal=rol.objetivo, backstory=rol.contexto,
                   llm=llm.crear_llm(), allow_delegation=False, verbose=False)
    tarea = Task(description=prompt, expected_output=rol.salida_esperada, agent=agente)
    resultado = Crew(agents=[agente], tasks=[tarea], process=Process.sequential,
                     verbose=False, tracing=False).kickoff()
    return str(getattr(resultado, "raw", None) or resultado)


def informe_simulado(rol: Rol, ids_spec: list[str]) -> str:
    """Informe de ejemplo para probar el flujo sin modelo. No es una revisión y no emite veredicto."""
    filas = "\n".join(f"| {i} | NO VERIFICABLE | Informe simulado: no se revisó |" for i in ids_en_foco(rol, ids_spec))
    return f"""# Informe de {rol.nombre}

> ⚠️ INFORME SIMULADO (LLM_PROVIDER=simulado). Sirve para probar el flujo; no contiene una revisión real.

## 1. Resumen
Informe generado sin modelo para comprobar que el flujo, las aprobaciones y los archivos de salida funcionan.

## 2. Cobertura de la spec
| ID | Estado | Evidencia |
|---|---|---|
{filas}

## 3. Hallazgos
Sin hallazgos: no hubo revisión.

## 4. Límites de esta revisión
No se usó ningún modelo. Ejecuta con LLM_PROVIDER=copilot o crewai para una revisión real.
"""


def ejecutar(rol: Rol, prompt: str, ids_spec: list[str]) -> str:
    if llm.proveedor() == "simulado":
        return informe_simulado(rol, ids_spec)
    return ejecutar_con_crewai(rol, prompt)

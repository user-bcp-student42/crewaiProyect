"""Definición de un rol validador y armado de su prompt."""
from __future__ import annotations

from dataclasses import dataclass

from sdd_crew.formato import FORMATO_INFORME, LINEA_VEREDICTO_CHAPTER, LINEA_VEREDICTO_ROL, SECCIONES_CHAPTER


@dataclass(frozen=True)
class Rol:
    clave: str             # architect, backend, ...
    nombre: str            # nombre visible
    prefijo: str           # prefijo de los hallazgos: H-ARQ-1
    informe: str           # archivo de salida
    rol_agente: str        # role de CrewAI
    objetivo: str          # goal de CrewAI
    contexto: str          # backstory de CrewAI
    instrucciones: str     # qué revisa y cómo
    foco: tuple[str, ...]  # prefijos de IDs que debe cubrir: ("CA", "RN")
    usa_plan: bool = False
    usa_contrato: bool = False
    usa_evidencia: bool = False
    usa_informes: bool = False
    es_chapter: bool = False

    @property
    def salida_esperada(self) -> str:
        cierre = "VEREDICTO: APROBADO o VEREDICTO: RECHAZADO" if self.es_chapter else "VEREDICTO: CUMPLE o VEREDICTO: NO CUMPLE"
        return (f"Informe markdown '{self.informe}' con Resumen, Cobertura de la spec, Hallazgos "
                f"(H-{self.prefijo}-n con ubicación y evidencia), Límites de la revisión y la línea final {cierre}.")


def ids_en_foco(rol: Rol, ids_spec: list[str]) -> list[str]:
    return [i for i in ids_spec if i.split("-")[0] in rol.foco]


def construir_prompt(rol: Rol, paquete: dict) -> str:
    """Instrucciones del rol + formato común + material (spec, plan, contrato, código, evidencia)."""
    foco = ids_en_foco(rol, paquete["ids_spec"])
    formato = FORMATO_INFORME.format(
        nombre=rol.nombre, prefijo=rol.prefijo, foco=", ".join(foco) or "los IDs relevantes",
        linea_veredicto=LINEA_VEREDICTO_CHAPTER if rol.es_chapter else LINEA_VEREDICTO_ROL,
        secciones_extra=SECCIONES_CHAPTER if rol.es_chapter else "",
    )
    partes = [
        f"# Tarea: validación SDD como {rol.nombre}",
        f"Proyecto: {paquete['proyecto']} · commit `{paquete.get('commit') or 'desconocido'}`",
        rol.instrucciones.strip(),
        formato,
        "---",
        "# MATERIAL",
        "## Spec (fuente de verdad)",
        paquete["spec"],
    ]
    if rol.usa_plan and paquete.get("plan"):
        partes += ["## Plan técnico", paquete["plan"]]
    if rol.usa_contrato and paquete.get("contrato"):
        partes += ["## Contrato de API", paquete["contrato"]]
    if paquete.get("archivos"):
        partes += ["## Archivos del repositorio (con número de línea)", paquete["archivos"]]
    if rol.usa_evidencia:
        partes += ["## Evidencia ejecutada", paquete.get("evidencia") or "No hay evidencia ejecutada."]
    if rol.usa_informes:
        informes = paquete.get("informes") or {}
        partes += ["## Informes aprobados de los otros roles"]
        partes += [f"### {nombre}\n{texto}" for nombre, texto in informes.items()] or ["(ninguno)"]
    if paquete.get("feedback"):
        partes += ["---", "# FEEDBACK HUMANO SOBRE TU INFORME ANTERIOR",
                   f"Informe anterior:\n{paquete.get('informe_anterior', '')}",
                   f"Feedback: {paquete['feedback']}",
                   "Corrige el informe según este feedback."]
    return "\n\n".join(partes)

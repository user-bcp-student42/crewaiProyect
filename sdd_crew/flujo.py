"""Flujo de validación SDD: evidencia → roles con aprobación humana → veredicto final."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from sdd_crew import evidencia as ev
from sdd_crew import formato
from sdd_crew.proyecto import Proyecto, bloque_archivo
from sdd_crew.roles.base import Rol, construir_prompt

# runner(rol, prompt, ids_spec) -> informe ; aprobar(rol, informe, borrador) -> ("s"|"r"|"n", feedback)
Runner = Callable[[Rol, str, list[str]], str]
Aprobador = Callable[[Rol, str, Path], tuple[str, str]]


@dataclass
class EstadoFlujo:
    commit: str | None
    aprobados: dict[str, str] = field(default_factory=dict)

    @classmethod
    def cargar(cls, ruta: Path, commit: str | None, reiniciar: bool, log: Callable[[str], None]) -> "EstadoFlujo":
        if reiniciar or not ruta.exists():
            return cls(commit)
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        if datos.get("commit") != commit:
            log(f"El checkpoint es de otro commit ({str(datos.get('commit'))[:8]}); empiezo de cero.")
            return cls(commit)
        return cls(commit, datos.get("aprobados", {}))

    def guardar(self, ruta: Path) -> None:
        ruta.write_text(json.dumps({"commit": self.commit, "aprobados": self.aprobados},
                                   ensure_ascii=False, indent=2), encoding="utf-8")


def material_del_rol(proyecto: Proyecto, rol: Rol) -> str:
    """Archivos del rol con números de línea, hasta el límite de caracteres del proyecto."""
    bloques, usados, omitidos = [], 0, []
    for ruta in proyecto.resolver(proyecto.archivos.get(rol.clave, [])):
        bloque = bloque_archivo(ruta, proyecto.leer(ruta))
        if usados + len(bloque) > proyecto.limite_caracteres:
            omitidos.append(ruta)
            continue
        bloques.append(bloque)
        usados += len(bloque)
    if omitidos:
        bloques.append("⚠️ Archivos NO incluidos por el límite de tamaño (márcalos como no revisados): "
                       + ", ".join(omitidos))
    return "\n\n".join(bloques)


def paquete(proyecto: Proyecto, rol: Rol, commit: str | None, evidencia_md: str, informes: dict[str, str]) -> dict:
    return {
        "proyecto": proyecto.nombre,
        "commit": commit,
        "ids_spec": proyecto.ids_spec,
        "spec": bloque_archivo(proyecto.spec, proyecto.leer(proyecto.spec)),
        "plan": bloque_archivo(proyecto.plan, proyecto.leer(proyecto.plan)) if proyecto.plan else None,
        "contrato": bloque_archivo(proyecto.contrato, proyecto.leer(proyecto.contrato)) if proyecto.contrato else None,
        "archivos": material_del_rol(proyecto, rol),
        "evidencia": evidencia_md,
        "informes": informes,
    }


def resultado_final(evidencia_ok: bool | None, veredicto_chapter: str | None, simulado: bool) -> tuple[str, str]:
    """El veredicto del modelo nunca anula una verificación fallida."""
    if evidencia_ok is False:
        return "RECHAZADO", "Al menos una verificación ejecutada falló."
    if evidencia_ok is None:
        return "NO CONCLUYENTE", "No hay verificaciones ejecutadas: el veredicto de un modelo no basta."
    if simulado:
        return "NO CONCLUYENTE", "Ejecución simulada: no hubo revisión de un modelo."
    if veredicto_chapter in ("APROBADO", "RECHAZADO"):
        return veredicto_chapter, "Veredicto del Chapter, con la evidencia ejecutada en verde."
    return "NO CONCLUYENTE", "El Chapter no se ejecutó o no emitió un veredicto válido."


def ejecutar_flujo(proyecto: Proyecto, roles: tuple[Rol, ...], runner: Runner, aprobar: Aprobador,
                   salida: Path, modelo: str, reiniciar: bool = False, solo_evidencia: bool = False,
                   log: Callable[[str], None] = print) -> dict:
    salida.mkdir(parents=True, exist_ok=True)
    (salida / "borradores").mkdir(exist_ok=True)
    commit = proyecto.commit()

    log(f"Verificaciones deterministas en {proyecto.repo} ...")
    resultados = ev.ejecutar(proyecto)
    evidencia_ok = ev.todo_ok(resultados) if resultados else None
    evidencia_md = ev.como_markdown(resultados, commit)
    (salida / "evidencia.md").write_text(f"# Evidencia ejecutada\n\n{evidencia_md}\n", encoding="utf-8")
    (salida / "evidencia.json").write_text(json.dumps([r.a_dict() for r in resultados], ensure_ascii=False, indent=2),
                                           encoding="utf-8")
    for r in resultados:
        log(f"  {'✓' if r.ok else '✗'} {r.nombre} ({r.duracion_s} s)")
        if not r.ok:
            for linea in r.salida.splitlines()[-4:]:
                log(f"      {linea}")
    if evidencia_ok is False:
        log(f"  Salida completa en {salida / 'evidencia.md'}")

    estado = EstadoFlujo.cargar(salida / ".checkpoint.json", commit, reiniciar, log)
    detenido_en = None
    if not solo_evidencia:
        for rol in roles:
            if rol.clave in estado.aprobados:
                log(f"• {rol.nombre}: ya aprobado en el checkpoint, se reutiliza.")
                continue
            previos = {r.nombre: estado.aprobados[r.clave] for r in roles if r.clave in estado.aprobados}
            datos = paquete(proyecto, rol, commit, evidencia_md, previos)
            while True:
                log(f"• {rol.nombre}: revisando ...")
                informe = runner(rol, construir_prompt(rol, datos), proyecto.ids_spec)
                borrador = salida / "borradores" / rol.informe
                borrador.write_text(informe, encoding="utf-8")
                decision, feedback = aprobar(rol, informe, borrador)
                if decision == "s":
                    (salida / rol.informe).write_text(informe, encoding="utf-8")
                    estado.aprobados[rol.clave] = informe
                    estado.guardar(salida / ".checkpoint.json")
                    break
                if decision == "r":
                    datos = {**datos, "feedback": feedback, "informe_anterior": informe}
                    continue
                detenido_en = rol.clave
                break
            if detenido_en:
                log(f"Flujo detenido por decisión humana en {rol.nombre}.")
                break

    filas = []
    for rol in roles:
        texto = estado.aprobados.get(rol.clave)
        filas.append({
            "rol": rol.nombre,
            "informe": rol.informe if texto else None,
            "veredicto": formato.veredicto(texto) if texto else None,
            "hallazgos": formato.hallazgos_por_severidad(texto) if texto else None,
        })
    chapter = next((f["veredicto"] for f, r in zip(filas, roles) if r.es_chapter), None)
    if solo_evidencia:
        final = "RECHAZADO" if evidencia_ok is False else "SOLO EVIDENCIA"
        motivo = ("Al menos una verificación ejecutada falló." if evidencia_ok is False
                  else "Verificaciones deterministas ejecutadas; sin revisión de agentes.")
    else:
        final, motivo = resultado_final(evidencia_ok, chapter, modelo == "simulado")
    if evidencia_ok is False and chapter == "APROBADO":
        motivo += " El Chapter aprobó pese a la falla: revisa su informe."

    resumen = {
        "proyecto": proyecto.nombre, "commit": commit, "modelo": modelo,
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evidencia_ok": evidencia_ok, "evidencia": [r.a_dict() | {"salida": None} for r in resultados],
        "roles": filas, "detenido_en": detenido_en,
        "resultado": final, "motivo": motivo,
    }
    (salida / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    (salida / "resumen.md").write_text(resumen_markdown(resumen), encoding="utf-8")
    return resumen


def resumen_markdown(r: dict) -> str:
    def hallazgos(h):
        return "—" if not h else f"{h['ALTA']} alta · {h['MEDIA']} media · {h['BAJA']} baja"

    lineas = [
        f"# Validación SDD · {r['proyecto']}", "",
        f"**Resultado: {r['resultado']}** — {r['motivo']}", "",
        f"- Commit: `{r['commit'] or 'desconocido'}`",
        f"- Modelo: `{r['modelo']}`",
        f"- Fecha: {r['fecha']}", "",
        "## Evidencia ejecutada", "",
        "| Verificación | Resultado |", "|---|---|",
    ]
    lineas += [f"| {e['nombre']} | {'PASÓ' if e['ok'] else 'FALLÓ'} |" for e in r["evidencia"]] or ["| (ninguna) | — |"]
    lineas += ["", "Detalle en [evidencia.md](evidencia.md).", "", "## Roles", "",
               "| Rol | Veredicto | Hallazgos | Informe |", "|---|---|---|---|"]
    for f in r["roles"]:
        informe = f"[{f['informe']}]({f['informe']})" if f["informe"] else "pendiente"
        lineas.append(f"| {f['rol']} | {f['veredicto'] or '—'} | {hallazgos(f['hallazgos'])} | {informe} |")
    if r["detenido_en"]:
        lineas += ["", f"El flujo se detuvo por decisión humana en `{r['detenido_en']}`."]
    return "\n".join(lineas) + "\n"

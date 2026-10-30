"""Validación SDD por roles: Architect → Backend → Frontend → Testing → Security → Chapter.

Uso:
    python validar.py                                   # proyecto por defecto, con aprobación humana
    python validar.py --solo-evidencia                  # solo las verificaciones deterministas
    python validar.py --roles architect,testing         # solo algunos roles
    python validar.py --auto                            # aprueba cada informe sin preguntar
    python validar.py --repo ../otra/ruta --reiniciar   # otra copia del repo, ignorando el checkpoint
    python validar.py --crear-issues                    # issues de GitHub con los hallazgos aprobados
    python validar.py --crear-issues --github-project 2 # ... y agregarlas al Project número 2
    python validar.py --issues-auto --github-project 2  # validar y crear las issues al terminar, sin preguntar
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent
load_dotenv(RAIZ / ".env")

from sdd_crew import ejecutor, formato, issues, llm  # noqa: E402
from sdd_crew.flujo import ejecutar_flujo  # noqa: E402
from sdd_crew.proyecto import Proyecto  # noqa: E402
from sdd_crew.roles import POR_CLAVE, ROLES  # noqa: E402
from sdd_crew.roles.base import Rol  # noqa: E402

LINEAS_VISTA_PREVIA = 40


def elegir_roles(texto: str | None) -> tuple[Rol, ...]:
    if not texto:
        return ROLES
    claves = [c.strip().lower() for c in texto.split(",") if c.strip()]
    desconocidas = [c for c in claves if c not in POR_CLAVE]
    if desconocidas:
        raise SystemExit(f"Roles desconocidos: {', '.join(desconocidas)}. Usa: {', '.join(POR_CLAVE)}")
    return tuple(r for r in ROLES if r.clave in claves)


def aprobar_en_consola(rol: Rol, informe: str, borrador: Path) -> tuple[str, str]:
    lineas = informe.strip().splitlines()
    print("\n" + "─" * 72)
    print(f"Informe de {rol.nombre} · {len(lineas)} líneas · completo en: {borrador}")
    print("─" * 72)
    print("\n".join(lineas[:LINEAS_VISTA_PREVIA]))
    if len(lineas) > LINEAS_VISTA_PREVIA:
        print(f"[... {len(lineas) - LINEAS_VISTA_PREVIA} líneas más en el archivo ...]")
    h = formato.hallazgos_por_severidad(informe)
    print("─" * 72)
    print(f"Veredicto: {formato.veredicto(informe) or 'sin veredicto'} · "
          f"Hallazgos: {h['ALTA']} alta, {h['MEDIA']} media, {h['BAJA']} baja")
    while True:
        opcion = input("¿Aprobar? [s] sí · [r] reintentar con feedback · [n] rechazar y detener: ").strip().lower()
        if opcion == "s":
            return "s", ""
        if opcion == "n":
            return "n", ""
        if opcion == "r":
            feedback = input("Feedback para el agente: ").strip()
            if feedback:
                return "r", feedback
            print("Escribe el feedback para reintentar.")


def crear_issues(proyecto: Proyecto, salida: Path, severidades: list[str], github_project: int | None,
                 seleccion: str | None, gh: issues.Gh = issues.gh_real, entrada=input) -> int:
    """Hallazgos aprobados → selección humana → issues en GitHub."""
    commit, hallazgos = issues.desde_checkpoint(salida)
    hallazgos = [h for h in hallazgos if h.severidad in severidades]
    if commit and proyecto.commit() and commit != proyecto.commit():
        print(f"⚠ Los informes son del commit {commit[:8]} y el repo está en {proyecto.commit()[:8]}. "
              "Algunas ubicaciones pueden haber cambiado.")
    if not hallazgos:
        print(f"No hay hallazgos {'/'.join(severidades)} en los informes aprobados. No se crea nada.")
        return 0

    repo = issues.repo_github(proyecto.repo, proyecto.github)
    gh("auth status".split())
    hallazgos = issues.marcar_existentes(hallazgos, repo, commit, gh)
    if not hallazgos:
        print("Todos los hallazgos ya tienen issue. No se crea nada.")
        return 0

    print(f"\nHallazgos aprobados ({'/'.join(severidades)}) para crear en {repo}:\n")
    for n, h in enumerate(hallazgos, start=1):
        aviso = f"  ⚠ posible duplicado de {h.duplicado_de}" if h.duplicado_de else ""
        print(f"  {n:>2}. [{h.severidad}] {h.titulo_issue()}{aviso}")
        print(f"      {h.ubicacion}")
    por_defecto = [n for n, h in enumerate(hallazgos, start=1) if not h.duplicado_de]
    destino = f" y al Project {github_project}" if github_project else ""
    print(f"\nPor defecto: {', '.join(map(str, por_defecto)) or 'ninguno'} (los posibles duplicados quedan fuera).")
    while True:
        texto = seleccion if seleccion is not None else entrada(
            "¿Cuáles creo? [Enter] por defecto · todos · ninguno · 1,3 · 2-4: ")
        try:
            elegidos = issues.parsear_seleccion(texto, len(hallazgos), por_defecto)
            break
        except ValueError as exc:
            if seleccion is not None:
                raise SystemExit(f"Selección inválida: {exc}")
            print(exc)
    if not elegidos:
        print("No se crea ninguna issue.")
        return 0
    if seleccion is None:
        confirmar = entrada(f"Se crearán {len(elegidos)} issues en {repo}{destino}. ¿Confirmas? [s/n]: ").strip().lower()
        if confirmar != "s":
            print("Cancelado. No se creó nada.")
            return 0

    creadas = issues.crear([hallazgos[n - 1] for n in elegidos], repo, commit, gh, github_project)
    registro = salida / "issues_creadas.json"
    anteriores = json.loads(registro.read_text(encoding="utf-8")) if registro.exists() else []
    registro.write_text(json.dumps(anteriores + creadas, ensure_ascii=False, indent=2), encoding="utf-8")
    for c in creadas:
        print(f"  ✓ {c['id']} → {c['url']}{' (en el Project)' if c['en_project'] else ''}")
        if c.get("error_project"):
            print(f"    ⚠ No se pudo agregar al Project: {c['error_project']}")
            print("      Ejecuta `gh auth refresh -s project` y agrégala desde el Project.")
    print(f"Registro en {registro}")
    return 0


def issues_automaticas(proyecto: Proyecto, resumen: dict, args, gh: issues.Gh = issues.gh_real) -> None:
    """Crea las issues al final del flujo, sin preguntas. No cambia el resultado de la validación."""
    if args.solo_evidencia or resumen["modelo"] == "simulado":
        print("Issues automáticas: no aplica sin revisión de un modelo.")
        return
    if resumen["detenido_en"]:
        print("Issues automáticas: el flujo se detuvo por decisión humana; no se crea nada.")
        return
    severidades = [s.strip().upper() for s in args.severidades.split(",") if s.strip()]
    print("\n" + "═" * 72)
    print(f"Issues automáticas ({'/'.join(severidades)}, sin posibles duplicados):")
    try:
        crear_issues(proyecto, Path(args.salida), severidades, args.github_project, "", gh=gh)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"No se pudieron crear las issues: {exc}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Validación SDD con agentes por rol (CrewAI).")
    p.add_argument("--proyecto", default=str(RAIZ / "proyectos" / "wallet-onboarding.yaml"),
                   help="YAML del proyecto a validar")
    p.add_argument("--repo", help="Ruta del repositorio a validar (reemplaza la del YAML)")
    p.add_argument("--roles", help="Roles separados por coma (por defecto, los seis)")
    p.add_argument("--salida", default=str(RAIZ / "output"), help="Carpeta de informes")
    p.add_argument("--auto", action="store_true", help="Aprobar cada informe sin preguntar")
    p.add_argument("--reiniciar", action="store_true", help="Ignorar el checkpoint")
    p.add_argument("--solo-evidencia", action="store_true", help="Solo verificaciones deterministas, sin agentes")
    p.add_argument("--crear-issues", action="store_true",
                   help="Crear issues de GitHub con los hallazgos de los informes aprobados (no ejecuta agentes)")
    p.add_argument("--severidades", default="ALTA,MEDIA", help="Severidades para --crear-issues (ALTA,MEDIA,BAJA)")
    p.add_argument("--github-project", type=int, help="Número del GitHub Project donde agregar las issues")
    p.add_argument("--seleccion", help="Selección sin preguntar para --crear-issues: todos, ninguno, 1,3 o 2-4")
    p.add_argument("--issues-auto", action="store_true",
                   help="Al terminar la validación, crear sin preguntar las issues de los hallazgos aprobados "
                        "(excluye posibles duplicados)")
    args = p.parse_args(argv)

    try:
        proyecto = Proyecto.desde_yaml(args.proyecto, args.repo)
        roles = elegir_roles(args.roles)
        modelo = "ninguno" if args.solo_evidencia else llm.nombre_modelo()
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.crear_issues:
        severidades = [s.strip().upper() for s in args.severidades.split(",") if s.strip()]
        try:
            return crear_issues(proyecto, Path(args.salida), severidades, args.github_project, args.seleccion)
        except (FileNotFoundError, RuntimeError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2

    print(f"Validación SDD · {proyecto.nombre}")
    print(f"Repo: {proyecto.repo} · Spec: {proyecto.spec} · {len(proyecto.ids_spec)} IDs")
    if not args.solo_evidencia:
        print(f"Modelo: {modelo} · Roles: {' → '.join(r.nombre for r in roles)}")

    aprobar = (lambda *_: ("s", "")) if args.auto else aprobar_en_consola
    resumen = ejecutar_flujo(proyecto, roles, ejecutor.ejecutar, aprobar, Path(args.salida), modelo,
                             reiniciar=args.reiniciar, solo_evidencia=args.solo_evidencia)

    print("\n" + "═" * 72)
    print(f"RESULTADO: {resumen['resultado']} — {resumen['motivo']}")
    print(f"Informes en {Path(args.salida).resolve()} (empieza por resumen.md)")
    if args.issues_auto:
        issues_automaticas(proyecto, resumen, args)
    if args.solo_evidencia:
        return 0 if resumen["evidencia_ok"] is not False else 1
    return 0 if resumen["resultado"] == "APROBADO" else 1


if __name__ == "__main__":
    sys.exit(main())

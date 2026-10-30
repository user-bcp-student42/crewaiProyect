"""Convierte los hallazgos de los informes APROBADOS en issues de GitHub (con `gh`).

Nada se crea sin confirmación humana. Para no duplicar:
  - cada issue lleva una marca oculta con el commit validado y el ID del hallazgo;
  - si ya existe una issue abierta con el mismo ID de spec y el mismo archivo, se marca
    como posible duplicado y queda fuera de la selección por defecto.
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from sdd_crew.formato import seccion_hallazgos
from sdd_crew.roles import POR_CLAVE

ETIQUETA_BASE = "hallazgo"
COLORES = {"hallazgo": "5319e7", "ALTA": "b60205", "MEDIA": "fbca04", "BAJA": "c2e0c6", "rol": "0e8a16"}
MARCA_RE = re.compile(r"<!-- sdd-hallazgo: (\S+) commit: (\S+) -->")

# gh(args) -> stdout. Se inyecta para poder probar sin GitHub.
Gh = Callable[[list[str]], str]


@dataclass
class Hallazgo:
    id: str
    rol: str
    severidad: str
    spec: str
    titulo: str
    ubicacion: str
    evidencia: str
    correccion: str
    verificacion: str
    duplicado_de: str | None = None

    @property
    def archivo(self) -> str:
        return re.sub(r"[`\s]", "", self.ubicacion).split(":")[0]

    @property
    def etiquetas(self) -> list[str]:
        return [ETIQUETA_BASE, f"sdd:{self.rol}", f"severidad:{self.severidad.lower()}"]

    def marca(self, commit: str | None) -> str:
        return f"<!-- sdd-hallazgo: {self.id} commit: {commit or 'desconocido'} -->"

    def titulo_issue(self) -> str:
        spec = f" {self.spec}" if self.spec and self.spec != "—" else ""
        titulo = f"[{self.id}]{spec} · {self.titulo}"
        return titulo if len(titulo) <= 120 else titulo[:117] + "..."

    def cuerpo_issue(self, commit: str | None, informe: str) -> str:
        return f"""## Hallazgo de la validación SDD

| Campo | Valor |
|---|---|
| ID | `{self.id}` |
| Rol | {POR_CLAVE[self.rol].nombre} |
| Severidad | **{self.severidad}** |
| Spec | {self.spec} |
| Ubicación | {self.ubicacion} |
| Commit validado | `{commit or 'desconocido'}` |

**Problema:** {self.titulo}

**Evidencia:** {self.evidencia}

## Corrección propuesta

{self.correccion}

## Cómo verificar la corrección

{self.verificacion}

## Para cerrar esta issue

- [ ] La corrección está aplicada y revisada por otro integrante.
- [ ] La verificación anterior se ejecutó y su salida está en un comentario.
- [ ] Si cambia el comportamiento, la spec se actualizó primero.
- [ ] Una nueva ejecución de `python validar.py` ya no reporta el hallazgo.

---
Generado por `crew-validacion-sdd` desde `{informe}`. El informe fue aprobado por una persona y esta
issue se creó con su confirmación. Un hallazgo de un modelo puede estar equivocado: valídalo antes de corregir.
{self.marca(commit)}
"""


def _celdas(linea: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<!\\)\|", linea.strip().strip("|"))]


def extraer(informe: str, rol: str) -> list[Hallazgo]:
    """Filas `| H-XX-n | ... |` de la sección "3. Hallazgos" (8 columnas del formato común)."""
    hallazgos = []
    for linea in seccion_hallazgos(informe).splitlines():
        if not re.match(r"^\|\s*H-[A-Z]+-\d+\s*\|", linea):
            continue
        c = _celdas(linea)
        if len(c) < 8:
            c += [""] * (8 - len(c))
        id_, severidad, spec, titulo, ubicacion, evidencia, correccion, verificacion = c[:8]
        severidad = severidad.strip("* ").upper()
        if severidad not in ("ALTA", "MEDIA", "BAJA"):
            continue
        hallazgos.append(Hallazgo(id_, rol, severidad, spec, titulo or correccion[:80], ubicacion,
                                  evidencia, correccion, verificacion))
    return hallazgos


def desde_checkpoint(salida: Path) -> tuple[str | None, list[Hallazgo]]:
    """Hallazgos de los informes aprobados. Sin checkpoint no hay nada aprobado."""
    ruta = salida / ".checkpoint.json"
    if not ruta.exists():
        raise FileNotFoundError(f"No hay informes aprobados en {salida}. Ejecuta primero: python validar.py")
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    hallazgos = [h for clave in POR_CLAVE if clave in datos.get("aprobados", {})
                 for h in extraer(datos["aprobados"][clave], clave)]
    return datos.get("commit"), hallazgos


def gh_real(args: list[str]) -> str:
    try:
        r = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError as exc:
        raise RuntimeError("No encuentro `gh`. Instala GitHub CLI: https://cli.github.com") from exc
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])} falló: {(r.stderr or r.stdout).strip()}")
    return r.stdout


def repo_github(repo_local: Path, configurado: str | None) -> str:
    """owner/repo: el del YAML (`github:`) o el del remoto `origin` del repo validado."""
    if configurado:
        return configurado
    r = subprocess.run(["git", "remote", "get-url", "origin"], cwd=repo_local, capture_output=True, text=True)
    m = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?/?$", r.stdout.strip())
    if not m:
        raise RuntimeError("No pude deducir el repo de GitHub. Agrega `github: owner/repo` al YAML del proyecto.")
    return m.group(1)


def marcar_existentes(hallazgos: list[Hallazgo], repo: str, commit: str | None, gh: Gh) -> list[Hallazgo]:
    """Quita los ya creados (misma marca) y marca posibles duplicados (mismo ID de spec y archivo)."""
    salida = gh(["issue", "list", "--repo", repo, "--label", ETIQUETA_BASE, "--state", "open",
                 "--json", "number,title,body", "--limit", "200"])
    abiertas = json.loads(salida or "[]")
    pendientes = []
    for h in hallazgos:
        if any(h.marca(commit) in (i.get("body") or "") for i in abiertas):
            continue
        for i in abiertas:
            cuerpo = i.get("body") or ""
            if h.spec not in ("", "—") and f"| Spec | {h.spec} |" in cuerpo and h.archivo and h.archivo in cuerpo:
                h.duplicado_de = f"#{i['number']}"
                break
        pendientes.append(h)
    return pendientes


def crear(hallazgos: list[Hallazgo], repo: str, commit: str | None, gh: Gh,
          proyecto_github: int | None = None, owner: str | None = None) -> list[dict]:
    etiquetas = {e for h in hallazgos for e in h.etiquetas}
    for e in sorted(etiquetas):
        color = COLORES.get(e.split(":")[-1].upper(), COLORES["rol"] if e.startswith("sdd:") else COLORES["hallazgo"])
        gh(["label", "create", e, "--repo", repo, "--color", color, "--force",
            "--description", "Hallazgo de la validación SDD"])
    creadas = []
    for h in hallazgos:
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write(h.cuerpo_issue(commit, POR_CLAVE[h.rol].informe))
            cuerpo = f.name
        try:
            args = ["issue", "create", "--repo", repo, "--title", h.titulo_issue(), "--body-file", cuerpo]
            for e in h.etiquetas:
                args += ["--label", e]
            url = gh(args).strip().splitlines()[-1]
        finally:
            Path(cuerpo).unlink(missing_ok=True)
        registro = {**asdict(h), "url": url, "en_project": False}
        if proyecto_github:
            try:
                gh(["project", "item-add", str(proyecto_github), "--owner", owner or repo.split("/")[0], "--url", url])
                registro["en_project"] = True
            except RuntimeError as exc:
                # La issue ya existe: se registra igual y se avisa (suele faltar `gh auth refresh -s project`).
                registro["error_project"] = str(exc)
        creadas.append(registro)
    return creadas


def parsear_seleccion(texto: str, total: int, por_defecto: list[int]) -> list[int]:
    """'' → por defecto · 'todos' · 'ninguno' · '1,3,5' · '2-4'. Índices base 1."""
    t = texto.strip().lower()
    if t == "":
        return por_defecto
    if t in ("todos", "todo", "all"):
        return list(range(1, total + 1))
    if t in ("ninguno", "no", "n"):
        return []
    elegidos: set[int] = set()
    for parte in t.replace(" ", "").split(","):
        if "-" in parte:
            a, b = parte.split("-", 1)
            elegidos.update(range(int(a), int(b) + 1))
        elif parte:
            elegidos.add(int(parte))
    fuera = [n for n in elegidos if not 1 <= n <= total]
    if fuera:
        raise ValueError(f"Fuera de rango: {fuera}. Elige entre 1 y {total}.")
    return sorted(elegidos)

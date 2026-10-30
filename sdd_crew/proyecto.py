"""Carga del proyecto a validar: spec, plan, contrato y archivos por rol."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ID_RE = re.compile(r"\b(?:CA|RN|RS|RNF)-\d+\b")


@dataclass
class Proyecto:
    nombre: str
    repo: Path
    spec: str
    plan: str | None
    contrato: str | None
    evidencia: list[dict]
    archivos: dict[str, list[str]]
    limite_caracteres: int = 120_000
    github: str | None = None   # owner/repo; si falta, se deduce del remoto origin
    ids_spec: list[str] = field(default_factory=list)

    @classmethod
    def desde_yaml(cls, ruta: str | Path, repo: str | Path | None = None) -> "Proyecto":
        ruta = Path(ruta).resolve()
        datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
        base = Path(repo) if repo else (ruta.parent.parent / datos["repo"])
        proyecto = cls(
            nombre=datos["nombre"],
            repo=base.resolve(),
            spec=datos["spec"],
            plan=datos.get("plan"),
            contrato=datos.get("contrato"),
            evidencia=datos.get("evidencia", []),
            archivos=datos.get("archivos", {}),
            limite_caracteres=int(datos.get("limite_caracteres", 120_000)),
            github=datos.get("github"),
        )
        proyecto.validar()
        proyecto.ids_spec = ids_de_spec(proyecto.leer(proyecto.spec))
        return proyecto

    def validar(self) -> None:
        if not self.repo.is_dir():
            raise FileNotFoundError(
                f"No encuentro el repositorio a validar en {self.repo}. "
                "Clónalo ahí o indica otra ruta con --repo.")
        for nombre in filter(None, (self.spec, self.plan, self.contrato)):
            if not (self.repo / nombre).is_file():
                raise FileNotFoundError(f"Falta {nombre} en {self.repo}")

    def leer(self, relativa: str) -> str:
        return (self.repo / relativa).read_text(encoding="utf-8")

    def resolver(self, patrones: list[str]) -> list[str]:
        """Rutas relativas que cumplen los patrones, sin duplicados y en orden estable."""
        vistas: list[str] = []
        for patron in patrones:
            for ruta in sorted(self.repo.glob(patron)):
                rel = ruta.relative_to(self.repo).as_posix()
                if ruta.is_file() and rel not in vistas:
                    vistas.append(rel)
        return vistas

    def commit(self) -> str | None:
        try:
            r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.repo, capture_output=True, text=True, check=True)
            return r.stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return None

    def python(self) -> str:
        """Intérprete del entorno virtual del repo si existe; si no, el actual."""
        for candidato in (".venv/bin/python", ".venv/Scripts/python.exe", "venv/bin/python", "venv/Scripts/python.exe"):
            if (self.repo / candidato).is_file():
                return str(self.repo / candidato)
        return sys.executable


def ids_de_spec(texto: str) -> list[str]:
    """IDs definidos en la spec: encabezados `### CA-n` y primeras columnas `| RN-n |`."""
    ids = re.findall(r"^###\s+(CA-\d+)\b", texto, re.MULTILINE)
    ids += re.findall(r"^\|\s*((?:RN|RS|RNF)-\d+)\s*\|", texto, re.MULTILINE)
    vistos: list[str] = []
    for i in ids:
        if i not in vistos:
            vistos.append(i)
    return vistos


def con_numeros_de_linea(texto: str) -> str:
    """Numera las líneas para que los agentes citen `archivo:línea`."""
    lineas = texto.splitlines()
    ancho = len(str(len(lineas)))
    return "\n".join(f"{n:>{ancho}} | {linea}" for n, linea in enumerate(lineas, start=1))


def bloque_archivo(ruta: str, contenido: str) -> str:
    lenguaje = {".py": "python", ".js": "javascript", ".html": "html", ".css": "css",
                ".yaml": "yaml", ".yml": "yaml", ".md": "markdown"}.get(os.path.splitext(ruta)[1], "")
    return f"### Archivo: {ruta}\n```{lenguaje}\n{con_numeros_de_linea(contenido)}\n```"

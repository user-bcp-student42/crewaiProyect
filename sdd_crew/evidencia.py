"""Verificaciones deterministas: se ejecutan de verdad y su salida es la evidencia."""
from __future__ import annotations

import os
import subprocess
import time
from dataclasses import asdict, dataclass

from sdd_crew.proyecto import Proyecto

MAX_SALIDA = 6_000


@dataclass
class Resultado:
    nombre: str
    comando: str
    codigo_salida: int
    duracion_s: float
    salida: str

    @property
    def ok(self) -> bool:
        return self.codigo_salida == 0

    def a_dict(self) -> dict:
        return {**asdict(self), "ok": self.ok}


def entorno_utf8() -> dict[str, str]:
    """Fuerza UTF-8 en los procesos hijos: en Windows, la salida capturada usaría cp1252 y
    cualquier carácter como → o ✓ haría fallar el comando."""
    return {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


def ejecutar(proyecto: Proyecto, timeout: int = 600) -> list[Resultado]:
    python = proyecto.python()
    resultados = []
    for paso in proyecto.evidencia:
        comando = [python if parte == "python" else parte for parte in paso["comando"]]
        visible = " ".join(paso["comando"])
        inicio = time.monotonic()
        try:
            r = subprocess.run(comando, cwd=proyecto.repo, capture_output=True, text=True,
                               timeout=timeout, encoding="utf-8", errors="replace", env=entorno_utf8())
            codigo, salida = r.returncode, (r.stdout + r.stderr)
        except FileNotFoundError as exc:
            codigo, salida = 127, f"No se pudo ejecutar: {exc}"
        except subprocess.TimeoutExpired:
            codigo, salida = 124, f"Se superó el tiempo límite de {timeout} s"
        if len(salida) > MAX_SALIDA:
            salida = "[... salida recortada al final ...]\n" + salida[-MAX_SALIDA:]
        resultados.append(Resultado(paso["nombre"], visible, codigo, round(time.monotonic() - inicio, 2), salida.strip()))
    return resultados


def todo_ok(resultados: list[Resultado]) -> bool:
    return bool(resultados) and all(r.ok for r in resultados)


def como_markdown(resultados: list[Resultado], commit: str | None) -> str:
    if not resultados:
        return "No se configuraron verificaciones deterministas. No hay evidencia ejecutada."
    lineas = [f"Ejecutado por la herramienta (no por el modelo) sobre el commit `{commit or 'desconocido'}`.", ""]
    lineas += ["| Verificación | Comando | Resultado |", "|---|---|---|"]
    lineas += [f"| {r.nombre} | `{r.comando}` | {'PASÓ' if r.ok else f'FALLÓ (código {r.codigo_salida})'} |"
               for r in resultados]
    for r in resultados:
        lineas += ["", f"#### Salida real: {r.nombre}", "```text", r.salida or "(sin salida)", "```"]
    return "\n".join(lineas)

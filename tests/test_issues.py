"""Creación de issues a partir de hallazgos aprobados, con un `gh` falso."""
import json

import pytest

import validar
from sdd_crew import issues
from sdd_crew.proyecto import Proyecto
from tests.conftest import escribir_proyecto

INFORME_SEC = """# Informe de Security
## 1. Resumen
Texto.
## 3. Hallazgos
| ID | Severidad | Spec | Hallazgo | Ubicación | Evidencia | Corrección propuesta | Cómo verificar la corrección |
|---|---|---|---|---|---|---|---|
| H-SEC-1 | ALTA | RS-6 | Cualquiera con el id lee un registro ajeno | `app/main.py:12` | `def obtener(id)` | Ligar a sesión | Prueba con id ajeno → 403 |
| H-SEC-2 | **MEDIA** | RS-7 | Sin límite de intentos de OTP | `app/domain.py:40` | `otp != OTP` | Bloquear tras 5 | Prueba de 6 intentos |
| H-SEC-3 | BAJA | — | Falta cabecera CSP | `app/main.py:1` | — | Agregar CSP | curl -I |
## 4. Límites de esta revisión
Nada.
VEREDICTO: NO CUMPLE
"""

INFORME_CHAPTER = """# Informe de Chapter
## 3. Hallazgos
| ID | Severidad | Spec | Hallazgo | Ubicación | Evidencia | Corrección propuesta | Cómo verificar la corrección |
|---|---|---|---|---|---|---|---|
| H-CH-1 | MEDIA | CA-2 | Testing y Backend se contradicen en RN-3 | `tests/test_ca2.py:30` | cita | Agregar caso límite | pytest -k edad |
## Hallazgos consolidados de otros roles
| H-SEC-1 | Security | ALTA | Sí | Backend |
## 4. Límites de esta revisión
VEREDICTO: RECHAZADO
"""


def test_extrae_solo_la_tabla_de_hallazgos_con_sus_8_columnas():
    hs = issues.extraer(INFORME_SEC, "security")
    assert [(h.id, h.severidad, h.spec) for h in hs] == [("H-SEC-1", "ALTA", "RS-6"), ("H-SEC-2", "MEDIA", "RS-7"),
                                                         ("H-SEC-3", "BAJA", "—")]
    assert hs[0].titulo == "Cualquiera con el id lee un registro ajeno"
    assert hs[0].archivo == "app/main.py"
    assert hs[0].etiquetas == ["hallazgo", "sdd:security", "severidad:alta"]


def test_el_chapter_no_duplica_los_hallazgos_que_consolida():
    assert [h.id for h in issues.extraer(INFORME_CHAPTER, "chapter")] == ["H-CH-1"]


def test_cuerpo_de_issue_trazable_y_con_marca():
    h = issues.extraer(INFORME_SEC, "security")[0]
    cuerpo = h.cuerpo_issue("abc123", "security_review.md")
    assert "| Spec | RS-6 |" in cuerpo and "`app/main.py:12`" in cuerpo and "Prueba con id ajeno" in cuerpo
    assert "<!-- sdd-hallazgo: H-SEC-1 commit: abc123 -->" in cuerpo
    assert h.titulo_issue() == "[H-SEC-1] RS-6 · Cualquiera con el id lee un registro ajeno"


@pytest.mark.parametrize("texto,esperado", [
    ("", [1, 3]), ("todos", [1, 2, 3]), ("ninguno", []), ("1,3", [1, 3]), ("2-3", [2, 3]),
])
def test_seleccion(texto, esperado):
    assert issues.parsear_seleccion(texto, 3, [1, 3]) == esperado


def test_seleccion_fuera_de_rango():
    with pytest.raises(ValueError):
        issues.parsear_seleccion("4", 3, [])


def respuestas(*textos):
    it = iter(textos)
    return lambda _pregunta="": next(it)


class GhFalso:
    def __init__(self, abiertas=None, falla_project=False):
        self.llamadas = []
        self.abiertas = abiertas or []
        self.falla_project = falla_project
        self.n = 100

    def __call__(self, args):
        self.llamadas.append(args)
        if args[:2] == ["issue", "list"]:
            return json.dumps(self.abiertas)
        if args[:2] == ["issue", "create"]:
            self.n += 1
            cuerpo = open(args[args.index("--body-file") + 1], encoding="utf-8").read()
            self.abiertas.append({"number": self.n, "title": args[args.index("--title") + 1], "body": cuerpo})
            return f"https://github.com/o/r/issues/{self.n}\n"
        if args[:2] == ["project", "item-add"] and self.falla_project:
            raise RuntimeError("missing scope project")
        return ""

    def de_tipo(self, *prefijo):
        return [a for a in self.llamadas if a[:len(prefijo)] == list(prefijo)]


def preparar(tmp_path, repo, informes):
    proyecto = Proyecto.desde_yaml(escribir_proyecto(tmp_path, repo))
    proyecto.github = "o/r"
    salida = tmp_path / "out"
    salida.mkdir()
    (salida / ".checkpoint.json").write_text(json.dumps({"commit": None, "aprobados": informes}), encoding="utf-8")
    return proyecto, salida


def test_crea_alta_y_media_con_etiquetas_y_registro(tmp_path, repo):
    proyecto, salida = preparar(tmp_path, repo, {"security": INFORME_SEC, "chapter": INFORME_CHAPTER})
    gh = GhFalso()
    codigo = validar.crear_issues(proyecto, salida, ["ALTA", "MEDIA"], None, None, gh=gh,
                                  entrada=respuestas("", "s"))
    assert codigo == 0
    titulos = [a[a.index("--title") + 1] for a in gh.de_tipo("issue", "create")]
    assert [t.split("]")[0] for t in titulos] == ["[H-SEC-1", "[H-SEC-2", "[H-CH-1"]
    assert {a[2] for a in gh.de_tipo("label", "create")} >= {"hallazgo", "sdd:security", "severidad:alta"}
    registro = json.loads((salida / "issues_creadas.json").read_text(encoding="utf-8"))
    assert [r["id"] for r in registro] == ["H-SEC-1", "H-SEC-2", "H-CH-1"]


def test_sin_confirmacion_no_se_crea_nada(tmp_path, repo):
    proyecto, salida = preparar(tmp_path, repo, {"security": INFORME_SEC})
    gh = GhFalso()
    validar.crear_issues(proyecto, salida, ["ALTA"], None, None, gh=gh, entrada=respuestas("", "n"))
    assert gh.de_tipo("issue", "create") == []


def test_no_repite_issues_ya_creadas_y_avisa_posibles_duplicados(tmp_path, repo):
    proyecto, salida = preparar(tmp_path, repo, {"security": INFORME_SEC})
    gh = GhFalso()
    validar.crear_issues(proyecto, salida, ["ALTA"], None, "todos", gh=gh)
    assert len(gh.de_tipo("issue", "create")) == 1

    # Segunda vez con los mismos informes: ya existe la marca, no se crea nada.
    validar.crear_issues(proyecto, salida, ["ALTA"], None, "todos", gh=gh)
    assert len(gh.de_tipo("issue", "create")) == 1

    # Otra ejecución (otro commit) con el mismo problema: posible duplicado, fuera por defecto.
    hs = issues.marcar_existentes(issues.extraer(INFORME_SEC, "security")[:1], "o/r", "otro-commit", gh)
    assert hs[0].duplicado_de == "#101"


def test_agrega_al_project_y_tolera_falta_de_permiso(tmp_path, repo):
    proyecto, salida = preparar(tmp_path, repo, {"security": INFORME_SEC})
    gh = GhFalso(falla_project=True)
    validar.crear_issues(proyecto, salida, ["ALTA"], 2, "todos", gh=gh)
    assert gh.de_tipo("project", "item-add")[0][:3] == ["project", "item-add", "2"]
    registro = json.loads((salida / "issues_creadas.json").read_text(encoding="utf-8"))
    assert registro[0]["en_project"] is False and "scope" in registro[0]["error_project"]


def test_sin_informes_aprobados_avisa(tmp_path, repo):
    proyecto = Proyecto.desde_yaml(escribir_proyecto(tmp_path, repo))
    with pytest.raises(FileNotFoundError, match="No hay informes aprobados"):
        validar.crear_issues(proyecto, tmp_path / "vacio", ["ALTA"], None, None, gh=GhFalso())


def test_repo_github_desde_el_remoto(tmp_path):
    import subprocess
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "remote", "add", "origin", "https://github.com/ana/mi-repo.git"], check=True)
    assert issues.repo_github(tmp_path, None) == "ana/mi-repo"
    assert issues.repo_github(tmp_path, "x/y") == "x/y"


def test_issues_auto_al_final_del_flujo_sin_preguntar(tmp_path, repo, monkeypatch):
    import argparse
    proyecto, salida = preparar(tmp_path, repo, {"security": INFORME_SEC})
    monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("no debe preguntar"))
    gh = GhFalso()
    args = argparse.Namespace(solo_evidencia=False, severidades="ALTA,MEDIA", github_project=None, salida=str(salida))
    validar.issues_automaticas(proyecto, {"modelo": "copilot:x", "detenido_en": None}, args, gh=gh)
    assert [a[a.index("--title") + 1][:9] for a in gh.de_tipo("issue", "create")] == ["[H-SEC-1]", "[H-SEC-2]"]


def test_issues_auto_no_crea_si_el_flujo_se_detuvo_o_es_simulado(tmp_path, repo):
    import argparse
    proyecto, salida = preparar(tmp_path, repo, {"security": INFORME_SEC})
    gh = GhFalso()
    args = argparse.Namespace(solo_evidencia=False, severidades="ALTA", github_project=None, salida=str(salida))
    validar.issues_automaticas(proyecto, {"modelo": "copilot:x", "detenido_en": "backend"}, args, gh=gh)
    validar.issues_automaticas(proyecto, {"modelo": "simulado", "detenido_en": None}, args, gh=gh)
    assert gh.llamadas == []

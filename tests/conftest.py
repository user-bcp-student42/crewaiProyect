import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SPEC = textwrap.dedent("""\
    # SPEC de prueba
    ### CA-1 · Paso visible
    Texto.
    ### CA-2 · Errores
    Texto.
    | ID | Regla |
    |---|---|
    | RN-1 | El DNI tiene 8 dígitos. |
    | RS-1 | Sin datos personales en eventos. |
    | RNF-1 | Funciona en celular. |
    """)


@pytest.fixture
def repo(tmp_path):
    """Repositorio objetivo mínimo con spec, código, pruebas y un YAML de proyecto."""
    r = tmp_path / "objetivo"
    (r / "specs").mkdir(parents=True)
    (r / "app").mkdir()
    (r / "tests").mkdir()
    (r / "specs" / "spec.md").write_text(SPEC, encoding="utf-8")
    (r / "specs" / "plan.md").write_text("# Plan\nDEC-1", encoding="utf-8")
    (r / "specs" / "openapi.yaml").write_text("paths: {}\n", encoding="utf-8")
    (r / "app" / "main.py").write_text("def validar(dni):\n    return len(dni) == 8\n", encoding="utf-8")
    (r / "tests" / "test_x.py").write_text('"""CA-1."""\ndef test_a():\n    assert True\n', encoding="utf-8")
    return r


def escribir_proyecto(tmp_path, repo, evidencia_ok=True):
    codigo = 0 if evidencia_ok else 1
    yaml_txt = textwrap.dedent(f"""\
        nombre: Proyecto de prueba
        repo: {repo}
        spec: specs/spec.md
        plan: specs/plan.md
        contrato: specs/openapi.yaml
        evidencia:
          - nombre: Verificación
            comando: [python, -c, "import sys; print('salida real'); sys.exit({codigo})"]
        archivos:
          backend: [app/*.py]
          testing: [tests/*.py]
        limite_caracteres: 50000
        """)
    ruta = tmp_path / "proyecto.yaml"
    ruta.write_text(yaml_txt, encoding="utf-8")
    return ruta

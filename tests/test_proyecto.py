from sdd_crew.proyecto import Proyecto, con_numeros_de_linea, ids_de_spec
from tests.conftest import SPEC, escribir_proyecto

import pytest


def test_ids_de_spec_lee_encabezados_y_tablas():
    assert ids_de_spec(SPEC) == ["CA-1", "CA-2", "RN-1", "RS-1", "RNF-1"]


def test_carga_proyecto_y_resuelve_archivos(tmp_path, repo):
    p = Proyecto.desde_yaml(escribir_proyecto(tmp_path, repo))
    assert p.ids_spec[:2] == ["CA-1", "CA-2"]
    assert p.resolver(["app/*.py", "app/main.py"]) == ["app/main.py"]


def test_falla_con_mensaje_claro_si_no_existe_el_repo(tmp_path, repo):
    with pytest.raises(FileNotFoundError, match="No encuentro el repositorio"):
        Proyecto.desde_yaml(escribir_proyecto(tmp_path, repo), repo=tmp_path / "no-existe")


def test_numeros_de_linea_para_citar_ubicaciones():
    assert con_numeros_de_linea("a\nb") == "1 | a\n2 | b"


def test_proyecto_real_de_la_wallet_esta_bien_configurado():
    from pathlib import Path
    import yaml
    datos = yaml.safe_load((Path(__file__).parent.parent / "proyectos" / "wallet-onboarding.yaml").read_text(encoding="utf-8"))
    assert set(datos["archivos"]) == {"architect", "backend", "frontend", "testing", "security", "chapter"}
    assert all(paso["comando"][0] == "python" for paso in datos["evidencia"])

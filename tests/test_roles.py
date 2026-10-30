from sdd_crew.formato import hallazgos_por_severidad, veredicto
from sdd_crew.roles import POR_CLAVE, ROLES
from sdd_crew.roles.base import construir_prompt

PAQUETE = {
    "proyecto": "P", "commit": "abc123", "ids_spec": ["CA-1", "RN-1", "RS-1", "RNF-1"],
    "spec": "SPEC-TEXTO", "plan": "PLAN-TEXTO", "contrato": "CONTRATO-TEXTO",
    "archivos": "ARCHIVOS-TEXTO", "evidencia": "EVIDENCIA-TEXTO",
    "informes": {"Backend": "INFORME-BACKEND"},
}


def test_los_seis_roles_en_orden():
    assert [r.clave for r in ROLES] == ["architect", "backend", "frontend", "testing", "security", "chapter"]
    assert len({r.prefijo for r in ROLES}) == 6
    assert len({r.informe for r in ROLES}) == 6


def test_cada_rol_recibe_solo_su_material():
    arq = construir_prompt(POR_CLAVE["architect"], PAQUETE)
    assert "PLAN-TEXTO" in arq and "CONTRATO-TEXTO" in arq and "EVIDENCIA-TEXTO" not in arq

    qa = construir_prompt(POR_CLAVE["testing"], PAQUETE)
    assert "EVIDENCIA-TEXTO" in qa and "PLAN-TEXTO" not in qa

    ch = construir_prompt(POR_CLAVE["chapter"], PAQUETE)
    assert "INFORME-BACKEND" in ch and "EVIDENCIA-TEXTO" in ch
    assert "INFORME-BACKEND" not in construir_prompt(POR_CLAVE["backend"], PAQUETE)


def test_el_prompt_exige_formato_honestidad_y_cubre_los_ids_del_rol():
    sec = construir_prompt(POR_CLAVE["security"], PAQUETE)
    assert "H-SEC-1" in sec
    assert "RS-1" in sec.split("# MATERIAL")[0]
    assert "No inventes" in sec
    assert "VEREDICTO: CUMPLE" in sec
    assert "VEREDICTO: APROBADO" in construir_prompt(POR_CLAVE["chapter"], PAQUETE)


def test_el_feedback_humano_llega_al_reintento():
    p = construir_prompt(POR_CLAVE["backend"], {**PAQUETE, "feedback": "Cita líneas", "informe_anterior": "VIEJO"})
    assert "FEEDBACK HUMANO" in p and "Cita líneas" in p and "VIEJO" in p


def test_lectura_de_veredicto_y_hallazgos():
    informe = """
| ID | Severidad | Spec |
|---|---|---|
| H-BE-1 | ALTA | RN-1 |
| H-BE-2 | **MEDIA** | CA-1 |
| H-BE-3 | baja | — |
VEREDICTO: **NO CUMPLE**
"""
    assert veredicto(informe) == "NO CUMPLE"
    assert hallazgos_por_severidad(informe) == {"ALTA": 1, "MEDIA": 1, "BAJA": 1}
    assert veredicto("sin línea") is None
    assert veredicto("VEREDICTO: CUMPLE\n...\nVEREDICTO: APROBADO") == "APROBADO"


def test_el_formato_pide_titulo_de_hallazgo_y_el_chapter_consolida_aparte():
    be = construir_prompt(POR_CLAVE["backend"], PAQUETE)
    assert "| ID | Severidad | Spec | Hallazgo | Ubicación |" in be
    assert "Hallazgos consolidados" not in be
    ch = construir_prompt(POR_CLAVE["chapter"], PAQUETE)
    assert "## Hallazgos consolidados de otros roles" in ch and "## Matriz final" in ch

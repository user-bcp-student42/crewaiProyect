import json

from sdd_crew.flujo import ejecutar_flujo, resultado_final
from sdd_crew.proyecto import Proyecto
from sdd_crew.roles import ROLES
from tests.conftest import escribir_proyecto


def informe(rol, veredicto):
    return f"# Informe de {rol.nombre}\n| H-{rol.prefijo}-1 | MEDIA | CA-1 |\nVEREDICTO: {veredicto}\n"


def runner_fijo(chapter="APROBADO"):
    llamadas = []

    def run(rol, prompt, ids):
        llamadas.append((rol.clave, prompt))
        return informe(rol, chapter if rol.es_chapter else "CUMPLE")
    return run, llamadas


def aprobar_todo(*_):
    return "s", ""


def correr(tmp_path, repo, runner, aprobar=aprobar_todo, evidencia_ok=True, **kw):
    proyecto = Proyecto.desde_yaml(escribir_proyecto(tmp_path, repo, evidencia_ok))
    return ejecutar_flujo(proyecto, ROLES, runner, aprobar, tmp_path / "out", "copilot:test", log=lambda *_: None, **kw)


def test_flujo_completo_aprobado_con_evidencia_en_verde(tmp_path, repo):
    run, llamadas = runner_fijo()
    r = correr(tmp_path, repo, run)
    assert [c for c, _ in llamadas] == [x.clave for x in ROLES]
    assert r["resultado"] == "APROBADO"
    out = tmp_path / "out"
    for rol in ROLES:
        assert (out / rol.informe).exists()
    assert "salida real" in (out / "evidencia.md").read_text(encoding="utf-8")
    assert json.loads((out / "resumen.json").read_text(encoding="utf-8"))["roles"][1]["hallazgos"]["MEDIA"] == 1


def test_evidencia_fallida_rechaza_aunque_el_chapter_apruebe(tmp_path, repo):
    run, _ = runner_fijo(chapter="APROBADO")
    r = correr(tmp_path, repo, run, evidencia_ok=False)
    assert r["resultado"] == "RECHAZADO"
    assert "El Chapter aprobó pese a la falla" in r["motivo"]


def test_testing_y_chapter_reciben_la_salida_real_y_el_codigo_con_lineas(tmp_path, repo):
    run, llamadas = runner_fijo()
    correr(tmp_path, repo, run)
    prompts = dict(llamadas)
    assert "salida real" in prompts["testing"] and "salida real" in prompts["chapter"]
    assert "salida real" not in prompts["backend"]
    assert "1 | def validar(dni):" in prompts["backend"]
    assert "Informe de Architect" in prompts["chapter"]


def test_reintento_con_feedback_y_rechazo_detienen_donde_corresponde(tmp_path, repo):
    run, llamadas = runner_fijo()
    respuestas = iter([("s", ""), ("r", "Cita la línea exacta"), ("s", ""), ("n", "")])
    r = correr(tmp_path, repo, run, aprobar=lambda *_: next(respuestas))
    claves = [c for c, _ in llamadas]
    assert claves == ["architect", "backend", "backend", "frontend"]
    assert "Cita la línea exacta" in llamadas[2][1]
    assert r["detenido_en"] == "frontend"
    assert r["resultado"] == "NO CONCLUYENTE"


def test_checkpoint_reutiliza_lo_aprobado_y_se_reinicia_a_pedido(tmp_path, repo):
    respuestas = iter([("s", ""), ("n", "")])
    run1, _ = runner_fijo()
    correr(tmp_path, repo, run1, aprobar=lambda *_: next(respuestas))

    run2, llamadas2 = runner_fijo()
    correr(tmp_path, repo, run2)
    assert [c for c, _ in llamadas2] == [x.clave for x in ROLES][1:]

    run3, llamadas3 = runner_fijo()
    correr(tmp_path, repo, run3, reiniciar=True)
    assert len(llamadas3) == 6


def test_solo_evidencia_no_llama_al_modelo(tmp_path, repo):
    run, llamadas = runner_fijo()
    r = correr(tmp_path, repo, run, solo_evidencia=True)
    assert llamadas == []
    assert r["resultado"] == "SOLO EVIDENCIA"


def test_reglas_del_resultado_final():
    assert resultado_final(False, "APROBADO", False)[0] == "RECHAZADO"
    assert resultado_final(True, "APROBADO", True)[0] == "NO CONCLUYENTE"
    assert resultado_final(True, None, False)[0] == "NO CONCLUYENTE"
    assert resultado_final(True, "RECHAZADO", False)[0] == "RECHAZADO"
    assert resultado_final(None, "APROBADO", False)[0] == "NO CONCLUYENTE"


def test_la_evidencia_corre_con_utf8_aunque_la_consola_sea_cp1252(tmp_path, repo, monkeypatch):
    """En Windows la salida capturada usa cp1252: imprimir → fallaría sin forzar UTF-8."""
    from sdd_crew import evidencia
    monkeypatch.setenv("PYTHONIOENCODING", "cp1252")
    proyecto = Proyecto.desde_yaml(escribir_proyecto(tmp_path, repo))
    proyecto.evidencia = [{"nombre": "Unicode", "comando": ["python", "-c", "print('Trazabilidad spec → pruebas ✓')"]}]
    [r] = evidencia.ejecutar(proyecto)
    assert r.ok, r.salida
    assert "→" in r.salida and "✓" in r.salida


def test_una_verificacion_fallida_muestra_su_error_en_consola(tmp_path, repo):
    mensajes = []
    proyecto = Proyecto.desde_yaml(escribir_proyecto(tmp_path, repo, evidencia_ok=False))
    ejecutar_flujo(proyecto, ROLES, runner_fijo()[0], aprobar_todo, tmp_path / "out", "x",
                   solo_evidencia=True, log=mensajes.append)
    assert any("salida real" in m for m in mensajes)

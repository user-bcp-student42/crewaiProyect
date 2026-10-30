"""Conexión con CrewAI sin llamar a ningún modelo real."""
from crewai.llms.base_llm import BaseLLM

from sdd_crew import ejecutor, llm
from sdd_crew.roles import POR_CLAVE


RECIBIDO: list[str] = []


class LLMFalso(BaseLLM):
    def call(self, messages, tools=None, callbacks=None, available_functions=None,
             from_task=None, from_agent=None, response_model=None):
        texto = messages if isinstance(messages, str) else "\n".join(str(m.get("content", "")) for m in messages)
        RECIBIDO.append(texto)
        return "# Informe de Backend\nSin hallazgos.\nVEREDICTO: CUMPLE"

    def supports_function_calling(self):
        return False

    def supports_stop_words(self):
        return False


def test_un_rol_se_ejecuta_como_mini_crew_de_crewai(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "crewai")
    monkeypatch.setattr(llm, "crear_llm", lambda: LLMFalso(model="falso"))
    salida = ejecutor.ejecutar(POR_CLAVE["backend"], "PROMPT-DE-PRUEBA con la spec", ["CA-1"])
    assert "VEREDICTO: CUMPLE" in salida
    assert any("PROMPT-DE-PRUEBA" in t for t in RECIBIDO)


def test_proveedor_simulado_no_usa_crewai_ni_emite_veredicto(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "simulado")
    salida = ejecutor.ejecutar(POR_CLAVE["security"], "x", ["CA-1", "RS-1"])
    assert "INFORME SIMULADO" in salida
    assert "| RS-1 | NO VERIFICABLE" in salida and "CA-1" not in salida.split("## 2.")[1].split("## 3.")[0]
    assert "VEREDICTO" not in salida


def test_proveedor_invalido(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "otro")
    import pytest
    with pytest.raises(ValueError):
        llm.proveedor()

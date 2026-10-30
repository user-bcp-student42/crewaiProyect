"""Modelos disponibles: GitHub Copilot (como en los labs), cualquier modelo de CrewAI o simulado."""
from __future__ import annotations

import asyncio
import os
from typing import Any

from crewai.llms.base_llm import BaseLLM

PROVEEDORES = ("copilot", "crewai", "simulado")


def proveedor() -> str:
    valor = os.getenv("LLM_PROVIDER", "copilot").strip().lower()
    if valor not in PROVEEDORES:
        raise ValueError(f"LLM_PROVIDER debe ser uno de: {', '.join(PROVEEDORES)}")
    return valor


def _texto(messages: Any) -> str:
    if isinstance(messages, str):
        return messages
    partes = []
    for m in messages:
        rol, contenido = (m.get("role", "user"), m.get("content", "")) if isinstance(m, dict) else (m.type, m.content)
        if isinstance(contenido, list):
            contenido = "\n".join(i.get("text", "") if isinstance(i, dict) else str(i) for i in contenido)
        partes.append(f"[{rol.upper()}]\n{contenido}")
    return "\n\n".join(partes)


async def _copilot(prompt: str, model: str, timeout: float) -> str:
    import copilot
    from copilot.generated.rpc import PermissionDecisionReject
    from copilot.session_events import AssistantMessageData

    def negar(*_: Any) -> PermissionDecisionReject:
        return PermissionDecisionReject(feedback="El validador solo pide texto; no ejecuta herramientas.")

    sesion_cli = os.getenv("COPILOT_USE_LOGGED_IN_USER", "true").lower() in {"true", "1", "yes", "si", "sí"}
    async with copilot.CopilotClient(use_logged_in_user=sesion_cli) as cliente:
        async with await cliente.create_session(
            model=model,
            # Vacío = no enviarlo (para modelos que no admiten esfuerzo de razonamiento).
            reasoning_effort=os.getenv("COPILOT_REASONING_EFFORT", "high").strip() or None,
            available_tools=[], on_permission_request=negar,
            system_message={"mode": "replace", "content":
                            "Eres un validador. Sigue las instrucciones del historial y devuelve solo el informe "
                            "markdown solicitado, sin ejecutar herramientas."},
            skip_custom_instructions=True,
            working_directory=os.getcwd(),
        ) as sesion:
            evento = await sesion.send_and_wait(prompt, timeout=timeout)
            if evento is None or not isinstance(evento.data, AssistantMessageData) or not evento.data.content:
                raise RuntimeError("Copilot terminó sin devolver texto.")
            return evento.data.content


class CopilotLLM(BaseLLM):
    """Adaptador CrewAI → GitHub Copilot SDK. Solo texto, sin herramientas."""

    llm_type: str = "copilot"
    timeout: float = 900.0

    def call(self, messages, tools=None, callbacks=None, available_functions=None,
             from_task=None, from_agent=None, response_model=None) -> str:
        if tools or available_functions or response_model is not None:
            raise ValueError("CopilotLLM solo genera texto.")
        return asyncio.run(_copilot(_texto(messages), self.model, self.timeout))

    async def acall(self, messages, tools=None, callbacks=None, available_functions=None,
                    from_task=None, from_agent=None, response_model=None) -> str:
        if tools or available_functions or response_model is not None:
            raise ValueError("CopilotLLM solo genera texto.")
        return await _copilot(_texto(messages), self.model, self.timeout)

    def supports_function_calling(self) -> bool:
        return False

    def supports_stop_words(self) -> bool:
        return False


def crear_llm():
    p = proveedor()
    if p == "copilot":
        return CopilotLLM(model=os.getenv("COPILOT_MODEL", "gpt-6-luna"))
    if p == "crewai":
        from crewai import LLM
        modelo = os.getenv("LLM_MODEL")
        if not modelo:
            raise ValueError("Con LLM_PROVIDER=crewai debes definir LLM_MODEL (por ejemplo anthropic/claude-sonnet-5-5).")
        return LLM(model=modelo)
    raise ValueError("El proveedor simulado no usa un LLM.")


def nombre_modelo() -> str:
    p = proveedor()
    if p == "copilot":
        return f"copilot:{os.getenv('COPILOT_MODEL', 'gpt-6-luna')}"
    if p == "crewai":
        return f"crewai:{os.getenv('LLM_MODEL', '?')}"
    return "simulado"

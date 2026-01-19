from __future__ import annotations

from typing import Optional

from .registry import Persona, PersonaRegistry


class PersonaRouter:
    """Stateful router for persona selection (manual/auto/council skeleton)."""

    def __init__(self, registry: PersonaRegistry, persona_name: str = "default", auto: bool = False, council: bool = False):
        self.registry = registry
        self.mode = "auto" if auto else "manual"
        self.council = council
        self.persona_name = persona_name or "default"

    @property
    def current_persona(self) -> Persona:
        return self.registry.get(self.persona_name)

    def set_manual(self, persona_name: str) -> Persona:
        self.mode = "manual"
        self.persona_name = persona_name
        return self.current_persona

    def set_auto(self, on: bool) -> None:
        self.mode = "auto" if on else "manual"

    def set_council(self, on: bool) -> None:
        self.council = on

    def route(self, user_text: str) -> Persona:
        if self.mode != "auto":
            return self.current_persona
        text = user_text.lower()
        if any(k in text for k in ["deploy", "incident", "sla", "pager"]):
            self.persona_name = "ops"
        elif any(k in text for k in ["plan", "milestone", "roadmap"]):
            self.persona_name = "planner"
        elif any(k in text for k in ["bug", "traceback", "stack", "fix"]):
            self.persona_name = "dev"
        elif any(k in text for k in ["review", "risk", "critique"]):
            self.persona_name = "critic"
        else:
            self.persona_name = "default"
        return self.current_persona

    def status(self) -> str:
        mode = f"mode={self.mode}"
        council = "council=on" if self.council else "council=off"
        return f"{mode}, persona={self.persona_name}, {council}"

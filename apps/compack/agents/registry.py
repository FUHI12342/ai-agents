from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import yaml


@dataclass
class Persona:
    name: str
    description: str
    system_prompt: str
    constraints: Optional[list] = None
    style: Optional[str] = None

    def prompt_block(self) -> str:
        parts = [self.system_prompt.strip()]
        if self.constraints:
            parts.append("Constraints:\n- " + "\n- ".join(self.constraints))
        if self.style:
            parts.append(f"Style: {self.style}")
        return "\n\n".join(parts).strip()


class PersonaRegistry:
    """Load persona definitions from YAML and provide lookup."""

    def __init__(self, path: Path | None = None):
        self.path = path or Path(__file__).parent / "agents.yaml"
        self.personas: Dict[str, Persona] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            raise FileNotFoundError(f"Personas file not found: {self.path}")
        data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        personas: Dict[str, Persona] = {}
        for key, val in data.items():
            if not isinstance(val, dict):
                continue
            name = val.get("name") or key
            persona = Persona(
                name=name,
                description=val.get("description", ""),
                system_prompt=val.get("system_prompt", ""),
                constraints=val.get("constraints"),
                style=val.get("style"),
            )
            personas[name] = persona
        self.personas = personas

    def get(self, name: str, default: str = "default") -> Persona:
        if name in self.personas:
            return self.personas[name]
        return self.personas.get(default) or next(iter(self.personas.values()))

    def list(self) -> Dict[str, Persona]:
        return self.personas

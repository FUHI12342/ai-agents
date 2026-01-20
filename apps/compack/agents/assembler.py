from __future__ import annotations

from typing import Optional

DEFAULT_BASE_POLICY = """
You are Compack, a local-first assistant. Be concise, safe, and truthful.
- Respect user privacy and do not leak secrets.
- Prefer actionable, short answers.
- State when information is missing or uncertain.
""".strip()


def assemble_prompt(
    base_policy: str = DEFAULT_BASE_POLICY,
    user_profile: Optional[str] = None,
    memory_summary: Optional[str] = None,
    retrieved_context: Optional[str] = None,
    persona_block: Optional[str] = None,
) -> str:
    """Assemble a system prompt in a fixed order."""
    sections = []
    if base_policy:
        sections.append(f"Base Policy:\n{base_policy.strip()}")
    if user_profile:
        sections.append(f"User Profile (opt-in):\n{user_profile.strip()}")
    if memory_summary:
        sections.append(f"Memory Summary:\n{memory_summary.strip()}")
    if retrieved_context:
        sections.append(f"Retrieved Context:\n{retrieved_context.strip()}")
    if persona_block:
        sections.append(f"Persona Instructions:\n{persona_block.strip()}")
    return "\n\n".join(sections)

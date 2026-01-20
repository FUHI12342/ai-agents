# Compack Multi-Agent Skeleton (PR1)

## Overview
Compack will orchestrate multiple personas (role-specialized sub-agents). PR1 provides the skeleton: persona registry, router, prompt assembler, and CLI hooks.

## Flow (text/web)
```
User input
  -> PersonaRouter (manual/auto/council flag, default=manual)
  -> PromptAssembler (fixed order)
        1) Base policy (safety, brevity)
        2) User Profile (opt-in, local JSON)
        3) Memory Summary (placeholder for PR2)
        4) Retrieved Context (placeholder for PR3)
        5) Persona system prompt (from agents.yaml)
  -> LLM (Ollama/OpenAI)
  -> Optional tools
  -> Response + persona metadata in session log
```

## Personas (agents/agents.yaml)
- default: general-purpose, concise
- dev: engineering/debug focus
- ops: operations/SRE focus
- planner: planning/roadmap focus
- critic: reviews and highlights risks

## Routing modes (skeleton)
- manual: user selects persona (`/agent use <name>`)
- auto: simple keyword-based switch (dev/ops/planner/critic)
- council: flag only in PR1 (aggregation to be built later)

## Logging / audit
- Session messages store `metadata.persona` for assistant turns.
- Startup log includes the active persona.

## Extensibility (future PRs)
- PR2: memory store with agent metadata; auto-injection into assembler step 3.
- PR3: RAG retrieval and agent-specific injection/top_k control.
- PR4: dataset export (profile + memory + conversations) for fine-tune-style workflows.

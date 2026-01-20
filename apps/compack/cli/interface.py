from __future__ import annotations

import json

from apps.compack.core import ConfigManager, ConversationOrchestrator
from apps.compack.agents import PersonaRegistry, PersonaRouter, assemble_prompt, DEFAULT_BASE_POLICY
from apps.compack.profile import ProfileManager


class CLIInterface:
    """Lightweight CLI interface for Compack."""

    def __init__(
        self,
        orchestrator: ConversationOrchestrator,
        config: ConfigManager,
        persona_router: PersonaRouter | None = None,
        profile_manager: ProfileManager | None = None,
        base_policy: str = DEFAULT_BASE_POLICY,
    ):
        self.orchestrator = orchestrator
        self.config = config
        self.running = False
        self.persona_router = persona_router or PersonaRouter(PersonaRegistry())
        self.profile_manager = profile_manager or ProfileManager()
        self.base_policy = base_policy
        self._refresh_system_prompt()

    async def start(self, mode: str = "text", resume: str | None = None) -> None:
        """Start the interactive loop."""
        self.running = True
        self.display_welcome(mode)
        initial_input = self._init_session(resume)

        if initial_input:
            response = await self.orchestrator.process_text_input(initial_input)
            self.display_message("assistant", response)

        while self.running:
            prompt = "Enter a message (/quit to exit"
            if mode == "voice":
                prompt += ", press Enter to record"
            prompt += "): "
            user_input = input(prompt).strip()
            if user_input.startswith("/"):
                if not self.handle_command(user_input):
                    continue
                if not self.running:
                    break
                continue

            if user_input == "" and mode == "voice":
                await self.orchestrator.process_voice_input()
                continue

            if self.persona_router.mode == "auto":
                persona = self.persona_router.route(user_input)
                self._apply_persona(persona.name)

            response = await self.orchestrator.process_text_input(user_input)
            self.display_message("assistant", response)

    def display_welcome(self, mode: str) -> None:
        print("=== Compack Voice/Text CLI ===")
        print(f"Mode: {mode}")
        print("Commands: /help /config /quit /agents /agent ... /profile ...")
        if mode == "voice":
            print("Push-to-Talk: press Enter when prompted to record.")

    def display_message(self, role: str, content: str) -> None:
        label = "You" if role == "user" else "Compack"
        print(f"{label}: {content}")

    def display_streaming(self, content: str) -> None:
        print(content, end="", flush=True)

    def handle_command(self, command: str) -> bool:
        cmd = command.lower()
        if cmd in {"/quit", "quit", "/exit"}:
            self.running = False
            self.orchestrator.session.save_session()
            print("Session saved. Bye.")
            return True
        if cmd in {"/help", "help"}:
            print("Available commands: /help /config /quit /agents /agent [use|auto|council|status] /profile [show|set|delete|reset]")
            return False
        if cmd in {"/config", "config"}:
            self._display_config()
            return False
        if cmd.startswith("/agents"):
            self._list_agents()
            return False
        if cmd.startswith("/agent"):
            self._handle_agent_command(command)
            return False
        if cmd.startswith("/profile"):
            self._handle_profile_command(command)
            return False
        print("Unknown command. Use /help for the list of commands.")
        return False

    def wait_for_push_to_talk(self) -> bool:
        prompt = input("Press Enter to start recording (type anything to cancel): ").strip()
        return prompt == ""

    def _display_config(self) -> None:
        cfg = self.config.config or self.config.load()
        print("Current config:")
        for key, value in cfg.to_dict().items():
            if "api_key" in key:
                value = "***"
            print(f"- {key}: {value}")
        print(f"- persona: {self.persona_router.current_persona.name} (mode={self.persona_router.mode}, council={self.persona_router.council})")
        print(f"- profile path: {self.profile_manager.path}")

    def _list_agents(self) -> None:
        print("Personas:")
        for name, persona in self.persona_router.registry.list().items():
            marker = "*" if persona.name == self.persona_router.current_persona.name else " "
            print(f"{marker} {name}: {persona.description}")

    def _apply_persona(self, persona_name: str) -> None:
        self.persona_router.persona_name = persona_name
        persona = self.persona_router.registry.get(persona_name)
        profile_text = self.profile_manager.format_for_prompt()
        prompt = assemble_prompt(
            base_policy=self.base_policy,
            user_profile=profile_text,
            persona_block=persona.prompt_block(),
        )
        if hasattr(self.orchestrator, "set_system_prompt"):
            self.orchestrator.set_system_prompt(prompt, persona_name=persona.name)

    def _refresh_system_prompt(self) -> None:
        persona = self.persona_router.current_persona
        profile_text = self.profile_manager.format_for_prompt()
        prompt = assemble_prompt(
            base_policy=self.base_policy,
            user_profile=profile_text,
            persona_block=persona.prompt_block(),
        )
        if hasattr(self.orchestrator, "set_system_prompt"):
            self.orchestrator.set_system_prompt(prompt, persona_name=persona.name)

    def _handle_agent_command(self, command: str) -> None:
        parts = command.split()
        if len(parts) == 2 and parts[1].lower() == "status":
            print(f"Agent status: {self.persona_router.status()}")
            return
        if len(parts) >= 3 and parts[1].lower() == "use":
            target = parts[2]
            persona = self.persona_router.set_manual(target)
            self._apply_persona(persona.name)
            print(f"Switched to persona '{persona.name}' (manual mode).")
            return
        if len(parts) >= 3 and parts[1].lower() == "auto":
            on = parts[2].lower() in {"on", "true", "1", "yes"}
            self.persona_router.set_auto(on)
            mode = "auto" if on else "manual"
            print(f"Auto routing {mode}. Current persona: {self.persona_router.current_persona.name}")
            return
        if len(parts) >= 3 and parts[1].lower() == "council":
            on = parts[2].lower() in {"on", "true", "1", "yes"}
            self.persona_router.set_council(on)
            state = "on" if on else "off"
            print(f"Council mode {state} (skeleton; final aggregation not implemented).")
            return
        print("Usage: /agents | /agent status | /agent use <name> | /agent auto on|off | /agent council on|off")

    def _handle_profile_command(self, command: str) -> None:
        parts = command.split()
        if len(parts) == 2 and parts[1].lower() == "show":
            print(json.dumps(self.profile_manager.show(), ensure_ascii=False, indent=2))
            return
        if len(parts) >= 3 and parts[1].lower() == "set":
            kv = " ".join(parts[2:])
            if "=" not in kv:
                print("Usage: /profile set key=value")
                return
            key, value = kv.split("=", 1)
            self.profile_manager.set_value(key.strip(), value.strip())
            self._refresh_system_prompt()
            print(f"Profile updated: {key.strip()}")
            return
        if len(parts) >= 3 and parts[1].lower() == "delete":
            key = parts[2]
            self.profile_manager.delete_key(key)
            self._refresh_system_prompt()
            print(f"Profile key deleted: {key}")
            return
        if len(parts) == 2 and parts[1].lower() == "reset":
            self.profile_manager.reset()
            self._refresh_system_prompt()
            print("Profile reset.")
            return
        print("Usage: /profile show | /profile set key=value | /profile delete <key> | /profile reset")

    def _init_session(self, resume: str | None) -> str | None:
        sessions = self.orchestrator.session.list_sessions()

        def _latest_session() -> str | None:
            if not sessions:
                return None
            paths = [self.orchestrator.session.log_dir / f"{sid}.jsonl" for sid in sessions]
            latest = max(paths, key=lambda p: p.stat().st_mtime)
            return latest.stem

        if resume == "new":
            self.orchestrator.session.create_session()
            return None
        if resume == "latest":
            sid = _latest_session()
            if sid:
                try:
                    self.orchestrator.session.load_session(sid)
                    print(f"Resumed latest session {sid}.")
                    return None
                except Exception:
                    print("Failed to load latest session. Starting new.")
            self.orchestrator.session.create_session()
            return None
        if resume and resume not in {"new", "latest"}:
            if resume in sessions:
                try:
                    self.orchestrator.session.load_session(resume)
                    print(f"Resumed session {resume}.")
                    return None
                except Exception:
                    print("Failed to load the selected session. Starting a new one.")
            else:
                print(f"Session {resume} not found. Starting new session.")
            self.orchestrator.session.create_session()
            return None

        if sessions:
            print(f"Previous sessions: {', '.join(sessions)}")
            choice = input("Enter a session ID to resume (or leave blank for new): ").strip()
            if choice and choice in sessions:
                try:
                    self.orchestrator.session.load_session(choice)
                    print(f"Resumed session {choice}.")
                    return None
                except Exception:
                    print("Failed to load the selected session. Starting a new one.")
                    self.orchestrator.session.create_session()
                    return None
            if choice:
                # invalid ID; treat as first message of new session
                print("Invalid session ID. Starting a new session and using the input as your first message.")
                self.orchestrator.session.create_session()
                return choice
        self.orchestrator.session.create_session()
        return None

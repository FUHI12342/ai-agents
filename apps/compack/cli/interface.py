from __future__ import annotations

from apps.compack.core import ConfigManager, ConversationOrchestrator


class CLIInterface:
    """Lightweight CLI interface for Compack."""

    def __init__(self, orchestrator: ConversationOrchestrator, config: ConfigManager):
        self.orchestrator = orchestrator
        self.config = config
        self.running = False

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

            response = await self.orchestrator.process_text_input(user_input)
            self.display_message("assistant", response)

    def display_welcome(self, mode: str) -> None:
        print("=== Compack Voice/Text CLI ===")
        print(f"Mode: {mode}")
        print("Commands: /help /config /quit")
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
            print("Available commands: /help /config /quit")
            return False
        if cmd in {"/config", "config"}:
            self._display_config()
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

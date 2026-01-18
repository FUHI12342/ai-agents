from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from apps.compack.core import StructuredLogger
from apps.compack.models import Message, Session


class SessionManager:
    """セッションの生成・保存・復元を管理する。"""

    def __init__(self, log_dir: Path, logger: StructuredLogger, max_context_messages: int = 10):
        self.log_dir = Path(log_dir)
        self.logger = logger
        self.max_context_messages = max_context_messages
        self.current_session_id: Optional[str] = None
        self.messages: List[Message] = []
        self.created_at: Optional[datetime] = None
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def create_session(self) -> str:
        self.current_session_id = uuid.uuid4().hex
        self.messages = []
        self.created_at = datetime.utcnow()
        self.logger.info("新規セッション生成", session_id=self.current_session_id)
        return self.current_session_id

    def load_session(self, session_id: str) -> List[Message]:
        path = self.log_dir / f"{session_id}.jsonl"
        if not path.exists():
            raise FileNotFoundError(f"セッション {session_id} が見つかりません。")

        try:
            content = path.read_text(encoding="utf-8")
            session = Session.from_jsonl(session_id=session_id, jsonl_data=content)
        except Exception as exc:
            self.logger.error("セッション読み込みに失敗しました", error=exc, session_id=session_id)
            raise

        self.current_session_id = session_id
        self.messages = session.messages
        self.created_at = session.created_at
        self.logger.info("セッション復元完了", session_id=session_id, messages=len(self.messages))
        return self.messages

    def add_message(self, role: str, content: str, metadata: Optional[dict] = None) -> None:
        message = Message(role=role, content=content, timestamp=datetime.utcnow(), metadata=metadata or {})
        self.messages.append(message)
        self.logger.debug("メッセージ追加", role=role, length=len(content))

    def save_session(self) -> Path:
        if not self.current_session_id:
            self.current_session_id = uuid.uuid4().hex
            self.created_at = self.created_at or datetime.utcnow()
        session = Session(
            session_id=self.current_session_id or uuid.uuid4().hex,
            created_at=self.created_at or datetime.utcnow(),
            updated_at=datetime.utcnow(),
            messages=self.messages,
        )
        path = self.log_dir / f"{session.session_id}.jsonl"
        path.write_text(session.to_jsonl(), encoding="utf-8")
        self.logger.info("セッション保存完了", session_id=session.session_id, path=str(path))
        return path

    def list_sessions(self) -> List[str]:
        return [p.stem for p in self.log_dir.glob("*.jsonl")]

    def get_context(self, max_messages: Optional[int] = None) -> List[dict]:
        limit = max_messages or self.max_context_messages
        tail = self.messages[-limit:] if limit else self.messages
        return [m.to_dict() for m in tail]

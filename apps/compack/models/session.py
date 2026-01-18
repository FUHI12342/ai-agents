from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .message import Message


@dataclass
class Session:
    """会話セッションモデル."""

    session_id: str
    created_at: datetime
    updated_at: datetime
    messages: List[Message] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None

    def add_message(self, message: Message) -> None:
        """Append a message and refresh the update timestamp."""
        self.messages.append(message)
        self.updated_at = datetime.utcnow()

    def to_jsonl(self) -> str:
        """Serialize messages to JSONL string."""
        return "\n".join(json.dumps(msg.to_dict(), ensure_ascii=True) for msg in self.messages)

    @classmethod
    def from_jsonl(
        cls,
        session_id: str,
        jsonl_data: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "Session":
        """Rehydrate a Session from JSONL content."""
        messages = []
        for line in filter(None, jsonl_data.splitlines()):
            messages.append(Message.from_dict(json.loads(line)))

        now = datetime.utcnow()
        return cls(
            session_id=session_id,
            created_at=created_at or now,
            updated_at=updated_at or now,
            messages=messages,
            metadata=metadata or {},
        )

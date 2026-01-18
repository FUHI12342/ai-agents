from __future__ import annotations

import asyncio
from typing import Dict

from apps.compack.modules import Tool


class SetTimerTool(Tool):
    @property
    def name(self) -> str:
        return "set_timer"

    @property
    def description(self) -> str:
        return "指定秒数後に通知します。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "seconds": {"type": "integer", "description": "秒数"},
                "message": {"type": "string", "description": "通知メッセージ"},
            },
            "required": ["seconds"],
        }

    async def execute(self, seconds: int, message: str = "時間です！") -> Dict[str, str | int]:
        async def _notify(delay: int, note: str) -> None:
            await asyncio.sleep(delay)
            # Notification placeholder; could be extended to integrate with OS notifications.
            return None

        asyncio.create_task(_notify(seconds, message))
        return {"scheduled_in_seconds": seconds, "message": message}

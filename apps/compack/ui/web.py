from __future__ import annotations

import asyncio
import threading
import webbrowser
from typing import Optional

from apps.compack.core import ConversationOrchestrator


async def serve_web_ui(orchestrator: ConversationOrchestrator, host: str = "127.0.0.1", port: int = 8765, open_browser: bool = False) -> None:
    """Launch a minimal FastAPI-based web UI using async server."""
    try:
        from fastapi import FastAPI
        from fastapi.responses import HTMLResponse, JSONResponse
        import uvicorn
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("fastapi/uvicorn がインストールされていません。requirements-web.txt を参照してください。") from exc

    app = FastAPI()

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return """
<!doctype html>
<html>
<head><title>Compack</title></head>
<body>
<h1>Compack</h1>
<div id="messages"></div>
<textarea id="input" rows="4" cols="60" placeholder="メッセージを入力"></textarea><br>
<button onclick="send()">送信</button>
<pre id="status"></pre>
<script>
async function send() {
  const text = document.getElementById('input').value;
  const res = await fetch('/api/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({text})});
  const data = await res.json();
  document.getElementById('messages').innerHTML += '<p><b>あなた:</b> '+text+'</p><p><b>Compack:</b> '+data.reply+'</p>';
  document.getElementById('input').value='';
}
</script>
</body>
</html>
        """

    @app.post("/api/chat")
    async def chat(payload: dict):
        text = payload.get("text", "")
        reply = await orchestrator.process_text_input(text)
        return JSONResponse({"reply": reply})

    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(f"http://{host}:{port}")).start()

    # Use uvicorn.Server with await instead of uvicorn.run to avoid nested asyncio.run
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


def start_web_ui(orchestrator: ConversationOrchestrator, host: str = "127.0.0.1", port: int = 8765, open_browser: bool = False) -> None:
    """Launch a minimal FastAPI-based web UI (non-async wrapper)."""
    asyncio.run(serve_web_ui(orchestrator, host, port, open_browser))

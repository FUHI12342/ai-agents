from datetime import datetime, timedelta
from pathlib import Path
from typing import List

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from apps.compack.core import SessionManager, StructuredLogger
from apps.compack.models import Message, Session


@pytest.mark.property
@given(
    session_id=st.text(min_size=1, max_size=20),
    base_time=st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 12, 31)),
    messages=st.lists(
        st.fixed_dictionaries(
            {
                "role": st.sampled_from(["user", "assistant", "system", "tool"]),
                "content": st.text(min_size=1, max_size=50),
                "offset": st.integers(min_value=0, max_value=1000),
            }
        ),
        min_size=1,
        max_size=10,
    ),
)
def test_session_jsonl_roundtrip(session_id: str, base_time: datetime, messages: List[dict]) -> None:
    """
    Feature: voice-ai-agent-compack, Property 8: 会話ログのラウンドトリップ一貫性.
    Validates that JSONL serialization/deserialization preserves message order and content.
    """
    parsed_messages = []
    for item in messages:
        ts = base_time + timedelta(seconds=item["offset"])
        parsed_messages.append(Message(role=item["role"], content=item["content"], timestamp=ts))

    session = Session(
        session_id=session_id,
        created_at=base_time,
        updated_at=base_time if not parsed_messages else parsed_messages[-1].timestamp,
        messages=parsed_messages,
    )

    jsonl = session.to_jsonl()
    restored = Session.from_jsonl(session_id=session.session_id, jsonl_data=jsonl, created_at=session.created_at)

    assert [m.to_dict() for m in session.messages] == [m.to_dict() for m in restored.messages]
    assert restored.session_id == session.session_id
    assert restored.created_at == session.created_at


@pytest.mark.unit
def test_session_manager_save_and_load(tmp_path: Path) -> None:
    log_dir = tmp_path / "sessions"
    manager = SessionManager(log_dir=log_dir, logger=StructuredLogger(log_file=None), max_context_messages=3)
    session_id = manager.create_session()
    manager.add_message("user", "hello")
    manager.add_message("assistant", "hi there")
    saved_path = manager.save_session()

    assert saved_path.exists()
    loaded = manager.load_session(session_id)
    assert len(loaded) == 2
    assert manager.list_sessions() == [session_id]
    context = manager.get_context()
    assert context[-1]["content"] == "hi there"


@pytest.mark.property
@given(count=st.integers(min_value=1, max_value=20))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_session_ids_are_unique(tmp_path: Path, count: int) -> None:
    """
    Feature: voice-ai-agent-compack, Property 6: セッションIDのユニーク性.
    """
    manager = SessionManager(log_dir=tmp_path / "sessions", logger=StructuredLogger(log_file=None))
    session_ids = set()
    for _ in range(count):
        session_ids.add(manager.create_session())
    assert len(session_ids) == count


@pytest.mark.property
@given(
    contents=st.lists(st.text(min_size=1, max_size=30), min_size=1, max_size=8),
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_message_order_preserved(tmp_path: Path, contents: List[str]) -> None:
    """
    Feature: voice-ai-agent-compack, Property 7: 会話ログ追記の順序保持.
    """
    manager = SessionManager(log_dir=tmp_path / "sessions", logger=StructuredLogger(log_file=None))
    session_id = manager.create_session()
    for text in contents:
        manager.add_message("user", text)
    manager.save_session()
    manager.load_session(session_id)
    assert [msg.content for msg in manager.messages] == contents


@pytest.mark.property
@given(
    session_count=st.integers(min_value=1, max_value=5),
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_session_listing_complete(tmp_path: Path, session_count: int) -> None:
    """
    Feature: voice-ai-agent-compack, Property 9: セッション一覧の完備性.
    """
    manager = SessionManager(log_dir=tmp_path / "sessions", logger=StructuredLogger(log_file=None))
    created = []
    for _ in range(session_count):
        sid = manager.create_session()
        manager.add_message("user", "hello")
        manager.save_session()
        created.append(sid)
    sessions = manager.list_sessions()
    for sid in created:
        assert sid in sessions

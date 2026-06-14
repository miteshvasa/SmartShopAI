import uuid
from dataclasses import dataclass, field

from app.config import get_settings
from app.pii import redact_pii


@dataclass
class SessionMemory:
    messages: list[str] = field(default_factory=list)


class EphemeralMemoryStore:
    def __init__(self) -> None:
        self._items: dict[str, SessionMemory] = {}

    def new_session_id(self) -> str:
        return uuid.uuid4().hex

    def get_context(self, session_id: str) -> str:
        settings = get_settings()
        if not settings.enable_ephemeral_memory:
            return ""
        memory = self._items.get(session_id)
        if not memory:
            return ""
        return "\n".join(memory.messages)

    def append(self, session_id: str, role: str, content: str) -> None:
        settings = get_settings()
        if not settings.enable_ephemeral_memory:
            return
        redacted, _ = redact_pii(content)
        memory = self._items.setdefault(session_id, SessionMemory())
        memory.messages.append(f"{role}: {redacted[:1200]}")

    def clear(self, session_id: str) -> bool:
        return self._items.pop(session_id, None) is not None


memory_store = EphemeralMemoryStore()

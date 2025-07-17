from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class EventType(str, Enum):
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    RECONNECT = "reconnect"
    SHELL_CREATE = "shell_create"
    SHELL_CLOSE = "shell_close"
    SHELL_COMMAND = "shell_command"
    INTERRUPT = "interrupt"
    TIMEOUT_INTERRUPT = "timeout_interrupt"


class StepHistory(BaseModel):
    event: EventType
    error: str
    timestamp: datetime
    description: str | None = None

    # 명령 이벤트일 때만 아래 필드 사용
    command: str | None = None
    output: str | None = None

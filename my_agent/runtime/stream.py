from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class StreamEvent:
    type: str
    data: dict[str, Any] = field(default_factory=dict)


class StreamWriter:
    def __init__(self, sink: Callable[[StreamEvent], None] | None = None) -> None:
        self.sink = sink
        self.events: list[StreamEvent] = []

    def write(self, event_type: str, **data: Any) -> None:
        event = StreamEvent(event_type, data)
        self.events.append(event)
        if self.sink is not None:
            self.sink(event)


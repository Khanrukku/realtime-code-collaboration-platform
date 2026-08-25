import asyncio
from dataclasses import dataclass, field

from app.collab.models import CommittedOperation, Operation
from app.collab.transform import transform_against

@dataclass
class Document:
    text: str = ""
    version: int = 0
    history: list[CommittedOperation] = field(default_factory=list)
    max_history: int = 1000

    def _validate_base_version(self, base_version: int):
        if base_version > self.version:
            raise ValueError("base_version cannot be ahead of server version")
        if self.history:
            earliest_supported = self.history[0].version - 1
            if base_version < earliest_supported:
                raise ValueError("operation is older than retained history")

    def apply(self, operation: Operation) -> CommittedOperation:
        self._validate_base_version(operation.base_version)
        transformed = operation.model_copy(deep=True)

        for committed in self.history:
            if committed.version > operation.base_version:
                transformed = transform_against(transformed, committed)

        if transformed.type == "insert":
            if transformed.position > len(self.text):
                raise ValueError("insert position is outside document")
            self.text = (
                self.text[:transformed.position]
                + (transformed.text or "")
                + self.text[transformed.position:]
            )
        else:
            length = transformed.length or 0
            if transformed.position > len(self.text):
                raise ValueError("delete position is outside document")
            if transformed.position + length > len(self.text):
                raise ValueError("delete range is outside document")
            self.text = (
                self.text[:transformed.position]
                + self.text[transformed.position + length:]
            )

        self.version += 1
        committed = CommittedOperation(
            **transformed.model_dump(),
            version=self.version,
        )
        self.history.append(committed)

        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        return committed

class Room:
    def __init__(self, room_id: str, max_history: int = 1000):
        self.room_id = room_id
        self.document = Document(max_history=max_history)
        self.clients: set = set()
        self.lock = asyncio.Lock()

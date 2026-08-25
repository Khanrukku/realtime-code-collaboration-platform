from typing import Literal
from pydantic import BaseModel, Field, model_validator

class Operation(BaseModel):
    type: Literal["insert", "delete"]
    position: int = Field(ge=0)
    base_version: int = Field(ge=0)
    text: str | None = None
    length: int | None = Field(default=None, ge=1)
    client_id: str = ""
    operation_id: str = ""

    @model_validator(mode="after")
    def validate_payload(self):
        if self.type == "insert":
            if not self.text:
                raise ValueError("insert operation requires non-empty text")
            self.length = None
        else:
            if self.length is None:
                raise ValueError("delete operation requires length")
            self.text = None
        return self

class CommittedOperation(Operation):
    version: int

class RoomSnapshot(BaseModel):
    room_id: str
    text: str
    version: int
    clients: int = 0

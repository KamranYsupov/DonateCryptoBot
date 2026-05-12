import uuid

from pydantic import BaseModel

class TransferCreateSchema(BaseModel):
    from_id: uuid.UUID
    to_id: uuid.UUID
    amount: int
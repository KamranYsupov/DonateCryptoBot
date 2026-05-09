from uuid import UUID

from pydantic import BaseModel


class CreateContestSchema(BaseModel):
    sponsor_user_id: int
    contest_id: UUID
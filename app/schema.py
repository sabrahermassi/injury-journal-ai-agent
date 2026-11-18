from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Injury(BaseModel):
    injury: Text | None
    body_part: Text | None
    severity: int | None = Field(ge=1, le=10)
    cause: Text | None
    date: str | None
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

EMAIL_PATTERN = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
FILENAME_PATTERN = r"^[A-Za-z0-9._\- ]{1,100}$"


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class EmailSummary(StrictSchema):
    recipient: str = Field(pattern=EMAIL_PATTERN)
    filename: str = Field(pattern=FILENAME_PATTERN)


SCHEMAS: dict[str, type[StrictSchema]] = {
    "EmailSummary": EmailSummary,
}


def register(name: str, schema: type[StrictSchema]) -> None:
    SCHEMAS[name] = schema


def get(name: str) -> type[StrictSchema]:
    try:
        return SCHEMAS[name]
    except KeyError as e:
        raise KeyError(f"unknown schema '{name}'") from e

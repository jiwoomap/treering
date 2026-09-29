from __future__ import annotations

from dataclasses import dataclass
from typing import Any

PUBLIC = "*"
USER = "user"


@dataclass(frozen=True)
class Tagged:
    value: Any
    sources: frozenset[str]
    readers: frozenset[str]

    @classmethod
    def from_user(cls, value: Any) -> Tagged:
        return cls(value=value, sources=frozenset({USER}), readers=frozenset({PUBLIC}))

    def is_public(self) -> bool:
        return PUBLIC in self.readers

    def readable_by(self, principal: str) -> bool:
        return self.is_public() or principal in self.readers

    def derive(self, value: Any) -> Tagged:
        return Tagged(value=value, sources=self.sources, readers=self.readers)


def merge(tags: list[Tagged]) -> tuple[frozenset[str], frozenset[str]]:
    if not tags:
        return frozenset({USER}), frozenset({PUBLIC})
    sources: set[str] = set()
    readers: set[str] | None = None
    for t in tags:
        sources |= t.sources
        if t.is_public():
            continue
        readers = set(t.readers) if readers is None else readers & set(t.readers)
    return frozenset(sources), frozenset({PUBLIC}) if readers is None else frozenset(readers)


def tool_source(tool_name: str) -> str:
    return f"tool:{tool_name}"

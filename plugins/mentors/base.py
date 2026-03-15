from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class MentorClient(Protocol):
    def available(self) -> bool: ...

    def generate_text(self, prompt: str, model: str | None = None) -> str: ...


def generate_text_via_mentor(mentor: MentorClient | object | None, prompt: str) -> str:
    if mentor is None:
        raise RuntimeError("Mentor handle not found.")

    if hasattr(mentor, "generate_text"):
        return mentor.generate_text(prompt)

    if callable(mentor):
        return mentor(prompt)

    raise RuntimeError("Mentor handle does not expose generate_text() or __call__().")

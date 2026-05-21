"""Programme info shown in the overlay."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProgramInfo:
    title: str
    subtitle: str = ""
    description: str = ""

"""Shared data models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Country:
    name: str
    code: str
    flag: str

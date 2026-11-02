"""Horloges : la vraie, et une horloge figée pour les tests."""

from __future__ import annotations

from datetime import UTC, date, datetime


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)

    def today(self) -> date:
        return self.now().date()


class FixedClock:
    """Horloge figée : rend les tests reproductibles."""

    def __init__(self, at: datetime) -> None:
        if at.tzinfo is None:
            raise ValueError("FixedClock attend une date avec fuseau (UTC)")
        self.at = at

    def now(self) -> datetime:
        return self.at

    def today(self) -> date:
        return self.at.date()

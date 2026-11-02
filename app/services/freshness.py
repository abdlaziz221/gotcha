"""Fraîcheur : une fiche ou un piège non confirmé depuis 90 jours est « à revérifier »."""

from __future__ import annotations

from datetime import date

REVIEW_AFTER_DAYS = 90


def needs_review(
    last_confirmed_on: date, today: date, *, after_days: int = REVIEW_AFTER_DAYS
) -> bool:
    return (today - last_confirmed_on).days > after_days

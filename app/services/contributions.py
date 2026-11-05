"""Contributions, relecture et confirmations « ça marche encore ». Responsable : Abdoul Aziz."""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable, Sequence

from pydantic import ValidationError

from app.domain.errors import InvalidInputError, NotFoundError, SecretDetectedError
from app.domain.models import (
    Confirmation,
    Contribution,
    ContributionInput,
    ContributionStatus,
    TargetKind,
)
from app.domain.ports import Clock, ContributionStore
from app.security.secrets import SecretFinding
from app.services.fiches import FicheService

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

Scanner = Callable[[str], Sequence[SecretFinding]]


class ContributionService:
    def __init__(
        self,
        store: ContributionStore,
        fiches: FicheService,
        clock: Clock,
        *,
        scan: Scanner,
    ) -> None:
        self._store = store
        self._fiches = fiches
        self._clock = clock
        self._scan = scan

    async def submit(self, data: ContributionInput) -> Contribution:
        """Enregistre une contribution « en attente de relecture ».

        Refuse tout texte qui ressemble à une clé ou à un jeton : le secret n'est
        jamais stocké, l'auteur doit le retirer et renvoyer.
        """
        await self._fiches.get(data.fiche_slug)
        if not _EMAIL_RE.match(data.email):
            raise InvalidInputError("Adresse e-mail invalide.")
        text = "\n".join([data.title, data.body_md, str(data.source_url or "")])
        findings = self._scan(text)
        if findings:
            raise SecretDetectedError(sorted({f.kind for f in findings}))
        contribution = Contribution(
            id=uuid.uuid4().hex,
            created_at=self._clock.now(),
            **data.model_dump(),
        )
        await self._store.add_contribution(contribution)
        return contribution

    async def confirm(
        self,
        target_kind: TargetKind,
        target_id: str,
        *,
        still_works: bool = True,
        api_version: str | None = None,
        pseudo: str | None = None,
    ) -> Confirmation:
        fiche_slug = target_id.split(".", 1)[0]
        fiche = await self._fiches.get(fiche_slug)
        if target_kind is TargetKind.GOTCHA and fiche.find_gotcha(target_id) is None:
            raise NotFoundError(f"Piège introuvable : {target_id}")
        if target_kind is TargetKind.FICHE and target_id != fiche.slug:
            raise NotFoundError(f"Fiche introuvable : {target_id}")
        try:
            confirmation = Confirmation(
                target_kind=target_kind,
                target_id=target_id,
                still_works=still_works,
                api_version=api_version or None,
                pseudo=pseudo or None,
                created_at=self._clock.now(),
            )
        except ValidationError as exc:
            raise InvalidInputError("Pseudo ou version invalide.") from exc
        await self._store.add_confirmation(confirmation)
        return confirmation

    async def pending(self) -> list[Contribution]:
        return await self._store.list_contributions(status=ContributionStatus.PENDING)

    async def review(
        self,
        contribution_id: str,
        *,
        approve: bool,
        reviewer: str,
        note: str | None = None,
    ) -> Contribution:
        contribution = await self._store.get_contribution(contribution_id)
        if contribution is None:
            raise NotFoundError(f"Contribution introuvable : {contribution_id}")
        if contribution.status is not ContributionStatus.PENDING:
            raise InvalidInputError("Cette contribution a déjà été relue.")
        reviewed = contribution.model_copy(
            update={
                "status": ContributionStatus.APPROVED if approve else ContributionStatus.REJECTED,
                "reviewed_at": self._clock.now(),
                "reviewer": reviewer,
                "review_note": note or None,
            }
        )
        if not await self._store.update_contribution(reviewed):
            # Un autre relecteur a décidé entre la lecture et l'écriture.
            raise InvalidInputError("Cette contribution a déjà été relue.")
        return reviewed

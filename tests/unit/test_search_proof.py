"""La section Preuve est cherchable : un message d'erreur exact cité en preuve est trouvé."""

from __future__ import annotations

from app.domain.models import ConfidenceLevel, SearchHitKind, SearchQuery
from app.stores.content_files import load_fiches
from app.stores.search import search_fiches
from tests.conftest import TEST_CONTENT_DIR


def test_an_error_message_quoted_only_in_the_proof_is_found() -> None:
    fiche = next(f for f in load_fiches(TEST_CONTENT_DIR) if f.gotchas)
    gotcha = fiche.gotchas[0].model_copy(
        update={
            "confidence": ConfidenceLevel.REPRODUCED,
            "proof_md": "Réponse du bac à sable : `ZXQ-INTROUVABLE-9123`.",
        }
    )
    fiche = fiche.model_copy(update={"gotchas": [gotcha, *fiche.gotchas[1:]]})
    hits = search_fiches([fiche], SearchQuery(text="ZXQ-INTROUVABLE-9123"))
    assert [h.kind for h in hits] == [SearchHitKind.GOTCHA]

"""Relecture des contributions (réservée aux relecteurs, voir app/security/auth.py)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import RedirectResponse, Response

from app.security.auth import require_reviewer
from app.security.csrf import verify_csrf
from app.web.deps import ServicesDep, flash_from
from app.web.forms import form_values
from app.web.presenters import confirmation_view, contribution_view
from app.web.templating import render
from app.web.viewmodels import PageMeta, ReviewPage

router = APIRouter()

Reviewer = Annotated[str, Depends(require_reviewer)]


@router.get("/relecture")
async def review_list(request: Request, services: ServicesDep, reviewer: Reviewer) -> Response:
    titles = {f.slug: f.title for f in await services.fiches.list()}
    page = ReviewPage(
        meta=PageMeta(title="Relecture des contributions", path="/relecture", noindex=True),
        reviewer=reviewer,
        pending=[contribution_view(c, titles) for c in await services.contributions.pending()],
        flash=flash_from(request),
        confirmations=[
            confirmation_view(c) for c in await services.contributions.recent_confirmations()
        ],
    )
    return render(request, "pages/review.html", page)


@router.post("/relecture/{contribution_id}", dependencies=[Depends(verify_csrf)])
async def review_decide(
    request: Request, contribution_id: str, services: ServicesDep, reviewer: Reviewer
) -> Response:
    values = form_values(await request.form(), ("action", "note"))
    if values["action"] not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Action inconnue.")
    await services.contributions.review(
        contribution_id,
        approve=values["action"] == "approve",
        reviewer=reviewer,
        note=values["note"][:500] or None,
    )
    return RedirectResponse("/relecture?ok=relecture", status_code=303)

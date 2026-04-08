from __future__ import annotations

# Report upload and triage-result routes live on the shared API router so both
# the current workflow and the production contract stay aligned.
from app.routers.api import router

__all__ = ["router"]

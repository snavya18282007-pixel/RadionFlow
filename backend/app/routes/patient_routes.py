from __future__ import annotations

# Patient workflow routes are implemented on the shared API router to preserve
# the existing project structure while exposing the contract expected by the UI.
from app.routers.api import router

__all__ = ["router"]

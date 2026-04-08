from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import Patient

TOKEN_PREFIX = "TKN"
TOKEN_WIDTH = 4
TOKEN_PATTERN = re.compile(r"^TKN-(\d+)$")


class TokenService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def next_patient_token(self) -> str:
        result = await self.db.execute(select(Patient.token_number))
        current_max = 0
        for token_number in result.scalars():
            if not token_number:
                continue
            match = TOKEN_PATTERN.match(token_number.strip().upper())
            if not match:
                continue
            current_max = max(current_max, int(match.group(1)))

        next_value = current_max + 1
        return f"{TOKEN_PREFIX}-{next_value:0{TOKEN_WIDTH}d}"

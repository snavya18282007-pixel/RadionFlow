from __future__ import annotations

import uuid
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

logger = logging.getLogger(__name__)


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_email(self, email: str) -> User | None:
        try:
            result = await self.db.execute(select(User).where(User.email == email))
            return result.scalar_one_or_none()
        except Exception as exc:
            logger.exception("Failed to fetch user by email", exc_info=exc)
            raise

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        try:
            result = await self.db.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()
        except Exception as exc:
            logger.exception("Failed to fetch user by id", exc_info=exc)
            raise

    async def create_user(
        self,
        *,
        email: str,
        password_hash: str,
        role: str,
        display_name: str | None = None,
    ) -> User:
        user = User(
            email=email,
            password_hash=password_hash,
            role=role,
            display_name=display_name,
        )
        self.db.add(user)

        try:
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except Exception as exc:
            await self.db.rollback()
            logger.exception("Failed to create user", exc_info=exc)
            raise

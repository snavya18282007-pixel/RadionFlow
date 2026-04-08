from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories.user_repo import UserRepository
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, UserResponse


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.user_repo = UserRepository(db)
        self.settings = get_settings()

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def _normalize_display_name(display_name: str | None, email: str) -> str:
        cleaned = (display_name or "").strip()
        return cleaned or email.split("@", 1)[0]

    async def register_user(self, payload: RegisterRequest) -> UserResponse:
        expected_access_code = (self.settings.admin_access_code or "").strip()
        provided_access_code = (payload.access_code or "").strip()
        if expected_access_code and provided_access_code != expected_access_code:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin access code")

        email = self._normalize_email(str(payload.email))
        existing_user = await self.user_repo.get_by_email(email)
        if existing_user:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with this email already exists")

        user = await self.user_repo.create_user(
            email=email,
            password_hash=hash_password(payload.password),
            role=payload.role,
            display_name=self._normalize_display_name(payload.display_name, email),
        )

        return UserResponse(
            id=user.id,
            email=user.email,
            role=user.role,
            display_name=user.display_name,
            created_at=user.created_at,
        )

    async def login_user(self, payload: LoginRequest) -> LoginResponse:
        email = self._normalize_email(str(payload.email))
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

        if user.role != payload.role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Selected role does not match this account")

        display_name = self._normalize_display_name(user.display_name, user.email)
        token = create_access_token(
            user_id=user.id,
            role=user.role,
            display_name=display_name,
            email=user.email,
        )
        return LoginResponse(
            token=token,
            role=user.role,
            display_name=display_name,
            email=user.email,
        )

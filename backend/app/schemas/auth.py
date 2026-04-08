from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


UserRole = Literal["doctor", "lab_technician"]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    display_name: str | None = Field(default=None, max_length=120)
    access_code: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    role: UserRole
    display_name: str | None = None
    created_at: datetime


class LoginResponse(BaseModel):
    token: str
    role: UserRole
    display_name: str
    email: EmailStr

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, model_validator


class PatientRegistrationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: str | None = Field(default=None, validation_alias=AliasChoices("name", "patient_name"))
    patient_name: str | None = None
    email: EmailStr
    age: int = Field(ge=0, le=120)
    gender: str = Field(min_length=1)
    patient_type: str = Field(default="Outpatient", min_length=1)

    @model_validator(mode="after")
    def normalize_fields(self) -> "PatientRegistrationRequest":
        resolved_name = (self.name or self.patient_name or "").strip()
        if not resolved_name:
            raise ValueError("Patient name is required")

        self.name = resolved_name
        self.patient_name = resolved_name
        self.email = str(self.email).strip().lower()
        self.gender = self.gender.strip()
        self.patient_type = (self.patient_type or "Outpatient").strip() or "Outpatient"
        return self


class PatientRegistrationResponse(BaseModel):
    patient_id: UUID | None = None
    patient_token: str
    token_number: str | None = None
    patient_name: str
    name: str | None = None
    email: str | None = None
    age: int
    gender: str
    patient_type: str
    created_at: datetime


class PatientCreateResponse(PatientRegistrationResponse):
    id: UUID | None = None
    token_number: str
    name: str

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import Patient

logger = logging.getLogger(__name__)


class PatientRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_patient(
        self,
        *,
        token: str,
        patient_name: str,
        email: str,
        age: int,
        gender: str,
        patient_type: str,
    ) -> Patient:
        patient = Patient(
            id=uuid.uuid4(),
            token=token,
            token_number=token,
            patient_name=patient_name,
            name=patient_name,
            email=email,
            age=age,
            gender=gender,
            patient_type=patient_type,
        )
        try:
            self.db.add(patient)
            await self.db.commit()
            await self.db.refresh(patient)
            return patient
        except Exception as exc:
            await self.db.rollback()
            logger.exception("Failed to create patient", exc_info=exc)
            raise

    async def get_patient(self, token: str) -> Patient | None:
        try:
            result = await self.db.execute(select(Patient).where(Patient.token == token))
            return result.scalar_one_or_none()
        except Exception as exc:
            logger.exception("Failed to fetch patient", exc_info=exc)
            raise

    async def list_patients(self) -> list[Patient]:
        try:
            result = await self.db.execute(select(Patient).order_by(Patient.created_at.desc()))
            return list(result.scalars().all())
        except Exception as exc:
            logger.exception("Failed to list patients", exc_info=exc)
            raise

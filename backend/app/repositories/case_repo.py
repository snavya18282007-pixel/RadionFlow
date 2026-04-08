from __future__ import annotations

import uuid
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import TriageCase

logger = logging.getLogger(__name__)


class CaseRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_case(
        self,
        report_id: uuid.UUID,
        *,
        patient_name: str,
        patient_token: str,
        patient_email: str | None = None,
        patient_age: int | None = None,
        patient_gender: str | None = None,
        patient_type: str | None = None,
        upload_metadata: dict | None = None,
    ) -> TriageCase:
        try:
            triage_case = TriageCase(
                report_id=report_id,
                patient_name=patient_name,
                patient_token=patient_token,
                patient_email=patient_email,
                patient_age=patient_age,
                patient_gender=patient_gender,
                patient_type=patient_type,
                report_status="UPLOADED",
                upload_metadata=upload_metadata or {},
            )
            self.db.add(triage_case)
            await self.db.commit()
            await self.db.refresh(triage_case)
            return triage_case
        except Exception as exc:
            await self.db.rollback()
            logger.exception("Failed to create triage case", exc_info=exc)
            raise

    async def get_case(self, report_id: uuid.UUID) -> TriageCase | None:
        try:
            result = await self.db.execute(select(TriageCase).where(TriageCase.report_id == report_id))
            return result.scalar_one_or_none()
        except Exception as exc:
            logger.exception("Failed to fetch triage case", exc_info=exc)
            raise

    async def list_cases(self, report_status: str | None = None, patient_token: str | None = None) -> list[TriageCase]:
        try:
            statement = select(TriageCase)
            if report_status:
                statement = statement.where(TriageCase.report_status == report_status)
            if patient_token:
                statement = statement.where(TriageCase.patient_token == patient_token)
            result = await self.db.execute(statement.order_by(TriageCase.created_at.desc()))
            return result.scalars().all()
        except Exception as exc:
            logger.exception("Failed to list triage cases", exc_info=exc)
            raise

    async def update_case(self, report_id: uuid.UUID, **changes) -> TriageCase:
        triage_case = await self.get_case(report_id)
        if not triage_case:
            raise ValueError("Triage case not found")

        for key, value in changes.items():
            setattr(triage_case, key, value)

        triage_case.updated_at = datetime.utcnow()

        try:
            await self.db.commit()
            await self.db.refresh(triage_case)
            return triage_case
        except Exception as exc:
            await self.db.rollback()
            logger.exception("Failed to update triage case", exc_info=exc)
            raise

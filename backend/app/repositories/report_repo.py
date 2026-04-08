from __future__ import annotations

import uuid
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import Report, ReportResult, TriageResult

logger = logging.getLogger(__name__)


class ReportRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_report(
        self,
        source_type: str,
        raw_text: str,
        *,
        patient_id: uuid.UUID | None = None,
        patient_token: str | None = None,
        file_url: str | None = None,
        modality: str | None = None,
        status: str = "UPLOADED",
    ) -> Report:
        try:
            report = Report(
                source_type=source_type,
                raw_text=raw_text,
                patient_id=patient_id,
                patient_token=patient_token,
                file_url=file_url,
                modality=modality,
                status=status,
            )
            self.db.add(report)
            await self.db.commit()
            await self.db.refresh(report)
            return report
        except Exception as exc:
            await self.db.rollback()
            logger.exception("Failed to create report", exc_info=exc)
            raise

    async def get_report(self, report_id: uuid.UUID) -> Report | None:
        try:
            result = await self.db.execute(select(Report).where(Report.id == report_id))
            return result.scalar_one_or_none()
        except Exception as exc:
            logger.exception("Failed to fetch report", exc_info=exc)
            raise

    async def create_result(self, report_id: uuid.UUID, payload: dict) -> ReportResult:
        try:
            result = ReportResult(report_id=report_id, **payload)
            self.db.add(result)
            await self.db.commit()
            await self.db.refresh(result)
            return result
        except Exception as exc:
            await self.db.rollback()
            logger.exception("Failed to create report result", exc_info=exc)
            raise

    async def create_triage_result(
        self,
        report_id: uuid.UUID,
        *,
        disease_prediction: str,
        confidence_score: float,
        urgency_level: str,
        explanation: str,
    ) -> TriageResult:
        try:
            existing_result = await self.get_triage_result(report_id)
            if existing_result:
                existing_result.disease_prediction = disease_prediction
                existing_result.confidence_score = confidence_score
                existing_result.urgency_level = urgency_level
                existing_result.explanation = explanation
                await self.db.commit()
                await self.db.refresh(existing_result)
                return existing_result

            result = TriageResult(
                report_id=report_id,
                disease_prediction=disease_prediction,
                confidence_score=confidence_score,
                urgency_level=urgency_level,
                explanation=explanation,
            )
            self.db.add(result)
            await self.db.commit()
            await self.db.refresh(result)
            return result
        except Exception as exc:
            await self.db.rollback()
            logger.exception("Failed to create triage result", exc_info=exc)
            raise

    async def get_result(self, report_id: uuid.UUID) -> ReportResult | None:
        try:
            result = await self.db.execute(
                select(ReportResult)
                .where(ReportResult.report_id == report_id)
                .order_by(ReportResult.created_at.desc())
            )
            return result.scalars().first()
        except Exception as exc:
            logger.exception("Failed to fetch report result", exc_info=exc)
            raise

    async def get_triage_result(self, report_id: uuid.UUID) -> TriageResult | None:
        try:
            result = await self.db.execute(
                select(TriageResult)
                .where(TriageResult.report_id == report_id)
                .order_by(TriageResult.created_at.desc())
            )
            return result.scalars().first()
        except Exception as exc:
            logger.exception("Failed to fetch triage result", exc_info=exc)
            raise

    async def update_report(self, report_id: uuid.UUID, **changes) -> Report:
        report = await self.get_report(report_id)
        if not report:
            raise ValueError("Report not found")

        for key, value in changes.items():
            setattr(report, key, value)

        try:
            await self.db.commit()
            await self.db.refresh(report)
            return report
        except Exception as exc:
            await self.db.rollback()
            logger.exception("Failed to update report", exc_info=exc)
            raise

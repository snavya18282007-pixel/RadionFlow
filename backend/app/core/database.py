from __future__ import annotations

from collections.abc import AsyncGenerator
import logging
import uuid

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings, redact_database_url

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


_settings = get_settings()
_database_url = _settings.resolved_database_url
_active_database_url = _database_url
_database_fallback_active = False


def _build_engine(database_url: str):
    return create_async_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"timeout": 15} if database_url.startswith("postgresql+asyncpg://") else {},
    )


_engine = _build_engine(_database_url)
_SessionLocal = async_sessionmaker(bind=_engine, class_=AsyncSession, expire_on_commit=False)


async def _set_runtime_database(database_url: str, *, fallback_active: bool) -> None:
    global _engine, _SessionLocal, _active_database_url, _database_fallback_active

    if _active_database_url == database_url and _database_fallback_active == fallback_active:
        return

    await _engine.dispose()
    _engine = _build_engine(database_url)
    _SessionLocal = async_sessionmaker(bind=_engine, class_=AsyncSession, expire_on_commit=False)
    _active_database_url = database_url
    _database_fallback_active = fallback_active


def _ensure_column(sync_conn, table_name: str, column_name: str, ddl: str) -> None:
    columns = {column["name"] for column in inspect(sync_conn).get_columns(table_name)}
    if column_name not in columns:
        sync_conn.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN {ddl}")


def _run_compatibility_migrations(sync_conn) -> None:
    dialect = sync_conn.dialect.name
    tables = set(inspect(sync_conn).get_table_names())
    json_type = "JSONB" if dialect == "postgresql" else "JSON"

    if "patients" in tables:
        uuid_type = "UUID" if dialect == "postgresql" else "VARCHAR(36)"
        _ensure_column(sync_conn, "patients", "id", f"id {uuid_type}")
        _ensure_column(sync_conn, "patients", "token_number", "token_number VARCHAR(32)")
        _ensure_column(sync_conn, "patients", "name", "name VARCHAR(120)")
        _ensure_column(sync_conn, "patients", "email", "email VARCHAR(255)")

        rows = sync_conn.exec_driver_sql(
            "SELECT token, patient_name, id, token_number, name, email FROM patients"
        ).fetchall()
        for token, patient_name, patient_id, token_number, name, email in rows:
            resolved_id = patient_id or uuid.uuid4()
            if dialect != "postgresql":
                resolved_id = str(resolved_id)
            sync_conn.execute(
                text(
                    "UPDATE patients SET id = :id, token_number = :token_number, name = :name, email = :email "
                    "WHERE token = :token"
                ),
                {
                    "id": resolved_id,
                    "token_number": token_number or token,
                    "name": name or patient_name,
                    "email": email,
                    "token": token,
                },
            )

    if "reports" in tables:
        uuid_type = "UUID" if dialect == "postgresql" else "VARCHAR(36)"
        _ensure_column(sync_conn, "reports", "patient_id", f"patient_id {uuid_type}")
        _ensure_column(sync_conn, "reports", "patient_token", "patient_token VARCHAR(32)")
        _ensure_column(sync_conn, "reports", "file_url", "file_url TEXT")
        _ensure_column(sync_conn, "reports", "modality", "modality VARCHAR(32)")
        _ensure_column(sync_conn, "reports", "status", "status VARCHAR(32)")
        sync_conn.exec_driver_sql("UPDATE reports SET status = COALESCE(status, 'UPLOADED')")

    if "triage_cases" in tables:
        _ensure_column(sync_conn, "triage_cases", "patient_email", "patient_email VARCHAR(255)")

    if "report_results" in tables:
        _ensure_column(sync_conn, "report_results", "patient_explanation", f"patient_explanation {json_type}")
        _ensure_column(sync_conn, "report_results", "trend_analysis", f"trend_analysis {json_type}")
        _ensure_column(sync_conn, "report_results", "critical_alerts", f"critical_alerts {json_type}")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _SessionLocal() as session:
        try:
            yield session
        except SQLAlchemyError:
            await session.rollback()
            raise


async def ping_database() -> None:
    async with _engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def _initialize_active_database() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_run_compatibility_migrations)


def _should_use_fallback() -> bool:
    environment = _settings.environment.strip().lower()
    primary_url = _settings.resolved_database_url
    fallback_url = _settings.resolved_database_fallback_url
    return (
        _settings.database_allow_fallback
        and environment != "prod"
        and primary_url != fallback_url
        and primary_url.startswith("postgresql+asyncpg://")
    )


async def initialize_database() -> None:
    try:
        await _initialize_active_database()
        logger.info("Database initialized", extra={"database_url": redact_database_url(_active_database_url)})
    except Exception as exc:
        if _should_use_fallback():
            fallback_url = _settings.resolved_database_fallback_url
            failed_database_url = _active_database_url
            logger.warning(
                "Primary database initialization failed; retrying with local fallback",
                extra={
                    "failed_database_url": redact_database_url(failed_database_url),
                    "fallback_database_url": redact_database_url(fallback_url),
                },
                exc_info=exc,
            )
            try:
                await _set_runtime_database(fallback_url, fallback_active=True)
                await _initialize_active_database()
                logger.warning(
                    "Database initialized using fallback",
                    extra={"database_url": redact_database_url(_active_database_url)},
                )
                return
            except Exception as fallback_exc:
                logger.exception("Fallback database initialization failed", exc_info=fallback_exc)
                raise RuntimeError(
                    f"Unable to initialize database at {redact_database_url(failed_database_url)} "
                    f"or fallback {redact_database_url(fallback_url)}"
                ) from fallback_exc

        logger.exception("Database initialization failed", exc_info=exc)
        raise RuntimeError(f"Unable to initialize database at {redact_database_url(_active_database_url)}") from exc


def get_database_runtime_info() -> dict[str, object]:
    return {
        "database_url": redact_database_url(_active_database_url),
        "fallback_active": _database_fallback_active,
    }


def get_engine():
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return _SessionLocal

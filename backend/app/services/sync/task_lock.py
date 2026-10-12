import hashlib
import json
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.exceptions import TaskAlreadyRunningError, UniqueKeyMigrationConflictError
from app.schemas.tushare import WriteMode


def build_task_key(
    *,
    api_name: str,
    params: dict[str, Any],
    fields: list[str],
    write_mode: WriteMode,
) -> str:
    canonical = json.dumps(
        {
            "api_name": api_name,
            "params": params,
            "fields": sorted(set(fields)),
            "write_mode": write_mode.value,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class TaskLockService:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @asynccontextmanager
    async def acquire(self, task_key: str):
        lock_id = int.from_bytes(bytes.fromhex(task_key)[:8], byteorder="big", signed=True)
        async with self._engine.connect() as connection:
            acquired = bool(
                await connection.scalar(
                    text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": lock_id}
                )
            )
            if not acquired:
                raise TaskAlreadyRunningError(
                    "An identical sync task is already running.",
                    details={"task_key": task_key},
                )
            try:
                yield
            finally:
                await connection.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": lock_id}
                )


class ApiMutationLockService:
    """Serializes sync and unique-key migration for one API across processes."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @asynccontextmanager
    async def acquire(self, api_name: str, *, operation: str):
        digest = hashlib.sha256(f"api-mutation:{api_name}".encode()).digest()
        lock_id = int.from_bytes(digest[:8], byteorder="big", signed=True)
        async with self._engine.connect() as connection:
            acquired = bool(
                await connection.scalar(
                    text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": lock_id}
                )
            )
            if not acquired:
                raise UniqueKeyMigrationConflictError(
                    "该 API 正在执行同步或唯一键迁移，请稍后重试。",
                    details={"api_name": api_name, "operation": operation},
                )
            try:
                yield
            finally:
                await connection.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": lock_id}
                )

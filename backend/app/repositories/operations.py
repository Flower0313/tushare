from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.metadata import ApiMetadata, ApiValidationResult, DataOperation, Execution


class DataOperationRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_with_execution(
        self,
        execution: Execution,
        *,
        operation_type: str,
        api_name: str,
        filters: list[dict[str, object]],
        request: dict[str, object],
        matched_rows: int,
        status: str,
    ) -> DataOperation:
        now = datetime.now(UTC)
        operation = DataOperation(
            id=uuid4(),
            operation_type=operation_type,
            api_name=api_name,
            filters=filters,
            request=request,
            matched_rows=matched_rows,
            execution_id=execution.id,
            status=status,
            created_at=now,
            updated_at=now,
        )
        execution.data_operation_id = operation.id
        async with self._session_factory() as session, session.begin():
            session.add_all([operation, execution])
        return operation

    async def get(self, operation_id: UUID) -> DataOperation | None:
        async with self._session_factory() as session:
            return await session.get(DataOperation, operation_id)

    async def update(self, operation_id: UUID, **values: object) -> None:
        async with self._session_factory() as session, session.begin():
            record = await session.get(DataOperation, operation_id, with_for_update=True)
            if record is None:
                return
            for key, value in values.items():
                setattr(record, key, value)
            record.updated_at = datetime.now(UTC)

    async def list(
        self, *, page: int, page_size: int, api_name: str | None = None
    ) -> tuple[list[DataOperation], int]:
        filters = [DataOperation.api_name == api_name] if api_name else []
        statement = (
            select(DataOperation)
            .where(*filters)
            .order_by(DataOperation.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        count = select(func.count()).select_from(DataOperation).where(*filters)
        async with self._session_factory() as session:
            return (
                list((await session.scalars(statement)).all()),
                int(await session.scalar(count) or 0),
            )

    async def failed_after_delete_count(self) -> int:
        statement = (
            select(func.count())
            .select_from(DataOperation)
            .where(
                DataOperation.status.in_(
                    {
                        "FAILED_AFTER_DELETE",
                        "RESET_SYNC_FAILED",
                        "INCOMPLETE",
                        "VALIDATION_FAILED",
                    }
                )
            )
        )
        async with self._session_factory() as session:
            return int(await session.scalar(statement) or 0)


class ApiValidationResultRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create_with_execution(
        self, execution: Execution, *, api_name: str, scenario: str, notes: str | None = None
    ) -> ApiValidationResult:
        result = ApiValidationResult(
            id=uuid4(),
            api_name=api_name,
            scenario=scenario,
            status="PENDING",
            execution_id=execution.id,
            validated_at=datetime.now(UTC),
            notes=notes,
        )
        execution.validation_result_id = result.id
        async with self._session_factory() as session, session.begin():
            session.add_all([result, execution])
        return result

    async def update(self, result_id: UUID, **values: object) -> None:
        api_name: str | None = None
        async with self._session_factory() as session, session.begin():
            result = await session.get(ApiValidationResult, result_id)
            if result is None:
                return
            api_name = result.api_name
            for key, value in values.items():
                setattr(result, key, value)
            result.validated_at = datetime.now(UTC)
        if api_name:
            await self.refresh_api_status(api_name)

    async def refresh_api_status(self, api_name: str) -> str:
        async with self._session_factory() as session, session.begin():
            metadata = await session.get(ApiMetadata, api_name, with_for_update=True)
            if metadata is None:
                return "METADATA_VERIFIED"
            configured = {
                str(item.get("name") or "default")
                for item in list(metadata.validation_scenarios or [])
            }
            rows = list(
                (
                    await session.execute(
                        select(ApiValidationResult.scenario, ApiValidationResult.status).where(
                            ApiValidationResult.api_name == api_name
                        )
                    )
                ).all()
            )
            successful = {scenario for scenario, status in rows if status == "SUCCESS"}
            has_real_result = any(status in {"SUCCESS", "EMPTY"} for _, status in rows)
            if configured and configured.issubset(successful):
                level = "PRODUCTION_VALIDATED"
            elif has_real_result:
                level = "REAL_DATA_PARTIAL"
            else:
                level = "METADATA_VERIFIED"
            metadata.validation_status = level
            return level

    async def list(self, *, page: int, page_size: int) -> tuple[list[ApiValidationResult], int]:
        statement = (
            select(ApiValidationResult)
            .order_by(ApiValidationResult.validated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        async with self._session_factory() as session:
            items = list((await session.scalars(statement)).all())
            total = int(
                await session.scalar(select(func.count()).select_from(ApiValidationResult)) or 0
            )
        return items, total

    async def pending_api_count(self) -> int:
        statement = select(func.count(func.distinct(ApiValidationResult.api_name))).where(
            ApiValidationResult.status != "SUCCESS"
        )
        async with self._session_factory() as session:
            return int(await session.scalar(statement) or 0)

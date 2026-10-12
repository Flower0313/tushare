from collections.abc import Sequence

from sqlalchemy import MetaData, Table, select
from sqlalchemy.exc import NoSuchTableError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.exceptions import MetadataError
from app.services.sync.identifiers import validate_identifier


class PostgresCodeSource:
    """Loads codes from a Metadata-approved Tushare table."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def load(
        self,
        *,
        source: str,
        field: str = "ts_code",
        status_field: str | None = "list_status",
        status_values: Sequence[str] = ("L",),
    ) -> list[str]:
        validate_identifier(source, kind="table")
        validate_identifier(field, kind="column")
        if status_field:
            validate_identifier(status_field, kind="column")
        try:
            async with self._engine.connect() as connection:
                table = await connection.run_sync(
                    lambda sync_connection: Table(
                        source,
                        MetaData(),
                        schema="tushare",
                        autoload_with=sync_connection,
                    )
                )
                if field not in table.c:
                    raise MetadataError(f"Code source tushare.{source} has no {field} column")
                statement = select(table.c[field]).where(table.c[field].is_not(None)).distinct()
                if status_field and status_field in table.c and status_values:
                    statement = statement.where(table.c[status_field].in_(list(status_values)))
                values = (await connection.execute(statement)).scalars().all()
        except NoSuchTableError as exc:
            raise MetadataError(
                f"Code source tushare.{source} does not exist; sync it before this API"
            ) from exc
        except SQLAlchemyError as exc:
            raise MetadataError(f"Unable to read code source tushare.{source}") from exc
        codes = sorted({str(value).strip() for value in values if str(value).strip()})
        if not codes:
            raise MetadataError(f"Code source tushare.{source} contains no usable codes")
        return codes

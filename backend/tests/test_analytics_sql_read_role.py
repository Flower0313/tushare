import pytest

from app.core.exceptions import AnalyticsValidationError
from app.services.analytics_sql_source import assert_read_role


class FakeReadConnection:
    def __init__(
        self,
        *,
        privileged: bool = False,
        writable: bool = False,
        can_create: bool = False,
        readable_schemas: tuple[str, ...] = ("tushare",),
    ):
        self.privileged = privileged
        self.writable = writable
        self.can_create = can_create
        self.readable_schemas = readable_schemas

    async def fetchrow(self, _query: str) -> dict[str, bool]:
        return {
            "rolsuper": self.privileged,
            "rolcreaterole": False,
            "rolcreatedb": False,
            "rolreplication": False,
            "rolbypassrls": False,
        }

    async def fetchval(self, query: str) -> bool:
        return self.writable if "has_table_privilege" in query else self.can_create

    async def fetch(self, _query: str) -> list[dict[str, str]]:
        return [{"nspname": name} for name in self.readable_schemas]


@pytest.mark.asyncio
async def test_sql_reader_rejects_privileged_and_writable_roles() -> None:
    for role in (
        FakeReadConnection(privileged=True),
        FakeReadConnection(writable=True),
        FakeReadConnection(can_create=True),
        FakeReadConnection(readable_schemas=("tushare", "platform")),
    ):
        with pytest.raises(AnalyticsValidationError):
            await assert_read_role(role)


@pytest.mark.asyncio
async def test_sql_reader_accepts_unprivileged_read_only_role() -> None:
    await assert_read_role(FakeReadConnection())

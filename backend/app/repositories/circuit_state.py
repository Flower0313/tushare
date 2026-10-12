from datetime import datetime, timedelta

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.metadata import UpstreamCircuit


class CircuitStateRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def before_request(self, scope: str, now: datetime) -> tuple[bool, str]:
        async with self._session_factory() as session, session.begin():
            await session.execute(
                pg_insert(UpstreamCircuit)
                .values(
                    scope=scope,
                    state="CLOSED",
                    failure_count=0,
                    updated_at=now,
                    half_open_probe_in_flight=False,
                )
                .on_conflict_do_nothing(index_elements=[UpstreamCircuit.scope])
            )
            state = await session.get(UpstreamCircuit, scope, with_for_update=True)
            if state is None:
                return True, "CLOSED"
            if state.state == "OPEN":
                if state.open_until is not None and state.open_until > now:
                    return False, "OPEN"
                if state.half_open_probe_in_flight:
                    return False, "HALF_OPEN"
                state.state = "HALF_OPEN"
                state.half_open_probe_in_flight = True
                state.updated_at = now
                return True, "HALF_OPEN"
            if state.state == "HALF_OPEN" and state.half_open_probe_in_flight:
                return False, "HALF_OPEN"
            return True, state.state

    async def record_success(self, scope: str, now: datetime) -> None:
        async with self._session_factory() as session, session.begin():
            state = await session.get(UpstreamCircuit, scope, with_for_update=True)
            if state is None:
                return
            state.state = "CLOSED"
            state.failure_count = 0
            state.opened_at = None
            state.open_until = None
            state.half_open_probe_in_flight = False
            state.updated_at = now

    async def record_failure(
        self, scope: str, now: datetime, *, failure_threshold: int, reset_timeout: timedelta
    ) -> None:
        async with self._session_factory() as session, session.begin():
            await session.execute(
                pg_insert(UpstreamCircuit)
                .values(
                    scope=scope,
                    state="CLOSED",
                    failure_count=0,
                    updated_at=now,
                    half_open_probe_in_flight=False,
                )
                .on_conflict_do_nothing(index_elements=[UpstreamCircuit.scope])
            )
            state = await session.get(UpstreamCircuit, scope, with_for_update=True)
            if state is None:
                return
            state.failure_count += 1
            state.updated_at = now
            state.half_open_probe_in_flight = False
            if state.state == "HALF_OPEN" or state.failure_count >= failure_threshold:
                state.state = "OPEN"
                state.opened_at = now
                state.open_until = now + reset_timeout

from datetime import UTC, datetime

from sqlalchemy.dialects import postgresql

from app.models.metadata import Execution, ScheduleFire
from app.repositories.schedule import ScheduleRepository


def test_due_schedule_claim_uses_skip_locked() -> None:
    sql = str(
        ScheduleRepository.due_statement(datetime.now(UTC)).compile(dialect=postgresql.dialect())
    )
    assert "FOR UPDATE SKIP LOCKED" in sql
    assert "platform.schedule.enabled" in sql


def test_duplicate_fire_and_execution_have_database_unique_constraints() -> None:
    fire_constraints = {constraint.name for constraint in ScheduleFire.__table__.constraints}
    execution_constraints = {constraint.name for constraint in Execution.__table__.constraints}
    assert "uq_schedule_fire_scheduled_at" in fire_constraints
    assert "uq_execution_schedule_fire_time" in execution_constraints

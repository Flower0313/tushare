from sqlalchemy.dialects import postgresql

from app.repositories.execution import ExecutionRepository


def test_pending_claim_uses_for_update_skip_locked() -> None:
    sql = str(
        ExecutionRepository.pending_claim_statement().compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    ).upper()
    assert "FOR UPDATE SKIP LOCKED" in sql

from app import maintenance, scheduler, worker


def test_worker_and_scheduler_have_independent_entrypoints() -> None:
    assert callable(worker.main)
    assert callable(worker.run_worker)
    assert callable(scheduler.main)
    assert callable(scheduler.run_scheduler)
    assert callable(maintenance.main)
    assert callable(maintenance.run_maintenance)

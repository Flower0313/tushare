from pathlib import Path

ALLOWED_CONSUMERS = {"services/legacy/staging_compatibility.py"}


def test_no_new_legacy_staging_consumers() -> None:
    app_root = Path(__file__).parents[1] / "app"
    consumers: set[str] = set()
    for path in app_root.rglob("*.py"):
        relative = path.relative_to(app_root).as_posix()
        if relative.startswith("repositories/"):
            continue
        source = path.read_text(encoding="utf-8")
        if "StagingResourceRepository" in source or "ReplaceDatasetRepository" in source:
            consumers.add(relative)
    assert consumers == ALLOWED_CONSUMERS

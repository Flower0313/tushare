# Test suites

- `unit`: pure services, validators, transformers and policy tests.
- `integration`: FastAPI/ASGI and PostgreSQL boundary tests.
- `e2e`: complete local execution workflows.
- `real_upstream`: explicit opt-in checks against Tushare; excluded from the normal suite.

Commands:

```powershell
pytest
pytest -m integration
pytest -m e2e
pytest -m real_upstream
```

API tests use `httpx.AsyncClient` with `ASGITransport`; this avoids the deprecated
Starlette `TestClient` compatibility path and keeps the async boundary explicit.

from fastapi import APIRouter

from app.api.routes import (
    data,
    executions,
    health,
    metadata,
    operations,
    preview,
    replace_datasets,
    schedules,
    sync,
    unique_keys,
    validations,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(metadata.router)
api_router.include_router(preview.router)
api_router.include_router(sync.router)
api_router.include_router(unique_keys.router)
api_router.include_router(executions.router)
api_router.include_router(data.router)
api_router.include_router(replace_datasets.router)
api_router.include_router(schedules.router)
api_router.include_router(operations.router)
api_router.include_router(validations.router)

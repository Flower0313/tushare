from fastapi import APIRouter, Response, status

from app.core.config import get_settings
from app.core.database import AsyncSessionFactory
from app.repositories.runtime_secrets import RuntimeSecretRepository
from app.schemas.settings import TushareTokenStatus, TushareTokenUpdate
from app.services.tushare.credentials import TushareCredentialService

router = APIRouter(prefix="/settings", tags=["Settings"])


def _service() -> TushareCredentialService:
    return TushareCredentialService(RuntimeSecretRepository(AsyncSessionFactory), get_settings())


@router.get("/tushare-token", response_model=TushareTokenStatus)
async def get_tushare_token_status(response: Response) -> TushareTokenStatus:
    response.headers["Cache-Control"] = "no-store"
    value = await _service().status()
    return TushareTokenStatus.model_validate(value, from_attributes=True)


@router.put("/tushare-token", response_model=TushareTokenStatus)
async def replace_tushare_token(
    payload: TushareTokenUpdate, response: Response
) -> TushareTokenStatus:
    response.headers["Cache-Control"] = "no-store"
    value = await _service().replace(payload.token.get_secret_value())
    return TushareTokenStatus.model_validate(value, from_attributes=True)


@router.delete(
    "/tushare-token",
    response_model=TushareTokenStatus,
    status_code=status.HTTP_200_OK,
)
async def restore_environment_tushare_token(response: Response) -> TushareTokenStatus:
    response.headers["Cache-Control"] = "no-store"
    value = await _service().restore_environment()
    return TushareTokenStatus.model_validate(value, from_attributes=True)

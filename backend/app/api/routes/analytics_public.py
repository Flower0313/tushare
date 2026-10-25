"""Public read interface: only active immutable revisions are addressable."""

import asyncio
import time
from collections import defaultdict, deque
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.api.dependencies import SessionDep
from app.core.database import engine
from app.repositories.analytics import AnalyticsRepository
from app.schemas.analytics import (
    ChartData,
    PublicDashboard,
    PublicOptionsRequest,
    PublicOptionsResponse,
    PublicQueryRequest,
)
from app.services.analytics_publication import (
    DashboardPublicationService,
    cookie_for,
    cookie_valid,
    verify_password,
)
from app.services.analytics_query import SqlAlchemyQueryExecutor

router = APIRouter(prefix="/public/dashboards", tags=["公开看板"])
_windows: dict[str, deque[float]] = defaultdict(deque)
_window_lock = asyncio.Lock()
_query_slots = asyncio.Semaphore(8)


def get_public_service(session: SessionDep) -> DashboardPublicationService:
    return DashboardPublicationService(
        AnalyticsRepository(session), SqlAlchemyQueryExecutor(engine)
    )


PublicService = Annotated[DashboardPublicationService, Depends(get_public_service)]


async def _rate_limit(request: Request, key: str, limit: int = 60) -> None:
    host = request.client.host if request.client else "unknown"
    now = time.monotonic()
    async with _window_lock:
        for identifier, ceiling in ((f"ip:{host}", 120), (f"key:{key}", limit)):
            window = _windows[identifier]
            while window and now - window[0] > 60:
                window.popleft()
            if len(window) >= ceiling:
                raise HTTPException(status_code=429, detail="访问过于频繁，请稍后重试")
            window.append(now)
        if len(_windows) > 10_000:
            for identifier in list(_windows):
                if not _windows[identifier] or now - _windows[identifier][-1] > 60:
                    del _windows[identifier]


async def _authorize(
    public_key: str, request: Request, service: DashboardPublicationService
) -> int:
    publication, _ = await service.active_publication(public_key)
    if publication.password_hash and not cookie_valid(
        publication, request.cookies.get("dashboard_access")
    ):
        raise HTTPException(status_code=401, detail="此看板需要访问密码")
    return publication.version


class PasswordRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)


@router.post("/{public_key}/access", status_code=204)
async def unlock_dashboard(
    public_key: str,
    payload: PasswordRequest,
    request: Request,
    response: Response,
    service: PublicService,
) -> None:
    await _rate_limit(request, f"password:{public_key}", 10)
    publication, _ = await service.active_publication(public_key)
    if not publication.password_hash or not verify_password(
        payload.password, publication.password_hash
    ):
        raise HTTPException(status_code=401, detail="访问密码不正确")
    response.set_cookie(
        "dashboard_access",
        cookie_for(publication),
        max_age=12 * 3600,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/api/public/dashboards",
    )


@router.get("/{public_key}", response_model=PublicDashboard)
async def get_public_dashboard(
    public_key: str, request: Request, response: Response, service: PublicService
) -> PublicDashboard:
    await _rate_limit(request, public_key)
    await _authorize(public_key, request, service)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return await service.public_dashboard(public_key)


@router.post("/{public_key}/charts/{chart_public_id}/query", response_model=ChartData)
async def query_public_chart(
    public_key: str,
    chart_public_id: str,
    payload: PublicQueryRequest,
    request: Request,
    response: Response,
    service: PublicService,
) -> ChartData:
    await _rate_limit(request, public_key)
    version = await _authorize(public_key, request, service)
    response.headers["Cache-Control"] = "no-store"
    async with _query_slots:
        try:
            result = await asyncio.wait_for(
                service.chart_data(public_key, chart_public_id, payload.values), timeout=15
            )
        except TimeoutError as exc:
            raise HTTPException(status_code=504, detail="看板查询超时，请缩小筛选范围") from exc
    if await _authorize(public_key, request, service) != version:
        raise HTTPException(status_code=409, detail="看板已更新，请刷新后重试")
    return result


@router.post("/{public_key}/filters/{filter_id}/options", response_model=PublicOptionsResponse)
async def public_filter_options(
    public_key: str,
    filter_id: str,
    payload: PublicOptionsRequest,
    request: Request,
    service: PublicService,
) -> PublicOptionsResponse:
    await _rate_limit(request, public_key)
    version = await _authorize(public_key, request, service)
    async with _query_slots:
        try:
            result = await asyncio.wait_for(
                service.options(public_key, filter_id, payload.search, payload.values),
                timeout=15,
            )
        except TimeoutError as exc:
            raise HTTPException(status_code=504, detail="选项查询超时") from exc
    if await _authorize(public_key, request, service) != version:
        raise HTTPException(status_code=409, detail="看板已更新，请刷新后重试")
    return result

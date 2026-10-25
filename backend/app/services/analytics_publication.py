"""Immutable published revisions; public readers never consult draft chart definitions."""

import hashlib
import hmac
import secrets
import time
from datetime import UTC, datetime

from pydantic import TypeAdapter

from app.core.config import get_settings
from app.core.exceptions import (
    AnalyticsConflictError,
    AnalyticsNotFoundError,
    AnalyticsValidationError,
)
from app.models.analytics import (
    AnalyticsDashboardPublication,
    AnalyticsDashboardRevision,
    AnalyticsDataset,
)
from app.repositories.analytics import AnalyticsRepository
from app.schemas.analytics import (
    ChartConfig,
    ChartCreate,
    ChartData,
    ControlValue,
    FilterCondition,
    ManualOption,
    PublicationRead,
    PublicationSettings,
    PublicationSnapshot,
    PublicChart,
    PublicDashboard,
    PublicOptionsResponse,
    PublicQueryControl,
    PublishedChart,
    PublishedDataset,
    QueryControl,
    SqlParameterDefinition,
)
from app.services.analytics import _chart_request
from app.services.analytics_chart_config import chart_query, validate_chart_config
from app.services.analytics_controls import (
    chart_control_inputs,
    legacy_controls,
    resolve_controls,
    validate_control_targets,
)
from app.services.analytics_pivot import pivot_result
from app.services.analytics_query import SqlAlchemyQueryExecutor
from app.services.analytics_sql_source import infer_sql_fields

_CONFIG = TypeAdapter(ChartConfig)
_INVALID = "链接已失效或已停止发布"


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return salt.hex() + ":" + digest.hex()


def verify_password(password: str, saved: str) -> bool:
    try:
        salt_hex, digest_hex = saved.split(":", 1)
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
        return hmac.compare_digest(digest, bytes.fromhex(digest_hex))
    except (ValueError, TypeError):
        return False


def cookie_for(publication: AnalyticsDashboardPublication) -> str:
    secret = get_settings().public_cookie_secret
    if not secret:
        raise AnalyticsValidationError("受密码保护的看板尚未配置 Cookie 签名密钥")
    expiry = int(time.time()) + 12 * 3600
    payload = f"{publication.id}.{publication.version}.{expiry}"
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def cookie_valid(publication: AnalyticsDashboardPublication, cookie: str | None) -> bool:
    if not cookie or not get_settings().public_cookie_secret:
        return False
    try:
        publication_id, version, expiry, signature = cookie.split(".")
        if (int(publication_id), int(version)) != (publication.id, publication.version):
            return False
        if int(expiry) < int(time.time()):
            return False
        payload = f"{publication_id}.{version}.{expiry}"
        expected = hmac.new(
            get_settings().public_cookie_secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected)
    except (ValueError, AttributeError):
        return False


def publication_status(publication: AnalyticsDashboardPublication | None) -> str:
    if publication is None:
        return "DRAFT"
    if publication.status == "REVOKED":
        return "REVOKED"
    settings = PublicationSettings.model_validate(publication.settings)
    if settings.expires_at and settings.expires_at <= datetime.now(UTC):
        return "EXPIRED"
    return "PUBLISHED"


class DashboardPublicationService:
    def __init__(self, repository: AnalyticsRepository, executor: SqlAlchemyQueryExecutor):
        self._repository = repository
        self._executor = executor

    async def management_state(self, dashboard_id: int) -> PublicationRead:
        dashboard = await self._repository.dashboard(dashboard_id)
        if not dashboard:
            raise AnalyticsNotFoundError("看板不存在")
        publication = await self._repository.publication_for_dashboard(dashboard_id)
        if not publication:
            return PublicationRead(
                dashboard_id=dashboard_id,
                public_key="",
                version=0,
                status="DRAFT",
                settings=PublicationSettings(name=dashboard.name),
            )
        settings = PublicationSettings.model_validate(publication.settings)
        base = get_settings().public_app_base_url.rstrip("/")
        return PublicationRead(
            dashboard_id=dashboard_id,
            public_key=publication.public_key,
            version=publication.version,
            status=publication_status(publication),
            settings=settings,
            published_at=publication.published_at,
            public_url=f"{base}/public/d/{publication.public_key}",
            password_required=publication.password_hash is not None,
        )

    async def publish(  # noqa: C901 - snapshot validation remains atomic
        self, dashboard_id: int, settings: PublicationSettings | None = None
    ) -> PublicationRead:
        dashboard = await self._repository.dashboard(dashboard_id)
        if not dashboard:
            raise AnalyticsNotFoundError("看板不存在")
        charts = await self._repository.charts(dashboard_id)
        if not charts:
            raise AnalyticsValidationError("发布前至少需要一张图表")
        controls = [QueryControl.model_validate(item) for item in dashboard.query_controls or []]
        datasets = []
        dataset_ids = dict.fromkeys(
            [chart.dataset_id for chart in charts]
            + [control.option_dataset_id for control in controls if control.option_dataset_id]
        )
        for dataset_id in dataset_ids:
            dataset = await self._repository.dataset(dataset_id)
            if not dataset:
                raise AnalyticsValidationError(f"图表引用的数据集 {dataset_id} 已失效")
            datasets.append(dataset)
        if not controls and dashboard.global_filters:
            controls = legacy_controls(dashboard.global_filters, charts, datasets)
        validate_control_targets(controls, charts, datasets)
        by_dataset = {item.id: item for item in datasets}
        for dataset in datasets:
            if dataset.source_type == "SQL":
                if not dataset.sql_text:
                    raise AnalyticsValidationError(f"数据集 {dataset.name} 缺少 SQL")
                parameters = [
                    SqlParameterDefinition.model_validate(item) for item in dataset.parameters or []
                ]
                await infer_sql_fields(dataset.sql_text, parameters)
                for param in parameters:
                    if not param.required or param.default_value is not None:
                        continue
                    missing_charts = [
                        chart.title
                        for chart in charts
                        if chart.dataset_id == dataset.id
                        and not any(
                            control.required
                            and any(
                                target.chart_id == chart.id
                                and target.target_type == "DATASET_PARAMETER"
                                and target.target_name == param.name
                                for target in control.targets
                            )
                            for control in controls
                        )
                    ]
                    if missing_charts:
                        raise AnalyticsValidationError(
                            f"数据集 {dataset.name} 的必填 SQL 参数 {param.label} "
                            f"未绑定图表：{'、'.join(missing_charts)}"
                        )
        published_charts = []
        for chart in charts:
            dataset = by_dataset[chart.dataset_id]
            if chart.config_version == 2:
                config = _CONFIG.validate_python(chart.config)
                validate_chart_config(dataset, config)
            published_charts.append(
                PublishedChart.model_validate(
                    {
                        **chart.definition(),
                        "public_id": secrets.token_urlsafe(12),
                    }
                )
            )
        snapshot = PublicationSnapshot(
            name=dashboard.name,
            description=dashboard.description,
            updated_at=dashboard.updated_at,
            controls=controls,
            charts=published_charts,
            datasets=[
                PublishedDataset.model_validate(
                    {
                        "id": item.id,
                        "source_type": item.source_type,
                        "api_name": item.api_name,
                        "sql_text": item.sql_text,
                        "sql_hash": item.sql_hash,
                        "fields": item.fields,
                        "parameters": item.parameters or [],
                    }
                )
                for item in datasets
            ],
        )
        publication = await self._repository.publication_for_dashboard(dashboard_id, lock=True)
        if settings is None:
            if publication is None:
                raise AnalyticsValidationError("首次发布需要设置发布选项")
            settings = PublicationSettings.model_validate(publication.settings)
        if settings.expires_at and settings.expires_at <= datetime.now(UTC):
            raise AnalyticsValidationError("截止时间必须晚于当前时间")
        password_enabled = bool(
            settings.password
            or (publication and publication.password_hash and not settings.remove_password)
        )
        if password_enabled and not get_settings().public_cookie_secret:
            raise AnalyticsValidationError("设置访问密码前请配置 PUBLIC_COOKIE_SECRET")
        if password_enabled and not get_settings().public_app_base_url.startswith("https://"):
            raise AnalyticsValidationError("密码保护的看板需要 HTTPS 公开访问地址")
        snapshot.name = settings.name
        snapshot.settings = settings.model_copy(update={"password": None})
        now = datetime.now(UTC)
        if publication is None:
            publication = AnalyticsDashboardPublication(
                dashboard_id=dashboard_id,
                public_key=secrets.token_urlsafe(32),
                version=1,
                status="PUBLISHED",
                settings={},
                published_at=now,
            )
        else:
            if publication_status(publication) != "PUBLISHED":
                publication.public_key = secrets.token_urlsafe(32)
            publication.version += 1
            publication.status = "PUBLISHED"
            publication.revoked_at = None
            publication.published_at = now
        publication.settings = settings.model_dump(mode="json", exclude={"password"})
        if settings.password:
            publication.password_hash = _hash_password(settings.password)
        elif settings.remove_password:
            publication.password_hash = None
        revision = AnalyticsDashboardRevision(
            publication_id=0,
            version=publication.version,
            snapshot=snapshot.model_dump(mode="json"),
        )
        await self._repository.save_publication(publication, revision)
        return await self.management_state(dashboard_id)

    async def unpublish(self, dashboard_id: int) -> PublicationRead:
        publication = await self._repository.publication_for_dashboard(dashboard_id, lock=True)
        if not publication:
            raise AnalyticsNotFoundError("看板尚未发布")
        publication.status = "REVOKED"
        publication.revoked_at = datetime.now(UTC)
        await self._repository.save_publication(publication)
        return await self.management_state(dashboard_id)

    async def rotate(self, dashboard_id: int) -> PublicationRead:
        publication = await self._repository.publication_for_dashboard(dashboard_id, lock=True)
        if publication_status(publication) != "PUBLISHED":
            raise AnalyticsConflictError("只有有效发布的看板可以更换链接")
        assert publication is not None
        publication.public_key = secrets.token_urlsafe(32)
        await self._repository.save_publication(publication)
        return await self.management_state(dashboard_id)

    async def active_publication(
        self, key: str
    ) -> tuple[AnalyticsDashboardPublication, PublicationSnapshot]:
        if len(key) > 64:
            raise AnalyticsNotFoundError(_INVALID)
        publication = await self._repository.publication_for_key(key)
        if publication_status(publication) != "PUBLISHED":
            raise AnalyticsNotFoundError(_INVALID)
        assert publication is not None
        revision = await self._repository.publication_revision(publication.id, publication.version)
        if revision is None:
            raise AnalyticsNotFoundError(_INVALID)
        return publication, PublicationSnapshot.model_validate(revision.snapshot)

    async def public_dashboard(self, key: str) -> PublicDashboard:
        publication, snapshot = await self.active_publication(key)
        settings = snapshot.settings or PublicationSettings.model_validate(publication.settings)
        return PublicDashboard(
            name=snapshot.name,
            description=snapshot.description,
            version=publication.version,
            updated_at=snapshot.updated_at,
            controls=[
                PublicQueryControl.model_validate(
                    {
                        **control.model_dump(),
                        "affected_charts": [
                            chart.public_id
                            for chart in snapshot.charts
                            if any(target.chart_id == chart.id for target in control.targets)
                        ],
                    }
                )
                for control in snapshot.controls
            ],
            charts=[PublicChart.model_validate(chart.model_dump()) for chart in snapshot.charts],
            theme=settings.theme,
            refresh_seconds=settings.refresh_seconds,
            show_title=settings.show_title,
            show_updated_at=settings.show_updated_at,
            allow_url_parameters=settings.allow_url_parameters,
            allow_viewer_edit_url=settings.allow_viewer_edit_url,
            password_required=publication.password_hash is not None,
        )

    async def chart_data(
        self, key: str, public_chart_id: str, values: dict[str, ControlValue]
    ) -> ChartData:
        _, snapshot = await self.active_publication(key)
        chart = next((item for item in snapshot.charts if item.public_id == public_chart_id), None)
        if chart is None:
            raise AnalyticsNotFoundError("发布版本中不存在该图表")
        dataset_def = next(
            (item for item in snapshot.datasets if item.id == chart.dataset_id), None
        )
        if dataset_def is None:
            raise AnalyticsNotFoundError("发布版本中的数据集已失效")
        resolved = resolve_controls(snapshot.controls, values)
        filters, parameters, groups = chart_control_inputs(snapshot.controls, resolved, chart.id)
        dataset = AnalyticsDataset(
            id=dataset_def.id,
            source_type=dataset_def.source_type,
            api_name=dataset_def.api_name,
            sql_text=dataset_def.sql_text,
            sql_hash=dataset_def.sql_hash,
            fields=[item.model_dump(mode="json") for item in dataset_def.fields],
            parameters=[item.model_dump(mode="json") for item in dataset_def.parameters],
        )
        config = chart.config
        request = (
            chart_query(config)
            if config
            else _chart_request(ChartCreate.model_validate(chart.model_dump()), dataset)
        )
        request.filters.extend(filters)
        request.filter_groups.extend(groups)
        request.dataset_parameters = parameters
        data = await self._executor.execute(dataset, request)
        if config and config.chart_type == "pivot_table":
            data.pivot = await pivot_result(dataset, config, data, request, self._executor)
            data.truncated = data.truncated or data.pivot.truncated
        return data

    async def options(
        self, key: str, control_id: str, search: str, values: dict[str, ControlValue]
    ) -> PublicOptionsResponse:
        _, snapshot = await self.active_publication(key)
        control = next((item for item in snapshot.controls if item.id == control_id), None)
        if not control:
            raise AnalyticsNotFoundError("查询控件不存在")
        if control.option_source == "manual":
            matches = [
                item for item in control.manual_options if search.lower() in item.label.lower()
            ]
            return PublicOptionsResponse(options=matches[:1000], truncated=len(matches) > 1000)
        if control.control_type not in {"select", "multi_select"}:
            raise AnalyticsValidationError("此控件不支持加载下拉选项")
        dataset_id = (
            control.option_dataset_id
            if control.option_source == "dataset"
            else control.targets[0].dataset_id
        )
        source = next((item for item in snapshot.datasets if item.id == dataset_id), None)
        if source is None:
            raise AnalyticsValidationError("选项数据集已失效")
        value_field = control.option_value_field or control.targets[0].target_name
        label_field = control.option_label_field or value_field
        dataset = AnalyticsDataset(
            id=source.id,
            source_type=source.source_type,
            api_name=source.api_name,
            sql_text=source.sql_text,
            sql_hash=source.sql_hash,
            fields=[item.model_dump(mode="json") for item in source.fields],
            parameters=[item.model_dump(mode="json") for item in source.parameters],
        )
        relaxed = [item.model_copy(update={"required": False}) for item in snapshot.controls]
        selected = resolve_controls(relaxed, values)
        parent_filters: list[FilterCondition] = []
        source_parameters: dict[str, ControlValue] = {}
        for parent_id in control.depends_on:
            parent = next(item for item in snapshot.controls if item.id == parent_id)
            value = selected[parent.parameter_name]
            if value is None:
                continue
            for target in parent.targets:
                if target.dataset_id == dataset_id and target.target_type == "FIELD_FILTER":
                    parent_filters.append(
                        FilterCondition(
                            field=target.target_name,
                            operator=target.operator,
                            value=value,
                        )
                    )
                elif target.dataset_id == dataset_id and target.target_type == "DATASET_PARAMETER":
                    source_parameters[target.target_name] = value
        rows, truncated = await self._executor.distinct_options(
            dataset,
            value_field,
            label_field,
            search=search,
            filters=parent_filters,
            parameters=source_parameters,
            sort_field=control.option_sort_field,
            sort_desc=control.option_sort_desc,
        )
        return PublicOptionsResponse(
            options=[
                ManualOption(value=value, label=str(label))
                for value, label in rows
                if value is not None
            ],
            truncated=truncated,
        )

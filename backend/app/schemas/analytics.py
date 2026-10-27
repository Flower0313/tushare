from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ChartType = Literal[
    "line",
    "bar",
    "pie",
    "number",
    "table",
    "scatter",
    "candlestick",
    "treemap",
    "funnel",
    "pivot_table",
]
Aggregation = Literal["COUNT", "SUM", "AVG", "MIN", "MAX"]
FieldRole = Literal["dimension", "metric"]
FieldType = Literal["text", "number", "date", "datetime", "boolean"]
FilterOperator = Literal[
    "EQ",
    "NE",
    "CONTAINS",
    "NOT_CONTAINS",
    "STARTS_WITH",
    "ENDS_WITH",
    "IN",
    "NOT_IN",
    "BETWEEN",
    "GT",
    "GTE",
    "LT",
    "LTE",
    "IS_NULL",
    "NOT_NULL",
]
DateGranularity = Literal["day", "month", "year"]
FilterKind = Literal["text_select", "number_range", "date_range"]
Scalar = str | int | float | bool
ControlValue = Scalar | list[Scalar] | dict[str, Scalar | list[Scalar] | None] | None
ParameterType = Literal["text", "number", "boolean", "date", "datetime"]
ParameterShape = Literal["scalar", "list", "range"]


class SqlParameterDefinition(BaseModel):
    name: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,49}$")
    label: str = Field(min_length=1, max_length=120)
    data_type: ParameterType
    shape: ParameterShape = "scalar"
    required: bool = False
    default_value: ControlValue = None
    allow_null: bool = True
    allow_url: bool = False
    allowed_values: list[Scalar] | None = Field(default=None, max_length=100)
    description: str = Field(default="", max_length=500)


class QueryControlTarget(BaseModel):
    chart_id: int
    dataset_id: int
    target_type: Literal["FIELD_FILTER", "DATASET_PARAMETER"]
    target_name: str = Field(min_length=1, max_length=100)
    operator: FilterOperator = "EQ"
    data_type: ParameterType
    date_granularity: DateGranularity | None = None


class ManualOption(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    value: Scalar


class CompoundCondition(BaseModel):
    kind: Literal["condition"] = "condition"
    id: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,49}$")
    field: str = Field(min_length=1, max_length=100)
    operator: FilterOperator = "EQ"
    data_type: FieldType


class CompoundGroup(BaseModel):
    kind: Literal["group"] = "group"
    combinator: Literal["AND", "OR"] = "AND"
    children: list[CompoundCondition | CompoundGroup] = Field(min_length=1, max_length=10)


CompoundGroup.model_rebuild()


class QueryControl(BaseModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z_][A-Za-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=120)
    parameter_name: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,49}$")
    control_type: Literal[
        "text",
        "select",
        "multi_select",
        "number",
        "number_range",
        "date",
        "date_range",
        "month",
        "year",
        "relative_date",
        "compound",
    ]
    data_type: ParameterType
    operator: FilterOperator = "EQ"
    default_value: ControlValue = None
    required: bool = False
    allow_clear: bool = True
    trigger: Literal["immediate", "submit"] = "immediate"
    option_source: Literal["manual", "distinct", "dataset"] = "manual"
    manual_options: list[ManualOption] = Field(default_factory=list, max_length=1000)
    option_dataset_id: int | None = None
    option_value_field: str | None = None
    option_label_field: str | None = None
    option_sort_field: str | None = None
    option_sort_desc: bool = False
    targets: list[QueryControlTarget] = Field(default_factory=list, min_length=1, max_length=50)
    depends_on: list[str] = Field(default_factory=list, max_length=5)
    allow_url: bool = False
    allow_viewer_edit: bool = True
    locked: bool = False
    width: Literal["small", "medium", "wide"] = "medium"
    position: int = Field(default=0, ge=0)
    relative_period: (
        Literal["last_7_days", "last_30_days", "this_month", "last_month", "this_year"] | None
    ) = None
    compound_group: CompoundGroup | None = None

    @model_validator(mode="after")
    def validate_control(self) -> QueryControl:
        if self.control_type == "compound":
            if self.compound_group is None or self.allow_url or self.option_source != "manual":
                raise ValueError("复合控件需要条件组，且不能作为 URL 参数或下拉选项")
            if self.default_value is not None and not isinstance(self.default_value, dict):
                raise ValueError("复合控件默认值必须按条件 ID 配置")
        elif self.compound_group is not None:
            raise ValueError("仅复合控件可配置条件组")
        if self.locked and self.default_value is None:
            raise ValueError("锁定控件必须有默认值")
        if len({str(item.value) for item in self.manual_options}) != len(self.manual_options):
            raise ValueError("手工选项的查询值不能重复")
        if self.option_source == "dataset" and not (
            self.option_dataset_id and self.option_value_field and self.option_label_field
        ):
            raise ValueError("指定数据集选项需要数据集、查询值字段和显示名称字段")
        return self


class SemanticField(BaseModel):
    source_name: str = Field(min_length=1, max_length=100)
    display_name: str = Field(min_length=1, max_length=120)
    role: FieldRole
    data_type: FieldType
    default_aggregation: Aggregation = "COUNT"
    visible: bool = True


class FilterCondition(BaseModel):
    field: str
    operator: FilterOperator
    value: Scalar | list[Scalar] | None = None


class FilterGroup(BaseModel):
    combinator: Literal["AND", "OR"]
    children: list[FilterCondition | FilterGroup] = Field(min_length=1, max_length=10)


FilterGroup.model_rebuild()


class GlobalFilterDefinition(BaseModel):
    field: str
    label: str = Field(min_length=1, max_length=120)
    kind: FilterKind


class DatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    source_type: Literal["TABLE", "SQL"] = "TABLE"
    api_name: str | None = None
    sql_text: str | None = Field(default=None, max_length=100000)
    fields: list[SemanticField] = Field(min_length=1, max_length=80)
    parameters: list[SqlParameterDefinition] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def source_shape(self) -> DatasetCreate:
        if self.source_type == "TABLE" and (not self.api_name or self.sql_text):
            raise ValueError("表数据集必须选择接口且不能填写 SQL")
        if self.source_type == "SQL" and (self.api_name or not self.sql_text):
            raise ValueError("SQL 数据集必须填写只读 SQL，不能选择接口")
        if self.source_type == "TABLE" and self.parameters:
            raise ValueError("表数据集不支持 SQL 参数")
        if len({item.name for item in self.parameters}) != len(self.parameters):
            raise ValueError("SQL 参数名称不能重复")
        return self

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("名称不能为空")
        return value.strip()


class DatasetRead(DatasetCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sql_hash: str | None = None
    validation_status: str = "VALID"
    validated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class DashboardCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    global_filters: list[GlobalFilterDefinition] = Field(default_factory=list, max_length=12)
    query_controls: list[QueryControl] = Field(default_factory=list, max_length=30)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("名称不能为空")
        return value.strip()


class DashboardRead(DashboardCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class ChartCreate(BaseModel):
    dataset_id: int
    title: str = Field(min_length=1, max_length=120)
    chart_type: ChartType
    dimension: str | None = None
    metric: str | None = None
    aggregation: Aggregation = "COUNT"
    position: int = Field(default=0, ge=0)
    grid_span: int = Field(default=1, ge=1, le=12)
    height_px: int = Field(default=320, ge=190, le=800)
    filters: list[FilterCondition] = Field(default_factory=list, max_length=12)
    sort_by: Literal["dimension", "metric"] = "metric"
    sort_desc: bool = True
    top_n: int = Field(default=100, ge=1, le=100)
    date_granularity: DateGranularity | None = None
    config: ChartConfig | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("图表标题不能为空")
        return value.strip()


class ChartRead(ChartCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    dashboard_id: int

    @model_validator(mode="before")
    @classmethod
    def legacy_config(cls, value: object) -> object:
        if hasattr(value, "config_version") and value.config_version == 1:
            return value.definition()
        return value


class QueryMetric(BaseModel):
    field: str | None = None
    aggregation: Aggregation = "COUNT"


class ChartConfigBase(BaseModel):
    version: Literal[2] = 2
    dimensions: list[str] = Field(default_factory=list, max_length=3)
    metrics: list[QueryMetric] = Field(default_factory=list, max_length=4)
    filters: list[FilterCondition] = Field(default_factory=list, max_length=12)
    sort_by: str | None = None
    sort_desc: bool = True
    top_n: int = Field(default=100, ge=1, le=100)
    date_granularity: DateGranularity | None = None
    show_legend: bool = True
    show_labels: bool = False
    data_zoom: bool = True
    theme: Literal["auto", "light", "dark"] = "auto"


class LineConfig(ChartConfigBase):
    chart_type: Literal["line"]
    smooth: bool = False
    connect_nulls: bool = False


class BarConfig(ChartConfigBase):
    chart_type: Literal["bar"]
    orientation: Literal["vertical", "horizontal"] = "vertical"
    stacked: bool = False


class PieConfig(ChartConfigBase):
    chart_type: Literal["pie"]
    donut: bool = False
    merge_others: bool = True


class ScatterConfig(ChartConfigBase):
    chart_type: Literal["scatter"]
    x_field: str
    y_field: str
    category_field: str | None = None
    size_field: str | None = None


class CandlestickConfig(ChartConfigBase):
    chart_type: Literal["candlestick"]
    time_field: str
    open_field: str
    close_field: str
    low_field: str
    high_field: str
    volume_field: str | None = None


class TreemapConfig(ChartConfigBase):
    chart_type: Literal["treemap"]


class FunnelConfig(ChartConfigBase):
    chart_type: Literal["funnel"]


class PivotConfig(ChartConfigBase):
    chart_type: Literal["pivot_table"]
    row_dimensions: list[str] = Field(min_length=1, max_length=3)
    column_dimensions: list[str] = Field(min_length=1, max_length=3)
    row_subtotals: bool = True
    column_subtotals: bool = True
    grand_total: bool = True
    null_display: str = "—"


class NumberConfig(ChartConfigBase):
    chart_type: Literal["number"]


class TableConfig(ChartConfigBase):
    chart_type: Literal["table"]


ChartConfig = Annotated[
    LineConfig
    | BarConfig
    | PieConfig
    | ScatterConfig
    | CandlestickConfig
    | TreemapConfig
    | FunnelConfig
    | PivotConfig
    | NumberConfig
    | TableConfig,
    Field(discriminator="chart_type"),
]

ChartCreate.model_rebuild()
ChartRead.model_rebuild()


class QueryRequest(BaseModel):
    dimensions: list[str] = Field(default_factory=list, max_length=80)
    metrics: list[QueryMetric] = Field(default_factory=list, max_length=4)
    filters: list[FilterCondition] = Field(default_factory=list, max_length=20)
    filter_groups: list[FilterGroup] = Field(default_factory=list, max_length=10)
    sort_by: str | None = None
    sort_desc: bool = True
    limit: int = Field(default=100, ge=1, le=100)
    date_granularity: DateGranularity | None = None
    mode: Literal["aggregate", "table"] = "aggregate"
    dataset_parameters: dict[str, ControlValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_shape(self) -> QueryRequest:
        def count(group: FilterGroup, depth: int) -> int:
            if depth > 4:
                raise ValueError("复合筛选最多四层")
            return sum(
                count(child, depth + 1) if isinstance(child, FilterGroup) else 1
                for child in group.children
            )

        if sum(count(group, 1) for group in self.filter_groups) > 20:
            raise ValueError("复合筛选最多二十个条件")
        if self.mode == "aggregate" and not self.metrics:
            raise ValueError("聚合查询至少需要一个度量")
        if self.mode == "aggregate" and len(self.dimensions) > 6:
            raise ValueError("聚合查询最多允许六个维度")
        if self.mode == "table" and (self.metrics or self.date_granularity):
            raise ValueError("明细查询不能包含聚合度量或日期粒度")
        return self


class ChartQueryRequest(BaseModel):
    global_filters: list[FilterCondition] = Field(default_factory=list, max_length=12)
    dataset_parameters: dict[str, ControlValue] = Field(default_factory=dict, max_length=30)
    control_values: dict[str, ControlValue] = Field(default_factory=dict, max_length=30)


class ChartData(BaseModel):
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, str | float | int | bool | None]] = Field(default_factory=list)
    points: list[dict[str, str | float | int]] = Field(default_factory=list)
    truncated: bool = False
    pivot: PivotResult | None = None


class PivotCell(BaseModel):
    row_key: list[Scalar | None]
    column_key: list[Scalar | None]
    values: list[float | int | None]


class PivotTotal(BaseModel):
    key: list[Scalar | None]
    values: list[float | int | None]


class PivotResult(BaseModel):
    row_dimensions: list[str]
    column_dimensions: list[str]
    measures: list[QueryMetric]
    row_headers: list[list[Scalar | None]]
    column_headers: list[list[Scalar | None]]
    cells: list[PivotCell]
    row_totals: list[PivotTotal]
    column_totals: list[PivotTotal]
    grand_total: list[float | int | None]
    truncated: bool = False


class SourceFieldRead(SemanticField):
    pass


class SqlCatalogColumn(BaseModel):
    name: str
    pg_type: str


class SqlCatalogTable(BaseModel):
    schema_name: str
    table_name: str
    columns: list[SqlCatalogColumn]


class SqlInspectRequest(BaseModel):
    sql_text: str = Field(min_length=1, max_length=100000)
    parameters: list[SqlParameterDefinition] = Field(default_factory=list, max_length=30)
    test_values: dict[str, ControlValue] = Field(default_factory=dict)


class SqlInspectResponse(BaseModel):
    valid: bool = True
    formatted_sql: str
    sql_hash: str
    fields: list[SemanticField]
    rows: list[dict[str, Scalar | None]] = Field(default_factory=list)


ChartData.model_rebuild()


class PublicationSettings(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    expires_at: datetime | None = None
    allow_url_parameters: bool = True
    allow_viewer_edit_url: bool = True
    password: str | None = Field(default=None, min_length=8, max_length=128, exclude=True)
    remove_password: bool = Field(default=False, exclude=True)
    refresh_seconds: Literal[0, 60, 300, 900] = 0
    theme: Literal["light", "dark", "system"] = "system"
    show_title: bool = True
    show_updated_at: bool = True

    @field_validator("expires_at")
    @classmethod
    def ensure_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    @model_validator(mode="after")
    def password_change_is_unambiguous(self) -> PublicationSettings:
        if self.password and self.remove_password:
            raise ValueError("不能同时设置和移除访问密码")
        return self


class PublicationRead(BaseModel):
    dashboard_id: int
    public_key: str
    version: int
    status: Literal["DRAFT", "PUBLISHED", "EXPIRED", "REVOKED"]
    settings: PublicationSettings
    published_at: datetime | None = None
    public_url: str | None = None
    password_required: bool = False


class PublishedDataset(BaseModel):
    id: int
    source_type: Literal["TABLE", "SQL"]
    api_name: str | None = None
    sql_text: str | None = None
    sql_hash: str | None = None
    fields: list[SemanticField]
    parameters: list[SqlParameterDefinition] = Field(default_factory=list)


class PublishedChart(BaseModel):
    id: int
    public_id: str
    dataset_id: int
    title: str
    chart_type: ChartType
    dimension: str | None = None
    metric: str | None = None
    aggregation: Aggregation = "COUNT"
    position: int = 0
    grid_span: int = Field(default=1, ge=1, le=12)
    height_px: int = Field(default=320, ge=190, le=800)
    filters: list[FilterCondition] = Field(default_factory=list)
    sort_by: Literal["dimension", "metric"] = "metric"
    sort_desc: bool = True
    top_n: int = 100
    date_granularity: DateGranularity | None = None
    config_version: int = 1
    config: ChartConfig | None = None


class PublicationSnapshot(BaseModel):
    version: Literal[1] = 1
    name: str
    description: str
    updated_at: datetime
    settings: PublicationSettings | None = None
    controls: list[QueryControl]
    charts: list[PublishedChart]
    datasets: list[PublishedDataset]


class PublicChart(BaseModel):
    public_id: str
    title: str
    chart_type: ChartType
    position: int
    grid_span: int = Field(default=1, ge=1, le=12)
    height_px: int = Field(default=320, ge=190, le=800)
    dimension: str | None = None
    metric: str | None = None
    config: ChartConfig | None = None


class PublicQueryControl(BaseModel):
    id: str
    name: str
    parameter_name: str
    control_type: str
    data_type: ParameterType
    operator: FilterOperator
    default_value: ControlValue = None
    required: bool
    allow_clear: bool
    trigger: Literal["immediate", "submit"]
    option_source: Literal["manual", "distinct", "dataset"]
    manual_options: list[ManualOption]
    depends_on: list[str]
    allow_url: bool
    allow_viewer_edit: bool
    locked: bool
    width: Literal["small", "medium", "wide"]
    position: int
    affected_charts: list[str] = Field(default_factory=list)
    compound_group: CompoundGroup | None = None


class PublicDashboard(BaseModel):
    name: str
    description: str
    version: int
    updated_at: datetime | None = None
    controls: list[PublicQueryControl]
    charts: list[PublicChart]
    theme: Literal["light", "dark", "system"]
    refresh_seconds: int
    show_title: bool
    show_updated_at: bool
    allow_url_parameters: bool
    allow_viewer_edit_url: bool
    password_required: bool


class PublicQueryRequest(BaseModel):
    values: dict[str, ControlValue] = Field(default_factory=dict, max_length=30)
    request_id: str | None = Field(default=None, max_length=64)


class PublicOptionsResponse(BaseModel):
    options: list[ManualOption]
    truncated: bool = False


class PublicOptionsRequest(BaseModel):
    values: dict[str, ControlValue] = Field(default_factory=dict, max_length=30)
    search: str = Field(default="", max_length=120)

from pydantic import BaseModel, Field, field_validator


class SqlTargetColumn(BaseModel):
    name: str
    data_type: str
    nullable: bool


class SqlTargetTable(BaseModel):
    schema_name: str
    table_name: str
    columns: list[SqlTargetColumn]

    @property
    def qualified_name(self) -> str:
        return f"{self.schema_name}.{self.table_name}"


class SqlTargetListResponse(BaseModel):
    items: list[SqlTargetTable]


class SqlTaskValidationRequest(BaseModel):
    target_schema: str = Field(min_length=1, max_length=100)
    target_table: str = Field(min_length=1, max_length=100)
    target_columns: list[str] = Field(default_factory=list)
    sql_text: str = Field(min_length=1, max_length=100_000)

    @field_validator("target_columns")
    @classmethod
    def normalize_columns(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(column.strip() for column in value if column.strip()))


class SqlTaskValidationResponse(BaseModel):
    valid: bool = True
    target: str
    target_columns: list[str]
    message: str

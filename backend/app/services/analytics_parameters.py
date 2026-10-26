"""Typed SQL placeholders. Values cross this seam as binds, never SQL fragments."""

import re
from dataclasses import dataclass
from datetime import date, datetime
from hashlib import sha256
from typing import Any

from app.core.config import get_settings
from app.core.exceptions import AnalyticsValidationError
from app.schemas.analytics import SqlParameterDefinition
from app.services.analytics_sql_policy import validate_sql

_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_DOLLAR = re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$")
_ALIAS = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_CAST = {
    "text": "text",
    "number": "numeric",
    "boolean": "boolean",
    "date": "date",
    "datetime": "timestamptz",
}


@dataclass(frozen=True)
class SqlTemplate:
    original_sql: str
    postgres_sql: str
    sqlalchemy_sql: str
    bind_names: tuple[str, ...]
    content_hash: str


def compile_sql_template(  # noqa: C901 - lexical states must share one cursor
    sql: str, definitions: list[SqlParameterDefinition]
) -> SqlTemplate:
    defined = {item.name: item for item in definitions}
    if len(defined) != len(definitions):
        raise AnalyticsValidationError("SQL 参数名称不能重复")
    postgres: list[str] = []
    sqlalchemy: list[str] = []
    binds: list[str] = []
    used: set[str] = set()
    index = 0

    def copy(fragment: str, protected: bool = False) -> None:
        postgres.append(fragment)
        sqlalchemy.append(fragment.replace(":", r"\:") if protected else fragment)

    def bind_value(bind: str) -> None:
        owner = bind
        endpoint = None
        if bind not in defined:
            for suffix in ("_start", "_end"):
                if bind.endswith(suffix) and bind[: -len(suffix)] in defined:
                    owner = bind[: -len(suffix)]
                    endpoint = suffix
                    break
        definition = defined.get(owner)
        if definition is None or (endpoint and definition.shape != "range"):
            raise AnalyticsValidationError(f"SQL 参数 {bind} 未定义，请在右侧添加同名参数")
        if definition.shape == "range" and endpoint is None:
            raise AnalyticsValidationError(f"范围参数 {owner} 必须使用 _start 和 _end")
        used.add(owner)
        if bind not in binds:
            binds.append(bind)
        cast = _CAST[definition.data_type] + ("[]" if definition.shape == "list" else "")
        postgres.append(f"CAST(${binds.index(bind) + 1} AS {cast})")
        sqlalchemy.append(f"CAST(:{bind} AS {cast})")

    while index < len(sql):
        start = index
        if sql.startswith("--", index):
            end = sql.find("\n", index)
            index = len(sql) if end < 0 else end + 1
            copy(sql[start:index], True)
            continue
        alias = _ALIAS.match(sql, index)
        if alias:
            bind_value(alias.group(1))
            index = alias.end()
            continue
        if sql.startswith("/*", index):
            depth = 1
            index += 2
            while index < len(sql) and depth:
                if sql.startswith("/*", index):
                    depth += 1
                    index += 2
                elif sql.startswith("*/", index):
                    depth -= 1
                    index += 2
                else:
                    index += 1
            copy(sql[start:index], True)
            continue
        if sql[index] in {"'", '"'}:
            quote = sql[index]
            index += 1
            while index < len(sql):
                if sql[index] == quote:
                    index += 1
                    if index < len(sql) and sql[index] == quote:
                        index += 1
                    else:
                        break
                else:
                    index += 1
            fragment = sql[start:index]
            alias = _ALIAS.fullmatch(fragment[1:-1]) if quote == "'" else None
            if alias:
                if start > 0 and (sql[start - 1].isalnum() or sql[start - 1] == "_"):
                    raise AnalyticsValidationError("参数请使用完整的 ${参数名}，不需要字符串前缀")
                bind_value(alias.group(1))
            elif "${" in fragment:
                raise AnalyticsValidationError(
                    "参数必须作为完整的值使用，例如 ts_code = ${code}；"
                    "不能嵌入字符串或标识符，包含查询请使用 LIKE '%' || ${code} || '%'"
                )
            else:
                copy(fragment, True)
            continue
        dollar = _DOLLAR.match(sql, index)
        if dollar:
            tag = dollar.group()
            end = sql.find(tag, dollar.end())
            index = len(sql) if end < 0 else end + len(tag)
            copy(sql[start:index], True)
            continue
        if (
            sql[index] == ":"
            and not sql.startswith("::", index)
            and (index == 0 or sql[index - 1] != ":")
        ):
            name_match = _NAME.match(sql, index + 1)
            if name_match:
                bind_value(name_match.group())
                index = name_match.end()
                continue
        copy(sql[index])
        index += 1
    if set(defined) != used:
        raise AnalyticsValidationError(
            "参数定义与 SQL 占位符不一致：" + "、".join(sorted(set(defined) - used))
        )
    statement = "".join(postgres)
    validate_sql(statement, set(get_settings().analytics_allowed_schema_list))
    return SqlTemplate(
        sql, statement, "".join(sqlalchemy), tuple(binds), sha256(sql.encode()).hexdigest()
    )


def _scalar(value: Any, definition: SqlParameterDefinition) -> Any:
    kind = definition.data_type
    if kind == "text":
        if not isinstance(value, str) or len(value) > 500:
            raise AnalyticsValidationError(f"参数 {definition.label} 必须是长度不超过 500 的文本")
        converted: Any = value
    elif kind == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise AnalyticsValidationError(f"参数 {definition.label} 必须是数值")
        converted = value
    elif kind == "boolean":
        if not isinstance(value, bool):
            raise AnalyticsValidationError(f"参数 {definition.label} 必须是布尔值")
        converted = value
    else:
        if not isinstance(value, str):
            raise AnalyticsValidationError(f"参数 {definition.label} 必须是日期字符串")
        try:
            converted = (
                datetime.fromisoformat(value) if kind == "datetime" else date.fromisoformat(value)
            )
        except ValueError as exc:
            raise AnalyticsValidationError(f"参数 {definition.label} 日期格式无效") from exc
    if definition.allowed_values is not None and value not in definition.allowed_values:
        raise AnalyticsValidationError(f"参数 {definition.label} 不在允许值中")
    return converted


def resolve_parameter_values(
    definitions: list[SqlParameterDefinition], supplied: dict[str, Any]
) -> dict[str, Any]:
    by_name = {item.name: item for item in definitions}
    if len(supplied) > 30 or set(supplied) - set(by_name):
        raise AnalyticsValidationError("包含未声明的 SQL 参数")
    resolved: dict[str, Any] = {}
    for definition in definitions:
        value = supplied.get(definition.name, definition.default_value)
        if value is None:
            if definition.required or not definition.allow_null:
                raise AnalyticsValidationError(f"缺少必填参数 {definition.label}")
            if definition.shape == "range":
                resolved[f"{definition.name}_start"] = None
                resolved[f"{definition.name}_end"] = None
            else:
                resolved[definition.name] = None
            continue
        if definition.shape == "scalar":
            if isinstance(value, list):
                raise AnalyticsValidationError(f"参数 {definition.label} 只能传单值")
            resolved[definition.name] = _scalar(value, definition)
        else:
            if (
                not isinstance(value, list)
                or len(value) > 100
                or (definition.shape == "range" and len(value) != 2)
                or not value
            ):
                raise AnalyticsValidationError(f"参数 {definition.label} 的列表或区间形状无效")
            items = [_scalar(item, definition) for item in value]
            if definition.shape == "range":
                if items[0] > items[1]:
                    raise AnalyticsValidationError(f"参数 {definition.label} 区间起点不能大于终点")
                resolved[f"{definition.name}_start"] = items[0]
                resolved[f"{definition.name}_end"] = items[1]
            else:
                resolved[definition.name] = items
    return resolved

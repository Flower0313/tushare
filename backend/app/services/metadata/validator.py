from dataclasses import dataclass
from datetime import datetime

from pydantic import JsonValue

from app.core.exceptions import MetadataError
from app.models.metadata import ApiMetadata, ApiParam


@dataclass(frozen=True, slots=True)
class ValidatedPreviewQuery:
    params: dict[str, JsonValue]
    fields: list[str]


class MetadataParameterValidator:
    """Validate and normalize a generic query exclusively from API metadata."""

    def validate(
        self,
        metadata: ApiMetadata,
        params: dict[str, JsonValue],
        fields: list[str] | None,
    ) -> ValidatedPreviewQuery:
        param_definitions = {param.name: param for param in metadata.params}
        unknown_params = sorted(set(params) - set(param_definitions))
        if unknown_params:
            raise MetadataError(
                "请求包含元数据中不存在的参数",
                details={"unknown_params": unknown_params},
            )

        normalized_params: dict[str, JsonValue] = {}
        for name, value in params.items():
            if value is None or (isinstance(value, str) and not value.strip()):
                continue
            normalized_params[name] = self._coerce(param_definitions[name], value)

        conditional_names = self._validate_conditional_rules(
            metadata.validation_rules, normalized_params
        )
        missing_required = [
            param.name
            for param in metadata.params
            if param.required
            and param.name not in conditional_names
            and param.name not in normalized_params
        ]
        if missing_required:
            raise MetadataError(
                "缺少必填参数",
                details={"missing_params": missing_required},
            )

        field_definitions = {field.name: field for field in metadata.fields}
        selected_fields = fields or [field.name for field in metadata.fields if field.default]
        selected_fields = list(dict.fromkeys(selected_fields))
        unknown_fields = sorted(set(selected_fields) - set(field_definitions))
        if unknown_fields:
            raise MetadataError(
                "请求包含元数据中不存在的输出字段",
                details={"unknown_fields": unknown_fields},
            )
        if not selected_fields:
            raise MetadataError("至少需要选择一个输出字段")

        return ValidatedPreviewQuery(params=normalized_params, fields=selected_fields)

    def _validate_conditional_rules(
        self,
        rules: dict[str, object],
        params: dict[str, JsonValue],
    ) -> set[str]:
        any_of = rules.get("any_of", [])
        if not isinstance(any_of, list):
            raise MetadataError("元数据 validation_rules.any_of 格式无效")

        conditional_names: set[str] = set()
        for raw_group in any_of:
            if not isinstance(raw_group, list) or not all(
                isinstance(name, str) for name in raw_group
            ):
                raise MetadataError("元数据 any_of 条件格式无效")
            group = list(raw_group)
            conditional_names.update(group)
            if group and not any(name in params for name in group):
                raise MetadataError(
                    f"参数 {', '.join(group)} 至少填写一个",
                    details={"any_of": group},
                )
        return conditional_names

    def _coerce(self, definition: ApiParam, value: JsonValue) -> JsonValue:
        data_type = definition.data_type.lower()
        try:
            if data_type == "str":
                if isinstance(value, (dict, list)):
                    raise ValueError
                return str(value).strip()
            if data_type == "int":
                if isinstance(value, bool) or isinstance(value, (dict, list)):
                    raise ValueError
                return int(value)
            if data_type == "float":
                if isinstance(value, bool) or isinstance(value, (dict, list)):
                    raise ValueError
                return float(value)
            if data_type == "bool":
                return self._coerce_bool(value)
            if data_type == "datetime":
                if not isinstance(value, str):
                    raise ValueError
                normalized = value.strip()
                datetime.strptime(normalized, "%Y-%m-%d %H:%M:%S")
                return normalized
        except (TypeError, ValueError) as exc:
            raise MetadataError(
                f"参数 {definition.name} 必须是 {definition.data_type} 类型",
                details={"parameter": definition.name, "expected_type": definition.data_type},
            ) from exc

        raise MetadataError(
            f"元数据包含暂不支持的参数类型：{definition.data_type}",
            details={"parameter": definition.name},
        )

    @staticmethod
    def _coerce_bool(value: JsonValue) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "y"}:
                return True
            if normalized in {"false", "0", "no", "n"}:
                return False
        raise ValueError

from __future__ import annotations

from typing import Any


class EffectiveMetadataValidator:
    SUPPORTED_STRATEGIES = {
        "single",
        "offset",
        "date_range",
        "trade_date",
        "code_batch",
        "date_and_code",
        "custom",
    }
    SUPPORTED_RESET_POLICIES = {
        "NONE",
        "ROW_COUNT_EXPECTATION",
        "DATE_COVERAGE",
        "CODE_COVERAGE",
        "DATE_AND_CODE_COVERAGE",
        "CUSTOM",
    }

    def validate(self, metadata: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        for field in ("api_name", "api_title", "category", "subcategory"):
            if not metadata.get(field):
                errors.append(f"{field} is required")
        param_names = [item.get("name") for item in metadata.get("params", [])]
        field_names = [item.get("name") for item in metadata.get("fields", [])]
        if len(param_names) != len(set(param_names)):
            errors.append("parameter names must be unique")
        if len(field_names) != len(set(field_names)):
            errors.append("field names must be unique")
        if not field_names:
            errors.append("at least one output field is required")
        unknown_keys = sorted(set(metadata.get("unique_keys", [])) - set(field_names))
        if unknown_keys:
            errors.append(f"unique_keys not in fields: {', '.join(unknown_keys)}")
        order_fields = {item.get("field") for item in metadata.get("default_order_by", [])}
        unknown_order = sorted(order_fields - set(field_names))
        if unknown_order:
            errors.append(f"default_order_by fields not in fields: {', '.join(unknown_order)}")
        strategy = metadata.get("fetch_strategy") or {"type": "single"}
        strategy_type = strategy.get("type", "single")
        if strategy_type not in self.SUPPORTED_STRATEGIES:
            errors.append(f"unknown fetch strategy: {strategy_type}")
        referenced = [
            strategy.get(key)
            for key in (
                "start_param",
                "end_param",
                "date_param",
                "code_param",
                "limit_param",
                "offset_param",
            )
            if strategy.get(key)
        ]
        date_config = strategy.get("date") or {}
        code_config = strategy.get("code") or {}
        if isinstance(date_config, dict):
            referenced.extend(
                value
                for value in (date_config.get("start_param"), date_config.get("end_param"))
                if value
            )
        if isinstance(code_config, dict):
            code_param = code_config.get("param") or code_config.get("code_param")
            if code_param:
                referenced.append(code_param)
        unknown_params = sorted(set(referenced) - set(param_names))
        if unknown_params:
            errors.append(f"fetch_strategy params not in params: {', '.join(unknown_params)}")
        self._validate_reset_completeness_policy(
            metadata,
            param_names=set(param_names),
            field_names=set(field_names),
            errors=errors,
        )
        return errors

    def _validate_reset_completeness_policy(
        self,
        metadata: dict[str, Any],
        *,
        param_names: set[str | None],
        field_names: set[str | None],
        errors: list[str],
    ) -> None:
        policy = metadata.get("reset_completeness_policy") or {"type": "NONE"}
        policy_type = str(policy.get("type", "NONE")).upper()
        if policy_type not in self.SUPPORTED_RESET_POLICIES:
            errors.append(f"unknown reset completeness policy: {policy_type}")
            return
        if policy_type == "ROW_COUNT_EXPECTATION" and all(
            policy.get(name) is None for name in ("min_rows", "max_rows", "exact_rows")
        ):
            errors.append(
                "ROW_COUNT_EXPECTATION requires min_rows, max_rows or exact_rows"
            )
        if policy_type in {"DATE_COVERAGE", "DATE_AND_CODE_COVERAGE"}:
            storage_field = policy.get("storage_date_field")
            date_params = {policy.get("start_param"), policy.get("end_param")} - {None}
            if not storage_field or len(date_params) != 2:
                errors.append(
                    "date reset completeness requires storage_date_field, start_param and end_param"
                )
            elif storage_field not in field_names:
                errors.append(
                    f"reset completeness field not in fields: {storage_field}"
                )
            unknown_date_params = sorted(date_params - param_names)
            if unknown_date_params:
                errors.append(
                    "reset completeness params not in params: "
                    + ", ".join(unknown_date_params)
                )
        if policy_type in {"CODE_COVERAGE", "DATE_AND_CODE_COVERAGE"}:
            code_field = policy.get("code_field")
            if not code_field or not policy.get("code_source"):
                errors.append("code reset completeness requires code_field and code_source")
            elif code_field not in field_names:
                errors.append(f"reset completeness field not in fields: {code_field}")
        if policy_type == "CUSTOM" and not policy.get("handler"):
            errors.append("CUSTOM reset completeness requires handler")

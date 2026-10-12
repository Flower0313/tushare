from typing import Any

from sqlalchemy import Table

from app.core.exceptions import DeletePreviewError


class FilterCompiler:
    OPERATORS = {"eq", "gt", "gte", "lt", "lte", "in"}

    def compile(self, metadata: Any, table: Table, filters: list[dict[str, Any]]) -> list[Any]:
        if not filters:
            raise DeletePreviewError("删除条件不能为空；整表删除不在此接口支持范围内")
        allowed = {field.name for field in metadata.fields}
        expressions: list[Any] = []
        for item in filters:
            field = str(item.get("field", ""))
            operator = str(item.get("operator", ""))
            value = item.get("value")
            if field not in allowed or field not in table.c:
                raise DeletePreviewError("过滤字段不在 API Metadata 中", details={"field": field})
            if operator not in self.OPERATORS:
                raise DeletePreviewError("不支持的过滤操作符", details={"operator": operator})
            column = table.c[field]
            if operator == "in":
                if not isinstance(value, list) or not value:
                    raise DeletePreviewError("in 需要非空值列表")
                expressions.append(column.in_(value))
            else:
                expressions.append(
                    {
                        "eq": column == value,
                        "gt": column > value,
                        "gte": column >= value,
                        "lt": column < value,
                        "lte": column <= value,
                    }[operator]
                )
        return expressions

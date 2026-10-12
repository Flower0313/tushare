from pydantic import JsonValue

from app.core.exceptions import TushareResponseError
from app.schemas.tushare import TushareQueryResult


class DataTransformer:
    def transform(self, result: TushareQueryResult) -> list[dict[str, JsonValue]]:
        rows: list[dict[str, JsonValue]] = []
        for index, item in enumerate(result.items):
            if len(item) != len(result.fields):
                raise TushareResponseError(
                    "Tushare 返回字段数与数据列数不一致",
                    details={
                        "row_index": index,
                        "field_count": len(result.fields),
                        "value_count": len(item),
                    },
                )
            rows.append(dict(zip(result.fields, item, strict=True)))
        return rows

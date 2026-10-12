import logging
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Double, Text
from sqlalchemy.sql.type_api import TypeEngine

logger = logging.getLogger(__name__)


class TypeMapper:
    _MAPPINGS: dict[str, type[TypeEngine[Any]]] = {
        "str": Text,
        "string": Text,
        "int": BigInteger,
        "integer": BigInteger,
        "float": Double,
        "number": Double,
        "bool": Boolean,
        "boolean": Boolean,
        "datetime": DateTime,
        "timestamp": DateTime,
    }

    def to_sqlalchemy(self, metadata_type: str) -> TypeEngine[Any]:
        normalized = metadata_type.strip().lower()
        mapped = self._MAPPINGS.get(normalized)
        if mapped is None:
            logger.warning("Unknown Tushare metadata type %r; falling back to TEXT", metadata_type)
            return Text()
        return mapped()

    def is_compatible(self, metadata_type: str, database_type: TypeEngine[Any]) -> bool:
        expected = self.to_sqlalchemy(metadata_type)
        return database_type._type_affinity is expected._type_affinity

    def normalize_value(self, metadata_type: str, value: Any) -> Any:
        """Coerce upstream scalar values to the database type declared by Metadata."""
        if value is None or value == "":
            return value
        normalized = metadata_type.strip().lower()
        if normalized in {"str", "string"}:
            return str(value)
        if normalized in {"int", "integer"}:
            return int(value)
        if normalized in {"float", "number"}:
            return float(value)
        if normalized in {"bool", "boolean"}:
            if isinstance(value, str):
                return value.strip().lower() in {"1", "true", "yes", "y"}
            return bool(value)
        if normalized in {"datetime", "timestamp"} and isinstance(value, str):
            return datetime.fromisoformat(value)
        return value

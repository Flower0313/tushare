import re

from app.core.exceptions import SchemaMismatchError

IDENTIFIER_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")


def validate_identifier(value: str, *, kind: str) -> str:
    """Allow only the identifier shape used by registered Tushare metadata."""
    if not IDENTIFIER_PATTERN.fullmatch(value):
        raise SchemaMismatchError(
            f"非法的数据库{kind}标识符：{value}",
            details={"identifier": value, "kind": kind},
        )
    return value

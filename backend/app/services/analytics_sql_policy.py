"""PostgreSQL AST policy for user-authored analytics queries.

This is a first boundary, not a substitute for the dedicated read-only database role.
Unknown statement and function kinds are rejected deliberately.
"""

from dataclasses import dataclass
from hashlib import sha256

from pglast import ast, parse_sql, prettify
from pglast.parser import ParseError
from pglast.stream import RawStream

from app.core.exceptions import AnalyticsValidationError

SAFE_FUNCTIONS = frozenset(
    {
        "abs",
        "avg",
        "bool_and",
        "bool_or",
        "btrim",
        "ceil",
        "ceiling",
        "char_length",
        "coalesce",
        "concat",
        "concat_ws",
        "count",
        "date_part",
        "date_trunc",
        "dense_rank",
        "extract",
        "first_value",
        "floor",
        "greatest",
        "lag",
        "last_value",
        "lead",
        "least",
        "left",
        "length",
        "lower",
        "ltrim",
        "max",
        "min",
        "nullif",
        "rank",
        "replace",
        "right",
        "round",
        "row_number",
        "rtrim",
        "split_part",
        "substr",
        "substring",
        "sum",
        "to_char",
        "to_date",
        "trim",
        "upper",
    }
)


@dataclass(frozen=True)
class ValidatedSql:
    text: str
    content_hash: str


def _walk(node: object):
    if isinstance(node, ast.Node):
        yield node
        for attribute in node:
            yield from _walk(getattr(node, attribute))
    elif isinstance(node, (list, tuple)):
        for item in node:
            yield from _walk(item)


def _check_relation_scopes(
    node: object, allowed_schemas: set[str], scope: frozenset[str] = frozenset()
) -> None:
    if isinstance(node, ast.SelectStmt) and node.withClause is not None:
        available = scope
        clause = node.withClause
        for cte in clause.ctes or ():
            name = cte.ctename.lower()
            _check_relation_scopes(
                cte.ctequery,
                allowed_schemas,
                available | {name} if clause.recursive else available,
            )
            available = available | {name}
        for attribute in node:
            if attribute != "withClause":
                _check_relation_scopes(getattr(node, attribute), allowed_schemas, available)
        return
    if isinstance(node, ast.RangeVar):
        schema = (node.schemaname or "").lower()
        if not schema and node.relname.lower() in scope:
            return
        if schema not in allowed_schemas:
            raise AnalyticsValidationError("请显式使用允许的 schema 引用数据表")
    if isinstance(node, ast.Node):
        for attribute in node:
            _check_relation_scopes(getattr(node, attribute), allowed_schemas, scope)
    elif isinstance(node, (list, tuple)):
        for item in node:
            _check_relation_scopes(item, allowed_schemas, scope)


def _parse_query(sql: str):
    try:
        return parse_sql(sql)
    except ParseError as exc:
        offset = exc.args[1] if len(exc.args) > 1 else None
        if isinstance(offset, int) and offset >= 0:
            line = sql.count("\n", 0, offset) + 1
            column = offset - sql.rfind("\n", 0, offset)
            raise AnalyticsValidationError(
                f"SQL 语法错误：第 {line} 行，第 {column} 列附近"
            ) from exc
        raise AnalyticsValidationError("SQL 语法错误，请检查编辑器中的语句") from exc


def validate_sql(sql: str, allowed_schemas: set[str]) -> ValidatedSql:
    if not sql.strip() or len(sql) > 100_000:
        raise AnalyticsValidationError("SQL 不能为空且不能超过 100000 个字符")
    statements = _parse_query(sql)
    if len(statements) != 1 or not isinstance(statements[0].stmt, ast.SelectStmt):
        raise AnalyticsValidationError("只允许一条 SELECT 或 WITH ... SELECT 查询")
    root = statements[0].stmt
    if root.valuesLists is not None and root.targetList is None:
        raise AnalyticsValidationError("SQL 数据集必须以 SELECT 查询结束")
    output = root
    while output.larg is not None:
        output = output.larg
    for target in output.targetList or ():
        if target.name is None and not isinstance(target.val, ast.ColumnRef):
            raise AnalyticsValidationError("表达式输出必须设置稳定的 AS 别名")
    _check_relation_scopes(root, allowed_schemas)
    for item in _walk(root):
        if isinstance(item, ast.SelectStmt):
            if item.intoClause is not None or item.lockingClause:
                raise AnalyticsValidationError("SQL 数据集不允许 SELECT INTO 或行锁")
        elif isinstance(item, (ast.InsertStmt, ast.UpdateStmt, ast.DeleteStmt, ast.MergeStmt)):
            raise AnalyticsValidationError("CTE 中也不允许写操作")
        elif isinstance(item, ast.FuncCall):
            parts = [part.sval.lower() for part in item.funcname]
            if (len(parts) != 1 and parts[0] != "pg_catalog") or parts[-1] not in SAFE_FUNCTIONS:
                raise AnalyticsValidationError(f"函数 {'.'.join(parts)} 不在只读函数白名单中")
        elif isinstance(item, ast.RangeFunction):
            raise AnalyticsValidationError("不允许在 FROM 中调用函数")
    # Deparse the accepted AST so trailing comments/semicolons cannot escape the derived table.
    normalized = RawStream()(root)
    return ValidatedSql(normalized, sha256(normalized.encode("utf-8")).hexdigest())


def format_sql(sql: str, allowed_schemas: set[str]) -> str:
    validate_sql(sql, allowed_schemas)
    return prettify(sql)

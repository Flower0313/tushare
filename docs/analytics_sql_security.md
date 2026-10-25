# SQL 数据集安全与部署

SQL 数据集允许自定义 **单条只读 SELECT 查询**，不开放写操作。校验采用 `pglast` PostgreSQL AST，而非字符串或正则；禁止数据修改 CTE、DDL、`SELECT INTO`、行锁、未经授权的 schema、未列入白名单的函数及 `FROM` 函数。表达式输出必须有 `AS` 别名，输出列名唯一。允许的 schema 默认 `tushare,analytics,public`，通过 `ANALYTICS_ALLOWED_SCHEMAS` 缩小；实际可读对象仍由数据库 GRANT 决定。

工作台的来源树由 `GET /api/analytics/sql/catalog` 列出白名单 schema 中当前账号可见的表和字段；它只提供编辑辅助，不代表独立只读角色已获 SELECT 权限。SQL 校验与执行仍使用该只读角色重新验证。嵌套 CTE 名称按作用域判定，不能凭其他作用域中的同名 CTE 绕过 schema 白名单。

必须由数据库管理员创建与平台写入账号不同的登录角色，且**不能**是超级用户、数据库/角色创建者，也不能对任何业务表有 INSERT/UPDATE/DELETE/TRUNCATE、白名单外业务表 SELECT 或 schema CREATE 权限。角色运行时会检查它实际可读取的非系统 schema，不能依赖 SQL 解析器独自阻止误授权。示例（将密码与角色名称在安全渠道替换，勿提交到仓库）：

```sql
CREATE ROLE analytics_reader LOGIN PASSWORD '<strong-random-secret>' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
ALTER ROLE analytics_reader SET default_transaction_read_only = on;
ALTER ROLE analytics_reader SET statement_timeout = '10s';
ALTER ROLE analytics_reader SET lock_timeout = '1s';
REVOKE CREATE ON SCHEMA public FROM analytics_reader;
GRANT USAGE ON SCHEMA tushare, analytics, public TO analytics_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA tushare TO analytics_reader;
-- analytics/public 只给实际允许分析的表逐个授权，避免意外暴露敏感表：
-- GRANT SELECT ON analytics.some_wide_table TO analytics_reader;
```

后续新建的 Tushare 表需由表所有者配置默认权限，例如 `ALTER DEFAULT PRIVILEGES FOR ROLE <table_owner> IN SCHEMA tushare GRANT SELECT ON TABLES TO analytics_reader;`。设置环境变量 `ANALYTICS_READ_DATABASE_URL=postgresql+asyncpg://analytics_reader:<secret>@host:5432/database`，重启后端。绝不复用 `DATABASE_URL` 的写入账号；未配置时 SQL 数据集功能明确拒绝，现有 TABLE 数据集仍可用。

校验、字段推断、预览和图表运行都使用独立连接。运行时再次核验角色权限，事务设 `READ ONLY`，`search_path=pg_catalog`，`work_mem=16MB`，有界并发 4，语句超时 10 秒、锁超时 1 秒，SQL 预览最多 50 行，图表结果最多 100 分组。外围筛选值参数化。返回安全错误说明，不把数据库连接串或内部堆栈传给浏览器。角色 GRANT 是最终安全边界；上线前须用专门的 PostgreSQL 集成测试账号验证读允许表成功、读 `platform` 失败、写入失败。

本地验收：配置只读账号后设置 `RUN_DB_INTEGRATION=1`，运行 `pytest backend/tests/test_analytics_postgres_integration.py -q`。其中 SQL 数据集用例会经过校验、字段推断、预览、持久化、带参数筛选的查询、图表查询及破坏性字段变更拦截。未配置 `ANALYTICS_READ_DATABASE_URL` 时该用例明确跳过，不能视为 SQL 数据集真实数据库验收已通过。

`20261024_0036` 新增 `source_type=TABLE|SQL`、`sql_text`、内容哈希、校验状态和时间。老数据集保持 TABLE；旧图表的平面配置回填为版本 1，读取时走兼容适配，新图表使用强类型版本 2 配置。修改 SQL 后重新推断字段；若删除、重命名或改类型会影响既有图表则拒绝保存并列出图表名称。

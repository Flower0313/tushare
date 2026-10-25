# 系统架构

## Process topology

```text
React / Vite
     |
     v
FastAPI Web ---------------------------> PostgreSQL
     |                                    platform.*
     | creates Execution(PENDING)         tushare.*
     v                                         ^
Execution Queue <--- Scheduler                |
     |                  |                      |
     |                  +-- ScheduleFire       |
     v                                         |
Worker -- FOR UPDATE SKIP LOCKED --> SyncService
                                              |
Maintenance --> recovery / trade_cal / health archive
```

Web、Worker、Scheduler、Maintenance 是独立进程。Scheduler 不调用 Tushare；它只创建 Execution。Maintenance 不实现第二套同步逻辑；trade_cal 补齐同样创建 SYSTEM Execution。

## Data pipeline

```text
Effective Metadata
       |
       v
QueryStrategy
       |
       v
TushareRequestExecutor
  | RateLimiter
  | RetryPolicy
  v
Tushare HTTP API
       |
       v
DataTransformer -> TableSchemaManager -> PostgresDataWriter
                                            |
                                            v
                                      tushare.{api_name}
```

Official Metadata 与 Platform Override 合并为 Effective Metadata。普通 API 不拥有专属采集模块；差异由 unique keys、fetch strategy、validation scenarios、replace range、reset completeness policy 和排序 Metadata 表达。

## 边界与分层

- **API 层**：只处理 HTTP 输入输出、依赖注入和状态码。
- **Service 层**：承载用例和业务规则，不依赖 FastAPI。
- **Repository 层**：封装 SQLAlchemy 查询与持久化细节。
- **Model 层**：定义 PostgreSQL `platform` schema 的关系模型。
- **Schema 层**：定义稳定的 Pydantic API 契约。
- **Frontend**：只依赖元数据响应，通过同一套组件呈现任意 Tushare API。

## 目标架构

```text
Browser
  │
  ├── GET /api/apis ───────────────┐
  └── GET /api/apis/{api_name}     │
                                   ▼
FastAPI Route → MetadataService → MetadataRepository → platform schema

Preview Route → PreviewService
                  └→ TushareQueryService
                        ├→ MetadataRepository
                        ├→ MetadataParameterValidator
                        ├→ TushareClient → Tushare HTTPS API
                        └→ DataTransformer

Sync Route → Execution(PENDING) ← ScheduleFire ← Scheduler Process
                       │
                       ▼
Worker Process（FOR UPDATE SKIP LOCKED）→ SyncService
               ├→ TushareQueryService.prepare（Metadata 与参数规范化）
               ├→ TaskLockService（PostgreSQL advisory lock）
               ├→ PaginationService（逐页 fetch/transform/write）
               ├→ TableSchemaManager / TypeMapper / UNIQUE
               ├→ PostgresDataWriter（基于 Effective Unique Keys 的幂等 UPSERT）
               └→ ExecutionRepository（独立短事务与逐页进度）
```

手动执行、重跑与 Scheduler 只负责创建 Execution；独立 Worker 领取后统一调用 `SyncService.run()`，避免形成三套采集路径。Scheduler 使用 PostgreSQL advisory leader lock，多实例下只有 leader 生成 ScheduleFire。

## 数据集与看板读取链路

```text
已同步 tushare.{api_name} 表 ─┐
用户只读 SQL（SELECT / WITH）──┤ PostgreSQL AST 安全策略 + schema/函数白名单
                           ├→ 独立只读角色 + READ ONLY 事务（SQL 来源）
                           ▼
DatasetDefinition / SqlSource（字段推断与来源验证）
             ▼
platform.analytics_dataset（语义字段：名称、角色、类型、默认聚合、可见性）
             ▼
AnalyticsService（数据集 / 看板 / 图表用例与兼容筛选）
             ▼
QueryPlanner（验证维度、度量、筛选、排序、日期粒度与 Top N）
             ▼
SqlAlchemyQueryExecutor（TABLE / SQL 派生表、参数化、限时执行）
             ▼
FastAPI analytics routes ──> 全屏数据集 / 图表工作台 ──> ECharts / 交叉表
```

TABLE 数据集继续限定为已登记接口；SQL 数据集仅保存只读查询定义，可跨允许的 schema 进行 JOIN，不复制业务数据。SQL 先由 pglast 解析为 PostgreSQL AST，拒绝多语句、写入语句、未授权来源、危险函数，再在独立只读账号的 READ ONLY 事务里推断字段和执行。前端传入的外围维度与筛选字段只能引用已验证的语义字段，筛选值由 SQLAlchemy 参数化。看板全局筛选只影响同名兼容字段。`20261024_0036` 增加来源类型及版本化图表配置，旧配置继续可读。更多边界与部署要求见 [SQL 数据集安全与部署](analytics_sql_security.md)。

旧图表的 `dimension`、`metric`、`aggregation`、`filters`、`sort_by`、`top_n` 和 `date_granularity` 保持原字段与查询语义，迁移后 `config_version=1`；读取接口的 `config=null` 表示旧配置，图表工作台从旧字段确定性地装载。新图表使用 `config_version=2` 与按图表类型区分的 `config` JSONB；数据集与查询服务负责校验、规划和执行，前端仅将有界查询结果适配到统一 ECharts 渲染器或交叉表。SQL 来源树由白名单 schema 的表字段目录提供，但最终读取权限仍由独立只读角色判定。

## 关键设计决定

数据看板的发布边界使用 `20261025_0037` 建立 publication/revision：草稿可继续编辑，公开查询只读取已发布定义快照，业务数据仍实时查询。查询控件显式映射图表输出字段或 SQL 类型化参数，详情见 [数据看板发布与查询控件](dashboard_publication.md)。

1. **元数据规范化存储**：接口、参数、字段分表，便于排序、差异比较和增量导入。暂不使用单个 JSONB 大字段作为唯一事实源。
2. **迁移负责初始数据**：初始元数据随 Alembic 版本化；服务启动不隐式改数据库。
3. **业务 schema 隔离**：平台信息进入 `platform`，Tushare 原始数据进入 `tushare`。业务表不添加平台内部字段。
4. **不虚构主键规则**：Metadata 提供默认唯一键，用户覆盖保存在独立 Runtime Config；只有生效唯一键与数据库平台约束一致时才允许 UPSERT。
5. **原始类型优先**：官方 `str` 日期在首版保持文本，不进行语义性类型转换。
6. **凭据只来自环境**：Token 和数据库密码不进入元数据、响应、执行日志或代码。
7. **失败日志独立提交**：Execution 的 RUNNING/SUCCESS/FAILED 各用短事务持久化；业务数据 DDL 与 INSERT 使用独立事务，业务回滚不会抹掉失败记录。
8. **安全演进表结构**：表按完整输出 Metadata 创建，只允许 `ADD COLUMN`；数据库额外列保留，类型差异仅告警。
9. **唯一键由 Default + User Override 决定**：统一计算 Effective Keys；SchemaManager 校验稳定命名的 UNIQUE 约束，Writer 据此生成 ON CONFLICT，不包含任何 API 名称分支。迁移流程见 [Unique Key Management](unique_key_management.md)。
10. **任务锁跨进程有效**：规范化请求生成 SHA-256 task key，再映射为 PostgreSQL advisory lock；连接断开会自动释放。
11. **分页按页提交**：每页获取后立即转换和写入，不累计全量结果；中途失败保留已完成页数和累计行数。
12. **调度与执行解耦**：`platform.schedule_fire` 记录“是否触发”，`platform.execution` 记录“是否执行成功”；两者不混用状态。
13. **时区显式化**：Cron 与动态变量按 Schedule 自身的 IANA timezone 计算，默认 `Asia/Shanghai`，不依赖服务器时区。
14. **调度幂等**：`schedule_id + scheduled_at` 在 Fire 与 Execution 层均有数据库唯一约束，进程重启和多实例不能重复生成同一触发点。
15. **Reset 完整性独立于 Execution 成功**：Reset Operation 只有在异步同步成功且 Metadata 驱动的完整性校验通过后才能进入 SUCCESS。缺少策略时禁止整表 Reset。
16. **稳定行身份**：跨 HTTP 请求不使用 PostgreSQL `ctid`。重复清理使用行 fingerprint 重新定位并要求唯一匹配；普通 Delete 使用不可变 Preview Token，并在执行前检查 matched count 与 Effective Unique Keys 快照是否仍一致。

## 已识别的架构风险

- Tushare 文档中的“必选”常包含“二选一”等条件，单个 `required: bool` 不足以表达。模型额外提供 `validation_rules` JSON，由通用表单和后端校验器解释。
- 文档会更新，迁移中的种子是版本快照。Phase 2 之后应增加幂等的 metadata import/upsert 流程和来源版本字段，而不是频繁改历史迁移。
- Scheduler 已作为独立进程并通过 PostgreSQL advisory lock 选主；当前尚未实现自动恢复 stale RUNNING Execution。
- 动态建表属于 DDL，表名和字段名必须先来自已注册 Metadata，再经过严格标识符校验和 dialect quoting。值始终参数化。
- DDL 和数据页写入继续使用独立事务，这是避免长事务锁住 schema 的设计决策。分页中途失败可能已经提交前序页面，Execution 会明确记录部分完成状态。
- 所有同步写入只接受 UPSERT，并要求 Effective Keys 非空且平台管理约束状态为 `SYNCED`；条件不满足时拒绝执行。DELETE 等非同步操作使用 `write_mode=NONE`。
- PostgreSQL UPSERT 通过同一条语句的 RETURNING 结果精确累计 rows_inserted / rows_updated，不增加预查询竞态。

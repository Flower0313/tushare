# Tushare Data Platform

一个基于 Tushare Pro、PostgreSQL 与 Metadata Driven Architecture 的可视化数据采集平台。用户可以浏览接口、动态填写参数、预览或同步数据、管理定时任务、追踪执行过程，并通过审计化的数据生命周期操作维护业务表。

## Architecture

平台不会为每个 Tushare API 编写独立采集模块。接口差异由 Metadata 表达，手工执行、重跑和定时调度最终汇聚到同一条链路：

```text
React → FastAPI → Execution(PENDING) → PostgreSQL queue
                                           ↓
Scheduler → ScheduleFire ───────────────→ Worker
                                           ↓
Metadata → QueryStrategy → RequestExecutor → Tushare
                                           ↓
Transformer → SchemaManager → DataWriter → PostgreSQL
```

Web、Worker、Scheduler 与 Maintenance 是可独立部署的进程。Worker 使用 `FOR UPDATE SKIP LOCKED` 领取任务；Scheduler 只创建 Execution；Maintenance 负责 stale recovery、交易日历覆盖与健康事件归档。详细设计见 [Architecture](docs/architecture.md)。

## Quick Start

要求：Python 3.12+、Node.js 20+、PostgreSQL 15+。

1. 复制 `.env.example` 为 `.env`，填写 `DATABASE_URL` 和 `TUSHARE_TOKEN`。
2. 初始化后端与数据库：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
alembic upgrade head
```

3. 安装前端依赖：

```powershell
npm --prefix frontend install
```

4. Windows 可双击桌面启动脚本，或执行：

```powershell
.\scripts\dev.ps1 dev
```

访问前端 `http://localhost:5173`，OpenAPI 文档位于 `http://localhost:8000/docs`。

## Local Development

建议在不同终端分别启动，便于查看日志：

```powershell
.\scripts\dev.ps1 backend
.\scripts\dev.ps1 frontend
.\scripts\dev.ps1 worker
.\scripts\dev.ps1 scheduler
.\scripts\dev.ps1 maintenance
```

开发期可设置 `RUN_EMBEDDED_WORKER=true` 让 FastAPI 内嵌 Worker；此时不要再启动独立 Worker。生产环境应设为 `false`。Linux/macOS 可使用根目录 `Makefile`。

## Environment Variables

`.env.example` 已按 APP、DATABASE、TUSHARE、WORKER、SCHEDULER、RETRY、RATE LIMIT、数据生命周期、TRADE CALENDAR、HEALTH、RETENTION 与 FRONTEND 分区。常用配置：

- `DATABASE_URL`：SQLAlchemy asyncpg 连接串。
- `TUSHARE_TOKEN`：Tushare Pro Token，禁止提交版本库。
- `RUN_EMBEDDED_WORKER`：仅用于本地开发的内嵌 Worker 开关。
- `EXECUTION_STALE_TIMEOUT_SECONDS`：RUNNING 任务的心跳超时阈值。
- `TUSHARE_RETRY_*`：重试次数、指数退避与 jitter。
- `TRADE_CALENDAR_*`：本地交易日历覆盖与告警阈值。
- `UPSTREAM_HEALTH_RETENTION_DAYS`：上游原始健康事件保留天数。

完整说明和默认值以 [.env.example](.env.example) 为准。接口不会向前端返回 Token 或数据库密码。

## Database Migration

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
```

平台对象位于 `platform` schema；Tushare 业务表位于 `tushare` schema，业务字段名保持官方原名。首次同步自动建表，后续只安全增加缺失字段，不自动删除列或改变字段类型。

## Backend

```powershell
.\scripts\dev.ps1 backend
```

主要入口：

- `/api/apis`：Metadata 目录、详情、Preview 与 Sync。
- `/api/executions`：执行历史、详情、重跑、取消与失败 Chunk 重试。
- `/api/schedules`：调度 CRUD、校验、启停、立即执行与历史。
- `/api/data`：Metadata 白名单约束下的数据浏览、删除预览、删除与范围重刷。
- `/api/system`：服务、交易日历与上游健康状态。
- `/health`、`/health/ready`：进程与依赖健康检查。

## Frontend

```powershell
.\scripts\dev.ps1 frontend
```

前端使用 React、TypeScript、Vite 和 Ant Design。路由页面及大型调试弹窗按需加载；共享 Design Token、StatusBadge、PageHeader、EmptyState 与错误/告警 Presenter 保证全站一致性。主题支持 Light、Dark 与跟随系统，偏好保存在浏览器本地并在 React 挂载前生效，避免刷新闪烁。

FastAPI OpenAPI 是 API Contract 的唯一来源。修改响应 Schema 或枚举后重新生成 TypeScript 契约：

```powershell
.\scripts\dev.ps1 generate-api
```

生成文件 `frontend/src/generated/api-types.ts` 禁止手工修改。Bundle 可视化分析使用：

```powershell
.\scripts\dev.ps1 analyze
```

产物为 `frontend/dist/bundle-stats.html` 与 `bundle-stats.json`。

## Worker

```powershell
.\scripts\dev.ps1 worker
```

Worker 从 PostgreSQL 队列领取 `PENDING` Execution，执行锁、QueryStrategy、限流、重试、转换、建表与批量写入。所有同步写入都基于 `effective_unique_keys` 和平台管理 UNIQUE Constraint 执行幂等 UPSERT；非同步数据操作显式记录为 `write_mode=NONE`。Execution 会记录精确的 `rows_inserted` 与 `rows_updated`。

唯一键分为 Metadata 默认值、用户 Override 和运行时 Effective 值。修改或恢复默认值必须先预览重复数据，再通过事务同步 PostgreSQL 平台 UNIQUE Constraint 与 Runtime Config。详细安全语义见 [Unique Key Management](docs/unique_key_management.md)。

## Scheduler

```powershell
.\scripts\dev.ps1 scheduler
```

Scheduler 使用 PostgreSQL advisory leader lock 防止多实例重复触发，并通过 ScheduleFire 的唯一约束保证同一 fire time 只创建一次 Execution。动态参数按 Schedule timezone 解析。

任务中心同时支持“宽表 SQL 写入”任务。先在 `SQL_TASK_ALLOWED_SCHEMAS` 白名单中的 schema（默认 `analytics,public`）创建目标宽表，然后在任务编辑器中选择目标表、按 SELECT 输出顺序选择目标列，并填写单条 `SELECT` 或 `WITH ... SELECT` 查询。平台会先使用 PostgreSQL `EXPLAIN` 校验查询与目标列，再由 Scheduler 创建 `SQL_TASK` Execution，最后交给独立 Worker 执行：

```sql
INSERT INTO analytics.daily_wide (trade_date, ts_code, close)
SELECT d.trade_date, d.ts_code, d.close
FROM tushare.daily AS d
WHERE d.trade_date = :trade_date
```

SQL 编辑器不接受 `INSERT`、`UPDATE`、`DELETE`、DDL、多语句或对 `platform`/系统 schema 的读取。可使用 `:execution_date` 参数；选择“交易日（来自本地 trade_cal）”时，还可使用 `:trade_date`。非交易日不会创建 Execution，而会留下 `NON_TRADING_DAY` 的 ScheduleFire 记录。目标表必须由用户预先创建，平台不会从自由 SQL 推断或创建宽表结构。

## Testing

```powershell
.\scripts\dev.ps1 test
.\scripts\dev.ps1 lint
```

Pytest marker 分为 `unit`、`integration`、`e2e` 与 `real_upstream`。普通测试默认排除真实上游：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -m "not real_upstream"
.\.venv\Scripts\python.exe -m pytest -m real_upstream
```

前端检查：`npm --prefix frontend run lint`、`npm --prefix frontend run build`。Ruff 与 ESLint 均启用适度的圈复杂度门槛；它用于发现职责过载，不作为机械拆文件的行数限制。

危险操作浏览器回归使用 Playwright 和确定性的 HTTP mock，不连接开发数据库，也不调用真实 Tushare：

```powershell
npm --prefix frontend run test:e2e
```

覆盖唯一键冲突、Delete Preview/Confirm、取消保护、Reset 策略门禁、Replace Range 与 `FAILED_AFTER_DELETE` 恢复入口。CI 还会重新生成 OpenAPI/TypeScript 契约并通过 `git diff --exit-code` 阻止契约漂移。

后端依赖由 `backend/requirements.lock.txt` 固定；Docker 和 CI 先按锁文件安装，再以 `--no-deps` 安装本项目。更新依赖时必须显式更新锁文件并执行完整测试。普通 CI 运行 Ruff、Pytest Unit、真实 PostgreSQL Integration、ESLint、TypeScript、Vitest 和前端 Build；`real_upstream` 仍保持人工执行。

## Docker

```bash
docker compose up --build
```

Compose 包含 `postgres`、`backend`、`worker`、`scheduler`、`maintenance` 和 `frontend`。生产部署前请替换默认凭据，并由反向代理提供前端静态资源与 TLS。

## Metadata Import

运行时不抓取官方文档。开发工具将官方文档导入 official metadata，再与 platform overrides 合并：

```powershell
.\scripts\dev.ps1 metadata-import
```

离线重建时可直接运行 `backend/tools/import_stock_metadata.py`（不带 `--refresh`）。Inventory、兼容性与审查报告位于 `docs/`。

## Validation Runner

```powershell
.\scripts\dev.ps1 validation
```

Validation Runner 根据每个 API 的 `validation_scenarios` 提交低流量验收任务，并将结果写入 `platform.api_validation_result`。`real_upstream` 验收会消耗上游额度，不属于默认 CI。

## Data Lifecycle

删除必须经过 Preview Token；空条件整表删除被禁止。当前产品化 Replace Range 语义是 `DELETE → 异步 SYNC`，不是长事务或伪回滚。若同步失败，操作会标记 `FAILED_AFTER_DELETE`，可只重试同步步骤而不会再次删除。详见 [Replace Range](docs/replace_range.md) 和 [幂等写入兼容说明](docs/append_mode.md)。

`RESET_AND_RESYNC` 默认关闭。只有 Metadata 配置明确完整性策略时才允许提交，并且最终 SUCCESS 必须同时满足删除成功、同步成功和完整性校验通过。SYNC 成功但覆盖不足会显示 `INCOMPLETE`。

仓库仍保留早期 staging atomic replacement 基础设施用于兼容和迁移参考，但不应被理解为当前默认产品路径；状态见 [Legacy Audit](docs/legacy_audit.md)。

## Troubleshooting

- 页面无法加载：检查 `http://localhost:8000/health/ready` 和 `VITE_API_BASE_URL`。
- Execution 一直 PENDING：确认 Worker 正在运行且心跳正常。
- 调度不触发：确认 Scheduler、timezone、Schedule enabled 状态与 ScheduleFire。
- Tushare 超时：在执行详情查看人类可读错误、自动重试次数和 Raw Error。
- UNIQUE 创建失败：先使用重复检测工具定位历史重复数据，平台不会自动删除。
- trade_cal 告警：启动 Maintenance，由系统 Execution 补齐未来覆盖。
- Replace Range 同步失败：在数据操作历史点击“重新同步”，不要再次执行删除。

更多文档：[Execution State Machine](docs/execution_state_machine.md)、[Error and Warning Catalog](docs/error_catalog.md)、[Engineering Risk Register](docs/engineering_risk_register.md)、[Dependency Security Report](docs/dependency_security_report.md)、[Legacy Audit](docs/legacy_audit.md) 与 [ADR](docs/adr/)。

前端供应链高危门禁可运行 `npm run audit:high`。已评估但暂时无法升级的传递依赖必须记录在 Dependency Security Report 中，并注明实际暴露面与复查日期，不能通过 `--force` 静默绕过。

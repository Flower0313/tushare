# 股票 API Natural Key 验证报告

验证时间：2026-09-30

## 实际样本

| API | 候选自然键 | 上游行数 | 抽样行数 | 抽样重复 | 数据库重复 | 结论 |
|---|---|---:|---:|---:|---:|---|
| `daily` | `ts_code, trade_date` | 5,420 | 100 | 0 | 0 | PASS |
| `income` | `ts_code, end_date, report_type, comp_type, end_type, update_flag, ann_date, f_ann_date` | 1 | 1 | 0 | 0 | SAMPLE_PASS |
| `income_vip` | `ts_code, end_date` | 7,769 | 100 | 0 | 待按新键复核 | USER_CONFIRMED |
| `pro_bar` | `ts_code, trade_date` | 21 | 21 | 0 | 0 | PASS |

## 结论

- `daily` 与 `pro_bar` 已完成非空同步、重跑和数据库重复检测，可进入 PRODUCTION。
- `income` 的小样本无重复，但财务修订维度复杂，保持 VERIFIED，不提升到 PRODUCTION。
- `income_vip` 的自然键已由项目确认调整为 `ts_code + end_date`，接口恢复为 VERIFIED / ACTIVE。
- 旧的重复检测基于已废弃的八字段候选键，不再作为禁用接口的依据；本地数据库启动后仍需按新键执行一次重复检测。

原始证据：`natural_key_daily.json`、`natural_key_income.json`、`natural_key_income_vip.json`、`natural_key_pro_bar.json`、`duplicate_report_income_vip.json`。

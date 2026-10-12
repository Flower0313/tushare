# 财务 API 人工审查报告

财务接口可能同时包含原始报告、更正报告、不同公司类型和不同报告类型。
下表中的唯一键来自独立 Override 人工配置；
标记为 AUTO_IMPORTED 的接口仍不得据此自动 UPSERT。

| API | 参数组合 | Override unique_keys | Review | 重复维度提示 |
|---|---|---|---|---|
| `balancesheet` | ts_code, ann_date, start_date, end_date, period, report_type, comp_type | ts_code, end_date, report_type, comp_type, end_type, update_flag, ann_date, f_ann_date | VERIFIED | ann_date、period、report_type、comp_type |
| `cashflow` | ts_code, ann_date, f_ann_date, start_date, end_date, period, report_type, comp_type, is_calc | ts_code, end_date, report_type, comp_type, end_type, update_flag, ann_date, f_ann_date | VERIFIED | ann_date、f_ann_date、period、report_type、comp_type |
| `disclosure_date` | ts_code, end_date, pre_date, ann_date, actual_date | ts_code, end_date, ann_date, pre_date, modify_date | VERIFIED | ann_date |
| `dividend` | ts_code, ann_date, record_date, ex_date, imp_ann_date | ts_code, end_date, ann_date, div_proc, record_date, ex_date | VERIFIED | ann_date |
| `express` | ts_code, ann_date, start_date, end_date, period | ts_code, end_date, ann_date | VERIFIED | ann_date、period |
| `fina_audit` | ts_code, ann_date, start_date, end_date, period | ts_code, end_date, ann_date, audit_agency, audit_sign | VERIFIED | ann_date、period |
| `fina_indicator` | ts_code, ann_date, start_date, end_date, period | ts_code, end_date, ann_date, update_flag | VERIFIED | ann_date、period |
| `fina_mainbz` | ts_code, period, type, start_date, end_date | ts_code, end_date, bz_item, bz_code, curr_type, update_flag | VERIFIED | period、type |
| `forecast` | ts_code, ann_date, start_date, end_date, period, type | ts_code, ann_date, end_date, type | VERIFIED | ann_date、period、type |
| `income` | ts_code, ann_date, f_ann_date, start_date, end_date, period, report_type, comp_type | ts_code, end_date, report_type, comp_type, end_type, update_flag, ann_date, f_ann_date | VERIFIED | ann_date、f_ann_date、period、report_type、comp_type |
| `income_vip` | ts_code, ann_date, f_ann_date, start_date, end_date, period, report_type, comp_type | ts_code, end_date | VERIFIED | ann_date、f_ann_date、period、report_type、comp_type |

## 审查结论

- `income`、`balancesheet`、`cashflow` 保留公告日、报告期、
  报告类型、公司类型和期末类型维度。
- 普通财务历史接口同一报告期可能存在多次披露或更正，需要保留版本维度。
- 11 个财务接口均已完成文档级自然键与抓取边界审查。
- `income_vip` 的自然键已由项目确认使用 `ts_code + end_date`，
  按必填 `period` 参数执行单季度批量查询，状态为 VERIFIED。
- `income`、`balancesheet`、`cashflow` 的复合键仍需扩大真实样本验证，
  当前结论为 VERIFIED，不提升到 PRODUCTION。
- Importer 不会根据字段名自动写入 unique_keys。

# 股票 API Fetch Boundary 风险报告

| API | Category | Row Limit | Strategy | Risk |
|---|---|---:|---|---|
| `slb_len_mm` | 两融及转融通 | 5000 | SINGLE | SINGLE_WITH_DOCUMENTED_ROW_LIMIT |
| `slb_sec_detail` | 两融及转融通 | 5000 | SINGLE | SINGLE_WITH_DOCUMENTED_ROW_LIMIT |
| `slb_sec` | 两融及转融通 | 5000 | SINGLE | SINGLE_WITH_DOCUMENTED_ROW_LIMIT |
| `stock_basic` | 基础数据 | 6000 | SINGLE | SINGLE_WITH_DOCUMENTED_ROW_LIMIT |
| `limit_cpt_list` | 打板专题数据 | 2000 | SINGLE | SINGLE_WITH_DOCUMENTED_ROW_LIMIT |
| `ths_index` | 打板专题数据 | 5000 | SINGLE | SINGLE_WITH_DOCUMENTED_ROW_LIMIT |
| `limit_step` | 打板专题数据 | 2000 | SINGLE | SINGLE_WITH_DOCUMENTED_ROW_LIMIT |
| `broker_recommend` | 特色数据 | 1000 | SINGLE | SINGLE_WITH_DOCUMENTED_ROW_LIMIT |
| `suspend_d` | 行情数据 | 5000 | SINGLE | SINGLE_WITH_DOCUMENTED_ROW_LIMIT |
| `income_vip` | 财务数据 | UNKNOWN | SINGLE | VIP_LIMIT_NOT_DOCUMENTED |

## 实测

- `daily`: 2025-09-29 全市场返回 5,420 / 6,000，DATE_RANGE 可继续分片。
- `stock_basic`: 返回 5,572 / 6,000；当前未截断，但随上市公司增长存在风险。
- `income_vip`: 2025-06-30 返回 7,769 行，官方页面未明确 VIP 批量上限。

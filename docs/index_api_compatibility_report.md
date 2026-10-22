# 指数专题 API 兼容性报告

接口总数：22

## 汇总

- GENERIC_COMPATIBLE: 22

## 分类统计

| 分类 | 兼容性 | 数量 |
|---|---:|---:|
| 指数专题 | GENERIC_COMPATIBLE | 22 |

## 接口明细

| 分类 | API | 名称 | 结论 | Strategy | 原因 |
|---|---|---|---|---|---|
| 指数专题 | `rt_idx_min` | A股实时分钟 | GENERIC_COMPATIBLE | `code_batch` | Supported by the current generic engine |
| 指数专题 | `sw_mins` | SW历史分钟 | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| 指数专题 | `ci_index_member` | 中信行业成分 | GENERIC_COMPATIBLE | `single` | Supported by the current generic engine |
| 指数专题 | `ci_daily` | 中信行业指数行情 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 指数专题 | `index_global` | 国际指数 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 指数专题 | `index_dailybasic` | 大盘指数每日指标 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 指数专题 | `daily_info` | 市场交易统计 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 指数专题 | `idx_anns` | 指数公司公告 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 指数专题 | `idx_mins` | 指数历史分钟行情 | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| 指数专题 | `index_weekly` | 指数周线行情 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 指数专题 | `index_basic` | 指数基本信息 | GENERIC_COMPATIBLE | `single` | Supported by the current generic engine |
| 指数专题 | `rt_idx_k` | 指数实时日线 | GENERIC_COMPATIBLE | `code_batch` | Supported by the current generic engine |
| 指数专题 | `index_weight` | 指数成分和权重 | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| 指数专题 | `idx_factor_pro` | 指数技术因子(专业版) | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| 指数专题 | `index_daily` | 指数日线行情 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 指数专题 | `index_monthly` | 指数月线行情 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 指数专题 | `sz_daily_info` | 深圳市场每日交易概况 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 指数专题 | `rt_sw_k` | 申万实时行情 | GENERIC_COMPATIBLE | `single` | Supported by the current generic engine |
| 指数专题 | `index_classify` | 申万行业分类 | GENERIC_COMPATIBLE | `single` | Supported by the current generic engine |
| 指数专题 | `index_member_all` | 申万行业成分构成(分级) | GENERIC_COMPATIBLE | `code_batch` | Supported by the current generic engine |
| 指数专题 | `sw_daily` | 申万行业日线行情 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 指数专题 | `vix_index` | 美股恐慌指数行情 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |

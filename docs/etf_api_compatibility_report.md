# ETF专题 API 兼容性报告

接口总数：15

## 汇总

- GENERIC_COMPATIBLE: 15

## 分类统计

| 分类 | 兼容性 | 数量 |
|---|---:|---:|
| ETF专题 | GENERIC_COMPATIBLE | 15 |

## 接口明细

| 分类 | API | 名称 | 结论 | Strategy | 原因 |
|---|---|---|---|---|---|
| ETF专题 | `etf_share_size` | ETF份额规模 | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| ETF专题 | `etf_mins` | ETF历史分钟行情 | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| ETF专题 | `etf_index` | ETF基准指数列表 | GENERIC_COMPATIBLE | `code_batch` | Supported by the current generic engine |
| ETF专题 | `etf_basic` | ETF基础信息 | GENERIC_COMPATIBLE | `code_batch` | Supported by the current generic engine |
| ETF专题 | `rt_etf_min` | ETF实时分钟 | GENERIC_COMPATIBLE | `code_batch` | Supported by the current generic engine |
| ETF专题 | `rt_etf_min_daily` | ETF实时分钟-日累计 | GENERIC_COMPATIBLE | `code_batch` | Supported by the current generic engine |
| ETF专题 | `rt_etf_sz_iopv` | ETF实时参考 | GENERIC_COMPATIBLE | `code_batch` | Supported by the current generic engine |
| ETF专题 | `rt_etf_k` | ETF实时日线 | GENERIC_COMPATIBLE | `code_batch` | Supported by the current generic engine |
| ETF专题 | `etf_auction` | ETF当日集合竞价 | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| ETF专题 | `fund_daily` | ETF日线行情 | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| ETF专题 | `etf_limit` | ETF每日涨跌停价格 | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| ETF专题 | `fund_factor_pro` | 场内基金技术因子(专业版) | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| ETF专题 | `fund_adj` | 基金复权因子 | GENERIC_COMPATIBLE | `offset` | Supported by the current generic engine |
| ETF专题 | `etf_sh_cons` | 每日篮子组合(沪市PCF） | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| ETF专题 | `etf_sz_cons` | 每日篮子组合(深市PCF） | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |

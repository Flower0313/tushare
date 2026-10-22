# ETF / 指数专题接口验收矩阵

生成时间：2026-10-21T11:52:34.946593+00:00

| 分类 | API | Metadata | Generic Engine | 真实预览 | 字段一致 | 真实同步 | 结论 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ETF专题 | `etf_basic` | PASS | PASS | PASS | PASS | NOT_REQUESTED | 真实非空验证通过 |
| ETF专题 | `etf_index` | PASS | PASS | PASS | PASS | NOT_REQUESTED | 真实非空验证通过 |
| ETF专题 | `rt_etf_min` | PASS | PASS | PERMISSION_DENIED | — | NOT_REQUESTED | 当前凭证缺少官方权限 |
| ETF专题 | `rt_etf_min_daily` | PASS | PASS | PERMISSION_DENIED | — | NOT_REQUESTED | 当前凭证缺少官方权限 |
| ETF专题 | `etf_mins` | PASS | PASS | PERMISSION_DENIED | — | NOT_REQUESTED | 当前凭证缺少官方权限 |
| ETF专题 | `rt_etf_k` | PASS | PASS | PERMISSION_DENIED | — | NOT_REQUESTED | 当前凭证缺少官方权限 |
| ETF专题 | `fund_daily` | PASS | PASS | PASS | PASS | NOT_REQUESTED | 真实非空验证通过 |
| ETF专题 | `etf_auction` | PASS | PASS | PERMISSION_DENIED | — | NOT_REQUESTED | 当前凭证缺少官方权限 |
| ETF专题 | `fund_adj` | PASS | PASS | PASS | PASS | NOT_REQUESTED | 真实非空验证通过 |
| ETF专题 | `etf_limit` | PASS | PASS | PASS | PASS | NOT_REQUESTED | 真实非空验证通过 |
| ETF专题 | `fund_factor_pro` | PASS | PASS | PASS | PASS | NOT_REQUESTED | 真实非空验证通过 |
| ETF专题 | `etf_share_size` | PASS | PASS | PERMISSION_DENIED | — | NOT_REQUESTED | 当前凭证缺少官方权限 |
| ETF专题 | `etf_sh_cons` | PASS | PASS | PASS | PASS | NOT_REQUESTED | 真实非空验证通过 |
| ETF专题 | `etf_sz_cons` | PASS | PASS | PASS | PASS | NOT_REQUESTED | 真实非空验证通过 |
| ETF专题 | `rt_etf_sz_iopv` | PASS | PASS | PERMISSION_DENIED | — | NOT_REQUESTED | 当前凭证缺少官方权限 |
| 指数专题 | `index_basic` | PASS | PASS | PASS | PASS | NOT_REQUESTED | 真实非空验证通过 |
| 指数专题 | `index_daily` | PASS | PASS | PASS | PASS | NOT_REQUESTED | 真实非空验证通过 |
| 指数专题 | `rt_idx_k` | PASS | PASS | PERMISSION_DENIED | — | NOT_REQUESTED | 当前凭证缺少官方权限 |
| 指数专题 | `rt_idx_min` | PASS | PASS | PERMISSION_DENIED | — | NOT_REQUESTED | 当前凭证缺少官方权限 |
| 指数专题 | `index_weekly` | PASS | PASS | PASS | PASS | NOT_REQUESTED | 真实非空验证通过 |
| 指数专题 | `idx_mins` | PASS | PASS | PERMISSION_DENIED | — | NOT_REQUESTED | 当前凭证缺少官方权限 |
| 指数专题 | `index_monthly` | PASS | PASS | PASS | PASS | NOT_REQUESTED | 真实非空验证通过 |
| 指数专题 | `index_weight` | PASS | PASS | PASS | PASS | NOT_REQUESTED | 真实非空验证通过 |
| 指数专题 | `index_dailybasic` | PASS | PASS | PASS | PASS | NOT_REQUESTED | 真实非空验证通过 |
| 指数专题 | `index_classify` | PASS | PASS | PASS | PASS | NOT_REQUESTED | 真实非空验证通过 |
| 指数专题 | `index_member_all` | PASS | PASS | PASS | PASS | NOT_REQUESTED | 真实非空验证通过 |
| 指数专题 | `sw_daily` | PASS | PASS | PASS | PASS | NOT_REQUESTED | 真实非空验证通过 |
| 指数专题 | `rt_sw_k` | PASS | PASS | PERMISSION_DENIED | — | NOT_REQUESTED | 当前凭证缺少官方权限 |
| 指数专题 | `sw_mins` | PASS | PASS | PERMISSION_DENIED | — | NOT_REQUESTED | 当前凭证缺少官方权限 |
| 指数专题 | `ci_index_member` | PASS | PASS | PASS | PASS | NOT_REQUESTED | 真实非空验证通过 |
| 指数专题 | `ci_daily` | PASS | PASS | PASS | PASS | NOT_REQUESTED | 真实非空验证通过 |
| 指数专题 | `index_global` | PASS | PASS | PASS | PASS | NOT_REQUESTED | 真实非空验证通过 |
| 指数专题 | `idx_factor_pro` | PASS | PASS | PASS | PASS | NOT_REQUESTED | 真实非空验证通过 |
| 指数专题 | `daily_info` | PASS | PASS | PASS | PASS | NOT_REQUESTED | 真实非空验证通过 |
| 指数专题 | `sz_daily_info` | PASS | PASS | PASS | PASS | NOT_REQUESTED | 真实非空验证通过 |
| 指数专题 | `vix_index` | PASS | PASS | PASS | PASS | NOT_REQUESTED | 真实非空验证通过 |
| 指数专题 | `idx_anns` | PASS | PASS | PERMISSION_DENIED | — | NOT_REQUESTED | 当前凭证缺少官方权限 |

> PERMISSION_DENIED 表示请求已到达 Tushare 且被官方权限校验拒绝；不代表平台 Metadata、参数校验或 Generic Engine 失败。

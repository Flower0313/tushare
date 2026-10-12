# 股票 API 兼容性报告

接口总数：103

## 汇总

- GENERIC_COMPATIBLE: 93
- MANUAL_REVIEW: 9
- UNSUPPORTED: 1

## 分类统计

| 分类 | 兼容性 | 数量 |
|---|---:|---:|
| 两融及转融通 | GENERIC_COMPATIBLE | 4 |
| 两融及转融通 | MANUAL_REVIEW | 3 |
| 参考数据 | GENERIC_COMPATIBLE | 14 |
| 参考数据 | MANUAL_REVIEW | 1 |
| 基础数据 | GENERIC_COMPATIBLE | 13 |
| 打板专题数据 | GENERIC_COMPATIBLE | 19 |
| 打板专题数据 | MANUAL_REVIEW | 3 |
| 特色数据 | GENERIC_COMPATIBLE | 11 |
| 行情数据 | GENERIC_COMPATIBLE | 14 |
| 行情数据 | MANUAL_REVIEW | 2 |
| 行情数据 | UNSUPPORTED | 1 |
| 财务数据 | GENERIC_COMPATIBLE | 11 |
| 资金流向数据 | GENERIC_COMPATIBLE | 7 |

## 接口明细

| 分类 | API | 名称 | 结论 | Strategy | 原因 |
|---|---|---|---|---|---|
| 两融及转融通 | `slb_len_mm` | 做市借券交易汇总 | MANUAL_REVIEW | `single` | Official navigation marks this interface as stopped |
| 两融及转融通 | `margin_detail` | 融资融券交易明细 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 两融及转融通 | `margin` | 融资融券交易汇总 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 两融及转融通 | `margin_secs` | 融资融券标的（盘前更新） | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 两融及转融通 | `slb_sec_detail` | 转融券交易明细 | MANUAL_REVIEW | `single` | Official navigation marks this interface as stopped |
| 两融及转融通 | `slb_sec` | 转融券交易汇总 | MANUAL_REVIEW | `single` | Official navigation marks this interface as stopped |
| 两融及转融通 | `slb_len` | 转融资交易汇总 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 参考数据 | `stk_high_shock` | 个股严重异常波动 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 参考数据 | `stk_shock` | 个股异常波动 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 参考数据 | `stk_alert` | 交易所重点提示证券 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 参考数据 | `top10_floatholders` | 前十大流通股东 | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| 参考数据 | `top10_holders` | 前十大股东 | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| 参考数据 | `block_trade` | 大宗交易 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 参考数据 | `stk_holdernumber` | 股东人数 | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| 参考数据 | `stk_holdertrade` | 股东增减持 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 参考数据 | `pledge_detail` | 股权质押明细 | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| 参考数据 | `pledge_stat` | 股权质押统计数据 | GENERIC_COMPATIBLE | `single` | Supported by the current generic engine |
| 参考数据 | `repurchase` | 股票回购 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 参考数据 | `stk_seasoned` | 股票增发 | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| 参考数据 | `stk_account` | 股票账户开户数据 | MANUAL_REVIEW | `single` | Official navigation marks this interface as stopped |
| 参考数据 | `stk_account_old` | 股票账户开户数据（旧） | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 参考数据 | `share_float` | 限售股解禁 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 基础数据 | `new_share` | IPO新股列表 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 基础数据 | `stock_st` | ST股票列表 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 基础数据 | `st` | ST风险警示板股票 | GENERIC_COMPATIBLE | `code_batch` | Supported by the current generic engine |
| 基础数据 | `stock_company` | 上市公司基本信息 | GENERIC_COMPATIBLE | `single` | Supported by the current generic engine |
| 基础数据 | `stk_managers` | 上市公司管理层 | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| 基础数据 | `trade_cal` | 交易日历 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 基础数据 | `bse_mapping` | 北交所新旧代码对照表 | GENERIC_COMPATIBLE | `single` | Supported by the current generic engine |
| 基础数据 | `stock_hsgt` | 沪深港通股票列表 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 基础数据 | `stk_rewards` | 管理层薪酬和持股 | GENERIC_COMPATIBLE | `code_batch` | Supported by the current generic engine |
| 基础数据 | `stk_premarket` | 股本情况（盘前） | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 基础数据 | `bak_basic` | 股票历史列表（历史每天股票列表） | GENERIC_COMPATIBLE | `trade_date` | Supported by the current generic engine |
| 基础数据 | `stock_basic` | 股票基础信息 | GENERIC_COMPATIBLE | `single` | Supported by the current generic engine |
| 基础数据 | `namechange` | 股票曾用名 | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| 打板专题数据 | `dc_hot` | DC热榜 | GENERIC_COMPATIBLE | `trade_date` | Supported by the current generic engine |
| 打板专题数据 | `tdx_index` | TDX板块信息 | GENERIC_COMPATIBLE | `trade_date` | Supported by the current generic engine |
| 打板专题数据 | `tdx_member` | TDX板块成分 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 打板专题数据 | `tdx_daily` | TDX板块行情 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 打板专题数据 | `ths_hot` | THS热榜 | GENERIC_COMPATIBLE | `trade_date` | Supported by the current generic engine |
| 打板专题数据 | `kpl_list` | 开盘啦榜单数据 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 打板专题数据 | `kpl_concept_cons` | 开盘啦题材成分 | GENERIC_COMPATIBLE | `trade_date` | Supported by the current generic engine |
| 打板专题数据 | `stk_auction` | 当日集合竞价 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 打板专题数据 | `limit_cpt_list` | 最强板块统计 | MANUAL_REVIEW | `single` | Official navigation marks this interface as stopped |
| 打板专题数据 | `dc_member` | 板块成分 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 打板专题数据 | `ths_daily` | 板块指数行情 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 打板专题数据 | `ths_index` | 概念和行业指数 | GENERIC_COMPATIBLE | `single` | Supported by the current generic engine |
| 打板专题数据 | `dc_index` | 概念板块 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 打板专题数据 | `ths_member` | 概念板块成分 | GENERIC_COMPATIBLE | `single` | Supported by the current generic engine |
| 打板专题数据 | `dc_daily` | 概念板块行情 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 打板专题数据 | `limit_list_d` | 涨跌停列表（新） | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 打板专题数据 | `limit_list_ths` | 涨跌停榜单（同花顺） | MANUAL_REVIEW | `single` | Official navigation marks this interface as stopped |
| 打板专题数据 | `hm_list` | 游资名录 | GENERIC_COMPATIBLE | `single` | Supported by the current generic engine |
| 打板专题数据 | `hm_detail` | 游资每日明细 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 打板专题数据 | `limit_step` | 连板天梯 | MANUAL_REVIEW | `single` | Official navigation marks this interface as stopped |
| 打板专题数据 | `top_inst` | 龙虎榜机构明细 | GENERIC_COMPATIBLE | `trade_date` | Supported by the current generic engine |
| 打板专题数据 | `top_list` | 龙虎榜每日明细 | GENERIC_COMPATIBLE | `trade_date` | Supported by the current generic engine |
| 特色数据 | `stk_ah_comparison` | AH股比价 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 特色数据 | `broker_recommend` | 券商每月荐股 | GENERIC_COMPATIBLE | `single` | Supported by the current generic engine |
| 特色数据 | `report_rc` | 卖方盈利预测数据 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 特色数据 | `stk_surv` | 机构调研表 | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| 特色数据 | `cyq_chips` | 每日筹码分布 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 特色数据 | `cyq_perf` | 每日筹码及胜率 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 特色数据 | `stk_nineturn` | 神奇九转指标 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 特色数据 | `stk_auction_o` | 股票开盘集合竞价数据 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 特色数据 | `stk_factor` | 股票技术因子（量化因子） | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| 特色数据 | `stk_factor_pro` | 股票技术面因子(专业版) | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| 特色数据 | `stk_auction_c` | 股票收盘集合竞价数据 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 行情数据 | `rt_min` | A股实时分钟 | GENERIC_COMPATIBLE | `code_batch` | Supported by the current generic engine |
| 行情数据 | `rt_min_daily` | A股实时分钟-日累计 | GENERIC_COMPATIBLE | `code_batch` | Supported by the current generic engine |
| 行情数据 | `rt_k` | A股实时日线 | GENERIC_COMPATIBLE | `code_batch` | Supported by the current generic engine |
| 行情数据 | `daily` | A股日线行情 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 行情数据 | `weekly` | 周线行情 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 行情数据 | `bak_daily` | 备用行情 | GENERIC_COMPATIBLE | `offset` | Supported by the current generic engine |
| 行情数据 | `adj_factor` | 复权因子 | GENERIC_COMPATIBLE | `single` | Supported by the current generic engine |
| 行情数据 | `monthly` | 月线行情 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 行情数据 | `suspend_d` | 每日停复牌信息 | MANUAL_REVIEW | `single` | Official navigation marks this interface as stopped |
| 行情数据 | `daily_basic` | 每日指标 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 行情数据 | `stk_limit` | 每日涨跌停价格 | MANUAL_REVIEW | `single` | Official navigation marks this interface as stopped |
| 行情数据 | `hsgt_top10` | 沪深股通十大成交股 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 行情数据 | `stk_mins` | 股票历史分钟行情 | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| 行情数据 | `stk_week_month_adj` | 股票周/月线行情(复权--每日更新) | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| 行情数据 | `stk_weekly_monthly` | 股票周/月线行情(每日更新) | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| 行情数据 | `unknown_doc_109` | 通用行情接口 | UNSUPPORTED | `single` | Metadata validation failed |
| 财务数据 | `express` | 业绩快报 | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| 财务数据 | `forecast` | 业绩预告 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 财务数据 | `fina_mainbz` | 主营业务构成 | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| 财务数据 | `dividend` | 分红送股 | GENERIC_COMPATIBLE | `code_batch` | Supported by the current generic engine |
| 财务数据 | `income` | 利润表 | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| 财务数据 | `cashflow` | 现金流量表 | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| 财务数据 | `fina_audit` | 财务审计意见 | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| 财务数据 | `fina_indicator` | 财务指标数据 | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| 财务数据 | `disclosure_date` | 财报披露计划 | GENERIC_COMPATIBLE | `code_batch` | Supported by the current generic engine |
| 财务数据 | `balancesheet` | 资产负债表 | GENERIC_COMPATIBLE | `date_and_code` | Supported by the current generic engine |
| 资金流向数据 | `moneyflow_ind_dc` | 东财概念及行业板块资金流向（DC） | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 资金流向数据 | `moneyflow` | 个股资金流向 | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 资金流向数据 | `moneyflow_dc` | 个股资金流向（DC） | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 资金流向数据 | `moneyflow_ths` | 个股资金流向（THS） | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 资金流向数据 | `moneyflow_cnt_ths` | 同花顺概念板块资金流向（THS） | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 资金流向数据 | `moneyflow_ind_ths` | 同花顺行业资金流向（THS） | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 资金流向数据 | `moneyflow_mkt_dc` | 大盘资金流向（DC） | GENERIC_COMPATIBLE | `date_range` | Supported by the current generic engine |
| 财务数据 | `income_vip` | 利润表（VIP批量） | GENERIC_COMPATIBLE | `single` | Supported by the current generic engine |
| 行情数据 | `pro_bar` | 通用行情接口 | GENERIC_COMPATIBLE | `custom` | Supported by the current generic engine |

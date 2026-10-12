# 股票 API Review Report

接口总数：103

## 两融及转融通

### `margin` — 融资融券交易汇总

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`margin` / 股票数据 / 两融及转融通
- 参数：trade_date, start_date, end_date, exchange_id
- 输出字段：9 个
- 官方单次上限：4000
- start_date / end_date：是
- trade_date：是
- ts_code：否
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：trade_date, exchange_id
- default_order_by：trade_date DESC, exchange_id ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `margin_detail` — 融资融券交易明细

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`margin_detail` / 股票数据 / 两融及转融通
- 参数：trade_date, ts_code, start_date, end_date
- 输出字段：11 个
- 官方单次上限：6000
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：trade_date, ts_code
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `margin_secs` — 融资融券标的（盘前更新）

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`margin_secs` / 股票数据 / 两融及转融通
- 参数：ts_code, trade_date, exchange, start_date, end_date
- 输出字段：4 个
- 官方单次上限：6000
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：trade_date, ts_code, exchange
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `slb_len` — 转融资交易汇总

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`slb_len` / 股票数据 / 两融及转融通
- 参数：trade_date, start_date, end_date
- 输出字段：6 个
- 官方单次上限：5000
- start_date / end_date：是
- trade_date：是
- ts_code：否
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：trade_date
- default_order_by：trade_date DESC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：否
- 可安全 UPSERT：是

### `slb_len_mm` — 做市借券交易汇总

- 状态：DEPRECATED
- Maturity：DEPRECATED
- API / 分类：`slb_len_mm` / 股票数据 / 两融及转融通
- 参数：trade_date, ts_code, start_date, end_date
- 输出字段：7 个
- 官方单次上限：5000
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`SINGLE`
- unique_keys：未配置
- default_order_by：未配置
- 允许无边界全量查询：否
- 日期分片：否
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：否
- 可安全 UPSERT：否

### `slb_sec` — 转融券交易汇总

- 状态：DEPRECATED
- Maturity：DEPRECATED
- API / 分类：`slb_sec` / 股票数据 / 两融及转融通
- 参数：trade_date, ts_code, start_date, end_date
- 输出字段：7 个
- 官方单次上限：5000
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`SINGLE`
- unique_keys：未配置
- default_order_by：未配置
- 允许无边界全量查询：否
- 日期分片：否
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：否
- 可安全 UPSERT：否

### `slb_sec_detail` — 转融券交易明细

- 状态：DEPRECATED
- Maturity：DEPRECATED
- API / 分类：`slb_sec_detail` / 股票数据 / 两融及转融通
- 参数：trade_date, ts_code, start_date, end_date
- 输出字段：6 个
- 官方单次上限：5000
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`SINGLE`
- unique_keys：未配置
- default_order_by：未配置
- 允许无边界全量查询：否
- 日期分片：否
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：否
- 可安全 UPSERT：否

## 参考数据

### `block_trade` — 大宗交易

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`block_trade` / 股票数据 / 参考数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：7 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, trade_date, price, vol, buyer, seller
- default_order_by：trade_date DESC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `pledge_detail` — 股权质押明细

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`pledge_detail` / 股票数据 / 参考数据
- 参数：ts_code, ann_date, start_date, end_date
- 输出字段：14 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_AND_CODE`
- unique_keys：ts_code, ann_date, holder_name, start_date, pledge_amount
- default_order_by：ann_date DESC, end_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：是
- DATE_AND_CODE：是
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：ann_date
- 复合自然键：是
- 可安全 UPSERT：是

### `pledge_stat` — 股权质押统计数据

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`pledge_stat` / 股票数据 / 参考数据
- 参数：ts_code, end_date
- 输出字段：7 个
- 官方单次上限：未明确
- start_date / end_date：否
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`SINGLE`
- unique_keys：ts_code, end_date
- default_order_by：end_date DESC, ts_code ASC
- 允许无边界全量查询：是
- 日期分片：否
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `repurchase` — 股票回购

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`repurchase` / 股票数据 / 参考数据
- 参数：ann_date, start_date, end_date
- 输出字段：9 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：否
- ts_code：否
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, ann_date, end_date, proc
- default_order_by：ann_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：ann_date
- 复合自然键：是
- 可安全 UPSERT：是

### `share_float` — 限售股解禁

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`share_float` / 股票数据 / 参考数据
- 参数：ts_code, ann_date, float_date, start_date, end_date
- 输出字段：7 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, ann_date, float_date, holder_name, share_type
- default_order_by：float_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：ann_date
- 复合自然键：是
- 可安全 UPSERT：是

### `stk_account` — 股票账户开户数据

- 状态：DEPRECATED
- Maturity：DEPRECATED
- API / 分类：`stk_account` / 股票数据 / 参考数据
- 参数：date, start_date, end_date
- 输出字段：5 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：否
- ts_code：否
- offset / limit：否
- 推荐 Strategy：`SINGLE`
- unique_keys：未配置
- default_order_by：未配置
- 允许无边界全量查询：是
- 日期分片：否
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：否
- 可安全 UPSERT：否

### `stk_account_old` — 股票账户开户数据（旧）

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`stk_account_old` / 股票数据 / 参考数据
- 参数：start_date, end_date
- 输出字段：9 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：否
- ts_code：否
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：date
- default_order_by：date DESC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：否
- 可安全 UPSERT：是

### `stk_alert` — 交易所重点提示证券

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`stk_alert` / 股票数据 / 参考数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：5 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, start_date, type
- default_order_by：end_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `stk_high_shock` — 个股严重异常波动

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`stk_high_shock` / 股票数据 / 参考数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：6 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, trade_date, period, reason
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `stk_holdernumber` — 股东人数

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`stk_holdernumber` / 股票数据 / 参考数据
- 参数：ts_code, ann_date, enddate, start_date, end_date
- 输出字段：4 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_AND_CODE`
- unique_keys：ts_code, end_date, ann_date
- default_order_by：ann_date DESC, end_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：是
- DATE_AND_CODE：是
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：ann_date
- 复合自然键：是
- 可安全 UPSERT：是

### `stk_holdertrade` — 股东增减持

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`stk_holdertrade` / 股票数据 / 参考数据
- 参数：ts_code, ann_date, start_date, end_date, trade_type, holder_type
- 输出字段：13 个
- 官方单次上限：3000
- start_date / end_date：是
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, ann_date, holder_name, begin_date, close_date, in_de
- default_order_by：ann_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：ann_date
- 复合自然键：是
- 可安全 UPSERT：是

### `stk_seasoned` — 股票增发

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`stk_seasoned` / 股票数据 / 参考数据
- 参数：ts_code, ann_date, start_date, end_date
- 输出字段：69 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_AND_CODE`
- unique_keys：ts_code, ann_date, fo_type, update_flag
- default_order_by：ann_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：是
- DATE_AND_CODE：是
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：ann_date, update_flag
- 复合自然键：是
- 可安全 UPSERT：是

### `stk_shock` — 个股异常波动

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`stk_shock` / 股票数据 / 参考数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：6 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, trade_date, period, reason
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `top10_floatholders` — 前十大流通股东

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`top10_floatholders` / 股票数据 / 参考数据
- 参数：ts_code, period, ann_date, start_date, end_date
- 输出字段：9 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_AND_CODE`
- unique_keys：ts_code, end_date, ann_date, holder_name
- default_order_by：ann_date DESC, end_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：是
- DATE_AND_CODE：是
- 特殊业务维度：同一报告期按公告版本和股东名称区分
- 修订/公告/版本字段：ann_date
- 复合自然键：是
- 可安全 UPSERT：是

### `top10_holders` — 前十大股东

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`top10_holders` / 股票数据 / 参考数据
- 参数：ts_code, period, ann_date, start_date, end_date
- 输出字段：9 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_AND_CODE`
- unique_keys：ts_code, end_date, ann_date, holder_name
- default_order_by：ann_date DESC, end_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：是
- DATE_AND_CODE：是
- 特殊业务维度：同一报告期按公告版本和股东名称区分
- 修订/公告/版本字段：ann_date
- 复合自然键：是
- 可安全 UPSERT：是

## 基础数据

### `bak_basic` — 股票历史列表（历史每天股票列表）

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`bak_basic` / 股票数据 / 基础数据
- 参数：trade_date, ts_code
- 输出字段：24 个
- 官方单次上限：未明确
- start_date / end_date：否
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`TRADE_DATE`
- unique_keys：trade_date, ts_code
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `bse_mapping` — 北交所新旧代码对照表

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`bse_mapping` / 股票数据 / 基础数据
- 参数：o_code, n_code
- 输出字段：4 个
- 官方单次上限：未明确
- start_date / end_date：否
- trade_date：否
- ts_code：否
- offset / limit：否
- 推荐 Strategy：`SINGLE`
- unique_keys：o_code, n_code
- default_order_by：未配置
- 允许无边界全量查询：是
- 日期分片：否
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `namechange` — 股票曾用名

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`namechange` / 股票数据 / 基础数据
- 参数：ts_code, start_date, end_date
- 输出字段：6 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_AND_CODE`
- unique_keys：ts_code, name, start_date, ann_date
- default_order_by：ann_date DESC, end_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：是
- DATE_AND_CODE：是
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：ann_date
- 复合自然键：是
- 可安全 UPSERT：是

### `new_share` — IPO新股列表

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`new_share` / 股票数据 / 基础数据
- 参数：start_date, end_date
- 输出字段：12 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：否
- ts_code：否
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code
- default_order_by：ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：否
- 可安全 UPSERT：是

### `st` — ST风险警示板股票

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`st` / 股票数据 / 基础数据
- 参数：ts_code, pub_date, imp_date
- 输出字段：7 个
- 官方单次上限：未明确
- start_date / end_date：否
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`CODE_BATCH`
- unique_keys：ts_code, pub_date, st_type
- default_order_by：ts_code ASC
- 允许无边界全量查询：否
- 日期分片：否
- 股票代码分片：是
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `stk_managers` — 上市公司管理层

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`stk_managers` / 股票数据 / 基础数据
- 参数：ts_code, ann_date, start_date, end_date
- 输出字段：12 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_AND_CODE`
- unique_keys：ts_code, ann_date, name, begin_date, title
- default_order_by：ann_date DESC, end_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：是
- DATE_AND_CODE：是
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：ann_date
- 复合自然键：是
- 可安全 UPSERT：是

### `stk_premarket` — 股本情况（盘前）

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`stk_premarket` / 股票数据 / 基础数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：7 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：trade_date, ts_code
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `stk_rewards` — 管理层薪酬和持股

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`stk_rewards` / 股票数据 / 基础数据
- 参数：ts_code, end_date
- 输出字段：7 个
- 官方单次上限：未明确
- start_date / end_date：否
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`CODE_BATCH`
- unique_keys：ts_code, end_date, ann_date, name, title
- default_order_by：ann_date DESC, end_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：否
- 股票代码分片：是
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：ann_date
- 复合自然键：是
- 可安全 UPSERT：是

### `stock_basic` — 股票基础信息

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`stock_basic` / 股票数据 / 基础数据
- 参数：ts_code, name, market, list_status, exchange, is_hs
- 输出字段：17 个
- 官方单次上限：6000
- start_date / end_date：否
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`SINGLE`
- unique_keys：ts_code
- default_order_by：ts_code ASC
- 允许无边界全量查询：否
- 日期分片：否
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：否
- 可安全 UPSERT：是

### `stock_company` — 上市公司基本信息

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`stock_company` / 股票数据 / 基础数据
- 参数：ts_code, exchange
- 输出字段：18 个
- 官方单次上限：未明确
- start_date / end_date：否
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`SINGLE`
- unique_keys：ts_code
- default_order_by：ts_code ASC
- 允许无边界全量查询：是
- 日期分片：否
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：否
- 可安全 UPSERT：是

### `stock_hsgt` — 沪深港通股票列表

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`stock_hsgt` / 股票数据 / 基础数据
- 参数：ts_code, trade_date, type, start_date, end_date
- 输出字段：5 个
- 官方单次上限：2000
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, trade_date, type
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `stock_st` — ST股票列表

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`stock_st` / 股票数据 / 基础数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：5 个
- 官方单次上限：1000
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, trade_date, type
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `trade_cal` — 交易日历

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`trade_cal` / 股票数据 / 基础数据
- 参数：exchange, start_date, end_date, is_open
- 输出字段：4 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：否
- ts_code：否
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：exchange, cal_date
- default_order_by：cal_date DESC, exchange ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

## 打板专题数据

### `dc_daily` — 概念板块行情

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`dc_daily` / 股票数据 / 打板专题数据
- 参数：ts_code, trade_date, start_date, end_date, idx_type
- 输出字段：13 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, trade_date, category
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `dc_hot` — DC热榜

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`dc_hot` / 股票数据 / 打板专题数据
- 参数：trade_date, ts_code, market, hot_type, is_new
- 输出字段：8 个
- 官方单次上限：未明确
- start_date / end_date：否
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`TRADE_DATE`
- unique_keys：trade_date, data_type, ts_code, rank_time
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `dc_index` — 概念板块

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`dc_index` / 股票数据 / 打板专题数据
- 参数：ts_code, name, trade_date, start_date, end_date, idx_type
- 输出字段：13 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, trade_date, idx_type
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `dc_member` — 板块成分

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`dc_member` / 股票数据 / 打板专题数据
- 参数：ts_code, con_code, trade_date, start_date, end_date
- 输出字段：4 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：trade_date, con_code, ts_code
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `hm_detail` — 游资每日明细

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`hm_detail` / 股票数据 / 打板专题数据
- 参数：trade_date, ts_code, hm_name, start_date, end_date
- 输出字段：9 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：trade_date, ts_code, hm_name
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `hm_list` — 游资名录

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`hm_list` / 股票数据 / 打板专题数据
- 参数：name
- 输出字段：3 个
- 官方单次上限：未明确
- start_date / end_date：否
- trade_date：否
- ts_code：否
- offset / limit：否
- 推荐 Strategy：`SINGLE`
- unique_keys：name
- default_order_by：未配置
- 允许无边界全量查询：是
- 日期分片：否
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：否
- 可安全 UPSERT：是

### `kpl_concept_cons` — 开盘啦题材成分

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`kpl_concept_cons` / 股票数据 / 打板专题数据
- 参数：trade_date, ts_code, con_code
- 输出字段：7 个
- 官方单次上限：未明确
- start_date / end_date：否
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`TRADE_DATE`
- unique_keys：trade_date, con_code, ts_code
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `kpl_list` — 开盘啦榜单数据

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`kpl_list` / 股票数据 / 打板专题数据
- 参数：ts_code, trade_date, tag, start_date, end_date
- 输出字段：24 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, trade_date, tag
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `limit_cpt_list` — 最强板块统计

- 状态：DEPRECATED
- Maturity：DEPRECATED
- API / 分类：`limit_cpt_list` / 股票数据 / 打板专题数据
- 参数：trade_date, ts_code, start_date, end_date
- 输出字段：9 个
- 官方单次上限：2000
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`SINGLE`
- unique_keys：未配置
- default_order_by：未配置
- 允许无边界全量查询：否
- 日期分片：否
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：否
- 可安全 UPSERT：否

### `limit_list_d` — 涨跌停列表（新）

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`limit_list_d` / 股票数据 / 打板专题数据
- 参数：trade_date, ts_code, limit_type, exchange, start_date, end_date
- 输出字段：18 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：trade_date, ts_code, limit
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `limit_list_ths` — 涨跌停榜单（同花顺）

- 状态：DEPRECATED
- Maturity：DEPRECATED
- API / 分类：`limit_list_ths` / 股票数据 / 打板专题数据
- 参数：trade_date, ts_code, limit_type, market, start_date, end_date
- 输出字段：24 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`SINGLE`
- unique_keys：未配置
- default_order_by：未配置
- 允许无边界全量查询：是
- 日期分片：否
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：否
- 可安全 UPSERT：否

### `limit_step` — 连板天梯

- 状态：DEPRECATED
- Maturity：DEPRECATED
- API / 分类：`limit_step` / 股票数据 / 打板专题数据
- 参数：trade_date, ts_code, start_date, end_date, nums
- 输出字段：4 个
- 官方单次上限：2000
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`SINGLE`
- unique_keys：未配置
- default_order_by：未配置
- 允许无边界全量查询：否
- 日期分片：否
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：否
- 可安全 UPSERT：否

### `stk_auction` — 当日集合竞价

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`stk_auction` / 股票数据 / 打板专题数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：9 个
- 官方单次上限：8000
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, trade_date
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `tdx_daily` — TDX板块行情

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`tdx_daily` / 股票数据 / 打板专题数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：38 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, trade_date
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `tdx_index` — TDX板块信息

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`tdx_index` / 股票数据 / 打板专题数据
- 参数：ts_code, trade_date, idx_type
- 输出字段：9 个
- 官方单次上限：未明确
- start_date / end_date：否
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`TRADE_DATE`
- unique_keys：ts_code, trade_date, idx_type
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `tdx_member` — TDX板块成分

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`tdx_member` / 股票数据 / 打板专题数据
- 参数：ts_code, con_code, trade_date, start_date, end_date
- 输出字段：4 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, con_code, trade_date
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `ths_daily` — 板块指数行情

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`ths_daily` / 股票数据 / 打板专题数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：14 个
- 官方单次上限：3000
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, trade_date
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `ths_hot` — THS热榜

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`ths_hot` / 股票数据 / 打板专题数据
- 参数：trade_date, ts_code, market, is_new
- 输出字段：11 个
- 官方单次上限：未明确
- start_date / end_date：否
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`TRADE_DATE`
- unique_keys：trade_date, data_type, ts_code, rank_time
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `ths_index` — 概念和行业指数

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`ths_index` / 股票数据 / 打板专题数据
- 参数：ts_code, exchange, type
- 输出字段：6 个
- 官方单次上限：5000
- start_date / end_date：否
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`SINGLE`
- unique_keys：ts_code
- default_order_by：ts_code ASC
- 允许无边界全量查询：否
- 日期分片：否
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：否
- 可安全 UPSERT：是

### `ths_member` — 概念板块成分

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`ths_member` / 股票数据 / 打板专题数据
- 参数：ts_code, con_code
- 输出字段：7 个
- 官方单次上限：未明确
- start_date / end_date：否
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`SINGLE`
- unique_keys：ts_code, con_code, in_date, out_date
- default_order_by：ts_code ASC
- 允许无边界全量查询：是
- 日期分片：否
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `top_inst` — 龙虎榜机构明细

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`top_inst` / 股票数据 / 打板专题数据
- 参数：trade_date, ts_code
- 输出字段：10 个
- 官方单次上限：10000
- start_date / end_date：否
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`TRADE_DATE`
- unique_keys：trade_date, ts_code, exalter, side
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `top_list` — 龙虎榜每日明细

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`top_list` / 股票数据 / 打板专题数据
- 参数：trade_date, ts_code
- 输出字段：15 个
- 官方单次上限：10000
- start_date / end_date：否
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`TRADE_DATE`
- unique_keys：trade_date, ts_code
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

## 特色数据

### `broker_recommend` — 券商每月荐股

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`broker_recommend` / 股票数据 / 特色数据
- 参数：month
- 输出字段：4 个
- 官方单次上限：1000
- start_date / end_date：否
- trade_date：否
- ts_code：否
- offset / limit：否
- 推荐 Strategy：`SINGLE`
- unique_keys：month, broker, ts_code
- default_order_by：month DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：否
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `cyq_chips` — 每日筹码分布

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`cyq_chips` / 股票数据 / 特色数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：4 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, trade_date, price
- default_order_by：trade_date DESC, ts_code ASC, price ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `cyq_perf` — 每日筹码及胜率

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`cyq_perf` / 股票数据 / 特色数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：11 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, trade_date
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `report_rc` — 卖方盈利预测数据

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`report_rc` / 股票数据 / 特色数据
- 参数：ts_code, report_date, start_date, end_date
- 输出字段：23 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, report_date, report_title, org_name, author_name
- default_order_by：ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：report_type
- 复合自然键：是
- 可安全 UPSERT：是

### `stk_ah_comparison` — AH股比价

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`stk_ah_comparison` / 股票数据 / 特色数据
- 参数：hk_code, ts_code, trade_date, start_date, end_date
- 输出字段：11 个
- 官方单次上限：1000
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, hk_code, trade_date
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `stk_auction_c` — 股票收盘集合竞价数据

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`stk_auction_c` / 股票数据 / 特色数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：9 个
- 官方单次上限：10000
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, trade_date
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `stk_auction_o` — 股票开盘集合竞价数据

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`stk_auction_o` / 股票数据 / 特色数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：9 个
- 官方单次上限：10000
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, trade_date
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `stk_factor` — 股票技术因子（量化因子）

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`stk_factor` / 股票数据 / 特色数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：35 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_AND_CODE`
- unique_keys：ts_code, trade_date
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：是
- DATE_AND_CODE：是
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `stk_factor_pro` — 股票技术面因子(专业版)

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`stk_factor_pro` / 股票数据 / 特色数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：261 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_AND_CODE`
- unique_keys：ts_code, trade_date
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：是
- DATE_AND_CODE：是
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `stk_nineturn` — 神奇九转指标

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`stk_nineturn` / 股票数据 / 特色数据
- 参数：ts_code, trade_date, freq, start_date, end_date
- 输出字段：13 个
- 官方单次上限：10000
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, trade_date, freq
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `stk_surv` — 机构调研表

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`stk_surv` / 股票数据 / 特色数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：10 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_AND_CODE`
- unique_keys：ts_code, surv_date, rece_org, rece_mode
- default_order_by：ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：是
- DATE_AND_CODE：是
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

## 行情数据

### `adj_factor` — 复权因子

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`adj_factor` / 股票数据 / 行情数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：3 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`SINGLE`
- unique_keys：ts_code, trade_date
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：是
- 日期分片：否
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `bak_daily` — 备用行情

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`bak_daily` / 股票数据 / 行情数据
- 参数：ts_code, trade_date, start_date, end_date, offset, limit
- 输出字段：31 个
- 官方单次上限：7000
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：是
- 推荐 Strategy：`OFFSET`
- unique_keys：ts_code, trade_date
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：否
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `daily` — A股日线行情

- 状态：VERIFIED
- Maturity：PRODUCTION
- API / 分类：`daily` / 股票数据 / 行情数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：13 个
- 官方单次上限：6000
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, trade_date
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `daily_basic` — 每日指标

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`daily_basic` / 股票数据 / 行情数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：19 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, trade_date
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `hsgt_top10` — 沪深股通十大成交股

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`hsgt_top10` / 股票数据 / 行情数据
- 参数：ts_code, trade_date, start_date, end_date, market_type
- 输出字段：11 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：trade_date, market_type, ts_code, rank
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `monthly` — 月线行情

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`monthly` / 股票数据 / 行情数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：11 个
- 官方单次上限：4500
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, trade_date
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `pro_bar` — 通用行情接口

- 状态：VERIFIED
- Maturity：PRODUCTION
- API / 分类：`pro_bar` / 股票数据 / 行情数据
- 参数：ts_code, start_date, end_date, trade_date, adj, freq, asset
- 输出字段：12 个
- 官方单次上限：6000
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`CUSTOM`
- unique_keys：ts_code, trade_date
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：否
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `rt_k` — A股实时日线

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`rt_k` / 股票数据 / 行情数据
- 参数：ts_code
- 输出字段：15 个
- 官方单次上限：未明确
- start_date / end_date：否
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`CODE_BATCH`
- unique_keys：ts_code, trade_time
- default_order_by：ts_code ASC
- 允许无边界全量查询：否
- 日期分片：否
- 股票代码分片：是
- DATE_AND_CODE：否
- 特殊业务维度：实时快照按 trade_time 保留
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `rt_min` — A股实时分钟

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`rt_min` / 股票数据 / 行情数据
- 参数：freq, ts_code
- 输出字段：8 个
- 官方单次上限：1000
- start_date / end_date：否
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`CODE_BATCH`
- unique_keys：ts_code, time
- default_order_by：ts_code ASC
- 允许无边界全量查询：否
- 日期分片：否
- 股票代码分片：是
- DATE_AND_CODE：否
- 特殊业务维度：实时分钟数据只适合当前交易时段
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `rt_min_daily` — A股实时分钟-日累计

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`rt_min_daily` / 股票数据 / 行情数据
- 参数：freq, ts_code
- 输出字段：9 个
- 官方单次上限：未明确
- start_date / end_date：否
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`CODE_BATCH`
- unique_keys：ts_code, freq, time
- default_order_by：ts_code ASC
- 允许无边界全量查询：否
- 日期分片：否
- 股票代码分片：是
- DATE_AND_CODE：否
- 特殊业务维度：实时日累计数据只适合当前交易时段
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `stk_limit` — 每日涨跌停价格

- 状态：DEPRECATED
- Maturity：DEPRECATED
- API / 分类：`stk_limit` / 股票数据 / 行情数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：7 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`SINGLE`
- unique_keys：未配置
- default_order_by：未配置
- 允许无边界全量查询：是
- 日期分片：否
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：否
- 可安全 UPSERT：否

### `stk_mins` — 股票历史分钟行情

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`stk_mins` / 股票数据 / 行情数据
- 参数：ts_code, freq, start_date, end_date
- 输出字段：8 个
- 官方单次上限：8000
- start_date / end_date：是
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_AND_CODE`
- unique_keys：ts_code, trade_time
- default_order_by：ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：是
- DATE_AND_CODE：是
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `stk_week_month_adj` — 股票周/月线行情(复权--每日更新)

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`stk_week_month_adj` / 股票数据 / 行情数据
- 参数：ts_code, trade_date, start_date, end_date, freq
- 输出字段：21 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_AND_CODE`
- unique_keys：ts_code, trade_date, freq
- default_order_by：trade_date DESC, end_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：是
- DATE_AND_CODE：是
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `stk_weekly_monthly` — 股票周/月线行情(每日更新)

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`stk_weekly_monthly` / 股票数据 / 行情数据
- 参数：ts_code, trade_date, start_date, end_date, freq
- 输出字段：13 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_AND_CODE`
- unique_keys：ts_code, trade_date, freq
- default_order_by：trade_date DESC, end_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：是
- DATE_AND_CODE：是
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `suspend_d` — 每日停复牌信息

- 状态：DEPRECATED
- Maturity：DEPRECATED
- API / 分类：`suspend_d` / 股票数据 / 行情数据
- 参数：ts_code, trade_date, start_date, end_date, suspend_type
- 输出字段：4 个
- 官方单次上限：5000
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`SINGLE`
- unique_keys：未配置
- default_order_by：未配置
- 允许无边界全量查询：否
- 日期分片：否
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：否
- 可安全 UPSERT：否

### `unknown_doc_109` — 通用行情接口

- 状态：UNSUPPORTED
- Maturity：EXPERIMENTAL
- API / 分类：`unknown_doc_109` / 股票数据 / 行情数据
- 参数：ts_code, start_date, end_date, asset, adj, freq, ma, factors, adjfactor
- 输出字段：0 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`SINGLE`
- unique_keys：未配置
- default_order_by：未配置
- 允许无边界全量查询：否
- 日期分片：否
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：否
- 可安全 UPSERT：否

### `weekly` — 周线行情

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`weekly` / 股票数据 / 行情数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：11 个
- 官方单次上限：6000
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, trade_date
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

## 财务数据

### `balancesheet` — 资产负债表

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`balancesheet` / 股票数据 / 财务数据
- 参数：ts_code, ann_date, start_date, end_date, period, report_type, comp_type
- 输出字段：158 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_AND_CODE`
- unique_keys：ts_code, end_date, report_type, comp_type, end_type, update_flag, ann_date, f_ann_date
- default_order_by：end_date DESC, ann_date DESC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：是
- DATE_AND_CODE：是
- 特殊业务维度：report_type, comp_type, end_type
- 修订/公告/版本字段：ann_date, f_ann_date, update_flag, report_type
- 复合自然键：是
- 可安全 UPSERT：是

### `cashflow` — 现金流量表

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`cashflow` / 股票数据 / 财务数据
- 参数：ts_code, ann_date, f_ann_date, start_date, end_date, period, report_type, comp_type, is_calc
- 输出字段：97 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_AND_CODE`
- unique_keys：ts_code, end_date, report_type, comp_type, end_type, update_flag, ann_date, f_ann_date
- default_order_by：end_date DESC, ann_date DESC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：是
- DATE_AND_CODE：是
- 特殊业务维度：report_type, comp_type, end_type
- 修订/公告/版本字段：ann_date, f_ann_date, update_flag, report_type
- 复合自然键：是
- 可安全 UPSERT：是

### `disclosure_date` — 财报披露计划

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`disclosure_date` / 股票数据 / 财务数据
- 参数：ts_code, end_date, pre_date, ann_date, actual_date
- 输出字段：6 个
- 官方单次上限：未明确
- start_date / end_date：否
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`CODE_BATCH`
- unique_keys：ts_code, end_date, ann_date, pre_date, modify_date
- default_order_by：ann_date DESC, end_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：否
- 股票代码分片：是
- DATE_AND_CODE：否
- 特殊业务维度：预披露日期可能多次修改
- 修订/公告/版本字段：ann_date
- 复合自然键：是
- 可安全 UPSERT：是

### `dividend` — 分红送股

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`dividend` / 股票数据 / 财务数据
- 参数：ts_code, ann_date, record_date, ex_date, imp_ann_date
- 输出字段：16 个
- 官方单次上限：2000
- start_date / end_date：否
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`CODE_BATCH`
- unique_keys：ts_code, end_date, ann_date, div_proc, record_date, ex_date
- default_order_by：ann_date DESC, end_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：否
- 股票代码分片：是
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：ann_date
- 复合自然键：是
- 可安全 UPSERT：是

### `express` — 业绩快报

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`express` / 股票数据 / 财务数据
- 参数：ts_code, ann_date, start_date, end_date, period
- 输出字段：32 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_AND_CODE`
- unique_keys：ts_code, end_date, ann_date
- default_order_by：ann_date DESC, end_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：是
- DATE_AND_CODE：是
- 特殊业务维度：按公告日保留同一报告期不同版本
- 修订/公告/版本字段：ann_date
- 复合自然键：是
- 可安全 UPSERT：是

### `fina_audit` — 财务审计意见

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`fina_audit` / 股票数据 / 财务数据
- 参数：ts_code, ann_date, start_date, end_date, period
- 输出字段：7 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_AND_CODE`
- unique_keys：ts_code, end_date, ann_date, audit_agency, audit_sign
- default_order_by：ann_date DESC, end_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：是
- DATE_AND_CODE：是
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：ann_date
- 复合自然键：是
- 可安全 UPSERT：是

### `fina_indicator` — 财务指标数据

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`fina_indicator` / 股票数据 / 财务数据
- 参数：ts_code, ann_date, start_date, end_date, period
- 输出字段：167 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_AND_CODE`
- unique_keys：ts_code, end_date, ann_date, update_flag
- default_order_by：ann_date DESC, end_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：是
- DATE_AND_CODE：是
- 特殊业务维度：update_flag 区分更新版本
- 修订/公告/版本字段：ann_date, update_flag
- 复合自然键：是
- 可安全 UPSERT：是

### `fina_mainbz` — 主营业务构成

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`fina_mainbz` / 股票数据 / 财务数据
- 参数：ts_code, period, type, start_date, end_date
- 输出字段：9 个
- 官方单次上限：100
- start_date / end_date：是
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_AND_CODE`
- unique_keys：ts_code, end_date, bz_item, bz_code, curr_type, update_flag
- default_order_by：end_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：是
- DATE_AND_CODE：是
- 特殊业务维度：业务分类、币种和更新标志均属于自然键
- 修订/公告/版本字段：update_flag
- 复合自然键：是
- 可安全 UPSERT：是

### `forecast` — 业绩预告

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`forecast` / 股票数据 / 财务数据
- 参数：ts_code, ann_date, start_date, end_date, period, type
- 输出字段：12 个
- 官方单次上限：3500
- start_date / end_date：是
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, ann_date, end_date, type
- default_order_by：ann_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：ann_date
- 复合自然键：是
- 可安全 UPSERT：是

### `income` — 利润表

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`income` / 股票数据 / 财务数据
- 参数：ts_code, ann_date, f_ann_date, start_date, end_date, period, report_type, comp_type
- 输出字段：94 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_AND_CODE`
- unique_keys：ts_code, end_date, report_type, comp_type, end_type, update_flag, ann_date, f_ann_date
- default_order_by：end_date DESC, ann_date DESC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：是
- DATE_AND_CODE：是
- 特殊业务维度：report_type, comp_type, end_type
- 修订/公告/版本字段：ann_date, f_ann_date, update_flag, report_type
- 复合自然键：是
- 可安全 UPSERT：是

### `income_vip` — 利润表（VIP批量）

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`income_vip` / 股票数据 / 财务数据
- 参数：ts_code, ann_date, f_ann_date, start_date, end_date, period, report_type, comp_type
- 输出字段：94 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：否
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`SINGLE`
- unique_keys：ts_code, end_date
- default_order_by：end_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：否
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：report_type, comp_type, end_type
- 修订/公告/版本字段：ann_date, f_ann_date, update_flag, report_type
- 复合自然键：是
- 可安全 UPSERT：是

## 资金流向数据

### `moneyflow` — 个股资金流向

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`moneyflow` / 股票数据 / 资金流向数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：20 个
- 官方单次上限：6000
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：ts_code, trade_date
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `moneyflow_cnt_ths` — 同花顺概念板块资金流向（THS）

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`moneyflow_cnt_ths` / 股票数据 / 资金流向数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：12 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：trade_date, ts_code
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `moneyflow_dc` — 个股资金流向（DC）

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`moneyflow_dc` / 股票数据 / 资金流向数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：15 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：trade_date, ts_code
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `moneyflow_ind_dc` — 东财概念及行业板块资金流向（DC）

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`moneyflow_ind_dc` / 股票数据 / 资金流向数据
- 参数：ts_code, trade_date, start_date, end_date, content_type
- 输出字段：18 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：trade_date, content_type, ts_code
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `moneyflow_ind_ths` — 同花顺行业资金流向（THS）

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`moneyflow_ind_ths` / 股票数据 / 资金流向数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：12 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：trade_date, ts_code
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

### `moneyflow_mkt_dc` — 大盘资金流向（DC）

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`moneyflow_mkt_dc` / 股票数据 / 资金流向数据
- 参数：trade_date, start_date, end_date
- 输出字段：15 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：否
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：trade_date
- default_order_by：trade_date DESC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：否
- 可安全 UPSERT：是

### `moneyflow_ths` — 个股资金流向（THS）

- 状态：VERIFIED
- Maturity：VERIFIED
- API / 分类：`moneyflow_ths` / 股票数据 / 资金流向数据
- 参数：ts_code, trade_date, start_date, end_date
- 输出字段：13 个
- 官方单次上限：未明确
- start_date / end_date：是
- trade_date：是
- ts_code：是
- offset / limit：否
- 推荐 Strategy：`DATE_RANGE`
- unique_keys：trade_date, ts_code
- default_order_by：trade_date DESC, ts_code ASC
- 允许无边界全量查询：否
- 日期分片：是
- 股票代码分片：否
- DATE_AND_CODE：否
- 特殊业务维度：无明确特殊维度
- 修订/公告/版本字段：未发现
- 复合自然键：是
- 可安全 UPSERT：是

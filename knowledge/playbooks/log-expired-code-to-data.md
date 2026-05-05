# 日志过期时：代码到数据补证

## 适用场景

故障时间超过日志保留期，或线上 SLS 已查不到完整链路，但仍能通过代码、表、订单号、用户 ID、支付单号等线索继续补证。

默认经验：SLS 未指定时间时先查最近一周；若故障时间超过约 5 天、已确认 SLS 无法覆盖故障窗口，或根据事件时间判断日志证据不足，不要反复扩大日志时间窗；应转向代码和数据证据。

## 排查路径

1. 先记录日志不可用的 scene fact 或 evidence
   - 写清楚故障时间、当前查询时间、日志保留期或 SLS 未命中情况。
   - 不要把“查不到日志”直接当作业务结论。

2. 从代码确定业务入口和表
   - 根据页面、接口、服务、日志模板或已知实体定位 Controller / Service / Mapper / DAO。
   - 找到真实表名、字段名、状态枚举、关联键和时间字段。
   - 禁止凭业务词猜表名。

3. 按数据源顺序查表
   - 先查 Doris Internal Catalog / CDC 表。
   - 如果 internal catalog 查不到，读取 `knowledge/data-source-index.md` 和 `knowledge/doris-jdbc-catalogs.md`。
   - 如果 CDC 未同步但 Doris JDBC Catalog 覆盖，使用三段式路径。
   - test/uat 问题或结构验证可用 MySQL profile；不能把非生产数据当作线上事实。

4. 用实体和时间窗约束查询
   - 订单号、支付单号、用户 ID、手机号、枪编码、站点 ID 等必须尽量带上。
   - 分区表要带 `dt_month`。
   - 查询要有 LIMIT，prod SQL 必须先 EXPLAIN。

5. 回填证据链
   - 数据证据要说明来源表、关键字段、状态、时间字段、关联键。
   - 如果从短订单号推导长订单号、从订单号推导支付单号，要把推导规则作为 scene fact 或 evidence 写明。

6. 决定是否收敛
   - 若代码条件和数据状态能解释现象，可写 hypothesis / conclude。
   - 若数据只说明状态，不说明原因，需要继续找上游写入点或配置来源。

## 门禁提醒

- 日志过期后不要无限尝试泛关键词。
- SQL 不能跳过 EXPLAIN 和风险确认。
- Doris JDBC Catalog 不会出现在普通 `SHOW DATABASES` 中，必须按三段式路径查。
- 非生产 MySQL 查询只能做结构或逻辑参考，不能直接证明 prod 事实。

## 证据落点

- 日志不可用：evidence 或 scene fact。
- 代码表名/字段来源：evidence。
- Doris / JDBC / MySQL 查询结果：evidence。
- ID 推导规则：scene fact 或 `memory/knowledge.yaml` 的小颗粒知识。

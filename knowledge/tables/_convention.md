# 数据表知识规范

## 生成方式

AI 执行 `SHOW TABLES` + `DESC table_name` 自动生成，用户确认后落盘。

## 文件命名

每个数据库一个 YAML 文件：`<database_name>.yaml`

## 文件格式

```yaml
database: "finance_db"
tables:
  - name: "t_user_wallet"
    description: "用户钱包主表"
    key_columns:
      - name: "user_id"
        type: "bigint"
        description: "用户ID"
      - name: "balance"
        type: "decimal(18,2)"
        description: "余额（分）"
    partition_key: "dt_month"
    common_queries:
      - "SELECT * FROM t_user_wallet WHERE user_id = ?"
    notes: "Doris 分区表，查询必须带 dt_month"
```

## 字段说明

- `key_columns`: 仅列出排查中常用的关键字段，无需全量列
- `partition_key`: Doris 表必填，MySQL 表可选
- `common_queries`: 常见查询模板
- `notes`: 特殊注意事项

"""
MySQL 查询 Adapter
职责：只读查询，直连 MySQL/PolarDB，支持多库多环境。

安全说明（双重防护）：
  - 主防护：AI 在调用前读取 guards/sql-safety.md 应用安全规则
  - 兜底防护：adapter 内置 SQL 分类，拒绝执行 DDL/写操作，不依赖上层是否检查

设计要点：
  - SQL 分类基于词法解析（首关键字），不依赖简单字符串匹配
  - query_sql 自动注入 LIMIT，防止未指定 LIMIT 的 SELECT 拉取全表
  - describe_table 通过 information_schema 返回行数估算和表大小
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional

_ADAPTERS_DIR = Path(__file__).resolve().parent.parent
if str(_ADAPTERS_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_ADAPTERS_DIR.parent))

from adapters.base import MultiProfileAdapter


# ── SQL 安全分析 ──────────────────────────────────────────────────────────────

_DDL_KEYWORDS = {"CREATE", "ALTER", "DROP", "TRUNCATE", "RENAME"}
_WRITE_KEYWORDS = {"INSERT", "UPDATE", "DELETE", "REPLACE"}
_READ_KEYWORDS = {"SELECT", "SHOW", "DESC", "DESCRIBE", "EXPLAIN"}


def _first_keyword(sql: str) -> str:
    """取 SQL 第一个有效关键字（跳过注释和空白）。"""
    for line in sql.strip().splitlines():
        line = line.strip()
        if line.startswith("--") or line.startswith("#"):
            continue
        m = re.match(r"^([a-zA-Z_]+)", line)
        if m:
            return m.group(1).upper()
    return ""


def classify_sql(sql: str) -> str:
    """返回 SQL 类型：SELECT | DDL | WRITE | OTHER"""
    first = _first_keyword(sql)
    if first in _READ_KEYWORDS:
        return "SELECT"
    if first in _DDL_KEYWORDS:
        return "DDL"
    if first in _WRITE_KEYWORDS:
        return "WRITE"
    return "OTHER"


def _inject_limit(sql: str, max_rows: int, limit: Optional[int], offset: Optional[int]) -> str:
    """如果 SQL 中没有 LIMIT，自动注入，防止无意间拉全表。"""
    sql_clean = sql.rstrip(";").strip()
    sql_no_comment = re.sub(r"--[^\n]*", "", sql_clean, flags=re.MULTILINE).upper()
    if "LIMIT" not in sql_no_comment:
        l = limit if limit is not None else max_rows
        o = offset or 0
        return f"{sql_clean} LIMIT {int(l)} OFFSET {int(o)}"
    return sql_clean


# ────────────────────────────────────────────────────────────────────────────

class MySQLClient(MultiProfileAdapter):
    """MySQL 查询客户端，支持多 profile 切换。"""

    ADAPTER_NAME = "mysql"
    REQUIRED_CONFIG_KEYS = ["profiles"]
    MAX_ROWS = 100

    def __init__(self, config_path: Optional[str] = None):
        super().__init__(config_path, caller_file=__file__)

    def _connect(self, profile: dict):
        import pymysql
        return pymysql.connect(
            host=profile["host"],
            port=profile["port"],
            user=profile["user"],
            password=profile["password"],
            database=profile.get("database", ""),
            charset="utf8mb4",
            connect_timeout=10,
            cursorclass=pymysql.cursors.DictCursor,
        )

    def health_check(self) -> bool:
        if not self._enabled:
            return False
        try:
            conn = self._connect(self._get_profile())
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            finally:
                conn.close()
            return True
        except Exception:
            return False

    def query_sql(self, sql: str, profile_name: Optional[str] = None,
                  limit: Optional[int] = None, offset: Optional[int] = None) -> dict:
        """
        执行 SELECT SQL，自动注入 LIMIT 防止拉取过多。
        返回: { success, data: { columns, rows, count, truncated, sql_executed }, error }
        """
        if not self._enabled:
            return self._disabled_response()
        sql_type = classify_sql(sql)
        if sql_type in ("DDL", "WRITE"):
            return {"success": False, "data": None,
                    "error": f"拒绝执行 {sql_type} 语句，本 adapter 仅支持 SELECT/SHOW/DESC"}
        try:
            profile = self._get_profile(profile_name)
            conn = self._connect(profile)
            try:
                actual_sql = _inject_limit(sql, self.MAX_ROWS, limit, offset)
                with conn.cursor() as cur:
                    cur.execute(actual_sql)
                    rows = cur.fetchall()
                    columns = [d[0] for d in cur.description] if cur.description else []
            finally:
                conn.close()
            truncated = len(rows) >= (limit or self.MAX_ROWS)
            return {
                "success": True,
                "data": {
                    "columns": columns,
                    "rows": [list(r.values()) for r in rows],
                    "count": len(rows),
                    "truncated": truncated,
                    "sql_executed": actual_sql,
                },
                "error": None,
            }
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def describe_table(self, table: str, database: Optional[str] = None,
                       profile_name: Optional[str] = None) -> dict:
        """
        查看表结构，通过 information_schema 获取字段信息 + 行数估算 + 表大小。
        table 支持 db.table 格式，也可单独传 database 参数。
        """
        if not self._enabled:
            return self._disabled_response()
        try:
            profile = self._get_profile(profile_name)
            conn = self._connect(profile)
            try:
                if "." in table:
                    db, tbl = table.split(".", 1)
                else:
                    db = database or profile.get("database", "")
                    tbl = table
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_KEY, COLUMN_DEFAULT, EXTRA
                        FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s
                        ORDER BY ORDINAL_POSITION""",
                        (db, tbl),
                    )
                    columns = [dict(r) for r in cur.fetchall()]
                    cur.execute(
                        """SELECT TABLE_ROWS,
                        ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024) AS size_kb,
                        TABLE_COMMENT
                        FROM information_schema.TABLES
                        WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s""",
                        (db, tbl),
                    )
                    meta = cur.fetchone() or {}
            finally:
                conn.close()
            return {
                "success": True,
                "data": {
                    "database": db, "table": tbl,
                    "columns": columns,
                    "rows_approx": meta.get("TABLE_ROWS"),
                    "size_kb": meta.get("size_kb"),
                    "comment": meta.get("TABLE_COMMENT", ""),
                },
                "error": None,
            }
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def list_tables(self, database: Optional[str] = None, profile_name: Optional[str] = None) -> dict:
        """列出数据库的所有表，含行数估算和注释。"""
        if not self._enabled:
            return self._disabled_response()
        try:
            profile = self._get_profile(profile_name)
            db = database or profile.get("database", "")
            conn = self._connect(profile)
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT TABLE_NAME AS name, TABLE_ROWS AS rows_approx, TABLE_COMMENT AS comment
                        FROM information_schema.TABLES
                        WHERE TABLE_SCHEMA=%s AND TABLE_TYPE='BASE TABLE'
                        ORDER BY TABLE_NAME""",
                        (db,),
                    )
                    tables = [dict(r) for r in cur.fetchall()]
            finally:
                conn.close()
            return {"success": True, "data": {"database": db, "tables": tables}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def list_profiles(self) -> dict:
        """列出所有可用的数据库连接配置。"""
        blocked = self._check_enabled()
        if blocked:
            return blocked
        profiles = [
            {"name": p["name"], "env": p["env"], "database": p.get("database", ""),
             "description": p.get("description", "")}
            for p in self._profiles.values()
        ]
        return {"success": True, "data": profiles, "error": None}


if __name__ == "__main__":
    client = MySQLClient()
    result = client.list_profiles()
    if result["success"]:
        print(f"可用 profiles: {[p['name'] for p in result['data']]}")
    ok = client.health_check()
    print(f"MySQL health_check: {'✅ 连通' if ok else '❌ 失败'}")
    if ok:
        result = client.list_tables()
        if result["success"]:
            tables = result["data"]["tables"]
            print(f"表数量: {len(tables)}，示例: {[t['name'] for t in tables[:5]]}")

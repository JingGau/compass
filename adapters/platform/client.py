"""
Platform 数据查询 Adapter
底层为 Apache Doris，通过 FastMCP HTTP 协议访问。
协议：JSON-RPC 2.0，响应为 SSE 格式。

安全说明（双重防护）：
  - 主防护：AI 在调用前读取 guards/sql-safety.md 应用安全规则
  - 兜底防护：adapter 内置 SQL 分类，拒绝执行 DDL/写操作
"""

import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional

import httpx

_ADAPTERS_DIR = Path(__file__).resolve().parent.parent
if str(_ADAPTERS_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_ADAPTERS_DIR.parent))

from adapters.base import MultiProfileAdapter, runtime_action_guard


# ── SQL 安全分析 ──────────────────────────────────────────────────────────────

_FORBIDDEN_PREFIXES = frozenset({
    "DELETE", "UPDATE", "INSERT", "DROP", "ALTER",
    "TRUNCATE", "CREATE", "GRANT", "REVOKE",
})

_READ_PREFIXES = frozenset({
    "SELECT", "SHOW", "DESC", "DESCRIBE", "EXPLAIN",
})


def _classify_sql(sql: str) -> str:
    """取 SQL 首关键字判断类型：READ | FORBIDDEN | OTHER"""
    for line in sql.strip().splitlines():
        line = line.strip()
        if line.startswith("--") or line.startswith("#"):
            continue
        m = re.match(r"^([a-zA-Z_]+)", line)
        if m:
            kw = m.group(1).upper()
            if kw in _FORBIDDEN_PREFIXES:
                return "FORBIDDEN"
            if kw in _READ_PREFIXES:
                return "READ"
            return "OTHER"
    return "OTHER"


# ── SSE 响应解析 ──────────────────────────────────────────────────────────────

def _parse_sse(raw: str) -> Any:
    """从 SSE 响应中提取业务数据（支持 data: 行格式）。"""
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            payload = line[5:].strip()
            try:
                outer = json.loads(payload)
            except json.JSONDecodeError:
                continue
            try:
                text = outer["result"]["content"][0]["text"]
                return json.loads(text)
            except (KeyError, IndexError, json.JSONDecodeError):
                return outer
    return None


class PlatformClient(MultiProfileAdapter):
    """平台数据查询客户端，封装 Doris SQL 的执行和结果解析。"""

    ADAPTER_NAME = "platform"
    REQUIRED_CONFIG_KEYS = ["profiles"]

    def __init__(self, config_path: Optional[str] = None):
        super().__init__(config_path, caller_file=__file__)
        self.timeout = 30
        self.export_timeout = 120

    def _profile_request_config(self, profile_name: Optional[str] = None) -> tuple[str, dict, int, int]:
        profile = self._get_profile(profile_name)
        base_url = profile["base_url"].rstrip("/")
        headers = {
            profile.get("header_user", "X-User-Name"): profile["username"],
            profile.get("header_pass", "X-Password"): profile["password"],
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        return (
            base_url,
            headers,
            int(profile.get("timeout", self.timeout)),
            int(profile.get("export_timeout", self.export_timeout)),
        )

    def _call(self, tool: str, arguments: dict, timeout: Optional[int] = None, profile_name: Optional[str] = None) -> dict:
        """发起一次 JSON-RPC 调用，返回解析后的业务数据。"""
        base_url, auth_headers, default_timeout, _ = self._profile_request_config(profile_name)
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
        }
        try:
            resp = httpx.post(
                f"{base_url}/mcp",
                headers=auth_headers,
                json=payload,
                timeout=timeout or default_timeout,
            )
            resp.raise_for_status()
            data = _parse_sse(resp.text)
            if data is None:
                return {"success": False, "data": None, "error": "无法解析响应"}
            return {"success": True, "data": data, "error": None}
        except httpx.TimeoutException:
            return {"success": False, "data": None, "error": f"请求超时（>{timeout or default_timeout}s）"}
        except httpx.HTTPStatusError as e:
            return {"success": False, "data": None, "error": f"HTTP 错误 {e.response.status_code}"}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def _guard_sql(self, sql: str) -> Optional[dict]:
        """兜底防护：拦截非读操作。返回 None 表示放行，返回 dict 表示拦截。"""
        sql_type = _classify_sql(sql)
        if sql_type == "FORBIDDEN":
            return {"success": False, "data": None,
                    "error": "拒绝执行写/DDL 语句，本 adapter 仅支持 SELECT/SHOW/DESC"}
        return None

    def health_check(self) -> dict:
        """验证连通性：执行一条简单 SQL，返回标准结构。"""
        profile = self._get_profile()
        if not self._enabled:
            return self._health_payload(status="disabled", environment=profile.get("env"))
        start = time.perf_counter()
        result = self._call("query_doris", {"sql": "SELECT 1"})
        elapsed = int((time.perf_counter() - start) * 1000)
        if result["success"]:
            return self._health_payload(status="ok", latency_ms=elapsed, environment=profile.get("env"))
        return self._health_payload(status="error", latency_ms=elapsed, environment=profile.get("env"), error=result["error"])

    def query_sql(self, sql: str, profile_name: Optional[str] = None) -> dict:
        """
        执行 Doris SQL，返回结构化结果。
        返回: { success, data: { columns, rows }, error }
        """
        if not self._enabled:
            return self._disabled_response()
        runtime_blocked = runtime_action_guard("platform", "query_sql", expected_track="sql")
        if runtime_blocked:
            return runtime_blocked
        blocked = self._guard_sql(sql)
        if blocked:
            return blocked
        return self._call("query_doris", {"sql": sql}, profile_name=profile_name)

    def count(self, sql: str, profile_name: Optional[str] = None) -> dict:
        """
        查询总条数。sql 应为原始查询（不含 COUNT），方法内部自动包装。
        返回: { success, data: int, error }
        """
        if not self._enabled:
            return self._disabled_response()
        runtime_blocked = runtime_action_guard("platform", "count", expected_track="sql")
        if runtime_blocked:
            return runtime_blocked
        blocked = self._guard_sql(sql)
        if blocked:
            return blocked
        count_sql = f"SELECT COUNT(*) AS cnt FROM ({sql}) t"
        result = self._call("get_query_count", {"sql": count_sql}, profile_name=profile_name)
        if not result["success"]:
            return result
        try:
            rows = result["data"].get("result", {}).get("data", [])
            cnt = int(rows[0][0]) if rows else 0
            return {"success": True, "data": cnt, "error": None}
        except (IndexError, ValueError, TypeError) as e:
            return {"success": False, "data": None, "error": f"解析 count 失败: {e}"}

    def export_async(self, sql: str, oss_path: Optional[str] = None, profile_name: Optional[str] = None) -> dict:
        """
        创建异步导出任务，适用于大结果集（> 1000 条）。
        返回: { success, data: { task_id }, error }
        """
        if not self._enabled:
            return self._disabled_response()
        runtime_blocked = runtime_action_guard("platform", "export_async", expected_track="sql")
        if runtime_blocked:
            return runtime_blocked
        blocked = self._guard_sql(sql)
        if blocked:
            return blocked
        args: dict = {"sql": sql}
        if oss_path:
            args["oss_path"] = oss_path
        _, _, _, export_timeout = self._profile_request_config(profile_name)
        return self._call("create_oss_export_task_async", args, timeout=export_timeout, profile_name=profile_name)

    def get_export_status(self, task_id: str, profile_name: Optional[str] = None) -> dict:
        """查询异步导出任务进度和下载链接。"""
        if not self._enabled:
            return self._disabled_response()
        return self._call("get_doris_export_status", {"task_id": task_id}, profile_name=profile_name)

    def list_databases(self, profile_name: Optional[str] = None) -> dict:
        """列出所有可用数据库。"""
        if not self._enabled:
            return self._disabled_response()
        return self._call("query_doris", {"sql": "SHOW DATABASES"}, profile_name=profile_name)

    def list_tables(self, database: str, profile_name: Optional[str] = None) -> dict:
        """列出指定数据库的所有表。"""
        if not self._enabled:
            return self._disabled_response()
        return self._call("query_doris", {"sql": f"SHOW TABLES FROM `{database}`"}, profile_name=profile_name)

    def describe_table(self, table: str, profile_name: Optional[str] = None) -> dict:
        """查看表结构（支持 db.table 格式）。"""
        if not self._enabled:
            return self._disabled_response()
        return self._call("query_doris", {"sql": f"DESC {table}"}, profile_name=profile_name)


if __name__ == "__main__":
    client = PlatformClient()
    hc = client.health_check()
    print(f"Platform health_check: {hc}")
    if hc["status"] == "ok":
        result = client.list_databases()
        if result["success"]:
            data = result["data"]
            dbs = data.get("result", {}).get("data", [])
            print(f"可用数据库（前10）: {[d[0] for d in dbs[:10]]}")

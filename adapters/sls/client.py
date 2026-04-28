"""
SLS 日志查询 Adapter
使用阿里云 aliyun-log-python-sdk 访问 SLS。
支持多环境（prod/test/uat）切换。
"""

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# 确保 adapters/ 父目录在 sys.path 中，以便 from adapters.base import ...
_ADAPTERS_DIR = Path(__file__).resolve().parent.parent
if str(_ADAPTERS_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_ADAPTERS_DIR.parent))

from adapters.base import BaseAdapter


def _parse_time(t: str) -> int:
    """
    将时间表达式转换为 Unix 时间戳（秒）。
    支持: "-1h", "-30m", "-7d", "now", ISO 格式字符串, Unix 时间戳字符串
    """
    now = datetime.now()
    if isinstance(t, int):
        return t
    t = str(t).strip()
    if t == "now":
        return int(now.timestamp())
    if t.startswith("-"):
        unit = t[-1]
        val_str = t[1:-1]
        units = {"h": "hours", "m": "minutes", "d": "days"}
        if unit in units and val_str.isdigit():
            return int((now - timedelta(**{units[unit]: int(val_str)})).timestamp())
        raise ValueError(f"无法解析时间表达式: {t}（支持的单位: h/m/d，格式如 -1h, -30m, -7d）")
    try:
        return int(t)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return int(datetime.strptime(t, fmt).timestamp())
        except ValueError:
            continue
    raise ValueError(f"无法解析时间表达式: {t}")


class SLSClient(BaseAdapter):
    """SLS 日志查询客户端，封装 aliyun-log-python-sdk。"""

    ADAPTER_NAME = "sls"
    REQUIRED_CONFIG_KEYS = ["profiles"]

    def __init__(self, config_path: Optional[str] = None):
        super().__init__(config_path, caller_file=__file__)
        self._clients: dict = {}
        self._profiles_by_env = {
            str(profile.get("env", "")).strip(): profile
            for profile in self._cfg.get("profiles", [])
            if profile.get("env")
        }
        if not self._cfg.get("default_profile") and self._cfg.get("profiles"):
            self._cfg["default_profile"] = self._cfg["profiles"][0].get("name")

    def _default_env(self) -> str:
        configured = str(self._cfg.get("default_env") or "").strip()
        if configured:
            return configured
        profiles = self._cfg.get("profiles", [])
        if profiles:
            return str(profiles[0].get("env") or "prod")
        return "prod"

    def _get_profile(self, env: Optional[str] = None) -> dict:
        selected_env = env or self._default_env()
        profile = self._profiles_by_env.get(selected_env)
        if not profile:
            available = sorted(k for k in self._profiles_by_env if k)
            raise ValueError(f"环境 '{selected_env}' 未配置 SLS profile，可用: {available}")
        return profile

    def _get_client(self, env: Optional[str] = None):
        """获取或创建指定环境的 SLS client（懒加载）。"""
        from aliyun.log import LogClient
        env = env or self._default_env()
        profile = self._get_profile(env)
        if env not in self._clients:
            self._clients[env] = LogClient(
                profile["endpoint"],
                profile["access_key_id"],
                profile["access_key_secret"],
            )
        return self._clients[env], env

    def _get_project(self, env: str) -> str:
        profile = self._get_profile(env)
        project = profile.get("project")
        if not project:
            raise ValueError(f"环境 '{env}' 未配置 SLS project")
        return project

    def _get_logstore(self, env: str, logstore: Optional[str] = None) -> str:
        profile = self._get_profile(env)
        return str(logstore or profile.get("logstore") or "all")

    def _check_logstore_confirmation(self, env: Optional[str], logstore: Optional[str], confirmed: bool = False) -> Optional[dict]:
        """非默认 logstore 会改变查询范围，必须先让用户确认。"""
        selected_env = env or self._default_env()
        default_logstore = self._get_logstore(selected_env).strip()
        requested_logstore = str(logstore or default_logstore).strip() or default_logstore
        if requested_logstore == "all" or confirmed:
            return None
        return {
            "success": False,
            "data": None,
            "error": "SLS 非默认 logstore 查询需要用户确认",
            "requires_confirmation": True,
            "confirmation": {
                "gate_type": "sls_logstore",
                "default_logstore": "all",
                "requested_logstore": requested_logstore,
                "required_reply": "确认使用该 logstore",
                "message": (
                    "默认仅使用 SLS_LOGSTORE=all。"
                    f"当前请求使用 logstore={requested_logstore}，请用户确认后再执行。"
                ),
            },
        }

    def health_check(self) -> dict:
        """验证连通性：列出 default_env 对应 project 的 logstore，返回标准结构。"""
        if not self._enabled:
            return self._health_payload(status="disabled", environment=self._default_env())
        try:
            start = time.perf_counter()
            from aliyun.log import ListLogstoresRequest
            default_env = self._default_env()
            client, env = self._get_client(default_env)
            project = self._get_project(default_env)
            req = ListLogstoresRequest(project)
            client.list_logstores(req)
            elapsed = int((time.perf_counter() - start) * 1000)
            return self._health_payload(status="ok", latency_ms=elapsed, environment=env)
        except Exception as e:
            return self._health_payload(status="error", environment=self._default_env(), error=str(e))

    def list_logstores(self, env: Optional[str] = None) -> dict:
        """列出指定环境的所有 logstore。"""
        blocked = self._check_enabled()
        if blocked:
            return blocked
        try:
            from aliyun.log import ListLogstoresRequest
            client, env = self._get_client(env)
            project = self._get_project(env)
            req = ListLogstoresRequest(project)
            resp = client.list_logstores(req)
            return {"success": True, "data": resp.get_logstores(), "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def query_logs(
        self,
        query: str,
        env: Optional[str] = None,
        from_time: str = "-1h",
        to_time: str = "now",
        limit: int = 20,
        offset: int = 0,
        logstore: Optional[str] = None,
        logstore_confirmed: bool = False,
    ) -> dict:
        """
        执行 SLS 查询语句。
        query: 支持全文搜索和 SQL 分析，如 "orderId:ORD123" 或 "* | SELECT COUNT(*)"
        env: prod / test / uat，默认 prod
        from_time/to_time: 支持 "-1h", "-30m", "-7d", "now", ISO 格式
        """
        blocked = self._check_enabled()
        if blocked:
            return blocked
        logstore_blocked = self._check_logstore_confirmation(env, logstore, logstore_confirmed)
        if logstore_blocked:
            return logstore_blocked
        try:
            from aliyun.log import GetLogsRequest
            client, env = self._get_client(env)
            project = self._get_project(env)
            ls = self._get_logstore(env, logstore)
            from_ts = _parse_time(from_time)
            to_ts = _parse_time(to_time)
            req = GetLogsRequest(
                project=project,
                logstore=ls,
                fromTime=from_ts,
                toTime=to_ts,
                query=query,
                line=limit,
                offset=offset,
                reverse=True,
            )
            resp = client.get_logs(req)
            raw = resp.get_logs()
            if raw is None:
                logs_raw: list = []
            elif isinstance(raw, list):
                logs_raw = raw
            else:
                # 部分 SDK/接口返回单个 QueriedLog，不可迭代
                logs_raw = [raw]

            def _log_to_dict(log) -> dict:
                if isinstance(log, dict):
                    return log
                if hasattr(log, "get_contents"):
                    contents = log.get_contents()
                    if isinstance(contents, dict):
                        return dict(contents)
                    pairs = contents or []
                    out = {}
                    for c in pairs:
                        k = getattr(c, "get_key", lambda: None)()
                        v = getattr(c, "get_value", lambda: None)()
                        if k is not None:
                            out[k] = v
                    return out
                return {"_raw": str(log)}

            logs = [_log_to_dict(log) for log in logs_raw]
            return {
                "success": True,
                "data": {
                    "logs": logs,
                    "count": len(logs),
                    "is_complete": resp.is_completed(),
                },
                "error": None,
            }
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def search_keyword(
        self,
        keyword: str,
        env: Optional[str] = None,
        from_time: str = "-24h",
        limit: int = 20,
        container: Optional[str] = None,
    ) -> dict:
        """
        关键字搜索（query_logs 的便捷版本）。
        container: 指定容器名，如 "finance-server"
        """
        q = keyword
        if container:
            q = f'__tag__:_container_name_:{container} AND {keyword}'
        return self.query_logs(query=q, env=env, from_time=from_time, limit=limit)

    def analyze_errors(
        self,
        env: Optional[str] = None,
        from_time: str = "-1h",
        top_n: int = 10,
        container: Optional[str] = None,
    ) -> dict:
        """统计高频错误日志，返回 Top N 错误。"""
        base = 'level:ERROR'
        if container:
            base = f'__tag__:_container_name_:{container} AND {base}'
        query = f'{base} | SELECT message, COUNT(*) AS cnt GROUP BY message ORDER BY cnt DESC LIMIT {top_n}'
        return self.query_logs(query=query, env=env, from_time=from_time, limit=top_n)


if __name__ == "__main__":
    client = SLSClient()
    hc = client.health_check()
    print(f"SLS health_check: {hc}")
    if hc["status"] == "ok":
        result = client.list_logstores()
        if result["success"]:
            print(f"Logstores: {result['data']}")

"""
Redis 查询 Adapter
职责：只读查询 Redis 缓存状态，适用于排查会话、分布式锁、计数器等实时状态。

设计要点：
  - 只暴露只读方法，不提供写操作接口
  - 用 SCAN 代替 KEYS，防止大库查询时阻塞 Redis
  - 支持 standalone 和 cluster 两种部署模式

Redis 命令安全分级（供 guards 层和 AI 规划参考，client 本身仅使用只读命令）：
  - READ_ONLY: GET, MGET, EXISTS, TYPE, TTL, SCAN, HGETALL, LRANGE, SMEMBERS, ZRANGE, INFO 等
  - WRITE:     SET, DEL, EXPIRE, HSET, LPUSH, RPUSH, SADD, ZADD 等
  - DANGEROUS: FLUSHALL, FLUSHDB, KEYS, CONFIG, SHUTDOWN 等
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

_ADAPTERS_DIR = Path(__file__).resolve().parent.parent
if str(_ADAPTERS_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_ADAPTERS_DIR.parent))

from adapters.base import MultiProfileAdapter


class RedisClient(MultiProfileAdapter):
    """Redis 只读查询客户端，支持 standalone 和 cluster 模式。"""

    ADAPTER_NAME = "redis"
    REQUIRED_CONFIG_KEYS = ["profiles"]

    def __init__(self, config_path: Optional[str] = None):
        super().__init__(config_path, caller_file=__file__)
        self._connections: dict = {}

    def _get_connection(self, profile_name: Optional[str] = None):
        name = profile_name or self._default
        if name not in self._connections:
            p = self._get_profile(name)
            mode = p.get("mode", "standalone")
            if mode == "cluster":
                from redis.cluster import RedisCluster
                hosts_raw = p.get("hosts", [f"{p['host']}:{p['port']}"])
                startup_nodes = []
                for h in hosts_raw:
                    host, _, port_str = h.rpartition(":")
                    startup_nodes.append({"host": host.strip(), "port": int(port_str or p.get("port", 6379))})
                self._connections[name] = RedisCluster(
                    startup_nodes=startup_nodes,
                    password=p.get("password") or None,
                    decode_responses=True,
                )
            else:
                import redis
                self._connections[name] = redis.Redis(
                    host=p["host"], port=p["port"],
                    password=p.get("password") or None,
                    db=p.get("db", 0),
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=10,
                )
        return self._connections[name]

    def health_check(self) -> dict:
        profile = self._get_profile()
        if not self._enabled:
            return self._health_payload(status="disabled", environment=profile.get("env"))
        try:
            start = time.perf_counter()
            ok = self._get_connection().ping()
            elapsed = int((time.perf_counter() - start) * 1000)
            if ok:
                return self._health_payload(status="ok", latency_ms=elapsed, environment=profile.get("env"))
            return self._health_payload(status="error", environment=profile.get("env"), error="ping=false")
        except Exception as e:
            return self._health_payload(status="error", environment=profile.get("env"), error=str(e))

    def get_value(self, key: str, profile_name: Optional[str] = None) -> dict:
        """
        根据 key 类型自动选择读取方式：
        STRING -> get, HASH -> hgetall, LIST -> lrange(0,19), SET -> smembers(前20), ZSET -> zrange(0,19)
        """
        if not self._enabled:
            return self._disabled_response()
        try:
            r = self._get_connection(profile_name)
            key_type = r.type(key)
            ttl = r.ttl(key)
            if key_type == "string":
                value = r.get(key)
            elif key_type == "hash":
                value = r.hgetall(key)
            elif key_type == "list":
                value = r.lrange(key, 0, 19)
            elif key_type == "set":
                value = list(r.smembers(key))[:20]
            elif key_type == "zset":
                value = r.zrange(key, 0, 19, withscores=True)
            else:
                value = None
            return {"success": True, "data": {"key": key, "type": key_type, "value": value, "ttl": ttl}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def key_info(self, key: str, profile_name: Optional[str] = None) -> dict:
        """获取 key 的元信息：是否存在、类型、TTL。"""
        if not self._enabled:
            return self._disabled_response()
        try:
            r = self._get_connection(profile_name)
            if not r.exists(key):
                return {"success": True, "data": {"key": key, "exists": False}, "error": None}
            return {
                "success": True,
                "data": {"key": key, "exists": True, "type": r.type(key), "ttl": r.ttl(key)},
                "error": None,
            }
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def scan_keys(self, pattern: str, count: int = 20, profile_name: Optional[str] = None) -> dict:
        """使用 SCAN 模糊查找 key（非阻塞，安全替代 KEYS）。"""
        if not self._enabled:
            return self._disabled_response()
        try:
            r = self._get_connection(profile_name)
            keys: list = []
            cursor = 0
            while True:
                cursor, batch = r.scan(cursor=cursor, match=pattern, count=100)
                keys.extend(batch)
                if cursor == 0 or len(keys) >= count:
                    break
            return {"success": True, "data": {"keys": keys[:count], "total_scanned": len(keys)}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def info(self, section: Optional[str] = None, profile_name: Optional[str] = None) -> dict:
        """
        查询 Redis INFO。
        section 可选：server / memory / clients / stats / replication / keyspace 等，None 表示全部。
        """
        if not self._enabled:
            return self._disabled_response()
        try:
            r = self._get_connection(profile_name)
            data = r.info(section) if section else r.info()
            return {"success": True, "data": data, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def hgetall(self, key: str, profile_name: Optional[str] = None) -> dict:
        """直接获取 Hash 类型 key 的所有字段。"""
        if not self._enabled:
            return self._disabled_response()
        try:
            r = self._get_connection(profile_name)
            return {"success": True, "data": {"key": key, "value": r.hgetall(key)}, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def list_profiles(self) -> dict:
        """列出所有可用的 Redis 连接配置。"""
        blocked = self._check_enabled()
        if blocked:
            return blocked
        profiles = [
            {"name": p["name"], "env": p["env"], "mode": p.get("mode", "standalone"),
             "description": p.get("description", "")}
            for p in self._profiles.values()
        ]
        return {"success": True, "data": profiles, "error": None}


if __name__ == "__main__":
    client = RedisClient()
    hc = client.health_check()
    print(f"Redis health_check: {hc}")
    if hc["status"] == "ok":
        r = client.info("keyspace")
        if r["success"]:
            print(f"Keyspace: {r['data']}")

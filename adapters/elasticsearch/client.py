"""
Elasticsearch 查询 Adapter
职责：全文检索和聚合查询，支持 ES 6.x / 7.x / 8.x 多版本。

版本路由策略：
  - 连接前通过原生 HTTP 探测 ES 版本（GET /），无需手动配置
  - ES 6.x -> 纯 urllib 实现（绕过 SDK 兼容性问题）
  - ES 7.x -> elasticsearch-py，使用 http_auth 参数
  - ES 8.x -> elasticsearch-py，使用 basic_auth 参数
  - 版本信息懒加载并缓存，同一会话内只探测一次
"""

from __future__ import annotations

import base64
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

_ADAPTERS_DIR = Path(__file__).resolve().parent.parent
if str(_ADAPTERS_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_ADAPTERS_DIR.parent))

from adapters.base import MultiProfileAdapter


def _detect_version(url: str, username: str = "", password: str = "") -> Optional[int]:
    """
    通过原生 HTTP 探测 ES 主版本号，不依赖 SDK。
    成功返回主版本号（int），失败返回 None（调用方应处理为错误而非静默降级）。
    """
    try:
        req = urllib.request.Request(url)
        if username and password:
            cred = base64.b64encode(f"{username}:{password}".encode()).decode()
            req.add_header("Authorization", f"Basic {cred}")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            major = int(data["version"]["number"].split(".")[0])
            return major
    except Exception:
        return None


class _BaseHTTPOps:
    """ES 6.x 原生 HTTP 操作（不依赖 elasticsearch-py SDK）。"""

    def __init__(self, url: str, username: str = "", password: str = ""):
        self.url = url.rstrip("/")
        self._auth_header = ""
        if username and password:
            cred = base64.b64encode(f"{username}:{password}".encode()).decode()
            self._auth_header = f"Basic {cred}"

    def _request(self, path: str, method: str = "GET", body: Optional[dict] = None) -> dict:
        url = f"{self.url}{path}"
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if self._auth_header:
            req.add_header("Authorization", self._auth_header)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            err = e.read().decode() if e.fp else ""
            raise Exception(f"HTTP {e.code}: {err}")

    def ping(self) -> bool:
        try:
            self._request("/")
            return True
        except Exception:
            return False

    def search(self, index: str, query: Optional[dict] = None, size: int = 20, from_: int = 0) -> dict:
        body = {"query": query or {"match_all": {}}}
        resp = self._request(f"/{index}/_search?size={size}&from={from_}", "POST", body)
        hits = resp["hits"]["hits"]
        total = resp["hits"]["total"]
        if isinstance(total, dict):
            total = total["value"]
        return {
            "total": total,
            "hits": [{"_id": h["_id"], "_source": h["_source"]} for h in hits],
        }

    def search_keyword(self, index: str, keyword: str, fields: Optional[list] = None, size: int = 20) -> dict:
        query = {"multi_match": {"query": keyword, "fields": fields or ["*"]}}
        return self.search(index=index, query=query, size=size)

    def aggregate(self, index: str, query: dict, aggs: dict, size: int = 0) -> dict:
        body = {"query": query, "aggs": aggs, "size": size}
        resp = self._request(f"/{index}/_search", "POST", body)
        return {"aggregations": resp.get("aggregations", {})}

    def list_indices(self, pattern: str = "*") -> list:
        resp = self._request(f"/_cat/indices/{pattern}?format=json")
        result = []
        for idx in resp:
            name = idx.get("index", "")
            if not name or name.startswith("."):
                continue
            docs = idx.get("docs.count") or 0
            result.append({
                "name": name,
                "docs_count": int(docs) if docs else 0,
                "size": idx.get("store.size", "0b"),
                "health": idx.get("health", "unknown"),
            })
        return result

    def get_mapping(self, index: str) -> dict:
        return self._request(f"/{index}/_mapping")


class _SDKOps:
    """ES 7/8 SDK 操作，参数根据版本自动选择。"""

    def __init__(self, url: str, username: str, password: str, es_major: int):
        from elasticsearch import Elasticsearch
        kwargs: dict = {"hosts": [url], "verify_certs": False}
        if username and password:
            if es_major >= 8:
                kwargs["basic_auth"] = (username, password)
            else:
                kwargs["http_auth"] = (username, password)
        self.client = Elasticsearch(**kwargs)

    def ping(self) -> bool:
        return self.client.ping()

    def search(self, index: str, query: Optional[dict] = None, size: int = 20, from_: int = 0) -> dict:
        body = {"query": query or {"match_all": {}}}
        resp = self.client.search(index=index, body=body, size=size, from_=from_)
        hits = resp["hits"]["hits"]
        total = resp["hits"]["total"]
        if isinstance(total, dict):
            total = total["value"]
        return {
            "total": total,
            "hits": [{"_id": h["_id"], "_source": h["_source"]} for h in hits],
        }

    def search_keyword(self, index: str, keyword: str, fields: Optional[list] = None, size: int = 20) -> dict:
        query = {"multi_match": {"query": keyword, "fields": fields or ["*"]}}
        return self.search(index=index, query=query, size=size)

    def aggregate(self, index: str, query: dict, aggs: dict, size: int = 0) -> dict:
        resp = self.client.search(index=index, body={"query": query, "aggs": aggs, "size": size})
        return {"aggregations": resp.get("aggregations", {})}

    def list_indices(self, pattern: str = "*") -> list:
        resp = self.client.cat.indices(index=pattern, format="json")
        result = []
        for idx in resp:
            name = idx.get("index", "")
            if not name or name.startswith("."):
                continue
            docs = idx.get("docs.count") or 0
            result.append({
                "name": name,
                "docs_count": int(docs) if docs else 0,
                "size": idx.get("store.size", "0b"),
                "health": idx.get("health", "unknown"),
            })
        return result

    def get_mapping(self, index: str) -> dict:
        return dict(self.client.indices.get_mapping(index=index))


class ESClient(MultiProfileAdapter):
    """ES 查询客户端，自动检测版本并路由到正确的实现。"""

    ADAPTER_NAME = "elasticsearch"
    REQUIRED_CONFIG_KEYS = ["profiles"]

    def __init__(self, config_path: Optional[str] = None):
        super().__init__(config_path, caller_file=__file__)
        self._ops: dict = {}
        self._versions: dict = {}

    def _get_ops(self, profile_name: Optional[str] = None):
        name = profile_name or self._default
        if name not in self._ops:
            p = self._get_profile(name)
            url, user, pwd = p["url"], p.get("username", ""), p.get("password", "")
            es_major = _detect_version(url, user, pwd)
            if es_major is None:
                raise ConnectionError(f"无法探测 ES 版本（profile='{name}', url='{url}'），请检查连接或认证信息")
            if es_major <= 6:
                self._ops[name] = _BaseHTTPOps(url, user, pwd)
            else:
                self._ops[name] = _SDKOps(url, user, pwd, es_major)
            self._versions[name] = es_major
        return self._ops[name]

    def health_check(self) -> bool:
        if not self._enabled:
            return False
        try:
            ops = self._get_ops()
            return ops.ping()
        except Exception:
            return False

    def list_indices(self, pattern: str = "*", profile_name: Optional[str] = None) -> dict:
        if not self._enabled:
            return self._disabled_response()
        try:
            ops = self._get_ops(profile_name)
            data = ops.list_indices(pattern)
            return {"success": True, "data": data, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def search(self, index: str, query: Optional[dict] = None, size: int = 20,
               from_: int = 0, profile_name: Optional[str] = None) -> dict:
        """执行 ES DSL 查询。query 为 ES Query DSL，如 {"match": {"message": "xxx"}}"""
        if not self._enabled:
            return self._disabled_response()
        try:
            ops = self._get_ops(profile_name)
            data = ops.search(index=index, query=query, size=size, from_=from_)
            return {"success": True, "data": data, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def search_keyword(self, index: str, keyword: str, fields: Optional[list] = None,
                       size: int = 20, profile_name: Optional[str] = None) -> dict:
        """关键字全文搜索（multi_match 便捷版）。"""
        if not self._enabled:
            return self._disabled_response()
        try:
            ops = self._get_ops(profile_name)
            data = ops.search_keyword(index=index, keyword=keyword, fields=fields, size=size)
            return {"success": True, "data": data, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def aggregate(self, index: str, query: dict, aggs: dict,
                  size: int = 0, profile_name: Optional[str] = None) -> dict:
        """聚合查询。aggs 为 ES Aggregations DSL。"""
        if not self._enabled:
            return self._disabled_response()
        try:
            ops = self._get_ops(profile_name)
            data = ops.aggregate(index=index, query=query, aggs=aggs, size=size)
            return {"success": True, "data": data, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def get_mapping(self, index: str, profile_name: Optional[str] = None) -> dict:
        """查看索引 mapping（字段结构）。"""
        if not self._enabled:
            return self._disabled_response()
        try:
            ops = self._get_ops(profile_name)
            data = ops.get_mapping(index=index)
            return {"success": True, "data": data, "error": None}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    def list_profiles(self) -> dict:
        """列出所有可用的 ES 连接配置。"""
        blocked = self._check_enabled()
        if blocked:
            return blocked
        profiles = []
        for name, p in self._profiles.items():
            version = self._versions.get(name)
            profiles.append({
                "name": name,
                "url": p["url"],
                "es_version": f"{version}.x" if version else "未探测",
                "description": p.get("description", ""),
            })
        return {"success": True, "data": profiles, "error": None}


if __name__ == "__main__":
    client = ESClient()
    ok = client.health_check()
    print(f"ES health_check: {'✅ 连通' if ok else '❌ 失败'}")
    if ok:
        result = client.list_indices()
        if result["success"]:
            indices = result["data"]
            print(f"索引数量: {len(indices)}")
            for idx in indices[:5]:
                print(f"  {idx['name']}  docs={idx['docs_count']}  {idx['health']}")

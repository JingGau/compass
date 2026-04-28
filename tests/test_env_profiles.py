from adapters.base import build_profiles_from_env


def test_build_profiles_from_env_parses_indexed_values() -> None:
    environ = {
        "REDIS[0].NAME": "FINANCE_TEST",
        "REDIS[0].ENV": "test",
        "REDIS[0].DESC": "财务测试环境 Redis",
        "REDIS[0].HOST": "redis.example.com",
        "REDIS[0].PORT": "6379",
        "REDIS[0].PASSWORD": "secret",
        "REDIS[0].DB": "30",
        "REDIS[0].LINK": "https://example.com/redis",
        "REDIS[1].NAME": "FINANCE_UAT",
        "REDIS[1].ENV": "uat",
        "REDIS[1].HOST": "uat-redis.example.com",
        "REDIS[1].PORT": "6380",
        "REDIS[1].PASSWORD": "",
        "REDIS[1].DB": "31",
    }

    profiles = build_profiles_from_env("REDIS", environ=environ)

    assert profiles == [
        {
            "name": "FINANCE_TEST",
            "env": "test",
            "description": "财务测试环境 Redis",
            "host": "redis.example.com",
            "port": 6379,
            "password": "secret",
            "db": 30,
            "link": "https://example.com/redis",
        },
        {
            "name": "FINANCE_UAT",
            "env": "uat",
            "host": "uat-redis.example.com",
            "port": 6380,
            "password": "",
            "db": 31,
        },
    ]

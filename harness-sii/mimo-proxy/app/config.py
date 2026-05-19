"""Configuration for mimo-proxy."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    """Environment-driven settings."""

    host: str = os.getenv("MIMO_PROXY_HOST", "127.0.0.1")
    port: int = int(os.getenv("MIMO_PROXY_PORT", "8081"))

    # mimo API配置
    mimo_api_key: str = os.getenv("MIMO_API_KEY", "tp-cjeqnl3h4ekv8c1oot1s6pzp0x20yq886hs5d6x6e94f83qb")
    mimo_base_url: str = os.getenv("MIMO_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1")

    # 可选的API token用于认证GPU节点的请求
    api_token: str = os.getenv("MIMO_PROXY_API_TOKEN", "")


settings = Settings()

"""Configuration for mimo-proxy."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Environment-driven settings."""

    host: str = "0.0.0.0"
    port: int = 8080

    # mimo API配置
    mimo_api_key: str = "tp-cjeqnl3h4ekv8c1oot1s6pzp0x20yq886hs5d6x6e94f83qb"
    mimo_base_url: str = "https://token-plan-cn.xiaomimimo.com/v1"

    # 可选的API token用于认证GPU节点的请求
    api_token: str = ""

    model_config = {"env_prefix": "MIMO_PROXY_"}


settings = Settings()

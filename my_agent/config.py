from __future__ import annotations

import os
from pathlib import Path

from my_agent.models import DashScopeAgentModelClient, MockModelClient, OpenAICompatibleAgentModelClient
from my_agent.models.base import ModelClient


def load_env_file(path: str | Path = ".env") -> None:
    """Load local environment variables if python-dotenv is installed."""
    env_path = Path(path)
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Install python-dotenv or export environment variables manually.") from exc
    load_dotenv(env_path)


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value not in {None, ""} else default


def env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value not in {None, ""} else default


def build_model_client_from_env() -> ModelClient:
    """Build a model client from .env-compatible settings.

    Set MODEL_PROVIDER=dashscope for Bailian/DashScope, MODEL_PROVIDER=local
    for a local OpenAI-compatible server, or MODEL_PROVIDER=mock for smoke tests.
    """
    provider = os.getenv("MODEL_PROVIDER", "dashscope").strip().lower()
    if provider == "mock":
        return MockModelClient()

    model = os.getenv("MODEL_NAME") or os.getenv("SERVED_MODEL_NAME")
    if not model:
        raise RuntimeError("Missing MODEL_NAME or SERVED_MODEL_NAME.")

    common = {
        "base_url": os.getenv("MODEL_BASE_URL", "http://127.0.0.1:8000/v1"),
        "model": model,
        "api_key": os.getenv("MODEL_API_KEY"),
        "timeout": env_int("MODEL_TIMEOUT", 180),
        "max_tokens": env_int("MODEL_MAX_TOKENS", 1024),
        "temperature": env_float("MODEL_TEMPERATURE", 0.0),
        "stream": env_bool("MODEL_STREAM", True),
    }
    enable_thinking = os.getenv("MODEL_ENABLE_THINKING")

    if provider in {"dashscope", "bailian", "aliyun"}:
        return DashScopeAgentModelClient(
            **common,
            api_key_env=os.getenv("MODEL_API_KEY_ENV", "DASHSCOPE_API_KEY"),
            enable_thinking=env_bool("MODEL_ENABLE_THINKING", False),
        )

    if provider in {"local", "vllm", "openai-compatible", "openai_compatible"}:
        local_common = {**common, "api_key": common["api_key"] or "EMPTY"}
        return OpenAICompatibleAgentModelClient(
            **local_common,
            api_key_env=os.getenv("MODEL_API_KEY_ENV"),
            enable_thinking=env_bool("MODEL_ENABLE_THINKING") if enable_thinking is not None else None,
            provider_name="local OpenAI-compatible",
        )

    raise RuntimeError(f"Unsupported MODEL_PROVIDER={provider!r}.")

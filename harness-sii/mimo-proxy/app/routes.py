"""HTTP routes for the mimo-proxy service.

代理OpenAI格式的请求到mimo API。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse

from .config import settings

logger = logging.getLogger("mimo-proxy.routes")
router = APIRouter()


# ---------- auth ----------
async def auth_dep(authorization: str | None = Header(default=None)) -> None:
    """验证GPU节点的请求token。"""
    if not settings.api_token:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if token != settings.api_token:
        raise HTTPException(401, "invalid token")


# ---------- health ----------
@router.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "mimo_configured": bool(settings.mimo_api_key),
        "mimo_base_url": settings.mimo_base_url,
    }


# ---------- models ----------
@router.get("/v1/models", dependencies=[Depends(auth_dep)])
async def list_models() -> Dict[str, Any]:
    """返回可用模型列表。"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{settings.mimo_base_url}/models",
            headers={"Authorization": f"Bearer {settings.mimo_api_key}"},
        )
        return resp.json()


# ---------- chat completions ----------
@router.post("/v1/chat/completions", dependencies=[Depends(auth_dep)])
async def chat_completions(request: Request) -> Any:
    """代理OpenAI格式的chat completions请求到mimo API。"""
    body = await request.json()

    # 提取stream参数
    stream = body.get("stream", False)

    # 构建转发请求
    headers = {
        "Authorization": f"Bearer {settings.mimo_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=300.0) as client:
        if stream:
            # 流式响应
            async def generate():
                async with client.stream(
                    "POST",
                    f"{settings.mimo_base_url}/chat/completions",
                    headers=headers,
                    json=body,
                ) as resp:
                    async for chunk in resp.aiter_bytes():
                        yield chunk

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
            )
        else:
            # 非流式响应
            resp = await client.post(
                f"{settings.mimo_base_url}/chat/completions",
                headers=headers,
                json=body,
            )
            return resp.json()


# ---------- 通用代理（备用） ----------
@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"], dependencies=[Depends(auth_dep)])
async def proxy_all(path: str, request: Request) -> Any:
    """通用代理，转发所有其他请求到mimo API。"""
    body = await request.body()

    headers = {
        "Authorization": f"Bearer {settings.mimo_api_key}",
        "Content-Type": request.headers.get("Content-Type", "application/json"),
    }

    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.request(
            method=request.method,
            url=f"{settings.mimo_base_url}/{path}",
            headers=headers,
            content=body,
        )
        return resp.json()

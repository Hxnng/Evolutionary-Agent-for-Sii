from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from my_agent.harness.types import ToolResult


class BrowserGymSession:
    """Thin BrowserGym adapter.

    BrowserGym stays outside the core loop as an environment-backed tool. This
    mirrors BrowserGym's own reset/step/close contract and avoids coupling web
    interaction to any graph runtime.
    """

    def __init__(self, env_id: str = "browsergym/openended", **task_kwargs: Any) -> None:
        self.env_id = env_id
        self.task_kwargs = task_kwargs
        self.env = None
        self.last_observation: Any = None

    def start(self) -> Any:
        import gymnasium as gym
        import browsergym.core  # noqa: F401

        self.env = gym.make(self.env_id, task_kwargs=self.task_kwargs)
        self.last_observation, _ = self.env.reset()
        return self.last_observation

    def step(self, action: str) -> dict[str, Any]:
        if self.env is None:
            self.start()
        obs, reward, terminated, truncated, info = self.env.step(action)
        self.last_observation = obs
        return {
            "observation": obs,
            "reward": reward,
            "terminated": terminated,
            "truncated": truncated,
            "info": info,
        }

    def close(self) -> None:
        if self.env is not None:
            self.env.close()
            self.env = None


@dataclass
class BrowserGymTool:
    session: BrowserGymSession
    name: str = "browser_step"
    description: str = "Execute one BrowserGym high-level browser action and return the observation."

    async def __call__(self, action: str) -> ToolResult:
        try:
            result = self.session.step(action)
            done = bool(result["terminated"] or result["truncated"])
            return ToolResult(
                content=f"Browser step completed. done={done}; reward={result['reward']}; observation={result['observation']}",
                call_id=self.name,
                name=self.name,
                is_error=False,
                metadata={"done": done, "info": result["info"]},
            )
        except Exception as exc:
            return ToolResult(
                content=f"Error: BrowserGym step failed with {exc.__class__.__name__}: {exc}",
                call_id=self.name,
                name=self.name,
                is_error=True,
                metadata={"action": action},
            )


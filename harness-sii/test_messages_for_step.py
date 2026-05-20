"""
Test _messages_for_step to verify system messages are always at the beginning.

Run:
    python test_messages_for_step.py
"""

import sys
import types
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Stub out heavy external deps so the test can run without them
# ---------------------------------------------------------------------------

# dotenv
_dotenv = types.ModuleType("dotenv")
_dotenv.load_dotenv = lambda *a, **kw: None
sys.modules["dotenv"] = _dotenv

# openai
_openai = types.ModuleType("openai")
_openai.OpenAI = type("OpenAI", (), {})
sys.modules["openai"] = _openai

# curator
_curator = types.ModuleType("curator")
@dataclass
class _CuratedContext:
    system_prompt: str = ""
    family: str = ""
    selected_skills: list = field(default_factory=list)
    profile: dict = field(default_factory=dict)
_curator.CuratedContext = _CuratedContext
_curator.CuratorAgent = type("CuratorAgent", (), {})
sys.modules["curator"] = _curator

# skill_store
_skill_store = types.ModuleType("skill_store")
_skill_store.SkillStore = type("SkillStore", (), {})
sys.modules["skill_store"] = _skill_store

# memory_store
_memory_store = types.ModuleType("memory_store")
_memory_store.MemoryStore = type("MemoryStore", (), {})
sys.modules["memory_store"] = _memory_store

# reflection
_reflection = types.ModuleType("reflection")
_reflection.reflect = lambda **kw: None
sys.modules["reflection"] = _reflection

# tools.search_tool
_tools_search = types.ModuleType("tools.search_tool")
_tools_search.search_text = lambda **kw: []
_tools_search.search_image = lambda *a, **kw: []
sys.modules["tools.search_tool"] = _tools_search

# tools
_tools = types.ModuleType("tools")
sys.modules["tools"] = _tools

# tools.browser_tool
_tools_browser = types.ModuleType("tools.browser_tool")
_tools_browser.browser_navigate = lambda **kw: {}
_tools_browser.browser_get_text = lambda **kw: {}
_tools_browser.browser_click = lambda **kw: {}
_tools_browser.browser_type = lambda **kw: {}
_tools_browser.browser_parallel = lambda **kw: {}
sys.modules["tools.browser_tool"] = _tools_browser

# Set env vars before importing task_runner to avoid .env loading issues
import os
os.environ["LLM_BASE_URL"] = "http://localhost:8000/v1"
os.environ["LLM_API_KEY"] = "test"
os.environ["DISABLE_TOOLS"] = "1"

from roles import Role
from task_runner import (
    _messages_for_step,
    _force_answer_message,
    _react_state_message,
    _message_from_entry,
)


# ---------------------------------------------------------------------------
# Fake Trajectory
# ---------------------------------------------------------------------------
class FakeTrajectory:
    """Mimics Trajectory backed by an in-memory list."""

    def __init__(self, rows: list[dict]):
        self._rows = rows

    def read_all(self) -> list[dict]:
        return list(self._rows)

    def to_messages(self) -> list[dict]:
        from task_runner import _message_from_entry
        return [_message_from_entry(r) for r in self._rows]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _system(content: str, step_id=None):
    return {"role": Role.SYSTEM.value, "content": content, "step_id": step_id}

def _user(content: str, step_id=0):
    return {"role": Role.USER.value, "content": content, "step_id": step_id}

def _assistant(content: str, step_id=1, tool_calls=None):
    entry = {"role": Role.ASSISTANT.value, "content": content, "step_id": step_id}
    if tool_calls:
        entry["tool_calls"] = tool_calls
    return entry

def _tool(content: str, step_id=1, tool_call_id="tc_1", fn_name="search_text"):
    return {
        "role": Role.TOOL.value,
        "content": content,
        "step_id": step_id,
        "tool_call_id": tool_call_id,
        "fn_name": fn_name,
    }


def _assert_system_first(msgs: list[dict], label: str):
    """Assert that all system messages appear before any non-system messages."""
    seen_non_system = False
    for i, msg in enumerate(msgs):
        if msg["role"] != "system":
            seen_non_system = True
        elif seen_non_system:
            roles = [m["role"] for m in msgs]
            raise AssertionError(
                f"[{label}] system message at index {i} after non-system. "
                f"Roles: {roles}"
            )


def _assert_no_system_after_assistant(msgs: list[dict], label: str):
    """Assert no system message appears after an assistant or tool message."""
    seen_assistant_or_tool = False
    for i, msg in enumerate(msgs):
        if msg["role"] in ("assistant", "tool"):
            seen_assistant_or_tool = True
        elif msg["role"] == "system" and seen_assistant_or_tool:
            roles = [m["role"] for m in msgs]
            raise AssertionError(
                f"[{label}] system message at index {i} after assistant/tool. "
                f"Roles: {roles}"
            )


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------
def test_no_compression_passthrough():
    """When compression is off, messages come straight from to_messages()."""
    rows = [_system("sys"), _user("q"), _assistant("a")]
    traj = FakeTrajectory(rows)
    msgs = _messages_for_step(traj, current_step=1, tool_call_count=0,
                              repeated_tool_calls=0)
    assert len(msgs) == 3
    assert [m["role"] for m in msgs] == ["system", "user", "assistant"]
    _assert_system_first(msgs, "no_compression")
    print("  PASS test_no_compression_passthrough")


def test_no_compression_force_answer():
    """Without compression, force_answer is inserted after last system msg."""
    import task_runner
    old = task_runner.ENABLE_REACT_STATE_COMPRESSION
    task_runner.ENABLE_REACT_STATE_COMPRESSION = False
    try:
        rows = [_system("sys"), _user("q"), _assistant("a")]
        traj = FakeTrajectory(rows)
        msgs = _messages_for_step(traj, current_step=1, tool_call_count=0,
                                  repeated_tool_calls=0, force_answer=True)
        roles = [m["role"] for m in msgs]
        print(f"    roles: {roles}")
        assert len(msgs) == 4
        # force_answer(system) inserted after original system, before user
        assert roles == ["system", "system", "user", "assistant"]
        assert "Budget Exhausted" in msgs[1]["content"]
        _assert_system_first(msgs, "no_compression_force")
    finally:
        task_runner.ENABLE_REACT_STATE_COMPRESSION = old


def test_compression_few_rows():
    """When rows <= 4, compression path returns raw entries (no react state)."""
    import task_runner
    old = task_runner.ENABLE_REACT_STATE_COMPRESSION
    task_runner.ENABLE_REACT_STATE_COMPRESSION = True
    task_runner.REACT_STATE_AFTER_STEPS = 1
    try:
        rows = [_system("sys"), _user("q"), _assistant("a1", step_id=1),
                _tool("result", step_id=1)]
        traj = FakeTrajectory(rows)
        msgs = _messages_for_step(traj, current_step=3, tool_call_count=1,
                                  repeated_tool_calls=0)
        assert len(msgs) == 4
        assert [m["role"] for m in msgs] == ["system", "user", "assistant", "tool"]
        _assert_system_first(msgs, "compression_few_rows")
    finally:
        task_runner.ENABLE_REACT_STATE_COMPRESSION = old


def test_compression_few_rows_force_answer():
    """When rows <= 4 with force_answer, system message inserted after last system msg."""
    import task_runner
    old = task_runner.ENABLE_REACT_STATE_COMPRESSION
    task_runner.ENABLE_REACT_STATE_COMPRESSION = True
    task_runner.REACT_STATE_AFTER_STEPS = 1
    try:
        rows = [_system("sys"), _user("q"), _assistant("a1", step_id=1),
                _tool("result", step_id=1)]
        traj = FakeTrajectory(rows)
        msgs = _messages_for_step(traj, current_step=3, tool_call_count=1,
                                  repeated_tool_calls=0, force_answer=True)
        roles = [m["role"] for m in msgs]
        print(f"    roles: {roles}")
        # force_answer(system) inserted after original system, before user
        assert roles == ["system", "system", "user", "assistant", "tool"]
        assert "Budget Exhausted" in msgs[1]["content"]
        _assert_system_first(msgs, "compression_few_rows_force")
    finally:
        task_runner.ENABLE_REACT_STATE_COMPRESSION = old


def test_compression_many_rows_system_first():
    """With many rows and compression, system messages must be at the start."""
    import task_runner
    old_c = task_runner.ENABLE_REACT_STATE_COMPRESSION
    old_a = task_runner.REACT_STATE_AFTER_STEPS
    old_r = task_runner.REACT_STATE_RECENT_STEPS
    task_runner.ENABLE_REACT_STATE_COMPRESSION = True
    task_runner.REACT_STATE_AFTER_STEPS = 1
    task_runner.REACT_STATE_RECENT_STEPS = 1
    try:
        rows = [
            _system("sys prompt"),
            _user("What is X?"),
            _assistant("Let me search.", step_id=1),
            _tool('[{"title":"doc","snippet":"info"}]', step_id=1, fn_name="search_text"),
            _assistant("Found it: Y.", step_id=2),
            _tool('[{"title":"doc2","snippet":"more"}]', step_id=2, fn_name="search_text"),
        ]
        traj = FakeTrajectory(rows)
        msgs = _messages_for_step(traj, current_step=3, tool_call_count=2,
                                  repeated_tool_calls=0)
        roles = [m["role"] for m in msgs]
        print(f"    roles: {roles}")
        # system, system(react), user, then recent assistant/tool
        assert roles[0] == "system"
        assert roles[1] == "system"  # react state
        assert roles[2] == "user"
        _assert_system_first(msgs, "compression_many_rows")
        _assert_no_system_after_assistant(msgs, "compression_many_rows")
    finally:
        task_runner.ENABLE_REACT_STATE_COMPRESSION = old_c
        task_runner.REACT_STATE_AFTER_STEPS = old_a
        task_runner.REACT_STATE_RECENT_STEPS = old_r


def test_compression_many_rows_force_answer():
    """With compression + force_answer, system messages must be at the start."""
    import task_runner
    old_c = task_runner.ENABLE_REACT_STATE_COMPRESSION
    old_a = task_runner.REACT_STATE_AFTER_STEPS
    old_r = task_runner.REACT_STATE_RECENT_STEPS
    task_runner.ENABLE_REACT_STATE_COMPRESSION = True
    task_runner.REACT_STATE_AFTER_STEPS = 1
    task_runner.REACT_STATE_RECENT_STEPS = 1
    try:
        rows = [
            _system("sys prompt"),
            _user("What is X?"),
            _assistant("Let me search.", step_id=1),
            _tool('[{"title":"doc","snippet":"info"}]', step_id=1, fn_name="search_text"),
            _assistant("Found it: Y.", step_id=2),
            _tool('[{"title":"doc2","snippet":"more"}]', step_id=2, fn_name="search_text"),
        ]
        traj = FakeTrajectory(rows)
        msgs = _messages_for_step(traj, current_step=3, tool_call_count=10,
                                  repeated_tool_calls=5, force_answer=True)
        roles = [m["role"] for m in msgs]
        print(f"    roles: {roles}")
        # system, system(react), system(force), user, then recent assistant/tool
        assert roles == ["system", "system", "system", "user", "assistant", "tool"]
        _assert_system_first(msgs, "compression_many_rows_force")
        _assert_no_system_after_assistant(msgs, "compression_many_rows_force")
        # force_answer system message should be present
        system_contents = [m["content"] for m in msgs if m["role"] == "system"]
        assert any("Budget Exhausted" in c for c in system_contents), \
            f"force_answer message not found in system messages: {system_contents}"
    finally:
        task_runner.ENABLE_REACT_STATE_COMPRESSION = old_c
        task_runner.REACT_STATE_AFTER_STEPS = old_a
        task_runner.REACT_STATE_RECENT_STEPS = old_r


def test_compression_no_user_message():
    """Edge case: no user message in rows."""
    import task_runner
    old_c = task_runner.ENABLE_REACT_STATE_COMPRESSION
    old_a = task_runner.REACT_STATE_AFTER_STEPS
    old_r = task_runner.REACT_STATE_RECENT_STEPS
    task_runner.ENABLE_REACT_STATE_COMPRESSION = True
    task_runner.REACT_STATE_AFTER_STEPS = 1
    task_runner.REACT_STATE_RECENT_STEPS = 1
    try:
        rows = [
            _system("sys prompt"),
            _assistant("step1", step_id=1),
            _tool("result1", step_id=1),
            _assistant("step2", step_id=2),
            _tool("result2", step_id=2),
        ]
        traj = FakeTrajectory(rows)
        msgs = _messages_for_step(traj, current_step=3, tool_call_count=2,
                                  repeated_tool_calls=0)
        roles = [m["role"] for m in msgs]
        print(f"    roles: {roles}")
        # system, system(react), then recent assistant/tool
        assert roles == ["system", "system", "assistant", "tool"]
        _assert_system_first(msgs, "no_user_msg")
        _assert_no_system_after_assistant(msgs, "no_user_msg")
    finally:
        task_runner.ENABLE_REACT_STATE_COMPRESSION = old_c
        task_runner.REACT_STATE_AFTER_STEPS = old_a
        task_runner.REACT_STATE_RECENT_STEPS = old_r


def test_compression_multiple_system_messages():
    """Multiple system messages (e.g. from reflection) should all stay at front."""
    import task_runner
    old_c = task_runner.ENABLE_REACT_STATE_COMPRESSION
    old_a = task_runner.REACT_STATE_AFTER_STEPS
    old_r = task_runner.REACT_STATE_RECENT_STEPS
    task_runner.ENABLE_REACT_STATE_COMPRESSION = True
    task_runner.REACT_STATE_AFTER_STEPS = 1
    task_runner.REACT_STATE_RECENT_STEPS = 1
    try:
        rows = [
            _system("sys prompt"),
            _system("reflection data"),
            _user("What is X?"),
            _assistant("step1", step_id=1),
            _tool("result1", step_id=1),
            _assistant("step2", step_id=2),
            _tool("result2", step_id=2),
        ]
        traj = FakeTrajectory(rows)
        msgs = _messages_for_step(traj, current_step=3, tool_call_count=2,
                                  repeated_tool_calls=0)
        roles = [m["role"] for m in msgs]
        print(f"    roles: {roles}")
        # system, system, system(react), user, then recent assistant/tool
        assert roles == ["system", "system", "system", "user", "assistant", "tool"]
        _assert_system_first(msgs, "multi_system")
        _assert_no_system_after_assistant(msgs, "multi_system")
    finally:
        task_runner.ENABLE_REACT_STATE_COMPRESSION = old_c
        task_runner.REACT_STATE_AFTER_STEPS = old_a
        task_runner.REACT_STATE_RECENT_STEPS = old_r


def test_realistic_step3_scenario():
    """
    Reproduce the exact error scenario from the traceback:
    step 3, 6 rows (system + user + 2 assistant + 2 tool), compression on.
    Previously produced [system, user, system(react), assistant, assistant, system(force)]
    which caused 'System message must be at the beginning'.
    """
    import task_runner
    old_c = task_runner.ENABLE_REACT_STATE_COMPRESSION
    old_a = task_runner.REACT_STATE_AFTER_STEPS
    old_r = task_runner.REACT_STATE_RECENT_STEPS
    old_tc = task_runner.MAX_TOOL_CALLS
    old_id = task_runner.MAX_IDENTICAL_TOOL_CALLS
    task_runner.ENABLE_REACT_STATE_COMPRESSION = True
    task_runner.REACT_STATE_AFTER_STEPS = 1
    task_runner.REACT_STATE_RECENT_STEPS = 1
    task_runner.MAX_TOOL_CALLS = 9
    task_runner.MAX_IDENTICAL_TOOL_CALLS = 1
    try:
        rows = [
            _system("你是 generator-agent ..."),
            _user("Please answer the benchmark problem..."),
            _assistant("Let me search.", step_id=1,
                       tool_calls=[{"id": "tc1", "type": "function",
                                    "function": {"name": "search_text",
                                                 "arguments": '{"query":"test"}'}}]),
            _tool('[{"rank":1,"title":"doc","snippet":"info"}]', step_id=1,
                  tool_call_id="tc1", fn_name="search_text"),
            _assistant("I found some info.", step_id=2),
            _tool('[{"rank":1,"title":"doc2","snippet":"more info"}]', step_id=2,
                  tool_call_id="tc2", fn_name="search_text"),
        ]
        traj = FakeTrajectory(rows)

        # Simulate step 3 with force_answer (budget exhausted)
        force_answer = True
        msgs = _messages_for_step(
            traj, current_step=3, tool_call_count=10,
            repeated_tool_calls=5, force_answer=force_answer,
        )
        roles = [m["role"] for m in msgs]
        print(f"    roles: {roles}")

        # system, system(react), system(force), user, then recent assistant/tool
        assert roles == ["system", "system", "system", "user", "assistant", "tool"]

        # The critical assertion: no system message after assistant/tool
        _assert_system_first(msgs, "realistic_step3")
        _assert_no_system_after_assistant(msgs, "realistic_step3")

        # Verify the force_answer message is present
        system_contents = [m["content"] for m in msgs if m["role"] == "system"]
        assert any("Budget Exhausted" in c for c in system_contents)
    finally:
        task_runner.ENABLE_REACT_STATE_COMPRESSION = old_c
        task_runner.REACT_STATE_AFTER_STEPS = old_a
        task_runner.REACT_STATE_RECENT_STEPS = old_r
        task_runner.MAX_TOOL_CALLS = old_tc
        task_runner.MAX_IDENTICAL_TOOL_CALLS = old_id


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    tests = [
        test_no_compression_passthrough,
        test_no_compression_force_answer,
        test_compression_few_rows,
        test_compression_few_rows_force_answer,
        test_compression_many_rows_system_first,
        test_compression_many_rows_force_answer,
        test_compression_no_user_message,
        test_compression_multiple_system_messages,
        test_realistic_step3_scenario,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            print(f"Running {t.__name__} ...")
            t()
            passed += 1
        except Exception as e:
            print(f"  FAIL {t.__name__}: {e}")
            failed += 1
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    if failed:
        sys.exit(1)
    print("All tests passed!")

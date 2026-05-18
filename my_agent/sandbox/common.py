from __future__ import annotations

import hashlib
from pathlib import Path


def language_to_command(language: str) -> str:
    lang = language.lower()
    if lang in {"python", "py"} or lang.startswith("python"):
        return "python"
    if lang in {"bash", "sh", "shell"}:
        return "sh" if lang == "shell" else lang
    raise ValueError(f"Unsupported code language: {language}")


def safe_code_filename(code: str, language: str, workspace: Path, requested: str | None = None) -> str:
    if requested:
        path = Path(requested)
    else:
        first = code.splitlines()[0].strip() if code.splitlines() else ""
        if first.startswith("# filename:"):
            path = Path(first.split(":", 1)[1].strip())
        else:
            suffix = "py" if language.lower().startswith("python") else language.lower()
            path = Path(f"tmp_code_{hashlib.sha256(code.encode()).hexdigest()}.{suffix}")

    if path.is_absolute():
        resolved = path.resolve()
    else:
        resolved = (workspace / path).resolve()
    resolved.relative_to(workspace.resolve())
    return str(resolved.relative_to(workspace.resolve()))


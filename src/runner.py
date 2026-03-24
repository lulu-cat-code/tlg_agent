"""Run generated R code and capture execution outputs."""

from __future__ import annotations

from dataclasses import dataclass
import subprocess
import tempfile


@dataclass
class RunResult:
    success: bool
    stdout: str
    stderr: str
    returncode: int
    script_path: str | None


def run_r_code(code: str) -> RunResult:
    """Execute R code with Rscript and return captured process outputs."""
    if not str(code).strip():
        return RunResult(
            success=False,
            stdout="",
            stderr="No R code provided.",
            returncode=1,
            script_path=None,
        )

    script_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".R", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(code)
            script_path = tmp.name

        completed = subprocess.run(
            ["Rscript", script_path],
            capture_output=True,
            text=True,
            check=False,
        )
        return RunResult(
            success=completed.returncode == 0,
            stdout=completed.stdout,
            stderr=completed.stderr,
            returncode=completed.returncode,
            script_path=script_path,
        )
    except Exception as exc:  # pragma: no cover - exercised via tests with mocks
        return RunResult(
            success=False,
            stdout="",
            stderr=str(exc),
            returncode=-1,
            script_path=script_path,
        )

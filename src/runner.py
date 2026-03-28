"""Runner for generated R scripts."""

from __future__ import annotations

from dataclasses import dataclass
import subprocess


@dataclass
class RunResult:
    success: bool
    stdout: str
    stderr: str
    returncode: int
    script_path: str | None


def run_r_script(script_path: str) -> RunResult:
    """Execute an R script file with Rscript."""
    if not str(script_path).strip():
        return RunResult(False, "", "No script path provided.", 1, None)

    try:
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
    except Exception as exc:
        return RunResult(False, "", str(exc), -1, script_path)

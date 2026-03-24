import os
import shutil
import subprocess

import pytest

from src.runner import RunResult, run_r_code


def test_run_r_code_success_cat_hello() -> None:
    if shutil.which("Rscript") is None:
        pytest.skip("Rscript not installed in test environment")

    result = run_r_code('cat("hello")')

    assert isinstance(result, RunResult)
    assert result.success is True
    assert result.returncode == 0
    assert result.stdout == "hello"
    assert result.stderr == ""
    assert result.script_path is not None
    assert os.path.exists(result.script_path)


def test_run_r_code_empty_code_input() -> None:
    result = run_r_code("   \n\t")

    assert result.success is False
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "No R code provided."
    assert result.script_path is None


def test_run_r_code_execution_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=1,
            stdout="",
            stderr="Execution failed",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_r_code('stop("boom")')

    assert result.success is False
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "Execution failed"
    assert result.script_path is not None


def test_run_r_code_missing_rscript_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise FileNotFoundError("Rscript not found")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_r_code('cat("hello")')

    assert result.success is False
    assert result.returncode == -1
    assert result.stdout == ""
    assert "Rscript not found" in result.stderr
    assert result.script_path is not None

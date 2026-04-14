from types import SimpleNamespace

from src.optimizer import optimize_generated_code, simplify_r_code


def test_simplify_r_code_trims_trailing_spaces_and_excess_blank_lines() -> None:
    code = "x <- 1   \n\n\n\n# comment   \n\n"
    assert simplify_r_code(code) == "x <- 1\n\n# comment\n"


def test_optimize_generated_code_updates_code_in_place() -> None:
    generation = SimpleNamespace(code="x <- 1   \n\n\n")
    optimized = optimize_generated_code(generation)
    assert optimized is generation
    assert generation.code == "x <- 1\n"

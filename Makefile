.PHONY: setup lint fmt typecheck test run clean
# uv handles venv + lockfile + installs. https://docs.astral.sh/uv/

setup:          ## create venv, install deps, install pre-commit hooks
	uv sync
	uv run pre-commit install

lint:           ## lint without changing files
	uv run ruff check .

fmt:            ## auto-format + autofix
	uv run ruff format .
	uv run ruff check --fix .

typecheck:      ## static types
	uv run mypy src

test:           ## run tests with coverage
	uv run pytest

run:            ## run the meridian entry point (prints a sample DataFrame)
	uv run python -m meridian

clean:
	rm -rf .venv .pytest_cache .mypy_cache .ruff_cache __pycache__ */__pycache__

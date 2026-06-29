# meridian-core

Single source of truth for the **Meridian** fictional marketplace domain used across the
[Meridian data + AI platform portfolio](https://github.com/AndreFelippeVidal).

Every portfolio project depends on this package so customer IDs, column names, and data shapes
stay consistent across all repos. Never copy or redefine these generators — depend on `meridian-core`
and pin a tag.

## Install (git-tag pin)

```toml
# pyproject.toml
dependencies = [
    "meridian-core @ git+https://github.com/AndreFelippeVidal/meridian-core@v0.1.0",
]
```

## Usage

```python
from meridian.synthetic import generate_customers

df = generate_customers(n=1000, seed=42)
print(df.head())
```

## Domain entities (v0.1.0)

| Generator | Returns | Key columns |
|---|---|---|
| `generate_customers(n, seed)` | `pl.DataFrame` | `customer_id`, `name`, `email`, `country`, `signup_date` |

## Versioning

- Bump the version in `pyproject.toml`, commit, tag (`git tag vX.Y.Z`), push the tag.
- Downstream projects then update their pin and run `uv sync`.
- See `docs/adr/0001-shared-domain-vs-monorepo.md` for the rationale.

## Development

```bash
make setup       # uv sync + pre-commit install
make lint        # ruff check
make fmt         # ruff format + autofix
make typecheck   # mypy strict
make test        # pytest with coverage
make run         # print a 5-row sample
```

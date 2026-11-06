# Application guidance

Keep Click wiring in `src/local_secrets/cli.py`, application logic independent of Click, and external secret stores behind the backend interface. Never place secret values in process arguments, logs, manifests, or test fixtures that represent real credentials. Run `uv run pytest`, `uv run ruff check src tests`, and build distributions after changes.

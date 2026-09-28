# Contributing

Start with the [architecture](docs/development/architecture.md) for source ownership and the [data reference](docs/reference/data.md) for response semantics. Keep changes focused and preserve the shared MCP/HTTP service.

## Development setup

Use a native Python 3.11+ runtime and uv. Windows x64 with Python 3.12 is the verified development platform.

```powershell
git clone https://github.com/whuang214/oura-connector.git
cd oura-connector
uv sync --locked --extra dev
```

Read repository instructions and check Git status before editing. Do not overwrite unrelated work. Dependency updates should be deliberate, reviewed, and reflected in both `pyproject.toml` and `uv.lock`.

## Verification

Run focused tests for the affected behavior, then the full checks before submitting:

```powershell
uv run --locked pytest --cov=oura_connector --cov-report=term-missing
uv run --locked ruff check .
uv run --locked mypy
uv build
```

The branch-aware coverage threshold is 75%. Tests use synthetic credentials, mock Oura responses, and a real local stdio subprocess. They do not require a personal Oura account. Native-window tests require a working Tk installation/display; do not treat an untested platform as verified.

For documentation changes, check relative links, anchors, examples, and CLI flags against current source. Only claim checks actually run. Live verification is a separate, explicitly authorized step; never include its private output in Git.

## Changes and review

- Add resource definitions in `resources.py`; keep retrieval and formatting shared across interfaces.
- Add focused behavioral tests for meaningful changes. Keep examples synthetic and runnable from the checkout.
- Update the owning guide/reference when a command, response, or setting changes.
- Explain the problem, resulting behavior, verification, and limitations in a pull request.
- Preserve MIT license/copyright notices. Policies remain at the repository root so their public URLs stay stable.

The [issue tracker](https://github.com/whuang214/oura-connector/issues) is public. Report bugs without credentials or health records. Community participation does not imply a support or maintenance guarantee.

# pytest profile

Use for pytest major upgrades and plugin-related updates. Most relevant for major version bumps (e.g., 7.x -> 8.x).

## Common risks

- plugin compatibility across major versions
- fixture scoping and teardown behavior changes
- warning handling and deprecation promotion to errors
- test discovery changes (import mode, conftest loading)
- deprecated marks/options removed or renamed
- `yield` fixture behavior differences
- config file parsing changes (`pytest.ini`, `pyproject.toml`, `tox.ini`)

## Searches

```bash
rg -n "pytest_plugins|@pytest\.fixture|yield" tests/ .
rg -n "pytest\.mark|xfail|skipif" .
rg -n "pytest\.raises|warns\(|deprecated_call" .
rg -n "filterwarnings|addopts|testpaths" .
rg -n "pytest\.ini|conftest\.py|pyproject\.toml" .
```

## Smoke tests

- run a small representative subset first
- run full local test suite if feasible
- compare test collection count before/after if possible
- inspect warnings promoted to errors
- verify plugin-dependent features still work (coverage, xdist, etc.)

## Version awareness

This profile is most relevant for major version bumps (e.g., 7.x -> 8.x) where plugin compatibility is the primary concern. Minor or patch bumps rarely need the full profile; correlate the search patterns to the exact version jump in the alert.

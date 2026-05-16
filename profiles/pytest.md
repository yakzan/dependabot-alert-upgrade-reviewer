# pytest profile

Use for pytest major upgrades and plugin-related updates.

## Common risks

- plugin compatibility
- fixture behavior changes
- warning handling changes
- import path / test discovery changes
- deprecated marks/options removed

## Searches

```bash
rg -n "pytest_plugins|@pytest\.fixture|yield" tests .
rg -n "filterwarnings|pytest\.mark|xfail|skipif" .
rg -n "pytest\.raises|warns\(|deprecated_call" .
rg -n "addopts|pytest.ini|tox.ini|pyproject.toml" .
```

## Smoke tests

- run a small representative subset first
- run full local test suite if feasible
- compare test collection count before/after if possible
- inspect warnings promoted to errors

# Python runtime profile: 3.7 -> 3.10+

Use when the alert cannot be resolved while staying on Python 3.7 or when upgraded dependencies require Python 3.8/3.9/3.10+.

## Common risks

- dependencies dropping Python 3.7 support
- old `typing` / `typing_extensions` assumptions
- removed imports from `collections`
- deprecated `asyncio` loop parameters
- `distutils` usage
- changed dependency resolver behavior
- old build backends or setuptools pinning
- wheels unavailable for old platforms

## Searches

```bash
rg -n "from collections import .*Mapping|from collections import .*Sequence|from collections import .*Mutable" .
rg -n "asyncio\.coroutine|loop=|get_event_loop\(" .
rg -n "import imp|from imp import|distutils" .
rg -n "typing_extensions|dataclasses|importlib_metadata|pathlib2|configparser" .
rg -n "python_requires|requires-python|Programming Language :: Python :: 3\.7" .
```

## Smoke tests

- import all application modules
- run CLI entrypoints with `--help`
- run minimal job/task execution locally
- run serialization/deserialization round trips
- run dependency import checks with `python -m pip check`

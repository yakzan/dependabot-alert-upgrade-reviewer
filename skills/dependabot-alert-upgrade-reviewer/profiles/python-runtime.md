# Python runtime profile: 3.7 -> 3.10+

Use when the alert cannot be resolved while staying on Python 3.7 or when upgraded dependencies require Python 3.8/3.9/3.10+. Bumps within 3.10+ generally don't need this profile.

## Common risks

- dependencies dropping Python 3.7/3.8 support
- removed stdlib modules: `imp`, `distutils`, `parser`, `formatter`
- moved ABCs: `collections.abc` replaces `collections.Mapping`/`Sequence`/`Mutable*`
- `typing` module: deprecated aliases (`typing.List`, `typing.Dict`, etc.) may be removed
- `typing_extensions` imports needed for forward-compatible type annotations
- `asyncio.coroutine` removed; `loop=` parameter deprecated in many functions
- `dataclasses` backport no longer relevant (stdlib since 3.7, stable since 3.8)
- `importlib_metadata`, `pathlib2`, `configparser` backports unnecessary on 3.8+
- build backend compatibility (setuptools, wheel, build)
- wheel availability for target platform/architecture
- match/case pattern matching (3.10+) incompatible with older Python

## Searches

```bash
rg -n "from collections import" .
rg -n "asyncio\.coroutine|get_event_loop|loop=" .
rg -n "import imp\b|from imp import|distutils" .
rg -n "typing_extensions|dataclasses|importlib_metadata" .
rg -n "pathlib2|configparser" .
rg -n "python_requires|requires-python" .
rg -n "Programming Language :: Python :: 3\.[0-9]" .
rg -n "match .*:" .
```

## Smoke tests

- import all application modules with `python -c "import pkg"` for each top-level package
- run CLI entrypoints with `--help`
- run minimal job/task execution locally
- run serialization/deserialization round trips
- run dependency import checks with `python -m pip check`
- compile all files: `python -m compileall .`

## Version awareness

This profile is most relevant for 3.7 -> 3.10+ transitions where removed stdlib modules and typing changes are concentrated. Bumps within 3.10+ generally don't need this profile; correlate the search patterns to the exact version jump in the alert.

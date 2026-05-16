# SQLAlchemy profile

Use for SQLAlchemy 1.3/1.4 -> 2.x and related DB-layer changes.

## Common risks

- `engine.execute` removed
- legacy `session.query` behavior
- implicit autocommit removed / transaction behavior changed
- result row API changes
- ORM typing / declarative changes
- connection/session lifecycle changes
- connection leaks after changed cleanup paths

## Searches

```bash
rg -n "engine\.execute|\.execute\(" .
rg -n "session\.query|Query\(" .
rg -n "autocommit|commit\(|rollback\(|flush\(|close\(" .
rg -n "sessionmaker|scoped_session|create_engine|get_bind" .
rg -n "fetchone\(|fetchall\(|scalar\(|mappings\(" .
```

## Smoke tests

- successful write commits and closes session
- failed write rolls back and closes session
- readonly query path works
- repeated execution does not exhaust pool/connections
- result access still returns expected shape

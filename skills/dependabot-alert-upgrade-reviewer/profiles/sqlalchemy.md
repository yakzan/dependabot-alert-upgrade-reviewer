# SQLAlchemy profile

Use for SQLAlchemy 1.3/1.4 -> 2.x and related DB-layer changes. Patch bumps within 2.x generally do not need the full profile.

## Common risks

- `engine.execute` removed; use `session.execute` or `connection.execute`
- legacy `session.query` replaced by `select()` / `session.execute(select(...))`
- implicit autocommit removed; explicit transaction boundaries needed
- `Result` object replaces raw row tuples; `scalars()`, `mappings()` added
- `declarative_base` → declarative ORM with `Mapped[...]` / `mapped_column()`
- `backref` → `back_populates` requirement
- `session.merge()` / `session.refresh()` behavior changes
- `MetaData` handling and bind propagation changed
- connection pool and `dispose()` behavior changes
- `get_bind` removal in some contexts

## Searches

```bash
rg -n "engine\.execute|\.execute\(" .
rg -n "session\.execute|session\.query|Query\(" .
rg -n "\.scalars\(|\.scalar\(|\.fetchone\(|\.fetchall\(|\.mappings\(" .
rg -n "\bResult\b|\bCursorResult\b|\bScalarResult\b" .
rg -n "autocommit|commit\(|rollback\(|flush\(|close\(" .
rg -n "sessionmaker|scoped_session|create_engine|get_bind" .
rg -n "declarative_base|Mapped\[|mapped_column\(|relationship\(" .
rg -n "back_populates|backref|MetaData\b|dispose\(" .
rg -n "\bselect\(|\btext\(|\bbind=" .
rg -n "\.merge\(|\.refresh\(|\.expire\(" .
```

## Smoke tests

- successful write commits and closes session
- failed write rolls back and closes session
- readonly query path works
- repeated execution does not exhaust pool/connections
- result access returns expected shape (rows, mappings, scalars)
- lazy-loaded relationships resolve without detached instance errors
- session lifecycle correctly managed with `with` or explicit close

## Version awareness

This profile is most relevant for 1.3/1.4 -> 2.x upgrades where breaking API and behavior changes are concentrated. For 2.0.x -> 2.0.y patch bumps, trim to deprecation warnings and Result API changes only. Correlate search patterns to the exact version jump in the alert.

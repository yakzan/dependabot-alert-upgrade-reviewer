# Dependabot Alert Upgrade Reviewer

A skill for coding agents that starts from Dependabot alerts before a PR exists.

It guides the agent to:

1. create a safe non-master branch,
2. inspect Dependabot alerts,
3. choose the smallest safe package upgrade,
4. read changelogs/migration notes for the exact version jump,
5. apply the dependency change using the repo's existing package manager,
6. search the repo for affected APIs,
7. detect suspicious lifecycle call changes,
8. propose or add local smoke tests,
9. produce a merge-risk report.

The helper scripts are intentionally small and optional. The core value is the protocol in `SKILL.md`.

## Helper scripts

Run with `uv`:

```bash
uv run dependency-diff --base main --head HEAD
uv run risky-call-diff --base main --head HEAD
uv run risky-patterns --profile sqlalchemy
```

Or directly with Python:

```bash
python scripts/dependency_diff.py --base main --head HEAD
python scripts/risky_call_diff.py --base main --head HEAD
python scripts/risky_patterns.py --profile sqlalchemy
```

## Tests

```bash
uv run pytest
```

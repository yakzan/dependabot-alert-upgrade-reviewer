# Dependabot Alert Upgrade Reviewer

A skill for coding agents that creates PRs to address Dependabot alerts in Python repositories. Supports mono- and multi-package repos.

It guides the agent to:

1. create a safe non-master branch,
2. inspect Dependabot alerts (supports multiple alerts, batched by topic),
3. choose the smallest safe package upgrade,
4. read changelogs/migration notes for the exact version jump,
5. apply the dependency change using the repo's existing package manager,
6. search the repo for affected APIs,
7. detect suspicious lifecycle call changes,
8. propose or add local smoke tests,
9. produce a merge-risk report and suggest a PR body.

The core value is the protocol in `SKILL.md`. The helper scripts are small, deterministic, and optional.

## Helper scripts

All scripts support `--json` for structured output and auto-detect the default branch.

```bash
# Dependency file changes between branches (includes requirements, constraints, lockfiles)
uv run dependency-diff --json

# Risky call changes (lifecycle calls added/removed, focusing on resource management)
uv run risky-call-diff --json

# Pattern search using profiles or custom patterns
uv run risky-patterns --profile sqlalchemy --json
uv run risky-patterns --profile pydantic --profile http --json
uv run risky-patterns --profile python-runtime --profile pytest --json
uv run risky-patterns --pattern 'session\.query' --json
```

Available profiles: `lifecycle`, `sqlalchemy`, `pydantic`, `pandas`, `http`, `pytest`, `python-runtime`.

Or directly with Python:

```bash
python scripts/dependency_diff.py --base main --head HEAD --json
python scripts/risky_call_diff.py --base main --head HEAD --json
python scripts/risky_patterns.py --profile sqlalchemy --json
```

## Monorepos

For repositories with multiple Python packages, run pattern searches per package directory:

```bash
uv run risky-patterns --profile sqlalchemy --root packages/lib-a
```

## Tests

```bash
uv run pytest
```
# Dependabot Alert Upgrade Reviewer

A protocol for coding agents that creates PRs to address Dependabot alerts in Python repositories. Supports mono- and multi-package repos. The publishable skill lives at `skills/dependabot-alert-upgrade-reviewer/SKILL.md` so `gh skill install` can discover it for GitHub Copilot, Codex, and other Agent Skills-compatible hosts.

It guides the agent to:

1. create a safe non-master branch,
2. inspect Dependabot alerts (supports multiple alerts, batched by topic),
3. choose the smallest safe package upgrade,
4. check runtime/platform constraints and resolver installability,
5. read changelogs/migration notes for the exact version jump,
6. apply the dependency change using the repo's existing package manager,
7. create a checkpoint commit only after dependency resolution/install checks pass,
8. search the repo for affected APIs and optional dependency feature paths,
9. detect suspicious lifecycle call changes,
10. propose or add usage-derived local smoke tests,
11. produce a merge-risk report and suggest a PR body.

The core value is the protocol in `skills/dependabot-alert-upgrade-reviewer/SKILL.md`. The helper scripts are small, deterministic, and optional.

## Installation

When running `gh skill install` non-interactively, include the skill name `dependabot-alert-upgrade-reviewer`.

Install for GitHub Copilot CLI:

```bash
gh skill install yakzan/dependabot-alert-upgrade-reviewer dependabot-alert-upgrade-reviewer --agent github-copilot
```

Install for Codex:

```bash
gh skill install yakzan/dependabot-alert-upgrade-reviewer dependabot-alert-upgrade-reviewer --agent codex
```

When this repository is used as a helper package for another target repo, run the scripts from the target repo's working directory and reference the skill directory by path:

```bash
python <skill-dir>/scripts/dependency_diff.py --json
python <skill-dir>/scripts/risky_call_diff.py --json
python <skill-dir>/scripts/risky_patterns.py --profile sqlalchemy --json
```

## Helper scripts

`dependency-diff` and `risky-call-diff` are **branch-comparison tools** — they diff between a base ref and HEAD and auto-detect the default branch. `risky-patterns` is a **disk scanner** — it searches `.py` files on disk using `--root` (default `.`) and has no `--base` flag.

All scripts support `--json` for structured output.

If the package is installed in the active environment, the entry points are also available:

```bash
# Dependency file changes between branches (includes requirements, constraints, lockfiles)
uv run dependency-diff --json

# Risky call changes (lifecycle calls added/removed, focusing on resource management)
uv run risky-call-diff --json

# Pattern search using profiles or custom patterns (scans disk, not git diff)
uv run risky-patterns --profile sqlalchemy --json
uv run risky-patterns --profile pydantic --profile http --json
uv run risky-patterns --profile python-runtime --profile pytest --json
uv run risky-patterns --profile optional-deps --json
uv run risky-patterns --pattern 'session\.query' --json
```

Available profiles: `lifecycle`, `sqlalchemy`, `pydantic`, `pandas`, `http`, `pytest`, `python-runtime`, `optional-deps`.

Or directly with Python:

```bash
python <skill-dir>/scripts/dependency_diff.py --base main --head HEAD --json
python <skill-dir>/scripts/risky_call_diff.py --base main --head HEAD --json
python <skill-dir>/scripts/risky_patterns.py --profile sqlalchemy --json
```

### AST helper limitations

`risky-call-diff` uses Python AST parsing to detect function calls. It is a heuristic, not a semantic analyzer. It will **not** catch aliased imports, indirect calls (`fn = obj.commit; fn()`), decorator-based lifecycle patterns, chained calls (`obj.get_session().commit()` only detects the outermost), or same-name functions in one file (two `save` methods on different classes get pooled into a single diff entry). Treat its output as a starting point, supplemented by `risky-patterns` regex scans and manual `rg` searches.

## Monorepos

For repositories with multiple Python packages, run pattern searches per package directory:

```bash
python <skill-dir>/scripts/risky_patterns.py --profile sqlalchemy --root packages/lib-a
```

## Tests

```bash
uv run pytest
```

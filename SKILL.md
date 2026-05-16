# Dependabot Alert Upgrade Reviewer

Use this skill when a repository has Dependabot alerts but no upgrade PR exists yet. The goal is to create a safe, isolated upgrade branch, apply the minimum necessary dependency/runtime changes, inspect changelogs and migration notes for the exact version jump, and produce a skeptical review with repo-specific smoke tests.

This skill is intentionally not an auto-migration framework. It is an agent protocol with small deterministic helpers. The agent may use package managers, Git, GitHub CLI, local tests, AST/grep scripts, and changelog research, but must not claim safety without evidence.

## Core principle

Dependabot tells us what is vulnerable or outdated. It does not prove that the upgrade is behaviorally safe.

Your job is not to prove the migration is correct. Your job is to find what could be missed.

## When to use

Use this skill when the user says any of the following:

- There are Dependabot alerts in a Python repository.
- They need to upgrade vulnerable Python dependencies.
- The repo is old, especially Python 3.7, and may need Python 3.10+ migration.
- They usually fork a repo and create a non-master branch manually.
- They want a coding agent to perform local smoke tests and sanity review.
- They are worried about missed behavior such as `save -> close`, `commit -> rollback`, or resource cleanup.

## Hard rules

1. Never work directly on `master`, `main`, or a protected branch.
2. Never claim the upgrade is safe only because tests pass.
3. Never inspect only changed files. Also inspect suspicious untouched files.
4. Never summarize changelogs without mapping them to repo-local searches.
5. Never perform production-affecting commands.
6. Run only local tests unless the user explicitly authorizes external systems.
7. Prefer the smallest dependency change that resolves the alert.
8. Keep unrelated formatting and refactors out of the branch.
9. If Python runtime migration is required, treat it as a separate risk area, not just a dependency bump.
10. Always produce a final risk report and smoke-test checklist.

## Overall workflow

### Phase 0 — Establish safe branch

First inspect Git state:

```bash
git status --short
git branch --show-current
git remote -v
```

If the working tree is dirty, stop and report the dirty files. Do not overwrite user changes.

If current branch is `main`, `master`, `develop`, or another protected branch, create a dedicated branch.

Recommended branch naming:

```text
dependabot/<package-or-topic>-<yyyy-mm-dd>
upgrade/<package-or-topic>-<yyyy-mm-dd>
security/<package-or-topic>-<yyyy-mm-dd>
```

Example:

```bash
git checkout -b dependabot/urllib3-2026-05-16
```

If the user works from a fork, verify that `origin` is the fork and `upstream` is the original repository when available:

```bash
git remote -v
```

If `gh` is available and authenticated, inspect repository metadata:

```bash
gh repo view --json nameWithOwner,defaultBranchRef,isFork,parent
```

Do not create a PR until the user asks or the skill has completed the review and produced a report.

### Phase 1 — Collect Dependabot alert context

Prefer GitHub CLI when available:

```bash
gh api repos/:owner/:repo/dependabot/alerts --paginate --jq '.[] | {number, state, dependency: .dependency.package.name, ecosystem: .dependency.package.ecosystem, manifest: .dependency.manifest_path, vulnerable_requirements: .security_vulnerability.vulnerable_version_range, patched_versions: .security_vulnerability.first_patched_version.identifier, severity: .security_advisory.severity, summary: .security_advisory.summary}'
```

If GitHub CLI is unavailable, ask the user to paste the alert details or use the GitHub web UI. Required fields:

- package name
- ecosystem, usually `pip`
- manifest path
- vulnerable version range
- first patched version, if available
- severity
- advisory summary

Classify alerts:

```text
Critical/high severity -> prioritize first
Direct dependency -> usually actionable in manifest
Transitive dependency -> may require lockfile update or parent dependency bump
Runtime-related dependency -> may imply Python version bump
```

### Phase 2 — Create an upgrade plan before editing

For each alert, determine:

- current installed/locked version
- minimum safe patched version
- whether Python version constraints allow that patched version
- whether the dependency is direct or transitive
- which package manager is used: pip, pip-tools, Poetry, uv, Pipenv, setup.py/setup.cfg

Inspect files:

```bash
ls
find . -maxdepth 3 \( -name 'pyproject.toml' -o -name 'requirements*.txt' -o -name 'poetry.lock' -o -name 'uv.lock' -o -name 'Pipfile.lock' -o -name 'setup.py' -o -name 'setup.cfg' -o -name 'tox.ini' -o -name '.python-version' \)
```

Produce a short plan:

```text
Alert: package A current X -> patched >= Y
Manifest: requirements.txt
Likely action: bump direct pin or regenerate lockfile
Python risk: patched version requires Python >= 3.8, repo appears to use 3.7
Changelog review required: yes/no
Expected smoke tests: ...
```

### Phase 3 — Apply minimum dependency changes

Use the repository's existing dependency workflow. Do not introduce a new dependency manager just for the migration.

Common commands:

```bash
# pip-tools
python -m piptools compile requirements.in

# Poetry
poetry update <package>

# uv
uv lock --upgrade-package <package>

# pipenv
pipenv update <package>
```

If a repo only has `requirements.txt`, edit the direct pin cautiously and install in a local virtual environment.

After dependency changes, inspect the diff:

```bash
git diff --stat
git diff -- requirements.txt requirements-dev.txt pyproject.toml poetry.lock uv.lock Pipfile.lock setup.py setup.cfg tox.ini .python-version
```

Flag noisy lockfile explosions or unrelated dependency changes.

### Phase 4 — Changelog and migration-guide scout

For every package/version jump, gather official or highest-quality sources:

1. official migration guide
2. official changelog
3. official GitHub releases
4. PyPI release history
5. docs for deprecations/removals

Extract only actionable items:

- removed APIs
- changed defaults
- changed exception behavior
- changed serialization/deserialization behavior
- changed validation behavior
- changed transaction/session/resource lifecycle behavior
- changed typing/import paths
- changed minimum Python version
- security-specific behavioral guidance

For each item, create repo-local search patterns.

Bad:

```text
SQLAlchemy changed transaction behavior.
```

Good:

```text
Release-note risk: SQLAlchemy removed implicit autocommit / changed 2.0 execution style.
Repo searches:
- session.query
- engine.execute
- autocommit
- commit
- rollback
- close
- sessionmaker
- scoped_session
Smoke tests:
- successful write commits and closes
- failed write rolls back and closes
- repeated calls do not exhaust connections
```

### Phase 5 — Repo-local impact search

Search both changed and unchanged files. Use grep/ripgrep first, then AST helpers when useful.

```bash
rg -n "session\.query|engine\.execute|autocommit|commit\(|rollback\(|close\(" .
rg -n "parse_obj|dict\(|json\(|BaseModel|validator|root_validator" .
rg -n "read_csv|to_datetime|astype|fillna|groupby|merge" .
```

Run helper scripts if present:

```bash
uv run dependency-diff --base main --head HEAD
uv run risky-call-diff --base main --head HEAD
uv run risky-patterns --profile sqlalchemy
```

Classify findings:

```text
Changed and likely handled
Changed but suspicious
Untouched but affected by version jump
No local usage found
Unknown / needs manual inspection
```

### Phase 6 — Behavioral smoke-test design

Smoke tests must cover behavior, not just imports.

Always consider:

- success path
- failure path
- cleanup path
- early return path
- repeated-call path
- serialization/deserialization round trip
- database transaction boundaries
- external API parsing behavior
- empty/null/edge inputs

For lifecycle-sensitive code, explicitly test pairs and cleanup guarantees:

```text
save -> close
open -> close
connect -> close
commit -> close
exception -> rollback -> close
read -> close
write -> flush -> close
```

If the repo has no test suite, create a small local smoke script or pytest file, but keep it isolated and easy to remove.

### Phase 7 — Local validation

Run only local checks. Prefer the repo's existing commands.

Examples:

```bash
python --version
python -m pip check
python -m pytest
python -m pytest tests/path/to/relevant_tests.py -q
python -m compileall .
```

For Python 3.7 -> 3.10 migrations, also check:

```bash
python -m compileall .
rg -n "from collections import Mapping|MutableMapping|Sequence" .
rg -n "asyncio\.coroutine|loop=|imp\.|distutils" .
rg -n "typing_extensions|dataclasses|importlib_metadata" .
```

### Phase 8 — Final report

Always end with this structure:

```text
Upgrade branch
- branch name
- base branch

Alerts addressed
- package: old -> new
- manifest
- severity
- direct/transitive

Files changed
- dependency files
- source files
- tests/smoke scripts

Changelog/migration risks reviewed
- item
- local search performed
- repo impact

Suspicious findings
- changed risky behavior
- untouched affected files
- lifecycle changes
- missing tests

Local validation
- commands run
- result
- failures/skips

Merge risk
- Low / Medium / High
- why

Required human checks before PR/merge
- checklist

Suggested PR body
- concise summary
- risk notes
- tests run
```

## Package profiles

Use profiles when available, but do not rely on them exclusively. The changelog for the exact version range is still required for non-trivial updates.

Available profiles in this skill:

- `profiles/python-runtime.md`
- `profiles/sqlalchemy.md`
- `profiles/pydantic.md`
- `profiles/pandas.md`
- `profiles/pytest.md`
- `profiles/requests-urllib3-httpx.md`

## Good agent prompt

```text
Use the Dependabot Alert Upgrade Reviewer skill.

We do not have a PR yet. Start from the current repository state. Do not work on main/master. Create a dedicated upgrade branch if the tree is clean. Inspect Dependabot alerts, choose the smallest safe dependency upgrade, review official changelogs/migration notes for the exact version jump, apply the dependency change using the repo's existing package manager, search changed and unchanged code for affected APIs, add or propose behavior-level smoke tests, run only local validation, and finish with the skill's final risk report.

Be especially skeptical of resource lifecycle changes such as save -> close, commit -> rollback -> close, open -> close, connect -> close, and exception cleanup paths.
```

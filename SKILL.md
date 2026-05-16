# Dependabot Alert Upgrade Reviewer

Use this skill when a repository has Dependabot alerts and a PR needs to be created to address them. The goal is to create a safe, isolated upgrade branch, apply the minimum necessary dependency/runtime changes, inspect changelogs and migration notes for the exact version jump, produce a skeptical review with repo-specific smoke tests, and prepare a ready-to-push PR.

This skill is intentionally not an auto-migration framework. It is an agent protocol with small deterministic helpers. The agent may use package managers, Git, local tests, AST/grep scripts, and changelog research, but must not claim safety without evidence.

## Scope

This skill is written for **Python repositories**. The workflow and helper scripts target Python dependency managers (pip, pip-tools, Poetry, uv, Pipenv, setup.py/setup.cfg) and Python-specific migration patterns. Some phases (branch setup, changelog research, final report) are applicable to other ecosystems, but the scripts, profiles, and search patterns are Python-specific.

## Monorepo and multi-package repos

When the repository contains multiple Python packages (e.g., `packages/lib-a/pyproject.toml`, `packages/lib-b/pyproject.toml`), handle each manifest file separately:

1. Run the helper scripts for each package directory using `--root`:
   ```bash
   uv run risky-patterns --profile sqlalchemy --root packages/lib-a
   ```

2. Search each package's files independently:
   ```bash
   rg -n "pattern" packages/lib-a/
   rg -n "pattern" packages/lib-b/
   ```

3. If packages share a single lockfile at the repository root, upgrade commands still apply at the root but the impact search spans all packages.

4. In the final report, list each package and its affected dependency separately.

5. If a dependency affects multiple packages differently (e.g., lib-a uses SQLAlchemy 1.4 directly while lib-b imports it transitively), trace both dependency chains and report per-package risk.

## Two invocation modes

### Mode 1 — Full upgrade (default)

Start from the current repository state. Create a dedicated non-master branch, apply the minimum dependency change, search for affected code, run local smoke tests, and produce a final risk report with a suggested PR body.

### Mode 2 — Review existing changes

If there are already committed changes on a branch (e.g., a sequence of manual upgrades or a combined Dependabot alert fix), use the review portion of this skill to evaluate the existing diff.

```bash
uv run risky-call-diff --json
uv run dependency-diff --json
uv run risky-patterns --profile sqlalchemy --json
```

In this mode, skip Phase 0 (branch creation) and Phase 3 (dependency changes). Begin from Phase 4, using the already-committed changes as the diff to evaluate.

## Core principle

Dependabot tells us what is vulnerable or outdated. It does not prove that the upgrade is behaviorally safe.

Your job is not to prove the migration is correct. Your job is to find what could be missed.

Never claim the upgrade is proven safe solely because tests pass.

## Multi-alert handling

A single Dependabot alert is the simplest case. Real repositories often have 5-15 alerts. The default strategy is **one branch, one batched PR**. This keeps the review tractable and makes rollback straightforward.

Group alerts by topic when possible:

```text
security/http-clients:  urllib3 1.26.x -> 2.x, requests 2.28 -> 2.32
security/sqlalchemy:   SQLAlchemy 1.4 -> 2.0
runtime/python:        Python 3.7 -> 3.10 (if required by the above)
```

If alerts conflict (e.g., one requires a library upgrade that another depends on the old version of), split into separate branches. Otherwise, batch related alerts together.

Do not push or create the PR until the user explicitly asks. Prepare the branch, changes, and report locally first.

## Hard rules

1. Never work directly on `master`, `main`, or a protected branch.
2. Never claim the upgrade is proven safe solely because tests pass.
3. Never inspect only changed files. Also inspect suspicious untouched files.
4. Never summarize changelogs without mapping them to repo-local searches.
5. Never perform production-affecting commands or remote writes (no `git push`, no `gh pr create`, no deploy) unless the user explicitly authorizes it.
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

Do not push or create a PR unless the user explicitly asks.

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

For **transitive dependencies**, trace the dependency chain to determine why the vulnerable version is installed and which direct dependency pins it:

```bash
# pip
python -m pip show <vulnerable-package>
python -m pipdeptree -p <vulnerable-package>

# uv
uv pip show <vulnerable-package>

# Poetry
poetry show --tree
```

Determine whether the fix requires bumping the transitive dependency directly (e.g., via a constraint override) or bumping the parent that pins it.

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
Transitive: package A is pulled in by package B >= 2.0; bumping B may resolve it
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

After dependency changes, commit them before proceeding to Phase 5. The diff-based scripts require comparing the base branch against the current branch:

```bash
git add -A
git commit -m "bump <package> from X to Y"
```

Then inspect the diff:

```bash
git diff --stat
git diff -- requirements.txt requirements-dev.txt pyproject.toml poetry.lock uv.lock Pipfile.lock setup.py setup.cfg tox.ini .python-version
```

Flag noisy lockfile explosions or unrelated dependency changes.

### Phase 4 — Changelog and migration-guide scout

For every package/version jump, gather official or highest-quality sources. Prefer programmatic sources first:

1. **GitHub Releases API** — `gh api repos/:owner/:repo/releases --paginate --jq '.[] | {tag_name, name, body}' | head -200`
2. **PyPI JSON API** — `https://pypi.org/pypi/<package>/<version>/json` (check changelog links, requires_python, and dependencies)
3. **Official migration guide** — search the project's documentation site
4. **Official changelog** — usually in the repo's `CHANGELOG.md` or `HISTORY.rst`
5. **Breaking changes between exact versions** — use GitHub compare: `https://github.com/<owner>/<repo>/compare/<old-tag>...<new-tag>`

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

**Important:** Phase 3 changes must be committed before running the diff-based scripts in this phase. The scripts compare the base branch against HEAD; if there are no committed changes, the diff will be empty.

Search both changed and unchanged files. Use grep/ripgrep first, then AST helpers when useful.

```bash
rg -n "session\.query|engine\.execute|autocommit|commit\(|rollback\(|close\(" .
rg -n "parse_obj|dict\(|json\(|BaseModel|validator|root_validator" .
rg -n "read_csv|to_datetime|astype|fillna|groupby|merge" .
```

Run helper scripts. Use `--json` for machine-readable output:

```bash
# Dependency file changes (auto-detects default branch)
uv run dependency-diff --json

# Risky call changes between branches
uv run risky-call-diff --json

# Pattern search using profiles or custom patterns
uv run risky-patterns --profile sqlalchemy --json
uv run risky-patterns --profile pydantic --profile http --json
uv run risky-patterns --profile python-runtime --profile pytest --json
uv run risky-patterns --pattern 'session\.query' --pattern 'engine\.execute' --json
```

All scripts support `--json` for structured output that is easier to parse programmatically.

If `--base` is not specified, the scripts auto-detect the default branch (`origin/HEAD`, then `main`, then `master`, falling back to `main`).

**Cross-reference script outputs:** Correlate `dependency-diff` (which dependency files changed) with `risky-call-diff` (which risky calls appeared/disappeared in changed Python files) and `risky-patterns` (which patterns still exist in the repo). A lifecycle call removed in a file that is NOT in a dependency-changed path is lower-risk than one removed in a file that imports a bumped dependency. Focus investigation on files changed in the diff whose patterns match the upgraded package's migration guide.

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

If dependency resolution fails, tests cannot pass, or the lockfile explodes, abort and reset:

```bash
git checkout -- .
git clean -fd
```

Report the failure in the final risk report under "Merge risk" and recommend manual resolution.

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

Transitive dependency notes
- which direct dependency pins the vulnerable package
- whether bumping the parent resolves it

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

When the user is ready to create the PR:

```bash
git push -u origin <branch-name>
gh pr create --title "..." --body "..."
```

Only run these commands when the user explicitly asks. Do not push or create PRs automatically.

## Package profiles

Use profiles when available, but do not rely on them exclusively. The changelog for the exact version range is still required for non-trivial updates.

**Important:** Profiles provide general search patterns for a package family. Always correlate the profile to the exact version jump in the alert. For example, a SQLAlchemy profile is most relevant for 1.x -> 2.x migrations but may produce irrelevant noise for a 2.0.x -> 2.0.y patch bump. Focus on the changes documented in the changelog for the specific version range.

Available profiles in this skill:

- `profiles/python-runtime.md`
- `profiles/sqlalchemy.md`
- `profiles/pydantic.md`
- `profiles/pandas.md`
- `profiles/pytest.md`
- `profiles/requests-urllib3-httpx.md`

## Rollback guidance

If at any phase the upgrade cannot proceed cleanly:

```bash
# Discard all uncommitted changes
git checkout -- .
git clean -fd

# Delete the branch entirely if needed
git checkout main
git branch -D dependabot/<topic>-<date>
```

Report the failure clearly in the final report and recommend manual resolution or a different upgrade path.

## Good agent prompt

```text
Use the Dependabot Alert Upgrade Reviewer skill.

We do not have a PR yet. Start from the current repository state. Do not work on main/master. Create a dedicated upgrade branch if the tree is clean. Inspect Dependabot alerts, choose the smallest safe dependency upgrade, review official changelogs/migration notes for the exact version jump, apply the dependency change using the repo's existing package manager, commit the changes, search changed and unchanged code for affected APIs, add or propose behavior-level smoke tests, run only local validation, and finish with the skill's final risk report.

When multiple alerts exist, batch related alerts on one branch and note any conflicts.

Be especially skeptical of resource lifecycle changes such as save -> close, commit -> rollback -> close, open -> close, connect -> close, and exception cleanup paths.

Do not push or create a PR unless I explicitly ask.
```
# Dependabot Alert Upgrade Reviewer

Use this skill when a repository has Dependabot alerts and a PR needs to be created to address them. Create a safe, isolated upgrade branch, apply the minimum necessary dependency changes, inspect changelogs for the exact version jump, produce a skeptical review with repo-specific smoke tests, and prepare a ready-to-push PR.

This is an agent protocol with small deterministic helpers — not an auto-migration framework. The agent may use package managers, Git, local tests, AST/grep scripts, and changelog research, but must not claim safety without evidence.

## Scope

**Python repositories.** The workflow and helper scripts target Python dependency managers (pip, pip-tools, Poetry, uv, Pipenv, setup.py/setup.cfg) and Python-specific migration patterns. Branch setup, changelog research, and the final report are applicable to other ecosystems, but scripts, profiles, and search patterns are Python-specific.

## Monorepo and multi-package repos

For repos with multiple Python packages (e.g., `packages/lib-a/pyproject.toml`), handle each manifest separately:

1. Run helper scripts per package directory: `uv run risky-patterns --profile sqlalchemy --root packages/lib-a`
2. Search each package's files independently with `rg`
3. If packages share a root lockfile, upgrade commands apply at the root but impact search spans all packages
4. In the final report, list each package and its affected dependency separately
5. If a dependency affects multiple packages differently, trace both dependency chains and report per-package risk

## Two invocation modes

### Mode 1 — Full upgrade (default)

Start from current repo state. Create a non-master branch, apply the minimum dependency change, search for affected code, run smoke tests, produce a final risk report with a suggested PR body.

### Mode 2 — Review existing changes

If changes are already committed on a branch, use the review portion only. Skip Phase 0 and Phase 3. Begin from Phase 4, using the existing diff.

```bash
uv run risky-call-diff --json
uv run dependency-diff --json
uv run risky-patterns --profile sqlalchemy --json
```

## Core principle

Dependabot tells us what is vulnerable or outdated. It does not prove the upgrade is behaviorally safe. Your job is not to prove the migration is correct — it is to find what could be missed. Never claim the upgrade is proven safe solely because tests pass.

## Multi-alert handling

Default strategy: **one branch, one batched PR.** Group related alerts by topic:

```text
security/http-clients:  urllib3 1.26.x -> 2.x, requests 2.28 -> 2.32
security/sqlalchemy:   SQLAlchemy 1.4 -> 2.0
runtime/python:        Python 3.7 -> 3.10 (if required by the above)
```

Split into separate branches only if alerts conflict. Do not push or create the PR until the user explicitly asks.

## Hard rules

1. Never work directly on `master`, `main`, or a protected branch.
2. Never claim the upgrade is proven safe solely because tests pass.
3. Never inspect only changed files — also inspect suspicious untouched files.
4. Never summarize changelogs without mapping them to repo-local searches.
5. Never push, create PRs, or deploy unless the user explicitly authorizes it.
6. Run only local tests unless the user explicitly authorizes external systems.
7. Prefer the smallest dependency change that resolves the alert.
8. Keep unrelated formatting and refactors out of the branch.
9. If Python runtime migration is required, treat it as a separate risk area.
10. Always produce a final risk report and smoke-test checklist.

## Overall workflow

### Phase 0 — Establish safe branch

Inspect Git state:

```bash
git status --short
git branch --show-current
git remote -v
```

If the working tree is dirty, stop and report the dirty files. If on a protected branch, create a dedicated branch:

```bash
git checkout -b dependabot/<package-or-topic>-<yyyy-mm-dd>
```

If the user works from a fork, verify `origin`/`upstream` remotes. Do not push unless the user explicitly asks.

### Phase 1 — Collect Dependabot alert context

Prefer GitHub CLI:

```bash
gh api repos/:owner/:repo/dependabot/alerts --paginate --jq '.[] | {number, state, dependency: .dependency.package.name, ecosystem: .dependency.package.ecosystem, manifest: .dependency.manifest_path, vulnerable_requirements: .security_vulnerability.vulnerable_version_range, patched_versions: .security_vulnerability.first_patched_version.identifier, severity: .security_advisory.severity, summary: .security_advisory.summary}'
```

If unavailable, ask the user for: package name, ecosystem, manifest path, vulnerable version range, first patched version, severity, advisory summary.

Classify: critical/high first; direct vs transitive; runtime-related alerts that may imply a Python version bump.

For **transitive dependencies**, trace the chain:

```bash
python -m pip show <pkg> && python -m pipdeptree -p <pkg>
# or: uv pip show <pkg> / poetry show --tree
```

### Phase 2 — Create an upgrade plan before editing

For each alert determine: current version, minimum patched version, Python version constraints, direct vs transitive, which package manager is used. Inspect manifest files:

```bash
find . -maxdepth 3 \( -name 'pyproject.toml' -o -name 'requirements*.txt' -o -name 'poetry.lock' -o -name 'uv.lock' -o -name 'Pipfile.lock' -o -name 'setup.py' -o -name 'setup.cfg' -o -name 'tox.ini' -o -name '.python-version' \)
```

Produce a short plan per alert:

```text
Alert: package A current X -> patched >= Y
Manifest: requirements.txt
Likely action: bump direct pin or regenerate lockfile
Python risk: patched version requires Python >= 3.8, repo uses 3.7
Transitive: pulled in by package B >= 2.0; bumping B may resolve it
Changelog review required: yes/no
```

### Phase 3 — Apply minimum dependency changes

Use the repo's existing dependency workflow. Common commands:

```bash
python -m piptools compile requirements.in   # pip-tools
poetry update <package>                       # Poetry
uv lock --upgrade-package <package>           # uv
pipenv update <package>                       # Pipenv
```

If a repo only has `requirements.txt`, edit the direct pin cautiously and install in a local venv.

Commit dependency changes before Phase 5 (the diff-based scripts require committed changes):

```bash
git add -A && git commit -m "bump <package> from X to Y"
git diff --stat
```

Flag noisy lockfile explosions or unrelated dependency changes.

### Phase 4 — Changelog and migration-guide scout

For every version jump, gather official sources. Programmatic sources first:

1. **GitHub Releases API** — `gh api repos/:owner/:repo/releases --paginate --jq '.[] | {tag_name, name, body}'`
2. **PyPI JSON API** — `https://pypi.org/pypi/<package>/<version>/json`
3. **Official migration guide** — project documentation site
4. **Official changelog** — `CHANGELOG.md` or `HISTORY.rst`
5. **Breaking changes** — `https://github.com/<owner>/<repo>/compare/<old-tag>...<new-tag>`

Extract only actionable items: removed APIs, changed defaults, changed exception/validation/serialization behavior, changed transaction/session/resource lifecycle, changed typing/import paths, changed minimum Python version, security-specific guidance.

For each item, create repo-local search patterns. Always map abstract risks to concrete `rg` commands and smoke tests.

**Bad:** "SQLAlchemy changed transaction behavior."
**Good:**

```text
Risk: SQLAlchemy removed implicit autocommit / changed 2.0 execution style.
Searches: session.query, engine.execute, autocommit, commit, rollback, close, sessionmaker, scoped_session
Smoke tests: successful write commits+closes, failed write rolls back+closes, repeated calls don't exhaust connections
```

### Phase 5 — Repo-local impact search

**Important:** Phase 3 changes must be committed before running the diff-based scripts. They compare the base branch against HEAD; no committed changes means an empty diff.

#### Script purposes

| Script | What it does | Key flag |
|---|---|---|
| `dependency-diff` | Shows dependency files changed between branches | `--base` (auto-detects default branch) |
| `risky-call-diff` | Shows risky function calls added/removed in changed `.py` files between branches | `--base` (auto-detects default branch) |
| `risky-patterns` | Scans `.py` files on disk for regex patterns (no git diff) | `--root` (default `.`) |

`dependency-diff` and `risky-call-diff` are **branch-comparison tools** — they need a base ref. `risky-patterns` is a **disk scanner** — it searches the working tree and uses `--root` to scope the directory, not `--base`.

All scripts support `--json` for structured output.

#### Running the scripts

```bash
uv run dependency-diff --json
uv run risky-call-diff --json
uv run risky-patterns --profile sqlalchemy --json
uv run risky-patterns --profile pydantic --profile http --json
uv run risky-patterns --profile python-runtime --profile pytest --json
uv run risky-patterns --pattern 'session\.query' --pattern 'engine\.execute' --json
```

Also run manual grep searches for patterns from Phase 4:

```bash
rg -n "session\.query|engine\.execute|autocommit|commit\(|rollback\(|close\(" .
rg -n "parse_obj|dict\(|json\(|BaseModel|validator|root_validator" .
```

#### AST helper limitations

`risky-call-diff` uses Python AST parsing to detect function calls. It is a **heuristic**, not a semantic analyzer. It **will not** catch:

- **Aliased imports** — `from sqlalchemy import sessionmaker as sm` → `sm()` won't be recognized as `sessionmaker`
- **Indirect calls** — `fn = session.commit; fn()` won't be detected
- **Decorator-based patterns** — `@contextmanager` or `@pytest.fixture` resource lifecycle is invisible to AST walk
- **Chained/composed calls** — `obj.get_session().commit()` only detects the outermost call
- **Dynamic dispatch** — `getattr(obj, 'commit')()` or `__call__` overrides

Treat `risky-call-diff` output as a starting point for investigation, not exhaustive coverage. Always supplement with `risky-patterns` (regex scan) and manual `rg` searches.

#### Cross-referencing outputs

Correlate `dependency-diff` (which dep files changed), `risky-call-diff` (which risky calls appeared/disappeared in changed files), and `risky-patterns` (which patterns exist on disk). A lifecycle call removed in a file NOT in a dependency-changed path is lower-risk than one removed in a file that imports the bumped dependency.

Classify findings:

```text
Changed and likely handled
Changed but suspicious
Untouched but affected by version jump
No local usage found
Unknown / needs manual inspection
```

### Phase 6 — Behavioral smoke-test design

Smoke tests must cover behavior, not just imports. Always consider: success path, failure path, cleanup path, early return path, repeated-call path, serialization round trip, transaction boundaries, empty/null/edge inputs.

For lifecycle-sensitive code, test pairs and cleanup guarantees:

```text
save -> close     open -> close     connect -> close
commit -> close   exception -> rollback -> close
read -> close     write -> flush -> close
```

If the repo has no test suite, create a small local smoke script or pytest file — keep it isolated and easy to remove.

### Phase 7 — Local validation

Run only local checks, preferring the repo's existing commands:

```bash
python --version
python -m pip check
python -m pytest
python -m compileall .
```

For Python 3.7 → 3.10 migrations, also check:

```bash
rg -n "from collections import Mapping|MutableMapping|Sequence" .
rg -n "asyncio\.coroutine|loop=|imp\.|distutils" .
```

If dependency resolution fails or tests cannot pass, abort and reset:

```bash
git checkout -- . && git clean -fd
```

Report the failure in the final risk report and recommend manual resolution.

### Phase 8 — Final report

Always end with this structure (see `checklists/final-report-template.md` for a blank template):

```text
Upgrade branch          — branch name, base branch
Alerts addressed        — package: old -> new, manifest, severity, direct/transitive
Transitive notes        — which direct dep pins the vulnerable package
Files changed           — dependency files, source files, tests/smoke scripts
Changelog risks         — item, local search performed, repo impact
Suspicious findings     — changed risky behavior, untouched affected files, lifecycle changes, missing tests
Local validation        — commands run, result, failures/skips
Merge risk              — Low / Medium / High + reason
Required human checks   — checklist
Suggested PR body       — summary, risk notes, tests run
```

When the user is ready to create the PR:

```bash
git push -u origin <branch-name>
gh pr create --title "..." --body "..."
```

Only run these when the user explicitly asks.

## Package profiles

Use profiles when available, but do not rely on them exclusively. The changelog for the exact version range is still required. Profiles provide general search patterns; correlate them to the exact version jump. A SQLAlchemy profile for 1.x → 2.x is critical; for 2.0.x → 2.0.y patch bumps, trim to deprecation warnings only.

| Profile | When to use | Key risks covered |
|---|---|---|
| `http` | urllib3 1.x→2.x, requests/httpx major bumps | TLS, retry, timeout, session reuse, exception hierarchy |
| `sqlalchemy` | SQLAlchemy 1.x→2.x | `engine.execute`, `session.query` removal, autocommit, Result API |
| `pydantic` | Pydantic 1.x→2.x | `parse_obj`/`dict`/`json` removal, validators, BaseSettings move |
| `pandas` | pandas 1.x→2.x | dtype inference, nullable, deprecated methods, inplace/Copy-on-Write |
| `pytest` | pytest 7.x→8.x major bumps | plugin compatibility, fixture scoping, deprecation→error, discovery |
| `python-runtime` | Python 3.7→3.10+ migration | removed stdlib (`imp`, `distutils`), `collections.abc` move, typing |

Each profile file in `profiles/*.md` contains: purpose, common risks, specific `rg` search commands, smoke test guidance, and version-awareness notes. Read the profile files for full pattern lists.

## Rollback guidance

If the upgrade cannot proceed cleanly:

```bash
git checkout -- . && git clean -fd   # discard uncommitted changes
git checkout main && git branch -D dependabot/<topic>-<date>  # delete branch entirely
```

Report the failure clearly and recommend manual resolution.

## Good agent prompt

```text
Use the Dependabot Alert Upgrade Reviewer skill.

We do not have a PR yet. Start from the current repository state. Do not work on main/master. Create a dedicated upgrade branch if the tree is clean. Inspect Dependabot alerts, choose the smallest safe dependency upgrade, review official changelogs/migration notes for the exact version jump, apply the dependency change using the repo's existing package manager, commit the changes, search changed and unchanged code for affected APIs, add or propose behavior-level smoke tests, run only local validation, and finish with the skill's final risk report.

When multiple alerts exist, batch related alerts on one branch and note any conflicts.

Be especially skeptical of resource lifecycle changes such as save -> close, commit -> rollback -> close, open -> close, connect -> close, and exception cleanup paths.

Do not push or create a PR unless I explicitly ask.
```

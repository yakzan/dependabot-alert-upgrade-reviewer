---
name: dependabot-alert-upgrade-reviewer
description: Python-only. Use when a coding agent needs to address or review Dependabot security alerts in a Python repository (pip, pip-tools, Poetry, uv, Pipenv, setup.py, setup.cfg, or lockfile-based workflows). The protocol creates an isolated upgrade branch, applies the minimum dependency change, checks official changelogs and migration guides for the exact version jump, searches repo-local impact, runs local smoke tests, and produces a skeptical PR risk report. Works with Codex, Copilot CLI, and other terminal coding agents.
---

# Dependabot Alert Upgrade Reviewer

Use this protocol when a coding agent needs to address or review Dependabot alerts. Create a safe, isolated upgrade branch, apply the minimum necessary dependency changes, prove the dependency set can install on the target runtime before committing, inspect changelogs for the exact version jump, produce a skeptical review with repo-specific smoke tests, and prepare a ready-to-push PR.

This is an agent protocol with small deterministic helpers — not an auto-migration framework. The agent may use package managers, Git, local tests, AST/grep scripts, and changelog research, but must not claim safety without evidence.

## Scope

**Python repositories.** The workflow and helper scripts target Python dependency managers (pip, pip-tools, Poetry, uv, Pipenv, setup.py/setup.cfg) and Python-specific migration patterns. Branch setup, changelog research, and the final report are applicable to other ecosystems, but scripts, profiles, and search patterns are Python-specific.

## Prerequisites

Tools the protocol assumes are available on the agent's host:

- `git` — required for branch creation and diff-based scripts.
- Python 3.10+ — required to run the helper scripts.
- `gh` (GitHub CLI) — used for listing Dependabot alerts and (when authorized) creating the PR. Optional: if missing, ask the user for alert details and skip PR creation.
- `rg` (ripgrep) — used in manual searches. `grep -rn` is an acceptable fallback.
- `pipdeptree` — used in Phase 1 for transitive dependency tracing on pip-based projects. Optional for Poetry/uv (use `poetry show --tree` / `uv pip show`).

Missing optional tools are not blockers; degrade gracefully and note the gap in the final report.

## Agent compatibility

This protocol is written for coding agents such as Codex, Copilot CLI, and similar terminal-based agents. Codex can discover the skill from the YAML frontmatter. Agents without skill discovery can be pointed directly at this `SKILL.md` file or given the prompt in `examples/agent-prompt.md`.

Treat `<skill-dir>` as the directory containing this `SKILL.md`. Run bundled helper scripts from the target repository's working directory so Git comparisons and path scans operate on the repository being upgraded, not on the skill package.

## Monorepo and multi-package repos

For repos with multiple Python packages (e.g., `packages/lib-a/pyproject.toml`), handle each manifest separately:

1. Run helper scripts per package directory: `python <skill-dir>/scripts/risky_patterns.py --profile sqlalchemy --root packages/lib-a`
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
python <skill-dir>/scripts/risky_call_diff.py --json
python <skill-dir>/scripts/dependency_diff.py --json
python <skill-dir>/scripts/risky_patterns.py --profile sqlalchemy --json
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

**Never (without explicit user approval):**

1. Work directly on `master`, `main`, or a protected branch.
2. Push, create PRs, or deploy.
3. Run tests or scans against external/shared systems — local validation only.
4. Discard changes (`git restore`, `git checkout --`), clean untracked files (`git clean`), or delete branches.

**Always:**

1. Prefer the smallest dependency change that resolves the alert.
2. Keep unrelated formatting and refactors out of the branch.
3. Inspect both changed files *and* suspicious untouched files affected by the version jump.
4. Map every changelog item to a concrete repo-local search before claiming impact.
5. Treat a Python runtime bump (e.g., 3.7 → 3.10) as a separate risk area.
6. Treat resolver/install success as necessary but not sufficient; optional backends used by the repo still need usage-derived smoke checks.
7. Produce the final risk report and smoke-test checklist at the end.
8. Remember that passing tests are not proof of safety — they are weak evidence.

## Overall workflow

### Phase 0 — Establish safe branch

Inspect Git state:

```bash
git status --short
git branch --show-current
git remote -v
```

If the working tree is dirty, stop and report the dirty files. If the tree is clean, create a dedicated upgrade branch unless already on a clean dedicated non-protected upgrade branch:

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

For each alert determine: current version, minimum patched version, Python version constraints, direct vs transitive, which package manager is used. Skim the breaking-changes section of the official changelog *before* committing to a target version — if the planned bump crosses a major version with breaking lifecycle or API changes, plan for a full Phase 4 scout and budget time accordingly. Inspect manifest and runtime files:

```bash
find . -maxdepth 3 \( -name 'pyproject.toml' -o -name 'requirements*.txt' -o -name 'constraints*.txt' -o -name 'poetry.lock' -o -name 'uv.lock' -o -name 'Pipfile.lock' -o -name 'setup.py' -o -name 'setup.cfg' -o -name 'tox.ini' -o -name '.python-version' -o -name 'runtime.txt' -o -name 'Dockerfile' -o -name '*.yml' -o -name '*.yaml' \)
```

Before editing, make the upgrade constraint-aware:

1. Identify the **security floor** from the advisory: first patched version or minimum safe range.
2. Intersect it with **runtime/platform compatibility**: Python version, OS/base image, architecture, build toolchain, wheels vs source builds, and existing pins.
3. Run a **resolver preflight** with the repo's package manager to discover coupled upgrades before attempting a full install.
4. Scan for **optional dependency features** used by the repo, because metadata checks often miss them:

```bash
python <skill-dir>/scripts/risky_patterns.py --profile optional-deps --json
rg -n "read_excel|to_excel|ExcelWriter|read_sql|to_sql|read_parquet|to_parquet|openpyxl|xlrd|xlsxwriter|pyarrow|fastparquet|psycopg2|mysqlclient" .
```

Produce a short plan per alert:

```text
Alert: package A current X -> patched >= Y
Manifest: requirements.txt
Security floor: >= Y
Runtime/platform risk: patched version requires Python >= 3.8, repo uses 3.7
Transitive: pulled in by package B >= 2.0; bumping B may resolve it
Coupled upgrades likely: package C must move because resolver rejects old pin
Optional feature risks: pandas Excel path needs openpyxl/xlrd/xlsxwriter smoke coverage
Likely action: bump direct pin or regenerate lockfile
Changelog review required: yes/no
```

### Phase 3 — Apply minimum dependency changes and create checkpoint

Use the repo's existing dependency workflow. Common commands:

```bash
python -m piptools compile requirements.in   # pip-tools
poetry update <package>                       # Poetry
uv lock --upgrade-package <package>           # uv
pipenv update <package>                       # Pipenv
```

If a repo only has `requirements.txt`, edit the direct pin cautiously and install in a local venv.

Before committing, run a short **installability gate** in an isolated local environment using the repo's normal workflow:

```bash
python -m pip install -r requirements.txt     # pip/requirements example
python -m pip check
uv pip install -r requirements.txt            # uv/requirements example
uv pip check
```

Use equivalent Poetry/Pipenv commands when those tools own the environment. If dependency resolution, install, or metadata checks fail, **do not commit**. Mark the upgrade blocked, record the failing command, the resolver/install error, and the smallest plausible remediation (for example: raise an old pandas/numpy/psycopg2 pin to a version that supports the repo's Python runtime).

Only after resolution, install, and metadata checks are green, create a local **checkpoint commit**. This is a review anchor for Phase 5, not a final/push-ready commit. It may be kept, amended, or dropped after changelog review and smoke testing.

```bash
git add -A && git commit -m "bump <package> from X to Y"
git diff --stat
```

Flag noisy lockfile explosions or unrelated dependency changes.

If Phase 4 later reveals the planned bump is riskier than expected (e.g., a removed API the repo depends on heavily, or a runtime requirement the project can't meet), return to Phase 2 and revise the plan — pick a smaller patched version, take a different transitive route, or split the work into multiple branches — before continuing.

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

**Important:** Phase 3 changes must be checkpoint-committed before running the diff-based scripts. They compare the base branch against HEAD; no committed changes means an empty diff. If Phase 3 was blocked by resolver/install failure, skip the diff scripts and report the blocker instead of manufacturing a commit.

#### Script purposes

| Script | What it does | Key flag |
|---|---|---|
| `dependency-diff` | Shows dependency files changed between branches | `--base` (auto-detects default branch) |
| `risky-call-diff` | Shows risky function calls added/removed in changed `.py` files between branches | `--base` (auto-detects default branch) |
| `risky-patterns` | Scans `.py` files on disk for regex patterns (no git diff) | `--root` (default `.`) |

`dependency-diff` and `risky-call-diff` are **branch-comparison tools** — they need a base ref. `risky-patterns` is a **disk scanner** — it searches the working tree and uses `--root` to scope the directory, not `--base`.

All scripts support `--json` for structured output.

#### Running the scripts

Prefer bundled script paths when this skill package is separate from the target repository. If the helper package has been installed into the target repo's environment, equivalent entry points such as `uv run dependency-diff --json` are also acceptable.

```bash
python <skill-dir>/scripts/dependency_diff.py --json
python <skill-dir>/scripts/risky_call_diff.py --json
python <skill-dir>/scripts/risky_patterns.py --profile sqlalchemy --json
python <skill-dir>/scripts/risky_patterns.py --profile pydantic --profile http --json
python <skill-dir>/scripts/risky_patterns.py --profile python-runtime --profile pytest --json
python <skill-dir>/scripts/risky_patterns.py --profile optional-deps --json
python <skill-dir>/scripts/risky_patterns.py --pattern 'session\.query' --pattern 'engine\.execute' --json
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
- **Same-name functions in one file** — two methods named `save` on different classes (or two `__init__`s) are pooled into a single diff entry by name. Removed or added calls can appear attributed to the wrong overload. When a file defines multiple functions sharing a name, manually re-inspect that file rather than trusting the diff line-for-line.

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

Smoke tests must cover behavior, not just installs or imports. Always consider: success path, failure path, cleanup path, early return path, repeated-call path, serialization round trip, transaction boundaries, empty/null/edge inputs.

Derive smoke tests from the repo-local usage found in Phase 5. For optional dependency features, verify both the backend import and a tiny feature path. Examples:

```text
pandas read_excel / ExcelWriter -> import openpyxl/xlrd/xlsxwriter and read/write a tiny .xlsx
pandas read_sql / to_sql        -> import sqlalchemy and the configured DB driver; exercise a local or mocked query path
pandas parquet/feather/orc      -> import pyarrow or fastparquet and round-trip a tiny frame if used
HTTP clients with SOCKS/proxy   -> import socks/proxy extras and exercise local construction/config parsing
database adapters               -> import psycopg2/mysqlclient/asyncpg drivers used by configured URLs
```

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

Also run the checkpoint-gate commands and the usage-derived optional dependency checks selected in Phase 6. A passing `pip check` does not prove optional extras are present; if the repo uses `read_excel`, `ExcelWriter`, parquet, SQL engines, or native database drivers, verify those exact paths locally.

For Python 3.7 → 3.10 migrations, also check:

```bash
rg -n "from collections import Mapping|MutableMapping|Sequence" .
rg -n "asyncio\.coroutine|loop=|imp\.|distutils" .
```

If dependency resolution fails or tests cannot pass, stop. Report the failure, current Git state, and the cleanup commands that would discard the upgrade attempt. Do not run cleanup commands such as `git restore`, `git clean`, or branch deletion without explicit user approval.

### Phase 8 — Final report

Always end with the final risk report. Fill in `checklists/final-report-template.md` — it is the canonical structure (upgrade branch, alerts addressed, files changed, changelog risks reviewed, suspicious findings, local validation, merge risk + reason, required human checks, suggested PR body). Do not invent a different shape.

When the user is ready to create the PR:

```bash
git push -u origin <branch-name>
gh pr create --title "..." --body "..."
```

Only run these when the user explicitly asks.

## Package profiles

Use profiles when available, but do not rely on them exclusively. The changelog for the exact version range is still required. Profiles provide general search patterns; correlate them to the exact version jump. A SQLAlchemy profile for 1.x → 2.x is critical; for 2.0.x → 2.0.y patch bumps, trim to deprecation warnings only.

| Profile | Reference file | When to use | Key risks covered |
|---|---|---|---|
| `http` | `profiles/requests-urllib3-httpx.md` | urllib3 1.x→2.x, requests/httpx major bumps | TLS, retry, timeout, session reuse, exception hierarchy |
| `sqlalchemy` | `profiles/sqlalchemy.md` | SQLAlchemy 1.x→2.x | `engine.execute`, `session.query` removal, autocommit, Result API |
| `pydantic` | `profiles/pydantic.md` | Pydantic 1.x→2.x | `parse_obj`/`dict`/`json` removal, validators, BaseSettings move |
| `pandas` | `profiles/pandas.md` | pandas 1.x→2.x | dtype inference, nullable, deprecated methods, inplace/Copy-on-Write |
| `optional-deps` | Use with relevant package profile | Repos using optional integration paths | pandas Excel/SQL/parquet backends, DB drivers, SOCKS/proxy extras |
| `pytest` | `profiles/pytest.md` | pytest 7.x→8.x major bumps | plugin compatibility, fixture scoping, deprecation→error, discovery |
| `python-runtime` | `profiles/python-runtime.md` | Python 3.7→3.10+ migration | removed stdlib (`imp`, `distutils`), `collections.abc` move, typing |

Each profile file contains: purpose, common risks, specific `rg` search commands, smoke test guidance, and version-awareness notes. Read the relevant profile files for full pattern lists. The helper script also has `lifecycle` and `optional-deps` profiles without separate reference files because their behavior-level guidance lives in Phase 6.

## Rollback guidance

If the upgrade cannot proceed cleanly, report what happened and ask before discarding anything. Suggested cleanup commands may include:

```bash
git restore .                         # discard tracked-file changes
git clean -fd                         # delete untracked files
git checkout <base-branch>
git branch -D dependabot/<topic>-<date>
```

Only run these after explicit user approval.

## General coding-agent prompt

For agents without skill discovery, point them at `examples/agent-prompt.md` — that file is the canonical bootstrap prompt and includes fork/upstream handling and the skill-discovery hint. Do not maintain a second copy here.

Use the Dependabot Alert Upgrade Reviewer skill.

We do not have a PR yet. Start from the current repository state. Do not work on main/master. Create a dedicated non-master branch for the selected Dependabot alert(s). If this repo is a fork, preserve the fork/upstream setup and do not push unless asked.

Inspect Dependabot alerts, choose the smallest safe dependency upgrade, review official changelogs/migration notes for the exact version jump, apply the dependency change using the repo's existing package manager, commit the changes, search changed and unchanged code for affected APIs, add or propose behavior-level smoke tests, run only local validation, and finish with the skill's final risk report.

When multiple alerts exist, batch related alerts on one branch and note any conflicts.

Be especially skeptical of resource lifecycle changes such as save -> close, commit -> rollback -> close, open -> close, connect -> close, and exception cleanup paths.

Do not push or create a PR unless I explicitly ask.
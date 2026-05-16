Use the Dependabot Alert Upgrade Reviewer skill.

We do not have a PR yet. Start from the current repository state. Do not work on main/master. If the working tree is clean, create a dedicated non-master branch for the selected Dependabot alert. If this repo is a fork, preserve the fork/upstream setup and do not push unless asked.

Inspect Dependabot alerts, choose the smallest safe dependency upgrade, review official changelogs/migration notes for the exact version jump, apply the dependency change using the repo's existing package manager, search changed and unchanged code for affected APIs, add or propose behavior-level smoke tests, run only local validation, and finish with the skill's final risk report.

Be especially skeptical of resource lifecycle changes such as save -> close, commit -> rollback -> close, open -> close, connect -> close, and exception cleanup paths.

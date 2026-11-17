# Contributing

## Branch and commit conventions

| Item | Format | Example |
| --- | --- | --- |
| Branch name | `AGT-<id>-<message>` (id is a number; message is lowercase letters, digits and hyphens) | `AGT-21-login-page` |
| Commit message | `AGT-<id> <message>` | `AGT-21 Added login page` |
| Pull request title | `AGT-<id> <message>` (used as the commit message when squash-merging) | `AGT-21 Added login page` |

- `main` is the only branch exempt from the branch naming rule.
- Merge, revert, `fixup!` and `squash!` commits are exempt from the commit message rule.
- Every commit on a pull request must follow the format. To fix a wrong message, use `git commit --amend` (last commit) or `git rebase -i` (older commits), then force-push your branch.
- To rename a branch: `git branch -m AGT-21-login-page`.

## Enabling the local checks

The rules are enforced by Git hooks in [`.githooks/`](../.githooks). Enable them once per clone:

```bash
git config core.hooksPath .githooks
```

- `pre-commit` and `pre-push` reject branches that do not match the branch format.
- `commit-msg` rejects commit messages that do not match the commit format.

The same rules are checked on every pull request by the `naming / check` GitHub Actions workflow ([`.github/workflows/naming.yml`](../.github/workflows/naming.yml)). Skipping the local hooks with `--no-verify` will not get around it: the pull request cannot be merged until the check passes.

# Repository workflow

- Use `main` for all subsequent work in this repository. Do not create feature
  branches or separate Git worktrees unless the user explicitly requests one.
- Before pushing, confirm the current branch is `main`, preserve remote changes,
  and run the checks appropriate to the change.
- Docker Image CI publishes `tano26/kasumi_bot:latest` only after a push to `main`.
  A local commit or a commit on another branch does not update the deployed image.

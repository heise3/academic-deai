# GitHub releases

This directory is a standalone source repository for Academic DeAI 3.0.0. The release archive contains the directory and its runtime resources, excluding Git metadata, caches, private data, and local validation environments.

## Publication settings

- Public repository: [heise3/academic-deai](https://github.com/heise3/academic-deai).
- Project license: MIT, chosen under the maintainer's authorization.
- Humanizer attribution and its original MIT notice are retained.
- The repository publishes this self-contained skill and its validation resources. Keep private manuscripts and local execution artifacts outside the repository.

## Validate

From this directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_package.py .
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
git diff --check
```

Review [validation.md](docs/validation.md) for the actual tested environments, independent evaluation, and unverified limits.

## Publish a version

For a fresh local checkout without origin, configure the repository URL; then push the validated branch:

```sh
git remote add origin https://github.com/heise3/academic-deai.git
git push -u origin main
```

Clones already have origin. Inspect an existing origin before replacing it. Commit the intended release files and confirm the working tree is clean before pushing.

After the push, check the [GitHub Actions run](https://github.com/heise3/academic-deai/actions). Use the version from VERSION for a release tag and attach an archive verified against that commit. Local tests alone do not establish remote CI success.

## Release description

Academic DeAI 3.0.0 adds context-aware structural editing, author-sample guidance, academic exceptions for weak style signals, and explicit claim-level fidelity review. It keeps existing text audit tools, makes verification proportional to the edit, and includes portable package checks and source attribution.

No detector-score or general writing-quality gain is claimed.

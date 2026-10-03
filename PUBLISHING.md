# GitHub publication preparation

This directory is a standalone source repository for Academic DeAI 3.0.0. The release archive contains the directory and its runtime resources, excluding Git metadata, caches, private data, and local validation environments.

## Publication settings

- Repository name: academic-deai; public visibility is recommended for this reusable skill.
- Project license: MIT, chosen under the maintainer's authorization.
- Humanizer attribution and its original MIT notice are retained.
- Intended destination: `heise3/academic-deai`, using the connected GitHub account. The origin URL is configured locally; no remote repository has been created or uploaded.

## Validate

From this directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_package.py .
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
git diff --check
```

Review [validation.md](docs/validation.md) for the actual tested environments, independent evaluation, and unverified limits.

## Publish when the destination is chosen

If a new repository is desired, create an empty repository through GitHub or the authenticated GitHub CLI. Then use the actual URL:

```sh
git remote add origin https://github.com/heise3/academic-deai.git
git push -u origin main
```

This prepared local repository already has origin configured to that URL. For this copy, create the empty remote repository and run only the push command after publication is requested. For a fresh clone without origin, use the add command. Inspect an existing origin before replacing it.

After an authorized push, use the version from VERSION for a release tag and attach the validated archive if desired. The local CI workflow becomes active only after publication; local tests do not imply a GitHub Actions run.

## Release description

Academic DeAI 3.0.0 adds context-aware structural editing, author-sample guidance, academic exceptions for weak style signals, and explicit claim-level fidelity review. It keeps existing text audit tools, makes verification proportional to the edit, and includes portable package checks and source attribution.

No detector-score or general writing-quality gain is claimed.

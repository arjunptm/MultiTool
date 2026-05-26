# Releases

Windows releases are published through GitHub Actions when a version tag is
pushed.

## Tagged Release Flow

Confirm `main` is ready:

```bash
git checkout main
git pull
git status --short --branch
```

Create and push a version tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Tags should start with `v`, such as `v0.1.0`.

## GitHub Actions

The workflow lives at `.github/workflows/release-windows.yml`.

When a matching tag is pushed, the workflow:

1. Checks out the repository.
2. Sets up Python.
3. Installs `requirements-build.txt`.
4. Builds the app with PyInstaller.
5. Zips `dist/MultiTool/`.
6. Creates a GitHub Release.

The release asset is named like:

```text
MultiTool-v0.1.0-windows.zip
```

Normal pushes to `main` do not create releases.

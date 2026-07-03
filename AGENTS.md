# AGENTS.md

This file gives AI coding agents a short, predictable entry point for working
on MultiTool. For fuller project history, workflow details, and collaboration
rules, read `docs/ai-collaboration.md`.

## Project Basics

- MultiTool is a Windows-only Python desktop app built with PySide6.
- The active Codex workspace for this project is `W:\Codex Projects\MultiTool`.
- `W:\multitool` is an older legacy copy and should be left untouched unless
  the user explicitly asks to inspect or sync it.
- The app entry point is `app.py`.
- Source code lives under `app/`.
- Shared UI components live under `app/ui/`.
- Individual tools live under `app/tools/<tool_name>/`.

## Development Commands

```bash
source .venv/Scripts/activate
python app.py
python -m compileall app
```

Install runtime dependencies with:

```bash
pip install -r requirements.txt
```

Install packaging dependencies with:

```bash
pip install -r requirements-build.txt
```

## Coding Guidelines

- Use 2-space indentation in Python.
- Prefer direct, readable code over broad abstractions.
- Reuse shared widgets from `app/ui/` before creating new tool-specific UI.
- Keep tool-specific behavior inside the relevant `app/tools/<tool_name>/`
  folder.
- Keep runtime dependencies in `requirements.txt`.
- Keep packaging dependencies in `requirements-build.txt`.

## Git And Issue Workflow

- Check related open GitHub issues before meaningful changes.
- Ask whether a change should be pushed directly or go through a branch and PR
  when the right path is unclear.
- Default to a feature branch and PR for features, bugs, automation,
  packaging, or changes with meaningful review value.
- Before committing, check `git status` and `git diff`.
- At wrap-up, state whether changes are local-only, committed, pushed, or
  awaiting a PR.

## Verification

- Run `python -m compileall app` after Python source changes.
- For workflow or automation changes, mention that GitHub Actions will run after
  pushing. Check or wait for CI only when asked, when the task depends on it, or
  when the change is high risk.

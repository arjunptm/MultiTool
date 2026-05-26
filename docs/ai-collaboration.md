# AI Collaboration

This project is designed to work well with AI-assisted development while still
keeping the repository understandable to a human maintainer.

## Project Principles

- Understand the existing architecture before planning or coding.
- Keep the app modular and framework-first.
- Reuse shared UI from `app/ui/` before creating new widgets.
- Avoid broad rewrites unless explicitly requested.
- Prefer practical, beginner-friendly code over clever abstractions.
- Keep changes focused and easy to review.

## User Preferences

- The user usually uses Git Bash, not PowerShell. Prefer Git Bash syntax in
  written instructions unless PowerShell is specifically requested.
- The project runs from `W:\MultiTool`.
- Use 2-space indentation in Python.
- Keep explanations practical and beginner-friendly.

Git Bash activation:

```bash
source .venv/Scripts/activate
python app.py
```

## Issue-First Workflow

For meaningful features, bugs, polish tasks, refactors, or future ideas, check
existing GitHub issues before planning or coding.

Useful commands:

```bash
gh issue list --state open --limit 100
gh issue list --state all --search "<keywords>"
```

If a relevant issue exists, explain how the request fits it and whether the
existing issue should be used, refined, split, or superseded.

If no suitable issue exists, create a focused issue with the goal and acceptance
criteria.

## Git Workflow

Do not work directly on `main` for feature development. Use feature branches
prefixed with `AI-`, for example:

```bash
git checkout -b AI-sign-pdf-tool
```

Before committing, check:

```bash
git status
git diff
```

Prefer one clear, meaningful commit per coherent feature or fix unless the task
naturally needs multiple commits.

Keep `CHANGELOG.md` updated for notable changes. Small internal-only edits do
not need entries unless they affect users, releases, packaging, or project
management.

Use pull requests before merging feature branches into `main`, even for solo
work, because PRs provide a useful review checkpoint.

## GitHub Notes

The repository remote is:

```text
git@github.com:arjunptm/MultiTool.git
```

GitHub CLI has been used for issues and pull requests in prior sessions. When
creating or editing GitHub issue or PR bodies that contain markdown backticks,
tag patterns like `v*`, or other shell-sensitive characters, use a safe
multiline body approach such as a PowerShell single-quoted here-string assigned
to `$body`, then pass `--body $body`.

## Current Architecture Reminder

- `app.py`: application entry point.
- `app/main_window.py`: `QStackedWidget` navigation between home and tools.
- `app/core/tool_registry.py`: central registry of tools.
- `app/ui/`: shared UI components and styling.
- `app/tools/<tool_name>/page.py`: tool UI and behavior.
- `app/tools/<tool_name>/service.py`: optional tool-specific logic.

Every tool inherits from `ToolPageBase` and is registered with a
`ToolDefinition`.

## UI Reuse Rules

Before creating new UI components:

1. Check `app/ui/` for existing reusable widgets.
2. Reuse matching components instead of duplicating them.
3. Move patterns into `app/ui/` when they become shared by multiple tools.
4. Keep genuinely tool-specific UI inside the relevant tool folder.

Examples:

- Use `ReorderableFileListWidget` for drag-and-drop file ordering.
- Use `FileSelectionPanel` for file list, add/remove buttons, and count text.

## Completed AI-Assisted Work

The first AI-assisted feature added the Sign PDF tool.

- Feature branch: `AI-sign-pdf-tool`
- Issue: `#1 Add visual PDF signing tool`
- Pull request: `#2 Add visual PDF signing tool`
- PR #2 was merged into `main`.

The completed tool supports:

- opening one PDF
- navigating pages
- uploading a signature image
- drawing a signature with the mouse
- moving the signature visually
- resizing via edge handles
- proportional scaling via the bottom-right handle
- rotating via a top handle
- saving a signed copy without overwriting the original

This is visual signing only, not cryptographic certification.

## Packaging History

- Issue #5 covered local/manual Windows executable packaging and is closed.
- Issue #14 covered tagged GitHub Actions release automation and is closed.
- The first automated release tag, `v0.1.0`, published
  `MultiTool-v0.1.0-windows.zip`.
- Issue #17 tracks future evaluation of macOS/Linux support.

Useful local packaging commands:

```bash
source .venv/Scripts/activate
pip install -r requirements-build.txt
pyinstaller --noconfirm --clean MultiTool.spec
./dist/MultiTool/MultiTool.exe
```

## End-Of-Session Wrap-Up

When the user asks for a wrap-up check:

- Check `git status` and summarize uncommitted, staged, and untracked changes.
- State clearly whether completed changes are local-only, committed, pushed, or
  awaiting a pull request.
- If changes were committed, include the latest commit hash and message.
- If changes should be pushed or opened as a pull request, recommend that as the
  next action and ask before doing it unless the user already requested it.
- Review whether README, docs, or `CHANGELOG.md` need updates for the completed
  work.
- Add an `Unreleased` changelog entry for user-facing changes, repo management
  changes, packaging changes, or notable fixes.
- Run appropriate lightweight verification commands when practical.
- For workflow or automation changes, check or recommend checking the relevant
  GitHub Actions run after the push.
- Check related GitHub issues, pull requests, and action runs for status or
  follow-up notes.
- Prompt before committing, pushing, creating a PR, merging, closing issues, or
  making other state-changing GitHub/Git actions unless already requested.
- Leave the user with what is done, what remains, and the recommended next
  action.

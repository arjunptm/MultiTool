# Changelog

All notable changes to MultiTool will be documented in this file.

This project uses version tags such as `v0.1.0` for Windows releases. See
[docs/releases.md](docs/releases.md) for the release process.

## Unreleased

## v0.2.0 - 2026-07-03

### Added

- Added multi-signer support to Sign PDF.
- Added multiple signature placements across PDF pages.
- Added text fields for dates and other short PDF annotations.
- Added duplicate placement support for repeated signatures or text fields.
- Added undo for the latest stroke in the drawn signature dialog.

### Changed

- Reworked the Sign PDF layout with a scrollable setup panel, right-side
  placements panel, and shorter-screen-friendly preview sizing.
- Updated Sign PDF save behavior to write all visual signatures and text fields
  in one output pass.

### Fixed

- Fixed text fields disappearing from preview or export in some layouts.
- Fixed selected overlay handles painting over unrelated text fields.

### Added

- Added an MIT `LICENSE` file.
- Added README badges for release status, latest release, Python version,
  Windows platform support, and license.
- Added focused project documentation under `docs/`.
- Added AI collaboration notes under `docs/ai-collaboration.md`.
- Added lightweight CI checks for pushes and pull requests.
- Added `AGENTS.md` as a standard entry point for AI coding agents.

### Changed

- Shortened `README.md` into a concise overview with links to detailed docs.
- Moved long-form project, packaging, release, and roadmap details into
  dedicated documentation files.
- Clarified AI collaboration guidance for wrap-ups, direct pushes, pull
  requests, issue follow-up, and CI result checks.

### Fixed

- Replaced copied placeholder code in `app/tools/bulk_rename/__init__.py` with a
  simple package marker.

## v0.1.0 - 2026-05-25

### Added

- Added the initial Windows release workflow for tagged releases.
- Added PyInstaller packaging support with `MultiTool.spec`.
- Added the Combine PDFs tool.
- Added the Sign PDF tool for visual signatures.
- Added placeholder pages for Resize Images and Bulk Rename Files.
- Added shared UI structure for home navigation, tool pages, file selection, and
  reusable widgets.

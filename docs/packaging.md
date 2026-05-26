# Packaging

MultiTool uses PyInstaller for Windows packaging. The first packaging target is
a folder-based portable app, not a single-file executable or installer.

## Build Dependencies

Packaging dependencies live in `requirements-build.txt`, which includes normal
runtime dependencies plus PyInstaller.

```bash
pip install -r requirements-build.txt
```

## Build Command

```bash
pyinstaller --noconfirm --clean MultiTool.spec
```

The packaged application is created in:

```text
dist/MultiTool/
```

Run the packaged executable with:

```text
dist/MultiTool/MultiTool.exe
```

## Build Recipe

`MultiTool.spec` is the committed PyInstaller build recipe. Keep packaging
configuration there instead of relying on one-off local commands.

## Generated Folders

These folders are generated and should not be committed:

- `.venv/`
- `build/`
- `dist/`
- `__pycache__/`

## Sharing A Local Build

For release sharing, zip the full `dist/MultiTool/` folder so the executable and
supporting files stay together.

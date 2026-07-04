# PyInstaller spec for the one-click Mail Agent backend binary.
#
# Build (from the repo root or backend/):
#     pip install ./backend pyinstaller
#     pyinstaller backend/mailagent.spec
#
# Produces a single-file console executable named "mailagent" in dist/. CI
# renames it per-OS (mailagent-windows.exe / mailagent-macos / mailagent-linux).
# The console window is intentional: it doubles as the "keep this open" signal.

import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# SPECPATH is the directory containing this spec file (backend/). Putting it on
# pathex makes the `app` package importable during the build.
backend_dir = SPECPATH  # noqa: F821  (injected by PyInstaller)

# lingua ships its language models as package data — required at runtime because
# translation.py builds LanguageDetectorBuilder.from_all_languages().
datas = collect_data_files("lingua")
# certifi CA bundle for the anthropic/openai HTTPS clients (usually auto-picked
# up via hooks; included explicitly to be safe).
datas += collect_data_files("certifi")

hiddenimports = [
    # uvicorn resolves these workers dynamically, so PyInstaller can't see them.
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
    "uvicorn.loops.auto",
    # async SQLite driver, imported by URL not by name.
    "aiosqlite",
    # OS keyring backends (only the current platform's is used at runtime).
    "keyring.backends.Windows",
    "keyring.backends.macOS",
    "keyring.backends.SecretService",
    "keyring.backends.chainer",
]
# anthropic/openai pull in submodules lazily; collecting them avoids
# missing-module errors at runtime.
hiddenimports += collect_submodules("anthropic")
hiddenimports += collect_submodules("openai")

# Not used at runtime (DB init uses SQLAlchemy create_all, not Alembic). Excluded
# to trim the binary.
excludes = ["alembic", "pytest", "tkinter"]


a = Analysis(
    [os.path.join(backend_dir, "launch.py")],
    pathex=[backend_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="mailagent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

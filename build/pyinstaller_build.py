"""Helper script to build GUI and PRO executables with PyInstaller."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# --- Pre-initialization: Set up paths and environment ---

# Define project structure relative to this script's location
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
DIST_DIR = PROJECT_ROOT / "dist"
WORK_DIR = PROJECT_ROOT / "build" / "pyinstaller"

# Change working directory to the project root. This is CRUCIAL.
# It ensures that all relative paths and module lookups are consistent,
# especially for PyInstaller's module collection.
os.chdir(PROJECT_ROOT)

# Add the 'src' directory to sys.path. This allows Python and PyInstaller
# to find the `keyboard_simulator` package.
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Now that paths are set up, we can safely import from PyInstaller
try:
    from PyInstaller.utils.hooks import collect_submodules
except ImportError:
    print(
        "PyInstaller is not installed or not found. Please run 'pip install pyinstaller' or 'pip install .[build]'",
        file=sys.stderr,
    )
    sys.exit(1)

# --- Configuration ---

VARIANT_CONFIG = {
    "gui": {
        "script": PROJECT_ROOT / "keyboard_simulator_gui.py",
        "name": "KeyboardSimulatorGUI",
        "description": "标准版 GUI (SendInput 后端)",
        "hidden_imports": ["tkinterdnd2", "keyboard"],
        "datas": [],
    },
    "pro": {
        "script": PROJECT_ROOT / "keyboard_simulator_pro.py",
        "name": "KeyboardSimulatorPro",
        "description": "PRO 版 (Interception 驱动)",
        "hidden_imports": ["tkinterdnd2", "keyboard", "interception"],
        "datas": [],
    },
}


def _generate_spec_file(variant: str) -> Path:
    """Generates a .spec file for the given build variant."""
    config = VARIANT_CONFIG[variant]
    spec_file_path = WORK_DIR / f"{config['name']}.spec"

    # --- Module Discovery ---
    # Discover all submodules of the main package automatically
    hidden_imports = set(config["hidden_imports"])

    # Diagnostic print to see what submodules are found
    ks_submodules = collect_submodules("keyboard_simulator")
    print(f"Discovered keyboard_simulator submodules: {ks_submodules}")
    hidden_imports.update(ks_submodules)

    # Also collect submodules for other key packages
    hidden_imports.update(collect_submodules("tkinterdnd2"))
    if "interception" in hidden_imports:
        hidden_imports.update(collect_submodules("interception"))

    # PyInstaller requires paths to be strings. By ONLY including SRC_DIR,
    # we force PyInstaller to look for the `keyboard_simulator` package inside `src`,
    # avoiding the conflict with the `keyboard_simulator.py` shim at the project root.
    pathex = [str(SRC_DIR)]

    # Convert datas to the correct format for the spec file
    datas_formatted = [f"('{src}', '{dest}')" for src, dest in config["datas"]]

    # 使用 repr() 来获取一个安全的、带正确转义的路径字符串
    script_path_repr = repr(str(config["script"]))

    spec_content = f"""
# -*- mode: python ; coding: utf-8 -*-

import sys
sys.setrecursionlimit(5000)

block_cipher = None

a = Analysis(
    [{script_path_repr}],
    pathex={pathex!r},
    binaries=[],
    datas=[{", ".join(datas_formatted)}],
    hiddenimports={sorted(list(hidden_imports))!r},
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{config["name"]}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # You can specify an icon path here, e.g., 'assets/icon.ico'
)
"""
    spec_file_path.parent.mkdir(parents=True, exist_ok=True)
    spec_file_path.write_text(spec_content, encoding="utf-8")
    print(f"Generated spec file: {spec_file_path}")
    return spec_file_path


def _build_with_spec(spec_file: Path, variant: str):
    """
    Builds the executable using the generated .spec file.
    This function includes a critical workaround for the module name conflict.
    """
    config = VARIANT_CONFIG[variant]
    shim_script_path = PROJECT_ROOT / f"{config['script'].stem}.py"
    temp_shim_path = shim_script_path.with_name(f"_{shim_script_path.name}")

    try:
        # --- CRITICAL WORKAROUND ---
        # Temporarily rename the root-level shim script (`keyboard_simulator_gui.py` or
        # `keyboard_simulator_pro.py`) before running PyInstaller. This prevents
        # PyInstaller's analysis phase from getting confused by the name conflict
        # between the shim and the actual package (`src/keyboard_simulator`).
        # By renaming it, we ensure that when PyInstaller sees `import keyboard_simulator`,
        # it correctly resolves to the package in `src/` because `pathex` points there.
        if shim_script_path.exists():
            print(f"Temporarily renaming '{shim_script_path.name}' to '{temp_shim_path.name}' to avoid import conflicts.")
            shim_script_path.rename(temp_shim_path)

        # Now, run PyInstaller with the correct entry script path
        command = [
            sys.executable,
            "-m",
            "PyInstaller",
            str(spec_file),
            "--noconfirm",
            "--distpath",
            str(DIST_DIR),
            "--workpath",
            str(WORK_DIR),
        ]
        print(f"Running PyInstaller for {config['name']}...")
        subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8")
        print(f"Successfully built {config['name']}.exe")

    except subprocess.CalledProcessError as e:
        print(f"--- PyInstaller Build Failed for {variant} ---", file=sys.stderr)
        print(f"Return Code: {e.returncode}", file=sys.stderr)
        print("\n--- STDOUT ---", file=sys.stderr)
        print(e.stdout, file=sys.stderr)
        print("\n--- STDERR ---", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        print("------------------------------------------", file=sys.stderr)
        # Re-raise the exception to halt the script
        raise
    finally:
        # --- Cleanup ---
        # Always rename the shim script back to its original name,
        # whether the build succeeded or failed.
        if temp_shim_path.exists():
            print(f"Renaming '{temp_shim_path.name}' back to '{shim_script_path.name}'.")
            if shim_script_path.exists():
                shim_script_path.unlink()  # Remove any leftover file if it exists
            temp_shim_path.rename(shim_script_path)


def _ensure_pyinstaller_available() -> None:
    """Checks if PyInstaller is installed."""
    if shutil.which("pyinstaller") is None:
        raise SystemExit(
            "PyInstaller not detected. Please run `pip install pyinstaller` or install with `.[build]` dependencies."
        )


def _build_variant(variant: str) -> None:
    """Builds a single variant using its generated .spec file."""
    config = VARIANT_CONFIG[variant]
    script_path = config["script"]
    if not script_path.exists():
        raise FileNotFoundError(f"Entry script not found: {script_path}")

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    shim_file = PROJECT_ROOT / "keyboard_simulator.py"
    shim_backup = PROJECT_ROOT / "keyboard_simulator.py.bak"

    try:
        # Temporarily rename the conflicting shim file to avoid import conflicts
        if shim_file.exists():
            print(f"Temporarily renaming conflicting file: {shim_file} -> {shim_backup}")
            shim_file.rename(shim_backup)

        spec_file = _generate_spec_file(variant)

        command = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--distpath",
            str(DIST_DIR),
            "--workpath",
            str(WORK_DIR),
            str(spec_file),
        ]

        print("Executing PyInstaller command:\n" + " ".join(f'"{c}"' for c in command))

        # Set PYTHONPATH for the subprocess to ensure it finds modules inside 'src'.
        # This is crucial because the sys.path of the build script is not inherited.
        env = os.environ.copy()
        env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")

        subprocess.run(command, check=True, env=env, shell=False)

    finally:
        # Restore the original shim file
        if shim_backup.exists():
            print(f"Restoring original file: {shim_backup} -> {shim_file}")
            if shim_file.exists():
                shim_file.unlink()
            shim_backup.rename(shim_file)


def main() -> None:
    """Main function to parse arguments and run the build."""
    parser = argparse.ArgumentParser(
        description="Build standalone executables for keyboard_simulator using PyInstaller.",
    )
    parser.add_argument(
        "variant",
        choices=["gui", "pro", "all"],
        help="Select the build variant: gui, pro, or all.",
    )
    args = parser.parse_args()

    _ensure_pyinstaller_available()

    targets = VARIANT_CONFIG.keys() if args.variant == "all" else [args.variant]
    for variant in targets:
        print(f"\\n==> Building {variant.upper()} - {VARIANT_CONFIG[variant]['description']}")
        _build_variant(variant)
        print(f"✅ Build complete for {variant.upper()}. Output is in: {DIST_DIR}")


if __name__ == "__main__":
    main()

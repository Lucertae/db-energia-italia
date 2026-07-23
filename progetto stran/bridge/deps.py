"""Optional dependency helpers for bridge adapters."""
from __future__ import annotations

import importlib
import shutil
import subprocess
import sys
from typing import Any


def try_import(module: str, pip_name: str | None = None) -> Any | None:
    try:
        return importlib.import_module(module)
    except ImportError:
        return None


def pip_install_hint(pip_name: str) -> str:
    return f"pip install {pip_name}"


def have_pip_package(name: str) -> bool:
    try:
        import importlib.metadata as md

        md.version(name)
        return True
    except Exception:
        return False


def python_exe() -> str:
    return sys.executable


def run_harvest_script(root, rel_script: str) -> tuple[bool, str]:
    """Run existing desk_harvest script as fallback."""
    script = root / rel_script
    if not script.is_file():
        return False, f"missing {rel_script}"
    exe = python_exe()
    try:
        proc = subprocess.run(
            [exe, str(script)],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=300,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0, out.strip()[-400:]
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as exc:
        return False, str(exc)

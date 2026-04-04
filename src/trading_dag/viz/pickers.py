"""Native folder picker (host OS)."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


VIZ_FOLDER_FEEDBACK_KEY = "viz_folder_feedback"


def pick_folder_macos_osascript(initial_dir: Optional[Path]) -> tuple[Optional[str], Optional[str]]:
    """Native folder dialog on macOS (no tkinter). User cancel → ``(None, None)``."""
    if initial_dir is not None:
        cand = initial_dir.expanduser().resolve()
        if cand.is_dir():
            p_esc = str(cand).replace("\\", "\\\\").replace('"', '\\"')
            script = f"""try
    set defaultLocation to POSIX file "{p_esc}"
    set f to choose folder with prompt "Select output folder (Trading DAG Lab)" default location defaultLocation
    return POSIX path of f
on error number -128
    return ""
end try"""
        else:
            script = """try
    set f to choose folder with prompt "Select output folder (Trading DAG Lab)"
    return POSIX path of f
on error number -128
    return ""
end try"""
    else:
        script = """try
    set f to choose folder with prompt "Select output folder (Trading DAG Lab)"
    return POSIX path of f
on error number -128
    return ""
end try"""

    try:
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)

    if r.returncode != 0:
        return None, (r.stderr or r.stdout or "osascript failed").strip()

    out = (r.stdout or "").strip()
    if not out:
        return None, None
    return str(Path(out).expanduser().resolve()), None


def pick_folder_windows_powershell(initial_dir: Optional[Path]) -> tuple[Optional[str], Optional[str]]:
    start = str(Path.home())
    if initial_dir is not None:
        cand = initial_dir.expanduser().resolve()
        if cand.is_dir():
            start = str(cand)
    start_esc = start.replace("'", "''")
    ps = f"""
Add-Type -AssemblyName System.Windows.Forms
$f = New-Object System.Windows.Forms.FolderBrowserDialog
$f.Description = 'Select output folder (Trading DAG Lab)'
$f.SelectedPath = '{start_esc}'
if ($f.ShowDialog() -eq 'OK') {{ $f.SelectedPath }} else {{ '' }}
"""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)

    if r.returncode != 0:
        return None, (r.stderr or r.stdout or "powershell failed").strip()
    out = (r.stdout or "").strip()
    if not out:
        return None, None
    return str(Path(out).expanduser().resolve()), None


def pick_folder_zenity(zenity_bin: str, initial_dir: Optional[Path]) -> tuple[Optional[str], Optional[str]]:
    cmd: List[str] = [
        zenity_bin,
        "--file-selection",
        "--directory",
        "--title=Select output folder (Trading DAG Lab)",
    ]
    if initial_dir is not None:
        cand = initial_dir.expanduser().resolve()
        if cand.is_dir():
            cmd.append(f"--filename={cand}{'/' if not str(cand).endswith('/') else ''}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    out = (r.stdout or "").strip()
    if r.returncode != 0 or not out:
        return None, None
    return str(Path(out).expanduser().resolve()), None


def pick_folder_kdialog(kdialog_bin: str, initial_dir: Optional[Path]) -> tuple[Optional[str], Optional[str]]:
    start = str(Path.home())
    if initial_dir is not None:
        cand = initial_dir.expanduser().resolve()
        if cand.is_dir():
            start = str(cand)
    try:
        r = subprocess.run(
            [kdialog_bin, "--getexistingdirectory", start, "Select output folder"],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    out = (r.stdout or "").strip()
    if r.returncode != 0 or not out:
        return None, None
    return str(Path(out).expanduser().resolve()), None


def pick_folder_tk_if_available(
    initial_dir: Optional[Path],
) -> Optional[tuple[Optional[str], Optional[str]]]:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return None

    start = Path.home()
    if initial_dir is not None:
        cand = initial_dir.expanduser().resolve()
        if cand.is_dir():
            start = cand
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        root.update_idletasks()
        picked = filedialog.askdirectory(
            title="Select output folder (CSV / PNG / JSON)",
            initialdir=str(start),
        )
        root.destroy()
        if picked:
            return str(Path(picked).expanduser().resolve()), None
        return None, None
    except Exception as exc:
        return None, str(exc)


def pick_folder_native_dialog(initial_dir: Optional[Path]) -> tuple[Optional[str], Optional[str]]:
    if sys.platform == "darwin":
        return pick_folder_macos_osascript(initial_dir)

    if sys.platform == "win32":
        return pick_folder_windows_powershell(initial_dir)

    zen = shutil.which("zenity")
    if zen:
        return pick_folder_zenity(zen, initial_dir)

    kd = shutil.which("kdialog")
    if kd:
        return pick_folder_kdialog(kd, initial_dir)

    tk_result = pick_folder_tk_if_available(initial_dir)
    if tk_result is not None:
        return tk_result

    return (
        None,
        "No folder picker available. On macOS ensure `osascript` works; on Linux install `zenity`; "
        "on Windows use PowerShell; or install Python with tkinter. "
        "Otherwise run Streamlit on a machine with a desktop session.",
    )

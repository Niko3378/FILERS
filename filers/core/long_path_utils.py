"""
Long path support for Windows (MAX_PATH = 260).

On Windows, paths > 260 chars require the long prefix or
the LongPathsEnabled registry key (requires admin + reboot).

All helpers add the prefix automatically when path length
exceeds the safe threshold (248 chars).
"""

import os
import sys
import stat

MAX_PATH       = 260
SAFE_THRESHOLD = 248          # warn / normalise below true limit
_PFX           = "\\\\?\\"   # raw: \\?\
_PFX_UNC       = "\\\\?\\UNC\\"


# ---------------------------------------------------------------------------
# Path normalisation
# ---------------------------------------------------------------------------

def normalize(path: str) -> str:
    """Return path with \\?\\ prefix on Windows when length warrants it."""
    if sys.platform != "win32" or not path:
        return path
    if path.startswith(_PFX):
        return path
    try:
        path = os.path.abspath(path)
    except (ValueError, OSError):
        return path
    path = path.replace("/", "\\")
    if len(path) < SAFE_THRESHOLD:
        return path
    if path.startswith("\\\\"):          # UNC  \\server\share\...
        return _PFX_UNC + path[2:]
    return _PFX + path


def denormalize(path: str) -> str:
    """Strip \\?\\ prefix for display purposes."""
    if path.startswith(_PFX_UNC):
        return "\\\\" + path[len(_PFX_UNC):]
    if path.startswith(_PFX):
        return path[len(_PFX):]
    return path


def is_long(path: str) -> bool:
    """True when path already exceeds (or is close to) MAX_PATH."""
    return sys.platform == "win32" and len(os.path.abspath(path)) >= SAFE_THRESHOLD


def abbreviate(path: str, max_len: int = 80) -> str:
    """Shorten a path for display: C:\\...\\parent\\child."""
    if len(path) <= max_len:
        return path
    parts = path.replace("\\", "/").split("/")
    if len(parts) <= 2:
        return path
    head = parts[0]
    tail = "/".join(parts[-2:])
    short = f"{head}/.../{tail}"
    if len(short) <= max_len:
        return short
    return f"{head}/.../{parts[-1]}"


# ---------------------------------------------------------------------------
# Drop-in replacements for os / shutil with long path support
# ---------------------------------------------------------------------------

def scandir(path: str):
    return os.scandir(normalize(path))


def stat_path(path: str):
    return os.stat(normalize(path))


def exists(path: str) -> bool:
    return os.path.exists(normalize(path))


def isdir(path: str) -> bool:
    return os.path.isdir(normalize(path))


def makedirs(path: str, exist_ok: bool = True):
    os.makedirs(normalize(path), exist_ok=exist_ok)


def remove(path: str):
    os.remove(normalize(path))


def rmdir(path: str):
    os.rmdir(normalize(path))


def rename(src: str, dst: str):
    os.rename(normalize(src), normalize(dst))


def open_file(path: str, mode: str = "rb", **kwargs):
    return open(normalize(path), mode, **kwargs)


def copy2(src: str, dst: str):
    """Copy a single file, long-path aware."""
    import shutil
    try:
        shutil.copy2(normalize(src), normalize(dst))
    except OSError:
        # Manual fallback
        with open_file(src, "rb") as fsrc:
            with open_file(dst, "wb") as fdst:
                while chunk := fsrc.read(65536):
                    fdst.write(chunk)
        try:
            import shutil as _sh
            _sh.copystat(normalize(src), normalize(dst))
        except OSError:
            pass


def copytree(src: str, dst: str):
    """Recursively copy directory, long-path aware."""
    makedirs(dst)
    for entry in scandir(src):
        s = entry.path
        d = os.path.join(dst, entry.name)
        if entry.is_dir(follow_symlinks=False):
            copytree(s, d)
        else:
            copy2(s, d)


def rmtree(path: str):
    """Recursively remove directory, long-path aware."""
    norm = normalize(path)
    for entry in os.scandir(norm):
        ep = entry.path
        if entry.is_dir(follow_symlinks=False):
            rmtree(ep)
        else:
            # Clear read-only flag if set
            try:
                mode = entry.stat(follow_symlinks=False).st_mode
                if not (mode & stat.S_IWRITE):
                    os.chmod(normalize(ep), mode | stat.S_IWRITE)
            except OSError:
                pass
            try:
                os.remove(normalize(ep))
            except OSError:
                pass
    try:
        os.rmdir(norm)
    except OSError:
        pass


def checksum(path: str, algo: str = "md5") -> str:
    import hashlib
    h = hashlib.new(algo)
    with open_file(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def read_text(path: str) -> str:
    with open_file(path, "rb") as f:
        raw = f.read()
    try:
        import chardet
        enc = chardet.detect(raw)["encoding"] or "utf-8"
    except ImportError:
        enc = "utf-8"
    return raw.decode(enc, errors="replace")


# ---------------------------------------------------------------------------
# Windows registry helpers
# ---------------------------------------------------------------------------

def check_registry_long_paths() -> bool:
    """True if HKLM LongPathsEnabled == 1."""
    if sys.platform != "win32":
        return True
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\FileSystem",
        ) as k:
            val, _ = winreg.QueryValueEx(k, "LongPathsEnabled")
            return bool(val)
    except Exception:
        return False


def enable_registry_long_paths() -> str:
    """Enable LongPathsEnabled in registry. Returns '' on success, error msg otherwise."""
    if sys.platform != "win32":
        return ""
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\FileSystem",
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY,
        ) as k:
            winreg.SetValueEx(k, "LongPathsEnabled", 0, winreg.REG_DWORD, 1)
        return ""
    except PermissionError:
        return "Droits administrateur requis. Relancez Files Manager en tant qu'administrateur."
    except Exception as e:
        return str(e)


def python_long_paths_active() -> bool:
    """True if Python itself can open paths > 260 chars without \\?\\ prefix."""
    if sys.platform != "win32":
        return True
    return check_registry_long_paths()

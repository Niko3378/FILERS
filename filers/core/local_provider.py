import os
import stat
import hashlib
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from core import long_path_utils as lp


@dataclass
class FileEntry:
    name: str
    path: str
    is_dir: bool
    is_hidden: bool
    size: int
    modified: datetime
    permissions: str
    owner: str = ""
    is_long_path: bool = False


class LocalProvider:
    def __init__(self, show_hidden: bool = False):
        self.show_hidden = show_hidden

    def list_dir(self, path: str) -> List[FileEntry]:
        entries = []
        try:
            with lp.scandir(path) as it:
                for entry in it:
                    try:
                        info = entry.stat(follow_symlinks=False)
                        is_hidden = self._is_hidden(entry)
                        if not self.show_hidden and is_hidden:
                            continue
                        full_path = lp.denormalize(entry.path)
                        entries.append(FileEntry(
                            name=entry.name,
                            path=full_path,
                            is_dir=entry.is_dir(follow_symlinks=False),
                            is_hidden=is_hidden,
                            size=info.st_size if not entry.is_dir() else 0,
                            modified=datetime.fromtimestamp(info.st_mtime),
                            permissions=self._format_permissions(info.st_mode),
                            owner=self._get_owner(full_path),
                            is_long_path=lp.is_long(full_path),
                        ))
                    except PermissionError:
                        entries.append(FileEntry(
                            name=entry.name,
                            path=lp.denormalize(entry.path),
                            is_dir=entry.is_dir(),
                            is_hidden=False,
                            size=0,
                            modified=datetime.min,
                            permissions="----------",
                        ))
        except PermissionError:
            pass
        entries.sort(key=lambda e: (not e.is_dir, e.name.lower()))
        return entries

    def _is_hidden(self, entry: os.DirEntry) -> bool:
        if entry.name.startswith("."):
            return True
        if os.name == "nt":
            try:
                import ctypes
                attrs = ctypes.windll.kernel32.GetFileAttributesW(lp.normalize(entry.path))
                return bool(attrs & 2) if attrs != -1 else False
            except Exception:
                return False
        return False

    def _format_permissions(self, mode: int) -> str:
        kinds = [
            (stat.S_IRUSR, "r"), (stat.S_IWUSR, "w"), (stat.S_IXUSR, "x"),
            (stat.S_IRGRP, "r"), (stat.S_IWGRP, "w"), (stat.S_IXGRP, "x"),
            (stat.S_IROTH, "r"), (stat.S_IWOTH, "w"), (stat.S_IXOTH, "x"),
        ]
        prefix = "d" if stat.S_ISDIR(mode) else ("l" if stat.S_ISLNK(mode) else "-")
        return prefix + "".join(c if mode & m else "-" for m, c in kinds)

    def _get_owner(self, path: str) -> str:
        if os.name == "nt":
            try:
                import win32security
                sd = win32security.GetFileSecurity(
                    lp.normalize(path), win32security.OWNER_SECURITY_INFORMATION
                )
                sid = sd.GetSecurityDescriptorOwner()
                name, domain, _ = win32security.LookupAccountSid(None, sid)
                return f"{domain}\\{name}"
            except Exception:
                return ""
        else:
            try:
                import pwd
                return pwd.getpwuid(os.stat(lp.normalize(path)).st_uid).pw_name
            except Exception:
                return str(os.stat(lp.normalize(path)).st_uid)

    def get_drives(self) -> List[str]:
        if os.name == "nt":
            import string
            return [f"{d}:\\" for d in string.ascii_uppercase
                    if os.path.exists(f"{d}:\\")]
        return ["/"]

    def get_roots(self) -> List[str]:
        return self.get_drives()

    def copy(self, src: str, dst: str):
        if lp.isdir(src):
            lp.copytree(src, dst)
        else:
            lp.copy2(src, dst)

    def move(self, src: str, dst: str):
        import shutil
        try:
            lp.rename(src, dst)
        except OSError:
            # Cross-device or long-path rename failed — copy + delete
            self.copy(src, dst)
            self.delete(src)

    def delete(self, path: str):
        if lp.isdir(path):
            lp.rmtree(path)
        else:
            lp.remove(path)

    def mkdir(self, path: str):
        lp.makedirs(path, exist_ok=True)

    def rename(self, src: str, dst: str):
        lp.rename(src, dst)

    def checksum(self, path: str, algo: str = "md5") -> str:
        return lp.checksum(path, algo)

    def read_text(self, path: str) -> str:
        return lp.read_text(path)

    def get_permissions_detail(self, path: str) -> dict:
        result = {
            "path": path,
            "mode": "",
            "readable": False,
            "writable": False,
            "executable": False,
            "owner": "",
            "ntfs_acl": [],
        }
        try:
            s = os.stat(lp.normalize(path))
            result["mode"] = self._format_permissions(s.st_mode)
            result["readable"]   = os.access(lp.normalize(path), os.R_OK)
            result["writable"]   = os.access(lp.normalize(path), os.W_OK)
            result["executable"] = os.access(lp.normalize(path), os.X_OK)
            result["owner"] = self._get_owner(path)
            if os.name == "nt":
                result["ntfs_acl"] = self._get_ntfs_acl(path)
        except Exception as e:
            result["error"] = str(e)
        return result

    def _get_ntfs_acl(self, path: str) -> list:
        try:
            import win32security
            import ntsecuritycon as con
            sd = win32security.GetFileSecurity(
                lp.normalize(path),
                win32security.DACL_SECURITY_INFORMATION | win32security.OWNER_SECURITY_INFORMATION,
            )
            dacl = sd.GetSecurityDescriptorDacl()
            if not dacl:
                return []
            acl_entries = []
            for i in range(dacl.GetAceCount()):
                ace = dacl.GetAce(i)
                ace_type, ace_flags = ace[0]
                mask = ace[1]
                sid = ace[2]
                try:
                    name, domain, _ = win32security.LookupAccountSid(None, sid)
                    account = f"{domain}\\{name}"
                except Exception:
                    account = str(sid)
                rights = []
                if mask & con.FILE_GENERIC_READ:    rights.append("Lecture")
                if mask & con.FILE_GENERIC_WRITE:   rights.append("Écriture")
                if mask & con.FILE_GENERIC_EXECUTE: rights.append("Exécution")
                if mask & con.DELETE:               rights.append("Suppression")
                acl_entries.append({
                    "account": account,
                    "rights": rights,
                    "type": "Allow" if ace_type == 0 else "Deny",
                    "sid": sid,
                    "mask": mask,
                })
            return acl_entries
        except ImportError:
            return []
        except Exception:
            return []

    def set_hidden(self, path: str, hidden: bool):
        if os.name == "nt":
            import ctypes
            np = lp.normalize(path)
            attrs = ctypes.windll.kernel32.GetFileAttributesW(np)
            if hidden:
                ctypes.windll.kernel32.SetFileAttributesW(np, attrs | 2)
            else:
                ctypes.windll.kernel32.SetFileAttributesW(np, attrs & ~2)
        else:
            base = os.path.basename(path)
            parent = os.path.dirname(path)
            if hidden and not base.startswith("."):
                lp.rename(path, os.path.join(parent, "." + base))
            elif not hidden and base.startswith("."):
                lp.rename(path, os.path.join(parent, base[1:]))

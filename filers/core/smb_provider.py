import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

try:
    from smb.SMBConnection import SMBConnection
    from smb import smb_structs
    HAS_PYSMB = True
except ImportError:
    HAS_PYSMB = False


@dataclass
class SMBEntry:
    name: str
    path: str
    is_dir: bool
    size: int
    modified: datetime
    is_readonly: bool
    is_hidden: bool


class SMBProvider:
    def __init__(self):
        self._conn: Optional[object] = None
        self._share = ""
        self._host = ""

    def connect(self, host: str, share: str, user: str = "", password: str = "",
                domain: str = "", port: int = 445, timeout: int = 15):
        if not HAS_PYSMB:
            raise ImportError("pysmb non installé. pip install pysmb")
        self._host = host
        self._share = share
        import socket
        client_name = socket.gethostname()
        self._conn = SMBConnection(user, password, client_name, host,
                                   domain=domain, use_ntlm_v2=True,
                                   is_direct_tcp=(port == 445))
        ok = self._conn.connect(host, port, timeout=timeout)
        if not ok:
            raise ConnectionError(f"Impossible de se connecter à {host}:{port}")

    def disconnect(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def connected(self) -> bool:
        return self._conn is not None

    def list_shares(self) -> List[str]:
        if not self._conn:
            return []
        return [s.name for s in self._conn.listShares() if not s.name.endswith("$")]

    def list_dir(self, path: str = "/") -> List[SMBEntry]:
        if not self._conn:
            return []
        smb_path = path.replace("\\", "/")
        entries = []
        for f in self._conn.listPath(self._share, smb_path):
            if f.filename in (".", ".."):
                continue
            child_path = smb_path.rstrip("/") + "/" + f.filename
            entries.append(SMBEntry(
                name=f.filename,
                path=child_path,
                is_dir=f.isDirectory,
                size=f.file_size,
                modified=datetime.fromtimestamp(f.last_write_time),
                is_readonly=bool(f.file_attributes & 0x01),
                is_hidden=bool(f.file_attributes & 0x02),
            ))
        entries.sort(key=lambda e: (not e.is_dir, e.name.lower()))
        return entries

    def download(self, remote_path: str, local_path: str):
        with open(local_path, "wb") as f:
            self._conn.retrieveFile(self._share, remote_path, f)

    def upload(self, local_path: str, remote_path: str):
        with open(local_path, "rb") as f:
            self._conn.storeFile(self._share, remote_path, f)

    def mkdir(self, path: str):
        self._conn.createDirectory(self._share, path)

    def delete(self, path: str, is_dir: bool = False):
        if is_dir:
            self._conn.deleteDirectory(self._share, path)
        else:
            self._conn.deleteFiles(self._share, path)

    def rename(self, src: str, dst: str):
        self._conn.rename(self._share, src, dst)

    def read_text(self, remote_path: str) -> str:
        import io
        buf = io.BytesIO()
        self._conn.retrieveFile(self._share, remote_path, buf)
        raw = buf.getvalue()
        try:
            import chardet
            enc = chardet.detect(raw)["encoding"] or "utf-8"
        except ImportError:
            enc = "utf-8"
        return raw.decode(enc, errors="replace")

    @staticmethod
    def parse_unc(unc: str):
        r"""Parse \\host\share\path -> (host, share, path)"""
        unc = unc.replace("\\", "/").lstrip("/")
        parts = unc.split("/", 2)
        host = parts[0] if len(parts) > 0 else ""
        share = parts[1] if len(parts) > 1 else ""
        path = "/" + parts[2] if len(parts) > 2 else "/"
        return host, share, path

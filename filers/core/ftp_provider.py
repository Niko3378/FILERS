import ftplib
import paramiko
import stat
import io
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Callable


@dataclass
class RemoteEntry:
    name: str
    path: str
    is_dir: bool
    size: int
    modified: datetime
    permissions: str


class FTPProvider:
    def __init__(self):
        self._ftp: Optional[ftplib.FTP] = None
        self._host = ""
        self._port = 21

    def connect(self, host: str, port: int = 21, user: str = "anonymous",
                password: str = "", timeout: int = 15):
        self._host = host
        self._port = port
        self._ftp = ftplib.FTP()
        self._ftp.connect(host, port, timeout=timeout)
        self._ftp.login(user, password)
        self._ftp.set_pasv(True)

    def disconnect(self):
        if self._ftp:
            try:
                self._ftp.quit()
            except Exception:
                self._ftp.close()
            self._ftp = None

    @property
    def connected(self) -> bool:
        return self._ftp is not None

    def list_dir(self, path: str = "/") -> List[RemoteEntry]:
        entries = []
        lines = []
        self._ftp.retrlines(f"LIST {path}", lines.append)
        for line in lines:
            entry = self._parse_list_line(line, path)
            if entry and entry.name not in (".", ".."):
                entries.append(entry)
        entries.sort(key=lambda e: (not e.is_dir, e.name.lower()))
        return entries

    def _parse_list_line(self, line: str, parent: str) -> Optional[RemoteEntry]:
        parts = line.split(None, 8)
        if len(parts) < 9:
            return None
        perms = parts[0]
        size = int(parts[4]) if parts[4].isdigit() else 0
        name = parts[8]
        is_dir = perms.startswith("d")
        path = parent.rstrip("/") + "/" + name
        try:
            date_str = " ".join(parts[5:8])
            modified = datetime.strptime(date_str, "%b %d %H:%M")
            modified = modified.replace(year=datetime.now().year)
        except ValueError:
            try:
                date_str = " ".join(parts[5:8])
                modified = datetime.strptime(date_str, "%b %d %Y")
            except ValueError:
                modified = datetime.min
        return RemoteEntry(name=name, path=path, is_dir=is_dir,
                           size=size, modified=modified, permissions=perms)

    def download(self, remote_path: str, local_path: str,
                 progress: Optional[Callable[[int], None]] = None):
        with open(local_path, "wb") as f:
            def callback(data):
                f.write(data)
                if progress:
                    progress(len(data))
            self._ftp.retrbinary(f"RETR {remote_path}", callback)

    def upload(self, local_path: str, remote_path: str,
               progress: Optional[Callable[[int], None]] = None):
        with open(local_path, "rb") as f:
            def callback(data):
                if progress:
                    progress(len(data))
            self._ftp.storbinary(f"STOR {remote_path}", f, callback=callback)

    def mkdir(self, path: str):
        self._ftp.mkd(path)

    def delete(self, path: str):
        try:
            self._ftp.delete(path)
        except ftplib.error_perm:
            self._ftp.rmd(path)

    def rename(self, src: str, dst: str):
        self._ftp.rename(src, dst)

    def read_text(self, remote_path: str) -> str:
        buf = io.BytesIO()
        self._ftp.retrbinary(f"RETR {remote_path}", buf.write)
        raw = buf.getvalue()
        try:
            import chardet
            enc = chardet.detect(raw)["encoding"] or "utf-8"
        except ImportError:
            enc = "utf-8"
        return raw.decode(enc, errors="replace")


class SFTPProvider:
    def __init__(self):
        self._client: Optional[paramiko.SSHClient] = None
        self._sftp: Optional[paramiko.SFTPClient] = None

    def connect(self, host: str, port: int = 22, user: str = "",
                password: str = "", key_path: str = "", timeout: int = 15):
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kwargs = {"hostname": host, "port": port, "username": user, "timeout": timeout}
        if key_path:
            kwargs["key_filename"] = key_path
        else:
            kwargs["password"] = password
        self._client.connect(**kwargs)
        self._sftp = self._client.open_sftp()

    def disconnect(self):
        if self._sftp:
            self._sftp.close()
            self._sftp = None
        if self._client:
            self._client.close()
            self._client = None

    @property
    def connected(self) -> bool:
        return self._sftp is not None

    def list_dir(self, path: str = "/") -> List[RemoteEntry]:
        entries = []
        for attr in self._sftp.listdir_attr(path):
            is_dir = stat.S_ISDIR(attr.st_mode) if attr.st_mode else False
            entry_path = path.rstrip("/") + "/" + attr.filename
            perms = self._format_permissions(attr.st_mode or 0)
            entries.append(RemoteEntry(
                name=attr.filename,
                path=entry_path,
                is_dir=is_dir,
                size=attr.st_size or 0,
                modified=datetime.fromtimestamp(attr.st_mtime or 0),
                permissions=perms,
            ))
        entries.sort(key=lambda e: (not e.is_dir, e.name.lower()))
        return entries

    def _format_permissions(self, mode: int) -> str:
        import stat as s
        kinds = [
            (s.S_IRUSR, "r"), (s.S_IWUSR, "w"), (s.S_IXUSR, "x"),
            (s.S_IRGRP, "r"), (s.S_IWGRP, "w"), (s.S_IXGRP, "x"),
            (s.S_IROTH, "r"), (s.S_IWOTH, "w"), (s.S_IXOTH, "x"),
        ]
        prefix = "d" if s.S_ISDIR(mode) else "-"
        return prefix + "".join(c if mode & m else "-" for m, c in kinds)

    def download(self, remote_path: str, local_path: str,
                 progress: Optional[Callable[[int, int], None]] = None):
        self._sftp.get(remote_path, local_path, callback=progress)

    def upload(self, local_path: str, remote_path: str,
               progress: Optional[Callable[[int, int], None]] = None):
        self._sftp.put(local_path, remote_path, callback=progress)

    def mkdir(self, path: str):
        self._sftp.mkdir(path)

    def delete(self, path: str):
        try:
            self._sftp.remove(path)
        except Exception:
            self._sftp.rmdir(path)

    def rename(self, src: str, dst: str):
        self._sftp.rename(src, dst)

    def read_text(self, remote_path: str) -> str:
        with self._sftp.file(remote_path, "rb") as f:
            raw = f.read()
        try:
            import chardet
            enc = chardet.detect(raw)["encoding"] or "utf-8"
        except ImportError:
            enc = "utf-8"
        return raw.decode(enc, errors="replace")

    def get_permissions(self, path: str) -> dict:
        attr = self._sftp.stat(path)
        return {
            "path": path,
            "mode": self._format_permissions(attr.st_mode or 0),
            "size": attr.st_size,
            "modified": datetime.fromtimestamp(attr.st_mtime or 0),
            "uid": attr.st_uid,
            "gid": attr.st_gid,
        }

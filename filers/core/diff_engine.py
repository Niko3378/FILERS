import difflib
import os
import hashlib
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class DiffLine:
    left_num: int
    right_num: int
    left_text: str
    right_text: str
    kind: str  # "equal", "replace", "insert", "delete"


@dataclass
class FolderDiffEntry:
    name: str
    left_path: str
    right_path: str
    status: str  # "equal", "modified", "left_only", "right_only", "type_mismatch"
    is_dir: bool


def diff_texts(left: str, right: str) -> List[DiffLine]:
    left_lines = left.splitlines()
    right_lines = right.splitlines()
    result = []
    matcher = difflib.SequenceMatcher(None, left_lines, right_lines, autojunk=False)
    l_num = 1
    r_num = 1
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for l, r in zip(left_lines[i1:i2], right_lines[j1:j2]):
                result.append(DiffLine(l_num, r_num, l, r, "equal"))
                l_num += 1
                r_num += 1
        elif tag == "replace":
            l_chunk = left_lines[i1:i2]
            r_chunk = right_lines[j1:j2]
            max_len = max(len(l_chunk), len(r_chunk))
            for i in range(max_len):
                lt = l_chunk[i] if i < len(l_chunk) else ""
                rt = r_chunk[i] if i < len(r_chunk) else ""
                result.append(DiffLine(
                    l_num if i < len(l_chunk) else 0,
                    r_num if i < len(r_chunk) else 0,
                    lt, rt, "replace"
                ))
                if i < len(l_chunk):
                    l_num += 1
                if i < len(r_chunk):
                    r_num += 1
        elif tag == "delete":
            for l in left_lines[i1:i2]:
                result.append(DiffLine(l_num, 0, l, "", "delete"))
                l_num += 1
        elif tag == "insert":
            for r in right_lines[j1:j2]:
                result.append(DiffLine(0, r_num, "", r, "insert"))
                r_num += 1
    return result


def _file_hash(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compare_folders(left_dir: str, right_dir: str,
                    recursive: bool = True) -> List[FolderDiffEntry]:
    left_names = set()
    right_names = set()

    try:
        left_names = {e.name: e for e in os.scandir(left_dir)}
    except PermissionError:
        pass
    try:
        right_names = {e.name: e for e in os.scandir(right_dir)}
    except PermissionError:
        pass

    all_names = sorted(set(left_names) | set(right_names), key=str.lower)
    results = []

    for name in all_names:
        l_entry = left_names.get(name)
        r_entry = right_names.get(name)
        l_path = os.path.join(left_dir, name) if l_entry else ""
        r_path = os.path.join(right_dir, name) if r_entry else ""

        if l_entry and r_entry:
            l_is_dir = l_entry.is_dir()
            r_is_dir = r_entry.is_dir()
            if l_is_dir != r_is_dir:
                status = "type_mismatch"
            elif l_is_dir:
                status = "equal"
                if recursive:
                    sub = compare_folders(l_path, r_path, recursive)
                    if any(e.status != "equal" for e in sub):
                        status = "modified"
                results.append(FolderDiffEntry(name, l_path, r_path, status, True))
                if recursive and l_is_dir:
                    results.extend(_indent_results(sub, name))
                continue
            else:
                try:
                    status = "equal" if _file_hash(l_path) == _file_hash(r_path) else "modified"
                except Exception:
                    l_sz = l_entry.stat().st_size
                    r_sz = r_entry.stat().st_size
                    l_mt = l_entry.stat().st_mtime
                    r_mt = r_entry.stat().st_mtime
                    status = "equal" if (l_sz == r_sz and abs(l_mt - r_mt) < 2) else "modified"
        elif l_entry:
            status = "left_only"
            l_is_dir = l_entry.is_dir()
            results.append(FolderDiffEntry(name, l_path, "", status, l_is_dir))
            continue
        else:
            status = "right_only"
            r_is_dir = r_entry.is_dir()
            results.append(FolderDiffEntry(name, "", r_path, status, r_is_dir))
            continue

        results.append(FolderDiffEntry(name, l_path, r_path, status,
                                       l_entry.is_dir() if l_entry else False))
    return results


def _indent_results(entries: List[FolderDiffEntry], parent: str) -> List[FolderDiffEntry]:
    indented = []
    for e in entries:
        e2 = FolderDiffEntry(
            name="  " + e.name,
            left_path=e.left_path,
            right_path=e.right_path,
            status=e.status,
            is_dir=e.is_dir,
        )
        indented.append(e2)
    return indented

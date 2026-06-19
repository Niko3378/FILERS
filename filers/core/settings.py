import os
import json

_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'Files Manager')
_FILE = os.path.join(_DIR, 'settings.json')
_MAX_HISTORY = 15

_data: dict = {}
_loaded = False


def _load():
    global _loaded, _data
    _loaded = True
    try:
        with open(_FILE, 'r', encoding='utf-8') as f:
            _data = json.load(f)
    except Exception:
        _data = {}


def _save():
    os.makedirs(_DIR, exist_ok=True)
    with open(_FILE, 'w', encoding='utf-8') as f:
        json.dump(_data, f, ensure_ascii=False, indent=2)


def get(key: str, default=None):
    if not _loaded:
        _load()
    return _data.get(key, default)


def set_value(key: str, value):
    if not _loaded:
        _load()
    _data[key] = value
    _save()


def add_to_history(key: str, path: str):
    history = get(key, [])
    path = path.strip()
    if not path:
        return
    if path in history:
        history.remove(path)
    history.insert(0, path)
    _data[key] = history[:_MAX_HISTORY]
    _save()


def get_history(key: str) -> list:
    return get(key, [])

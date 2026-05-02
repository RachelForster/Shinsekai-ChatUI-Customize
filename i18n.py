"""本插件文案：按主程序当前语言从 ``locales/*.json`` 加载，与主工程 ``i18n/locales`` 分离。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from i18n import current_language
from sdk.lang import normalize_lang

_locales_dir = Path(__file__).resolve().parent / "locales"
_bundle_cache: dict[str, dict[str, Any]] = {}


def _load_bundle(code: str) -> dict[str, Any]:
    if code not in _bundle_cache:
        path = _locales_dir / f"{code}.json"
        if path.is_file():
            with open(path, encoding="utf-8") as f:
                _bundle_cache[code] = json.load(f)
        else:
            _bundle_cache[code] = {}
    return _bundle_cache[code]


def reload_strings() -> None:
    """开发或热切换时可清空缓存；按需调用。"""
    _bundle_cache.clear()


def tr(key: str, **kwargs: Any) -> str:
    lang = normalize_lang(current_language())
    s = _load_bundle(lang).get(key)
    if not isinstance(s, str):
        s = _load_bundle("en").get(key)
    if not isinstance(s, str):
        s = key
    if kwargs:
        try:
            s = s.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return s

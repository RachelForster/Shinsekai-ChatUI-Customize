"""
由调色参数生成 ``chat_ui_theme.json`` 结构的字典（与 :mod:`ui.chat_ui.theme_chrome` 解析一致）。
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from PySide6.QtGui import QColor, QImage, QPainter

logger = logging.getLogger(__name__)


def _hex(c: QColor) -> str:
    return c.name(QColor.NameFormat.HexRgb)


def _rgba(c: QColor, alpha: float) -> str:
    a = max(0.0, min(1.0, float(alpha)))
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {a:.3f})"


def _qss_image_url(path: Path) -> str:
    """
    Qt StyleSheet 的 url() 在 Windows 上对 ``file:///C:/...`` 易解析成非法路径（日志里出现 file:\\\\...）。
    使用 resolve 后的绝对路径、仅正斜杠、不加 file: 前缀，最稳妥。
    """
    return path.resolve().as_posix()


def _write_dimmed_pattern_cache(src: Path, opacity: float) -> Path:
    """将印花图按不透明度绘入 PNG 缓存（QSS 无法单独调节 background-image alpha）。"""
    src = src.resolve()
    try:
        mtime_ns = src.stat().st_mtime_ns
    except OSError as e:
        raise OSError(f"无法读取印花文件: {src}") from e
    key = hashlib.sha1(
        f"{src}|{mtime_ns}|{opacity:.5f}".encode("utf-8", errors="replace")
    ).hexdigest()[:20]
    cache_dir = src.parent / ".pattern_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    dest = cache_dir / f"dim_{key}.png"
    if dest.is_file():
        return dest

    img = QImage(str(src))
    if img.isNull():
        raise ValueError(f"无法加载印花图像: {src}")
    fmt = QImage.Format.Format_ARGB32_Premultiplied
    if img.format() != fmt:
        img = img.convertToFormat(fmt)
    out = QImage(img.size(), fmt)
    out.fill(0)
    painter = QPainter(out)
    try:
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setOpacity(opacity)
        painter.drawImage(0, 0, img)
    finally:
        painter.end()
    if not out.save(str(dest), "PNG"):
        raise OSError(f"无法写入印花缓存: {dest}")
    return dest


def _effective_pattern_path(
    pattern_path: Path | None,
    opacity: float,
    *,
    any_target: bool,
) -> Path | None:
    if (
        not any_target
        or pattern_path is None
        or not pattern_path.is_file()
    ):
        return None
    o = max(0.0, min(1.0, float(opacity)))
    if o <= 0.001:
        return None
    if o >= 0.999:
        return pattern_path.resolve()
    try:
        return _write_dimmed_pattern_cache(pattern_path.resolve(), o)
    except Exception:
        logger.exception("印花透明度处理失败，改用原图")
        return pattern_path.resolve()


def _pattern_clause(path: Path | None, enabled: bool) -> str:
    if not enabled or path is None or not path.is_file():
        return ""
    posix = _qss_image_url(path)
    return (
        f' background-image: url("{posix}"); background-repeat: repeat;'
        f" background-position: top left;"
    )


def build_theme_dict(
    *,
    primary: QColor,
    text: QColor,
    border: QColor,
    accent: QColor,
    panel_alpha: float,
    radius: int,
    pattern_path: Path | None,
    pattern_opacity: float = 1.0,
    pattern_dialog: bool,
    pattern_input: bool,
    pattern_options: bool,
    pattern_numeric: bool,
) -> dict[str, Any]:
    r = max(4, min(36, int(radius)))
    pa = max(0.35, min(0.99, float(panel_alpha)))
    tg = _hex(text)
    br = _hex(border)
    ac = _hex(accent)
    pr = _rgba(primary, pa)

    mic_i = _hex(QColor(primary).lighter(118))
    mic_a = _hex(QColor(accent).darker(110))

    use_pat = bool(pattern_dialog or pattern_input or pattern_options or pattern_numeric)
    eff_pat = _effective_pattern_path(
        pattern_path, pattern_opacity, any_target=use_pat
    )

    pd = _pattern_clause(eff_pat, pattern_dialog)
    pi = _pattern_clause(eff_pat, pattern_input)
    popts = _pattern_clause(eff_pat, pattern_options)
    pn = _pattern_clause(eff_pat, pattern_numeric)

    rr = max(4, r - 4)

    dialog = (
        f"color: {tg}; border: 2px solid {br}; background-color: {pr}; "
        f"border-radius: {r}px; padding: 8px 12px; letter-spacing: 1px;{pd}"
    )
    numeric = (
        f"color: {tg}; border: 1px solid {br}; background-color: {pr}; "
        f"border-radius: {rr}px; padding: 2px 6px; font-weight: 500;{pn}"
    )
    input_bar = (
        f"color: {tg}; background-color: {pr}; border: 2px solid {br}; "
        f"border-radius: {r}px; selection-background-color: {_rgba(accent, 0.35)}; "
        f"padding: 6px 10px;{pi}"
    )
    busy = (
        f"letter-spacing: 1.2px; color: {ac}; font-weight: bold; "
        f"background-color: {_rgba(primary, pa * 0.62)}; border-radius: {r + 4}px; "
        f"padding: 2px 8px;"
    )
    option_row = (
        f"color: {tg}; border: 1px solid {br}; background-color: {pr}; "
        f"border-radius: {rr}px; padding: 6px 12px;"
    )
    option_hover = (
        f"border: 1px solid {ac}; background-color: {_rgba(accent, 0.2)}; color: {ac};"
    )
    options_container = (
        f"border: 1px solid {br}; background-color: {pr}; border-radius: {r}px; "
        f"padding: 8px;{popts}"
    )
    send_btn = (
        f"font-weight: bold; color: #FFFFFF; background-color: {ac}; "
        f"border-radius: {min(36, r + 12)}px; border: none; padding: 6px 16px;"
    )
    mic_ex = (
        f"border: 2px solid {br}; border-radius: {min(36, r + 12)}px; padding: 6px;"
    )

    return {
        "numeric_label": {"extra_qss": numeric.strip()},
        "dialog_label": {"extra_qss": dialog.strip()},
        "input_bar": {"extra_qss": input_bar.strip()},
        "busy_bar_label": {"extra_qss": busy.strip()},
        "option_row": {
            "extra_qss": option_row.strip(),
            "hover_extra_qss": option_hover.strip(),
        },
        "options_container": {"extra_qss": options_container.strip()},
        "send_button": {"extra_qss": send_btn.strip()},
        "microphone_button": {
            "inactive_background": mic_i,
            "active_background": mic_a,
            "extra_qss": mic_ex.strip(),
        },
    }

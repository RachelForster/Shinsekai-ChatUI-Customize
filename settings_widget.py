from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from PySide6.QtCore import QTimer, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QApplication,
    QColorDialog,
)

from plugins.chat_ui_theme.i18n import tr
from sdk.plugin_host_context import PluginSettingsUIContext
from ui.chat_ui.chat_ui import ChatUIWindow
from ui.chat_ui.theme_chrome import (
    clear_chat_chrome_theme_cache,
    project_root,
    set_chat_chrome_theme_preview_path,
)

from plugins.chat_ui_theme.theme_builder import build_theme_dict


def _default_theme_path() -> Path:
    return project_root() / "data" / "chat_ui_theme.json"


def _example_theme_path() -> Path:
    return project_root() / "data" / "chat_ui_theme.example.json"


def _preview_theme_path() -> Path:
    return project_root() / "data" / ".chat_ui_theme_preview.json"


def _assets_dir() -> Path:
    d = project_root() / "data" / "chat_ui_theme_assets"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _refresh_open_chat_windows() -> None:
    app = QApplication.instance()
    if app is None:
        return
    for w in app.allWidgets():
        if isinstance(w, ChatUIWindow):
            try:
                w.apply_font_styles()
            except Exception:
                pass


def _swatch_stylesheet(hex_rgb: str) -> str:
    return (
        f"background-color: {hex_rgb}; border: 1px solid #888888;"
        f" min-height: 26px; max-height: 26px;"
    )


def build_chat_ui_theme_settings(plg: PluginSettingsUIContext) -> QWidget:
    _ = plg
    root = QWidget()
    main = QVBoxLayout(root)
    main.setContentsMargins(4, 8, 4, 8)

    hint = QLabel()
    hint.setWordWrap(True)
    hint.setTextFormat(Qt.TextFormat.RichText)
    hint.setText(tr("hint_html"))
    main.addWidget(hint)

    path_label = QLabel()
    path_label.setWordWrap(True)
    path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    theme_path = _default_theme_path()
    path_label.setText(f"{tr('file_label')}\n{theme_path.as_posix()}")
    main.addWidget(path_label)

    colors = {
        "primary": QColor(255, 252, 248),
        "text": QColor(94, 94, 94),
        "border": QColor(255, 208, 194),
        "accent": QColor(255, 189, 168),
    }

    pattern_path: list[Path | None] = [None]
    debounce = QTimer(root)
    debounce.setSingleShot(True)
    debounce.setInterval(160)

    splitter = QSplitter(Qt.Orientation.Horizontal)
    main.addWidget(splitter, 1)

    # --- 左侧滚动：可视化控件 ---
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    left = QWidget()
    left_l = QVBoxLayout(left)
    left_l.setContentsMargins(0, 0, 8, 0)

    visual = QGroupBox(tr("visual_group"))
    vg = QGridLayout(visual)

    color_btn: dict[str, QPushButton] = {}

    def _sync_one(key: str) -> None:
        b = color_btn[key]
        b.setStyleSheet(_swatch_stylesheet(colors[key].name(QColor.NameFormat.HexRgb)))

    def _pick_color(key: str) -> None:
        c = QColor(colors[key])
        d = QColorDialog.getColor(c, root, tr("pick_color_title"))
        if d.isValid():
            colors[key] = d
            _sync_one(key)
            _schedule_preview()

    row = 0
    for key, tr_key in (
        ("primary", "color_primary"),
        ("text", "color_text"),
        ("border", "color_border"),
        ("accent", "color_accent"),
    ):
        vg.addWidget(QLabel(tr(tr_key)), row, 0)
        b = QPushButton()
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setMinimumWidth(120)
        color_btn[key] = b
        b.clicked.connect(lambda _=False, k=key: _pick_color(k))
        _sync_one(key)
        vg.addWidget(b, row, 1)
        row += 1

    left_l.addWidget(visual)

    sliders_box = QGroupBox(tr("sliders_group"))
    sg = QVBoxLayout(sliders_box)

    radius_l = QLabel()
    radius_s = QSlider(Qt.Orientation.Horizontal)
    radius_s.setRange(8, 28)
    radius_s.setValue(16)

    def _radius_fmt(v: int) -> None:
        radius_l.setText(tr("slider_radius").format(value=v))

    radius_s.valueChanged.connect(_radius_fmt)
    _radius_fmt(radius_s.value())
    radius_s.valueChanged.connect(lambda _v: _schedule_preview())
    sg.addWidget(radius_l)
    sg.addWidget(radius_s)

    op_l = QLabel()
    op_s = QSlider(Qt.Orientation.Horizontal)
    op_s.setRange(50, 98)
    op_s.setValue(92)

    def _op_fmt(v: int) -> None:
        op_l.setText(tr("slider_panel_opacity").format(percent=v))

    op_s.valueChanged.connect(_op_fmt)
    _op_fmt(op_s.value())
    op_s.valueChanged.connect(lambda _v: _schedule_preview())
    sg.addWidget(op_l)
    sg.addWidget(op_s)

    left_l.addWidget(sliders_box)

    pat_box = QGroupBox(tr("pattern_group"))
    pg = QVBoxLayout(pat_box)
    pat_info = QLabel("—")
    pat_info.setWordWrap(True)
    pat_info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

    cb_dialog = QCheckBox(tr("pattern_dialog"))
    cb_input = QCheckBox(tr("pattern_input"))
    cb_options = QCheckBox(tr("pattern_options"))
    cb_numeric = QCheckBox(tr("pattern_numeric"))
    for cb in (cb_dialog, cb_input, cb_options, cb_numeric):
        cb.toggled.connect(lambda _c: _schedule_preview())

    def _pick_pattern() -> None:
        path, _ = QFileDialog.getOpenFileName(
            root,
            tr("pick_pattern"),
            "",
            tr("pattern_filter"),
        )
        if not path:
            return
        src = Path(path)
        try:
            dest = _assets_dir() / f"{uuid.uuid4().hex[:10]}_{src.name}"
            shutil.copy2(src, dest)
        except OSError as e:
            QMessageBox.warning(
                root,
                tr("pattern_copy_fail_title"),
                tr("pattern_copy_fail_body").format(detail=str(e)),
            )
            return
        pattern_path[0] = dest
        pat_info.setText(dest.as_posix())
        _schedule_preview()

    def _clear_pattern() -> None:
        pattern_path[0] = None
        pat_info.setText("—")
        _schedule_preview()

    br = QHBoxLayout()
    bp = QPushButton(tr("pick_pattern"))
    bc = QPushButton(tr("clear_pattern"))
    bp.clicked.connect(_pick_pattern)
    bc.clicked.connect(_clear_pattern)
    br.addWidget(bp)
    br.addWidget(bc)
    pg.addLayout(br)
    pg.addWidget(pat_info)
    pg.addWidget(cb_dialog)
    pg.addWidget(cb_input)
    pg.addWidget(cb_options)
    pg.addWidget(cb_numeric)

    pat_op_l = QLabel()
    pat_op_s = QSlider(Qt.Orientation.Horizontal)
    pat_op_s.setRange(0, 100)
    pat_op_s.setValue(100)

    def _pat_op_fmt(v: int) -> None:
        pat_op_l.setText(
            tr("slider_pattern_opacity").format(percent=v)
        )

    pat_op_s.valueChanged.connect(_pat_op_fmt)
    _pat_op_fmt(pat_op_s.value())
    pat_op_s.valueChanged.connect(lambda _v: _schedule_preview())
    pg.addWidget(pat_op_l)
    pg.addWidget(pat_op_s)

    left_l.addWidget(pat_box)

    gen_row = QHBoxLayout()
    gen_btn = QPushButton(tr("gen_json"))
    gen_row.addWidget(gen_btn)
    gen_row.addStretch(1)
    left_l.addLayout(gen_row)

    prev_row = QHBoxLayout()
    live_cb = QCheckBox(tr("live_preview"))
    live_cb.setChecked(False)
    stop_btn = QPushButton(tr("stop_preview"))
    prev_row.addWidget(live_cb)
    prev_row.addWidget(stop_btn)
    prev_row.addStretch(1)
    left_l.addLayout(prev_row)

    prev_note = QLabel(tr("preview_note"))
    prev_note.setWordWrap(True)
    left_l.addWidget(prev_note)

    left_l.addStretch(1)
    scroll.setWidget(left)
    splitter.addWidget(scroll)

    # --- 右侧：JSON ---
    right = QWidget()
    rl = QVBoxLayout(right)
    rl.setContentsMargins(0, 0, 0, 0)
    editor = QPlainTextEdit()
    editor.setPlaceholderText(tr("editor_placeholder"))
    editor.setMinimumWidth(280)
    rl.addWidget(editor, 1)

    btn_row = QHBoxLayout()
    load_btn = QPushButton(tr("load"))
    save_btn = QPushButton(tr("save"))
    example_btn = QPushButton(tr("from_example"))
    open_dir_btn = QPushButton(tr("open_data_folder"))
    btn_row.addWidget(load_btn)
    btn_row.addWidget(save_btn)
    btn_row.addWidget(example_btn)
    btn_row.addWidget(open_dir_btn)
    btn_row.addStretch(1)
    rl.addLayout(btn_row)
    splitter.addWidget(right)
    splitter.setSizes([360, 520])

    def _make_json_dict() -> dict:
        alpha = op_s.value() / 100.0
        return build_theme_dict(
            primary=colors["primary"],
            text=colors["text"],
            border=colors["border"],
            accent=colors["accent"],
            panel_alpha=alpha,
            radius=radius_s.value(),
            pattern_path=pattern_path[0],
            pattern_opacity=pat_op_s.value() / 100.0,
            pattern_dialog=cb_dialog.isChecked(),
            pattern_input=cb_input.isChecked(),
            pattern_options=cb_options.isChecked(),
            pattern_numeric=cb_numeric.isChecked(),
        )

    def _write_preview_file(data: dict) -> None:
        p = _preview_theme_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        set_chat_chrome_theme_preview_path(p)
        clear_chat_chrome_theme_cache()
        _refresh_open_chat_windows()

    def _apply_preview() -> None:
        if not live_cb.isChecked():
            return
        try:
            data = _make_json_dict()
        except Exception:
            return
        _write_preview_file(data)

    def _schedule_preview() -> None:
        debounce.start()

    debounce.timeout.connect(_apply_preview)

    def _generate_to_editor() -> None:
        try:
            data = _make_json_dict()
        except Exception as e:
            QMessageBox.warning(
                root,
                tr("gen_fail_title"),
                str(e),
            )
            return
        editor.setPlainText(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        if live_cb.isChecked():
            _write_preview_file(data)

    def _stop_preview() -> None:
        live_cb.blockSignals(True)
        live_cb.setChecked(False)
        live_cb.blockSignals(False)
        set_chat_chrome_theme_preview_path(None)
        clear_chat_chrome_theme_cache()
        _refresh_open_chat_windows()

    gen_btn.clicked.connect(_generate_to_editor)
    stop_btn.clicked.connect(_stop_preview)

    def _on_live_toggled(checked: bool) -> None:
        if checked:
            _apply_preview()
        else:
            set_chat_chrome_theme_preview_path(None)
            clear_chat_chrome_theme_cache()
            _refresh_open_chat_windows()

    live_cb.toggled.connect(_on_live_toggled)

    def _load_disk() -> None:
        live_cb.blockSignals(True)
        live_cb.setChecked(False)
        live_cb.blockSignals(False)
        set_chat_chrome_theme_preview_path(None)
        p = _default_theme_path()
        if p.is_file():
            editor.setPlainText(p.read_text(encoding="utf-8"))
        else:
            editor.setPlainText("{}")
        clear_chat_chrome_theme_cache()
        _refresh_open_chat_windows()

    def _save() -> None:
        live_cb.blockSignals(True)
        live_cb.setChecked(False)
        live_cb.blockSignals(False)
        set_chat_chrome_theme_preview_path(None)
        raw = editor.toPlainText().strip()
        if not raw:
            raw = "{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            QMessageBox.warning(
                root,
                tr("invalid_json_title"),
                tr("invalid_json_body").format(detail=str(e)),
            )
            return
        if not isinstance(data, dict):
            QMessageBox.warning(
                root,
                tr("invalid_json_title"),
                tr("invalid_json_not_object"),
            )
            return
        p = _default_theme_path()
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            pretty = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
            p.write_text(pretty, encoding="utf-8")
        except OSError as e:
            QMessageBox.warning(
                root,
                tr("save_fail_title"),
                tr("save_fail_body").format(detail=str(e)),
            )
            return
        clear_chat_chrome_theme_cache()
        _refresh_open_chat_windows()
        QMessageBox.information(
            root,
            tr("save_ok_title"),
            tr("save_ok_body"),
        )

    def _from_example() -> None:
        live_cb.blockSignals(True)
        live_cb.setChecked(False)
        live_cb.blockSignals(False)
        set_chat_chrome_theme_preview_path(None)
        ex = _example_theme_path()
        if not ex.is_file():
            QMessageBox.information(
                root,
                tr("example_missing_title"),
                tr("example_missing_body").format(path=ex.as_posix()),
            )
            return
        editor.setPlainText(ex.read_text(encoding="utf-8"))
        clear_chat_chrome_theme_cache()
        _refresh_open_chat_windows()

    def _open_dir() -> None:
        d = _default_theme_path().parent
        d.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(d.resolve().as_posix()))

    load_btn.clicked.connect(_load_disk)
    save_btn.clicked.connect(_save)
    example_btn.clicked.connect(_from_example)
    open_dir_btn.clicked.connect(_open_dir)

    def _on_close() -> None:
        set_chat_chrome_theme_preview_path(None)
        clear_chat_chrome_theme_cache()
        _refresh_open_chat_windows()

    root.destroyed.connect(_on_close)

    _load_disk()
    return root

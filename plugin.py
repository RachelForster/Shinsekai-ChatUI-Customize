from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from sdk.plugin import PluginBase
from sdk.plugin_host_context import PluginHostContext
from sdk.register import PluginCapabilityRegistry
from sdk.types import FrontendConfigContribution

from ui.chat_ui.theme_chrome import clear_chat_chrome_theme_cache, project_root


def _default_theme_path() -> Path:
    return project_root() / "data" / "chat_ui_theme.json"


def _load_theme_values() -> dict[str, Any]:
    path = _default_theme_path()
    if not path.is_file():
        return {"theme": {}}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raw = {}
    return {"theme": raw if isinstance(raw, dict) else {}}


def _save_theme_values(values: Mapping[str, object]) -> None:
    raw_theme = values.get("theme")
    if not isinstance(raw_theme, dict):
        raise ValueError("theme must be a JSON object")
    path = _default_theme_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw_theme, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    clear_chat_chrome_theme_cache()


class ChatUiThemePlugin(PluginBase):
    """在「设置 → 插件」中提供聊天主窗外观 JSON（data/chat_ui_theme.json）的可视化编辑。"""

    @property
    def plugin_id(self) -> str:
        return "com.shinsekai.chat_ui_customize"

    @property
    def plugin_version(self) -> str:
        return "0.2.0"

    @property
    def plugin_name(self) -> str:
        return "Chat UI theme"

    @property
    def plugin_description(self) -> str:
        return "编辑聊天主窗 QSS 补丁（对白、输入条、选项、麦克风等）；与 data/chat_ui_theme.json 同步。"

    @property
    def plugin_author(self) -> str:
        return "EasyAIDesktopAssistant"

    @property
    def priority(self) -> int:
        return 40

    def initialize(
        self,
        register: PluginCapabilityRegistry,
        plugin_root: Path,
        host: PluginHostContext,
    ) -> None:
        _ = plugin_root, host
        register.register_frontend_config_page(
            FrontendConfigContribution(
                page_id="chat_ui_theme.settings",
                title="Chat UI theme",
                kind="settings",
                description="Edit the raw data/chat_ui_theme.json theme payload used by the chat window.",
                restart_hint="Open chat windows refresh their chrome theme after saving.",
                schema=[
                    {
                        "fields": [
                            {
                                "defaultValue": {},
                                "description": "Root object written to data/chat_ui_theme.json.",
                                "key": "theme",
                                "label": "Theme JSON",
                                "span": "full",
                                "type": "json",
                            }
                        ],
                        "id": "theme",
                        "title": "Theme",
                    }
                ],
                i18n={
                    "zh_CN": {
                        "description": "编辑聊天窗口使用的 data/chat_ui_theme.json 原始主题配置。",
                        "groups": {
                            "theme": {
                                "fields": {
                                    "theme": {
                                        "description": "会写入 data/chat_ui_theme.json 的根对象。",
                                        "label": "主题 JSON",
                                    }
                                },
                                "title": "主题",
                            }
                        },
                        "restartHint": "保存后会刷新已打开聊天窗口的外观主题缓存。",
                        "title": "聊天外观主题",
                    },
                    "ja": {
                        "description": "チャット画面で使う data/chat_ui_theme.json のテーマ payload を編集します。",
                        "groups": {
                            "theme": {
                                "fields": {
                                    "theme": {
                                        "description": "data/chat_ui_theme.json に書き込まれる root object です。",
                                        "label": "テーマ JSON",
                                    }
                                },
                                "title": "テーマ",
                            }
                        },
                        "restartHint": "保存後、開いているチャット画面のテーマ cache を更新します。",
                        "title": "チャット外観テーマ",
                    },
                },
                load_values=_load_theme_values,
                save_values=_save_theme_values,
                order=42.0,
            )
        )

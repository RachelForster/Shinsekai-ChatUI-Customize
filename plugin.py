from __future__ import annotations

from pathlib import Path

from sdk.plugin import PluginBase
from sdk.plugin_host_context import PluginHostContext
from sdk.register import PluginCapabilityRegistry
from sdk.types import SettingsUIContribution

from plugins.chat_ui_customize.i18n import tr
from plugins.chat_ui_customize.settings_widget import build_chat_ui_theme_settings


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
        register.register_settings_ui(
            SettingsUIContribution(
                page_id="chat_ui_theme.settings",
                nav_label=tr("nav_label"),
                build=build_chat_ui_theme_settings,
                order=42.0,
            )
        )

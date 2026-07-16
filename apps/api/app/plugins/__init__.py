"""Plugin package — Extension SDK for ImpactFlow."""

from app.plugins.sdk import (
    PLUGIN_SDK_MANIFEST,
    PLUGIN_SDK_VERSION,
    PluginBuilder,
    clear_registry,
    register_plugin,
    registered_plugins,
)

__all__ = [
    "PLUGIN_SDK_MANIFEST",
    "PLUGIN_SDK_VERSION",
    "PluginBuilder",
    "clear_registry",
    "register_plugin",
    "registered_plugins",
]

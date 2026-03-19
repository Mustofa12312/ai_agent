"""
Tool Registry — Auto-discovers and manages all available tools.
"""
from .base import BaseTool
from typing import Dict, List, Optional


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def all_tools(self) -> List[BaseTool]:
        return list(self._tools.values())

    def schemas(self) -> List[Dict]:
        return [t.schema() for t in self._tools.values()]

    def run_tool(self, name: str, **kwargs) -> str:
        tool = self.get(name)
        if not tool:
            return f"❌ Tool '{name}' tidak ditemukan."
        return tool.safe_run(**kwargs)

    def list_names(self) -> List[str]:
        return list(self._tools.keys())


def build_registry(memory_manager=None, config: dict = None) -> ToolRegistry:
    """Build and return the default tool registry with all built-in tools."""
    from tools.file_tool import FileTool
    from tools.web_search_tool import WebSearchTool
    from tools.weather_tool import WeatherTool
    from tools.time_tool import TimeTool
    from tools.news_tool import NewsTool
    from tools.memory_tool import MemoryTool

    workspace = (config or {}).get("workspace_dir", "workspace")

    registry = ToolRegistry()
    registry.register(FileTool(workspace_dir=workspace))
    registry.register(WebSearchTool())
    registry.register(WeatherTool())
    registry.register(TimeTool())
    registry.register(NewsTool())
    if memory_manager:
        registry.register(MemoryTool(memory_manager=memory_manager))

    # Load plugins
    _load_plugins(registry)

    return registry


def _load_plugins(registry: ToolRegistry) -> None:
    """Auto-load plugins from the plugins/ directory."""
    import importlib, pkgutil, inspect, sys
    from pathlib import Path
    plugin_dir = Path(__file__).parent.parent / "plugins"
    if not plugin_dir.exists():
        return
    sys.path.insert(0, str(plugin_dir.parent))
    for _, module_name, _ in pkgutil.iter_modules([str(plugin_dir)]):
        if module_name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"plugins.{module_name}")
            for _, obj in inspect.getmembers(mod, inspect.isclass):
                if issubclass(obj, BaseTool) and obj is not BaseTool and obj.name != "base_tool":
                    registry.register(obj())
        except Exception as e:
            from utils.logger import log_error
            log_error(f"Plugin.{module_name}", e)

"""
LatheCadCam — entry point.

Usage:
  python main.py [recipe.json]

When launched from LinuxCNC (AXIS / GMOCCAPY / QtDragon) pass the recipe
path as the first argument so the part loads automatically.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

# Make sure the project root is importable regardless of CWD.
ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from domain.app_config import AppConfig
from domain.machine import MachineConfig
from domain.plugin_loader import PrimitivePluginLoader
from domain.tool_library import ToolLibrary
from ui.main_window import MainWindow


def _load_plugins() -> PrimitivePluginLoader:
    loader = PrimitivePluginLoader()
    loader.load(ROOT / "plugins" / "primitives")
    if loader.errors:
        for path, err in loader.errors:
            print(f"[WARN] Plugin load error {path.name}: {err}", file=sys.stderr)
    return loader


def _load_tools() -> ToolLibrary:
    path = ROOT / "data" / "tools" / "example_library.json"
    if path.exists():
        try:
            return ToolLibrary.load(path)
        except Exception as e:
            print(f"[WARN] Tool library load failed: {e}", file=sys.stderr)
    return ToolLibrary.empty()


def _load_machine() -> MachineConfig | None:
    path = ROOT / "data" / "machine_default.json"
    if path.exists():
        try:
            return MachineConfig.load(path)
        except Exception as e:
            print(f"[WARN] Machine config load failed: {e}", file=sys.stderr)
    return MachineConfig.default()


def _load_app_config() -> AppConfig:
    path = ROOT / "data" / "app_config.json"
    if path.exists():
        try:
            return AppConfig.load(path)
        except Exception as e:
            print(f"[WARN] App config load failed: {e}", file=sys.stderr)
    return AppConfig.default()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("LatheCadCam")
    app.setStyle("Fusion")

    loader     = _load_plugins()
    tools      = _load_tools()
    machine    = _load_machine()
    app_config = _load_app_config()

    win = MainWindow(
        loader=loader, tool_library=tools, machine=machine, app_config=app_config
    )

    # Optional: load recipe from command-line argument
    if len(sys.argv) > 1:
        recipe_path = Path(sys.argv[1])
        if recipe_path.exists():
            try:
                win._model.load_recipe(recipe_path)
            except Exception as e:
                print(f"[WARN] Could not load recipe: {e}", file=sys.stderr)

    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

"""
LatheCadCam — entry point.

Usage:
  python main.py [recipe.json] [--linuxcnc]

  --linuxcnc   Connect to a running LinuxCNC instance via the linuxcnc
               Python module.  Has no effect when the module is not available
               (safe to pass on development machines).
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

# Make sure the project root is importable regardless of CWD.
ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bridge.linuxcnc_driver import LinuxCNCDriver
from domain.app_config import AppConfig
from domain.machine import MachineConfig
from domain.material import MaterialLibrary
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


def _load_materials() -> MaterialLibrary:
    lib  = MaterialLibrary()
    path = ROOT / "data" / "materials" / "default.json"
    if path.exists():
        try:
            lib.load_file(path)
        except Exception as e:
            print(f"[WARN] Materials load failed: {e}", file=sys.stderr)
    return lib


def _parse_args() -> tuple[Path | None, bool]:
    """Return (recipe_path, use_linuxcnc) from sys.argv."""
    recipe_path: Path | None = None
    use_linuxcnc = False
    for arg in sys.argv[1:]:
        if arg == "--linuxcnc":
            use_linuxcnc = True
        elif not arg.startswith("-"):
            p = Path(arg)
            if p.exists():
                recipe_path = p
    return recipe_path, use_linuxcnc


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("LatheCadCam")
    app.setStyle("Fusion")

    recipe_path, use_linuxcnc = _parse_args()
    driver = LinuxCNCDriver() if use_linuxcnc else None

    loader    = _load_plugins()
    tools     = _load_tools()
    machine   = _load_machine()
    app_cfg   = _load_app_config()
    materials = _load_materials()

    win = MainWindow(
        loader=loader, tool_library=tools, machine=machine,
        app_config=app_cfg, material_library=materials, driver=driver,
    )

    if recipe_path:
        try:
            win._model.load_recipe(recipe_path)
        except Exception as e:
            print(f"[WARN] Could not load recipe: {e}", file=sys.stderr)

    if driver and driver.available:
        print("[INFO] LinuxCNC connection established.", file=sys.stderr)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

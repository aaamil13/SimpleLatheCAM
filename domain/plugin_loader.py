"""
Plug-in loader for LathePrimitive subclasses.

Scans a directory for .py files, imports each one, and registers every
concrete subclass of LathePrimitive it finds.  No explicit registration
is needed — dropping a new file in the directory is sufficient.

Usage:
    loader = PrimitivePluginLoader()
    loader.load(Path("plugins/primitives"))

    for primitive in loader.all():
        print(primitive.name, primitive.display_name)

    cyl = loader.get("cylinder")   # -> CylinderPrimitive instance, or None
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from domain.primitive_base import LathePrimitive


class PluginLoadError(Exception):
    """Raised when a plug-in file cannot be imported or contains bad code."""


class PrimitivePluginLoader:
    def __init__(self) -> None:
        self._plugins: dict[str, LathePrimitive] = {}
        self._errors: list[tuple[Path, Exception]] = []

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self, directory: Path) -> None:
        """
        Scan *directory* for .py files and register every LathePrimitive
        subclass found.  Files starting with '_' are skipped.

        Errors are collected in self.errors rather than raised so that a
        single bad plug-in does not prevent the rest from loading.
        """
        if not directory.is_dir():
            raise PluginLoadError(f"Plugin directory not found: {directory}")

        for path in sorted(directory.glob("*.py")):
            if path.stem.startswith("_"):
                continue
            try:
                module = self._import_file(path)
                self._register_from_module(module, path)
            except Exception as exc:
                self._errors.append((path, exc))

    def _import_file(self, path: Path) -> ModuleType:
        module_name = f"_lathe_plugin_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise PluginLoadError(f"Cannot create module spec for {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def _register_from_module(self, module: ModuleType, source: Path) -> None:
        for attr_name in dir(module):
            obj = getattr(module, attr_name)
            if (
                isinstance(obj, type)
                and issubclass(obj, LathePrimitive)
                and obj is not LathePrimitive
                and not getattr(obj, "__abstractmethods__", None)
            ):
                instance = obj()
                key = instance.name
                if key in self._plugins:
                    raise PluginLoadError(
                        f"Duplicate primitive name '{key}' "
                        f"(from {source}, already registered by "
                        f"{type(self._plugins[key]).__module__})"
                    )
                self._plugins[key] = instance

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def all(self) -> list[LathePrimitive]:
        """All loaded primitives, sorted by category then display_name."""
        return sorted(
            self._plugins.values(),
            key=lambda p: (p.category, p.display_name),
        )

    def by_category(self) -> dict[str, list[LathePrimitive]]:
        """Primitives grouped by category — useful for building toolbar sections."""
        groups: dict[str, list[LathePrimitive]] = {}
        for p in self.all():
            groups.setdefault(p.category, []).append(p)
        return groups

    def get(self, name: str) -> LathePrimitive | None:
        """Return the primitive with the given name, or None."""
        return self._plugins.get(name)

    def names(self) -> list[str]:
        return list(self._plugins.keys())

    @property
    def errors(self) -> list[tuple[Path, Exception]]:
        """Load errors collected during the last load() call."""
        return list(self._errors)

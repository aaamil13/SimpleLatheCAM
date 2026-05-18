"""
EditorModel — central application state and mutation hub.

Holds the PartRecipe, the last-built LatheProfile, and the selection.
All UI widgets read from and write to this model; no widget talks directly
to another.

Signals
-------
  recipe_changed   — recipe was mutated; profile was rebuilt
  selection_changed — selected (seq_idx, op_idx) changed (either may be -1)
  error_occurred   — non-fatal error string (e.g. validation failure)
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal

from domain.material import MaterialLibrary
from domain.plugin_loader import PrimitivePluginLoader
from domain.primitive_base import ProfileContext
from domain.profile import LatheProfile
from domain.recipe import OperationRecord, PartRecipe, StockSpec, ToolSequence
from domain.tool import SpindleMode, ToolDirection
from domain.tool_library import ToolLibrary


class EditorModel(QObject):
    recipe_changed    = Signal()
    selection_changed = Signal(int, int)   # seq_idx, op_idx  (-1 = none)
    error_occurred    = Signal(str)

    def __init__(
        self,
        loader:           PrimitivePluginLoader,
        tool_library:     Optional[ToolLibrary]     = None,
        material_library: Optional[MaterialLibrary] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._loader    = loader
        self._tools     = tool_library or ToolLibrary.empty()
        self._materials = material_library or MaterialLibrary()
        self._recipe   = PartRecipe.default()
        self._profile  = self._rebuild()
        self._sel_seq  = -1
        self._sel_op   = -1

    # ------------------------------------------------------------------
    # Read accessors
    # ------------------------------------------------------------------

    @property
    def recipe(self) -> PartRecipe:
        return self._recipe

    @property
    def profile(self) -> LatheProfile:
        return self._profile

    @property
    def selected_seq(self) -> int:
        return self._sel_seq

    @property
    def selected_op(self) -> int:
        return self._sel_op

    @property
    def loader(self) -> PrimitivePluginLoader:
        return self._loader

    @property
    def tool_library(self) -> ToolLibrary:
        return self._tools

    @tool_library.setter
    def tool_library(self, lib: ToolLibrary) -> None:
        self._tools = lib

    @property
    def material_library(self) -> MaterialLibrary:
        return self._materials

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def select(self, seq_idx: int, op_idx: int) -> None:
        self._sel_seq = seq_idx
        self._sel_op  = op_idx
        self.selection_changed.emit(seq_idx, op_idx)

    def selected_operation(self) -> Optional[OperationRecord]:
        if self._sel_seq < 0 or self._sel_op < 0:
            return None
        seqs = self._recipe.tool_sequences
        if self._sel_seq >= len(seqs):
            return None
        ops = seqs[self._sel_seq].operations
        if self._sel_op >= len(ops):
            return None
        return ops[self._sel_op]

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def new_recipe(self, stock_d: float = 50.0, stock_l: float = 150.0) -> None:
        self._recipe = PartRecipe.default(stock_d=stock_d, stock_l=stock_l)
        self._profile = self._rebuild()
        self._sel_seq = -1
        self._sel_op  = -1
        self.recipe_changed.emit()

    def load_recipe(self, path) -> None:
        self._recipe  = PartRecipe.load(path)
        self._profile = self._rebuild()
        self._sel_seq = -1
        self._sel_op  = -1
        self.recipe_changed.emit()

    def save_recipe(self, path) -> None:
        self._recipe.save(path)

    def update_stock(self, diameter: float, length: float, material_key: str) -> None:
        self._recipe.stock.diameter     = diameter
        self._recipe.stock.length       = length
        self._recipe.stock.material_key = material_key
        self._profile = self._rebuild()
        self.recipe_changed.emit()

    def add_operation(
        self,
        primitive_name: str,
        direction: ToolDirection = ToolDirection.EXTERNAL,
    ) -> None:
        plugin = self._loader.get(primitive_name)
        if plugin is None:
            self.error_occurred.emit(f"Unknown primitive: {primitive_name}")
            return
        params = plugin.default_params()
        op = OperationRecord(
            primitive_name=primitive_name,
            params=params,
            direction=direction,
        )
        # Ensure at least one ToolSequence exists
        if not self._recipe.tool_sequences:
            self._recipe.tool_sequences.append(ToolSequence(tool_id=1))
        seq_idx = max(self._sel_seq, 0)
        if seq_idx >= len(self._recipe.tool_sequences):
            seq_idx = len(self._recipe.tool_sequences) - 1
        self._recipe.tool_sequences[seq_idx].operations.append(op)
        op_idx = len(self._recipe.tool_sequences[seq_idx].operations) - 1
        self._mutated(seq_idx, op_idx)

    def update_params(self, params: dict) -> None:
        op = self.selected_operation()
        if op is None:
            return
        op.params = dict(params)
        self._mutated(self._sel_seq, self._sel_op)

    def update_coolant_override(self, coolant_on: Optional[bool]) -> None:
        op = self.selected_operation()
        if op is None:
            return
        op.coolant_on = coolant_on
        self._mutated(self._sel_seq, self._sel_op)

    def insert_operation_before(self, primitive_name: str) -> None:
        """Insert a new operation before the currently selected one."""
        self._insert_at(primitive_name, offset=0)

    def insert_operation_after(self, primitive_name: str) -> None:
        """Insert a new operation after the currently selected one."""
        self._insert_at(primitive_name, offset=1)

    def _insert_at(self, primitive_name: str, offset: int) -> None:
        plugin = self._loader.get(primitive_name)
        if plugin is None:
            self.error_occurred.emit(f"Unknown primitive: {primitive_name}")
            return
        op = OperationRecord(
            primitive_name=primitive_name,
            params=plugin.default_params(),
        )
        if not self._recipe.tool_sequences:
            self._recipe.tool_sequences.append(ToolSequence(tool_id=1))
        seq_idx = max(self._sel_seq, 0)
        if seq_idx >= len(self._recipe.tool_sequences):
            seq_idx = len(self._recipe.tool_sequences) - 1
        seq = self._recipe.tool_sequences[seq_idx]
        if not seq.operations or self._sel_op < 0:
            seq.operations.append(op)
            self._mutated(seq_idx, len(seq.operations) - 1)
        else:
            insert_at = self._sel_op + offset
            seq.operations.insert(insert_at, op)
            self._mutated(seq_idx, insert_at)

    def remove_selected(self) -> None:
        op = self.selected_operation()
        if op is None:
            return
        ops = self._recipe.tool_sequences[self._sel_seq].operations
        ops.remove(op)
        self._sel_op = min(self._sel_op, len(ops) - 1)
        self._mutated(self._sel_seq, self._sel_op)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _mutated(self, sel_seq: int, sel_op: int) -> None:
        self._profile = self._rebuild()
        self._sel_seq = sel_seq
        self._sel_op  = sel_op
        self.recipe_changed.emit()
        self.selection_changed.emit(sel_seq, sel_op)

    def insert_at(
        self,
        seq_idx: int,
        op_idx: int,
        primitive_name: str,
        direction: ToolDirection,
    ) -> None:
        """Insert a new operation at an absolute position (used by canvas context menu)."""
        plugin = self._loader.get(primitive_name)
        if plugin is None:
            self.error_occurred.emit(f"Unknown primitive: {primitive_name}")
            return
        op = OperationRecord(
            primitive_name=primitive_name,
            params=plugin.default_params(),
            direction=direction,
        )
        if seq_idx >= len(self._recipe.tool_sequences):
            return
        self._recipe.tool_sequences[seq_idx].operations.insert(op_idx, op)
        self._mutated(seq_idx, op_idx)

    def _rebuild(self) -> LatheProfile:
        stock = self._recipe.stock
        profile = LatheProfile(stock_d=stock.diameter, stock_l=stock.length)
        for si, seq in enumerate(self._recipe.tool_sequences):
            for oi, op in enumerate(seq.enabled_operations):
                profile.active_tag = (si, oi)
                plugin = self._loader.get(op.primitive_name)
                if plugin is None:
                    continue
                try:
                    plugin.build(profile, op.params)
                except Exception as e:
                    self.error_occurred.emit(str(e))
                    break
        return profile

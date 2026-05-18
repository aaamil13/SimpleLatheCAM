"""
Base class for all lathe primitive plug-ins.

Each plug-in is a single .py file in plugins/primitives/ that defines exactly
one concrete subclass of LathePrimitive.  The plugin_loader discovers them by
scanning that directory — no explicit registration required.

Responsibilities of a plug-in:
  - Declare its parameters via params_schema (drives the UI panel automatically)
  - Validate those parameters, with optional profile-context checks
  - Build geometry by appending segments to a LatheProfile
  - Draw a static symbolic icon for the toolbar button (QPainter, no params needed)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtGui import QPainter
    from PySide6.QtCore import QRect
    from domain.profile import LatheProfile


# ---------------------------------------------------------------------------
# Parameter descriptor
# ---------------------------------------------------------------------------

@dataclass
class ParamSpec:
    """Describes one numeric input field for a primitive."""

    name: str          # internal key used in params dict and JSON
    label: str         # displayed in the UI panel
    unit: str          # "mm", "deg", or "" for dimensionless
    default: float
    min_val: float
    max_val: float
    tooltip: str = ""
    step: float = field(default=0.0)  # spinner step; 0 → auto (0.1 for mm, 1 for deg)

    def __post_init__(self) -> None:
        if self.step == 0.0:
            self.step = 1.0 if self.unit == "deg" else 0.1


# ---------------------------------------------------------------------------
# Profile context (read-only snapshot passed to validate/build)
# ---------------------------------------------------------------------------

@dataclass
class ProfileContext:
    """
    Lightweight snapshot of the current profile state passed to plug-ins so
    they can do context-aware validation without depending on the full
    LatheProfile implementation.

    ``machine`` is optional — plug-ins that need machine limits (e.g. RapidTo)
    check ``getattr(context, 'machine', None)`` and fall back to wide defaults
    when it is absent, so the system works without a config file.
    """

    cursor_x: float      # current diameter at the tool cursor (mm, radius*2)
    cursor_z: float      # current Z position (mm, negative = into part)
    stock_d: float       # original stock diameter
    stock_l: float       # original stock length
    segment_count: int   # number of segments already in the profile
    machine: "object | None" = field(default=None)   # MachineConfig | None


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------

class LathePrimitive(ABC):
    """
    Abstract base for every lathe primitive plug-in.

    Subclass this, implement all abstract members, place the file in
    plugins/primitives/, and the loader will pick it up automatically.
    """

    # ------------------------------------------------------------------
    # Identity  (pure data — override as class-level properties or attrs)
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique snake_case key, e.g. 'cylinder'.  Used in JSON recipes."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Short human-readable label shown on the toolbar button."""

    @property
    def category(self) -> str:
        """
        Grouping for the toolbar.  Override to place the primitive in a
        specific group.  Defaults to 'General'.
        """
        return "General"

    @property
    def tooltip(self) -> str:
        """Longer description shown as a tooltip.  Defaults to display_name."""
        return self.display_name

    @property
    def min_segments(self) -> int:
        """Minimum number of existing profile segments required before this
        primitive can be applied.  Override to 1+ for primitives that need a
        previous segment (e.g. fillet).  Used by the test harness and UI."""
        return 0

    # ------------------------------------------------------------------
    # Parameters
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def params_schema(self) -> list[ParamSpec]:
        """
        Ordered list of parameter descriptors.  The UI panel is generated
        automatically from this list — no manual form code needed.
        """

    def default_params(self) -> dict[str, float]:
        """Convenience: returns {name: default} for every ParamSpec."""
        return {p.name: p.default for p in self.params_schema}

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(
        self,
        params: dict[str, float],
        context: ProfileContext,
    ) -> str | None:
        """
        Return an error message string if validation fails, or None if OK.

        Two levels of checks happen here:
          1. Range checks against ParamSpec.min_val / max_val
          2. Context checks against the current profile state

        The base implementation only performs range checks.  Override to add
        context-aware rules (e.g. 'chamfer cannot exceed the previous step').
        """
        for spec in self.params_schema:
            val = params.get(spec.name, spec.default)
            if val < spec.min_val:
                return (
                    f"{spec.label}: {val} {spec.unit} "
                    f"is below minimum {spec.min_val} {spec.unit}"
                )
            if val > spec.max_val:
                return (
                    f"{spec.label}: {val} {spec.unit} "
                    f"exceeds maximum {spec.max_val} {spec.unit}"
                )
        return None

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------

    @abstractmethod
    def build(
        self,
        profile: "LatheProfile",
        params: dict[str, float],
    ) -> None:
        """
        Append one or more segments to *profile*.

        Must advance profile.cursor_x and profile.cursor_z appropriately.
        Raise ValueError (with a user-readable message) for geometry errors
        that only become apparent during construction (e.g. arc too large).
        """

    # ------------------------------------------------------------------
    # Visualisation
    # ------------------------------------------------------------------

    @abstractmethod
    def draw_icon(self, painter: "QPainter", rect: "QRect") -> None:
        """
        Draw a static symbolic sketch of this primitive into *rect* using
        *painter*.  The sketch represents the shape, not specific dimensions.

        Guidelines:
          - Use painter.setPen() / painter.drawLine() / painter.drawArc()
          - Coordinate origin: rect.topLeft(); full area: rect
          - Do NOT depend on params — the icon is cached once at load time
          - Keep the sketch recognisable at 48×48 px
        """

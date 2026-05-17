"""
ToolOptimizer — minimize tool changes for a given recipe.

Problem
-------
Given an ordered list of ToolSequences (each bound to a tool_id) and a set
of available Tool objects, find an assignment that:
  1. Uses only available tools.
  2. Groups compatible consecutive operations under the same tool where
     possible (reducing physical tool changes).
  3. Minimises the total number of distinct tool slots required.

Compatibility rules
-------------------
A tool T can substitute for another tool S on a given operation when:
  - Same holder direction (external / internal).
  - T.nose_radius <= S.nose_radius  (finer tool can always replace coarser).
  - For roughing ops: T.nose_radius >= min_roughing_radius (default 0.4).
  - For parting ops:  T.insert.ic_size matches exactly (blade width).

The optimizer is intentionally simple (greedy sequential grouping) so it
runs instantly on the small sequences typical for lathe parts.  A future
version could use integer-programming for machines with many ATC positions.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.tool import CuttingData, Tool, ToolDirection


# ---------------------------------------------------------------------------
# Operation requirement descriptor
# ---------------------------------------------------------------------------

@dataclass
class OpRequirement:
    """
    Minimal tool requirement for one operation in a recipe.

    op_name       : primitive name (e.g. "cylinder", "chamfer", "parting")
    direction     : external or internal
    is_roughing   : True  → coarser tools acceptable
    is_parting    : True  → must match blade width exactly
    max_nose_radius: upper bound on nose_radius (for finishing, e.g. 0.4 mm)
    min_nose_radius: lower bound (for roughing, e.g. 0.4 mm acceptable)
    blade_width   : required blade width for parting (0 = not a parting op)
    preferred_tool_id : tool_id from the recipe (user's explicit choice, if any)
    """
    op_name:           str
    direction:         ToolDirection    = ToolDirection.EXTERNAL
    is_roughing:       bool             = False
    is_parting:        bool             = False
    max_nose_radius:   float            = 9999.0
    min_nose_radius:   float            = 0.0
    blade_width:       float            = 0.0
    preferred_tool_id: int | None       = None


# ---------------------------------------------------------------------------
# Compatibility check
# ---------------------------------------------------------------------------

def can_tool_do(tool: Tool, req: OpRequirement) -> bool:
    """Return True if *tool* satisfies *req*."""
    if tool.direction != req.direction:
        return False
    r = tool.nose_radius
    if r < req.min_nose_radius or r > req.max_nose_radius:
        return False
    if req.is_parting and req.blade_width > 0:
        # For parting: insert ic_size must match the blade width within 0.1 mm
        if abs(tool.insert.ic_size - req.blade_width) > 0.1:
            return False
    return True


# ---------------------------------------------------------------------------
# Optimisation result
# ---------------------------------------------------------------------------

@dataclass
class ToolGroup:
    """
    One group of consecutive operations assigned to a single tool.
    A group boundary = one tool change event.
    """
    tool_id:      int
    op_indices:   list[int]    = field(default_factory=list)
    is_manual_change: bool     = True    # False only for ATC


@dataclass
class OptimizationResult:
    groups:          list[ToolGroup]
    warnings:        list[str]          = field(default_factory=list)
    tool_changes:    int                = 0

    @property
    def is_feasible(self) -> bool:
        return not any("No tool" in w for w in self.warnings)


# ---------------------------------------------------------------------------
# ToolOptimizer
# ---------------------------------------------------------------------------

class ToolOptimizer:
    """
    Greedy sequential optimizer for tool-change minimisation.

    Usage::

        optimizer = ToolOptimizer(available_tools)
        result = optimizer.optimize(requirements, has_atc=False)
        for group in result.groups:
            print(group.tool_id, group.op_indices)
    """

    def __init__(self, available_tools: list[Tool]) -> None:
        self._tools = available_tools

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def optimize(
        self,
        requirements: list[OpRequirement],
        has_atc: bool = False,
    ) -> OptimizationResult:
        """
        Assign tools to operations, minimising the number of tool changes.

        Strategy
        --------
        For each unassigned operation (in order):
          1. Try to extend the current active tool's group if compatible.
          2. Otherwise, pick the tool that covers the most *remaining*
             consecutive operations (greedy look-ahead).
          3. If no tool covers the operation, record a warning and skip.
        """
        if not requirements:
            return OptimizationResult(groups=[])

        groups: list[ToolGroup] = []
        warnings: list[str] = []
        i = 0

        while i < len(requirements):
            req = requirements[i]

            # If there is an active group, try to extend it
            if groups:
                current_tool = self._get_tool(groups[-1].tool_id)
                if current_tool and can_tool_do(current_tool, req):
                    groups[-1].op_indices.append(i)
                    i += 1
                    continue

            # Need a new tool — find the best one
            best_tool = self._best_tool_for(requirements, i)
            if best_tool is None:
                warnings.append(
                    f"No tool available for operation {i} "
                    f"({req.op_name}, {req.direction.value})"
                )
                i += 1
                continue

            groups.append(ToolGroup(
                tool_id=best_tool.tool_id,
                op_indices=[i],
                is_manual_change=not has_atc,
            ))
            i += 1

        changes = max(0, len(groups) - 1)
        return OptimizationResult(
            groups=groups,
            warnings=warnings,
            tool_changes=changes,
        )

    def validate_recipe_tools(
        self,
        required_ids: list[int],
    ) -> list[str]:
        """
        Return a list of warning strings for tool IDs in *required_ids*
        that are not present in the available tool list.
        """
        available_ids = {t.tool_id for t in self._tools}
        return [
            f"Tool T{tid} is required but not in the available inventory."
            for tid in required_ids
            if tid not in available_ids
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_tool(self, tool_id: int) -> Tool | None:
        return next((t for t in self._tools if t.tool_id == tool_id), None)

    def _best_tool_for(
        self,
        requirements: list[OpRequirement],
        start: int,
    ) -> Tool | None:
        """
        Among all available tools that satisfy requirements[start], return
        the one that also satisfies the most *consecutive* requirements
        beginning at *start*.

        Respects preferred_tool_id if set on the requirement.
        """
        req = requirements[start]

        # Honour user's explicit tool choice if available
        if req.preferred_tool_id is not None:
            preferred = self._get_tool(req.preferred_tool_id)
            if preferred and can_tool_do(preferred, req):
                return preferred

        best_tool: Tool | None = None
        best_run = -1

        for tool in self._tools:
            if not can_tool_do(tool, req):
                continue
            run = self._consecutive_run(tool, requirements, start)
            if run > best_run:
                best_run = run
                best_tool = tool

        return best_tool

    def _consecutive_run(
        self,
        tool: Tool,
        requirements: list[OpRequirement],
        start: int,
    ) -> int:
        """Count how many consecutive requirements from *start* *tool* satisfies."""
        count = 0
        for req in requirements[start:]:
            if can_tool_do(tool, req):
                count += 1
            else:
                break
        return count

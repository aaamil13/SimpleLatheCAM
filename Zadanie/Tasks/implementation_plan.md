# LatheCadCam — Implementation Plan

> **Legend:** `[ ]` todo · `[x]` done · `[~]` in progress · `[!]` blocked

---

## Phase 1 — Core Domain (foundation for everything else)

### 1.1  Profile geometry
- [x] `domain/primitive_base.py` — `LathePrimitive` ABC, `ParamSpec`, `ProfileContext`
- [x] `domain/plugin_loader.py` — directory scanner, auto-discovery
- [x] `domain/profile.py` — `LatheProfile`, `LineSegment`, `ArcSegment`
  - cursor tracking (`cursor_x`, `cursor_z`)
  - `add_cylinder(d, length)`
  - `add_taper(d_end, length)`
  - `add_arc(radius, direction)` — fillet/radius
  - `add_line_to(x, z)` — generic absolute move
  - `to_polygon(arc_resolution)` — flat point list for pyclipper
  - `to_gcode_segments()` — typed segment list for finishing pass writer

### 1.2  Machine configuration
- [x] `domain/machine.py` — `MachineConfig`, `AxisLimits`, `SafePositions`
  - `AxisLimits`: `x_min`, `x_max`, `z_min`, `z_max` (software limits in mm)
  - `SafePositions`: `x_home`, `z_home`, `x_tool_change`, `z_tool_change`,
    `x_clearance` (radial clearance above stock for rapids)
  - `MachineConfig`: axis limits, safe positions, `max_spindle_rpm`,
    `x_rapid_speed`, `z_rapid_speed`, `chuck_diameter`, `bar_capacity`,
    `coolant_available: bool`
  - `load(path)` / `save(path)` — JSON
  - `default()` — reasonable defaults (can run without a config file)
- [x] `data/machine_default.json` — template for a typical hobby lathe
- [x] `plugins/primitives/rapid_to.py` — **RapidTo** positioning primitive
  - Category: `"Machine"`
  - Params: `x_target` (diameter), `z_target`
  - Validates against `MachineConfig` axis limits
  - Generates `G00 X{d/2} Z{z}` (no geometry added to profile)
  - Use case: explicit safe-position move between tool sequences
- [x] `domain/machine_tools.py` — `InstalledTool`, `MachineToolConfig`
  - installed tools (turret positions, ATC or manual)
  - available tools (shop inventory linked to ToolLibrary)
  - missing_from_available / missing_from_installed helpers
- [x] `domain/tool_optimizer.py` — `ToolOptimizer`, `OpRequirement`, `can_tool_do`
  - greedy look-ahead: assigns available tools to operations
  - minimises tool changes (groups consecutive compatible operations)
  - respects user's explicit preferred_tool_id
  - warns when no available tool covers an operation

### 1.3  Tool model
- [x] `domain/tool.py`
  - `CuttingData` dataclass: material key, `vc_rec`, `vc_max`, `fn_rec`, `fn_max`, `ap_rec`, `ap_max`
  - `ToolInsert`: ISO 1832 — shape letter, clearance angle, nose_radius, size
  - `ToolHolder`: approach angle, hand (L/R/N), shank size, direction (external/internal)
  - `Tool`: insert + holder + id + `cutting_data: dict[str, CuttingData]`
  - `ToolLibrary`: load/save JSON, lookup by id or manufacturer+code
- [x] `domain/tool_library.py` — serialisation, ToolLibrary CRUD

### 1.4  Material library
- [x] `domain/material.py`
  - `Material` dataclass: name, key, density, hardness category
- [x] `data/materials/default.json` — Steel_45, St37, Aluminium_6061, Brass, Cast_Iron

### 1.5  Recipe serialization
- [x] `domain/recipe.py`
  - `OperationRecord`: primitive name + params dict + direction (external/internal)
  - `ToolSequence`: tool_id + spindle_mode + operations list
  - `PartRecipe`: part_name + stock (D, L, material) + ordered list of ToolSequences
  - `save(path)` / `load(path)` — JSON round-trip

---

## Phase 2 — Primitive Plug-ins

- [x] `plugins/primitives/cylinder.py` — straight cylindrical step
- [x] `plugins/primitives/chamfer.py` — angled bevel (custom angle)
- [x] `plugins/primitives/taper.py` — conical step (D_start → D_end over L)
- [x] `plugins/primitives/fillet.py` — concave/convex radius between two steps
- [x] `plugins/primitives/face_turn.py` — face the end of the part
- [x] `plugins/primitives/groove.py` — rectangular or V groove (external/internal)
- [x] `plugins/primitives/parting.py` — cut-off with chip breaking
  - **Chip break modes** (ParamSpec `chip_break_mode` as enum choice):
    - `none` — continuous feed to full depth
    - `peck` — feed `peck_depth` mm, retract `retract_amount` mm, repeat
    - `full_retract` — feed `peck_depth` mm, retract to safe Z, re-enter, repeat
  - Params: `x_target` (final diameter, 0 = full cut-off), `peck_depth`, `retract_amount`, `safe_x`
  - Validation: warn if `peck_depth` > blade_width (tool data)

---

## Phase 3 — CAM Engine

### 3.1  Roughing
- [ ] `cam/roughing.py`
  - `RoughingPass` dataclass: list of (x, z) move tuples + feed_rate
  - `ExternalRougher`: pyclipper offset + horizontal slicing
  - `InternalRougher`: same but inverted polygon direction
  - Input: `LatheProfile`, `Tool`, step_down, stock polygon
  - Output: list of `RoughingPass`

### 3.2  Finishing
- [ ] `cam/finishing.py`
  - Walk `profile.to_gcode_segments()`
  - Output: G1 for lines, G2/G3 for arcs (with IJK or R)
  - Wrap with `G42 D{tool_id}` / `G40` (LinuxCNC handles offset)
  - Internal: use `G41` instead of `G42`

### 3.3  G-code writer
- [ ] `cam/gcode_writer.py`
  - Header: `G21 G18 G90 G40`
  - Spindle modes:
    - **Constant RPM** → `G97 S{rpm} M3`
    - **Constant surface speed (CSS)** → `G96 S{vc} D{max_rpm} M3`
      (`max_rpm` comes from `MachineConfig.max_spindle_rpm`)
  - Rapid approach/retract generated from `MachineConfig.safe_positions`
    (approach: `G00 X{clearance} Z{start+2mm}` before each pass)
  - Per ToolSequence: tool-change rapid to `z_tool_change`, `T{id} M6`,
    spindle setup, roughing block, finishing block, retract to `x_clearance`, `M9`
  - Footer: `G00 X{x_home} Z{z_home}`, `M5 M30`
  - Auto-compute RPM from `vc_recommended` and current diameter when CSS mode is active

---

## Phase 4 — User Interface (PySide6 standalone)

### 4.1  2D Canvas
- [ ] `ui/canvas_2d.py` — `LatheCanvas(QWidget)`
  - Draw stock outline (dashed)
  - Draw part profile (solid, coloured by tool)
  - Draw roughing passes (thin grey lines)
  - Draw finishing pass (green)
  - Draw tool indicator at cursor (nose radius circle)
  - Draw machine limit guides (soft-limit lines from `MachineConfig`)
  - Draw safe-position markers (tool-change position, home)
  - Zoom + pan (mouse wheel + drag)

### 4.2  Operation tree
- [ ] `ui/operation_tree.py` — `OperationTree(QTreeWidget)`
  - Top-level nodes: ToolSequence (shows T id + type)
  - Children: OperationRecord (primitive icon + summary line)
  - Drag-drop reordering within a sequence
  - Right-click: delete, duplicate, move to other tool

### 4.3  Parameters panel
- [ ] `ui/params_panel.py` — `ParamsPanel(QWidget)`
  - Auto-generated from `LathePrimitive.params_schema`
  - `QDoubleSpinBox` per param with unit label
  - Inline error display from `validate()`
  - Emits `params_changed` signal → triggers canvas redraw

### 4.4  Tool editor / library browser
- [ ] `ui/tool_editor.py`
  - List of tools from `ToolLibrary`
  - ISO 1832 dropdowns: shape, clearance, nose_radius, hand
  - Per-material cutting data table (`CuttingData` rows)
  - Manufacturer filter (Sandvik, Mitsubishi, Walter, Custom)
  - Import from JSON / export to JSON

### 4.5  Primitive picker toolbar
- [ ] `ui/primitive_toolbar.py`
  - One button per loaded plug-in (icon from `draw_icon()`)
  - Grouped by `LathePrimitive.category`
  - Click → appends new operation with default params to active ToolSequence

### 4.6  Main window
- [ ] `ui/main_window.py` — `MainWindow(QMainWindow)`
  - Layout: toolbar top, operation tree left, canvas centre, params panel right
  - Menu: File (new/open/save recipe, export G-code), View (2D/3D toggle), Machine (send to LinuxCNC)
  - Status bar: cursor X/Z, current tool, last error

### 4.7  3D viewer (on-demand)
- [ ] `ui/canvas_3d.py`
  - CadQuery: revolve `LatheProfile` 360° around Z axis
  - Render with pyqtgraph `GLViewWidget` or VTK
  - Opened via View → 3D Preview button

---

## Phase 5 — LinuxCNC Bridge

- [ ] `bridge/linuxcnc_driver.py`
  - `LinuxCNCDriver`: wraps `linuxcnc.command()` + `linuxcnc.stat()`
  - Graceful fallback when `import linuxcnc` fails (simulation mode)
  - `inject_gcode(path)`: checks `INTERP_IDLE`, switches to `MODE_AUTO`, calls `program_open()`
  - `get_status()` → neutral dict (estop, interp_state, current_tool, loaded_file)
  - `get_tool_table()` → parse `tool.tbl`, return list of tool dicts
  - `sync_tool_library(tool_library)` → write back to `tool.tbl`

---

## Phase 6 — Integration & Configuration

- [ ] `main.py` — app entry point, loads plugins, opens MainWindow
- [ ] `tests/test_plugin_loader.py` [x] done
- [x] `tests/test_profile.py` — segment building, cursor tracking, polygon export
- [ ] `tests/test_roughing.py` — pyclipper pass generation
- [ ] `tests/test_gcode_writer.py` — G-code output correctness
- [ ] `config/linuxcnc_qtdragon.ini.example` — INI snippet for QtDragon button
- [ ] `config/linuxcnc_gmoccapy.ini.example` — INI snippet for GMOCCAPY button
- [ ] `config/linuxcnc_axis.axisrc.example` — axisrc F12 binding

---

## Deferred (v2)

- [ ] Threading operations (G76 cycle) — plug-in `parting_thread.py`
- [ ] DXF/SVG profile import (ezdxf)
- [ ] Boring bar internal operations beyond simple cylinders
- [ ] Multi-start thread support
- [ ] Tool wear compensation / tool life tracking
- [ ] Direct HAL signal integration (spindle override, feed override read-back)

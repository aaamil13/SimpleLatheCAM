# LatheCadCam (formerly SimpleLatheCAM)

> **⚠️ CRITICAL WARNING: PRE-ALPHA SOFTWARE ⚠️**
> 
> This project is currently under **heavy, active development**. The codebase is highly volatile and changes on a daily basis. 
> 
> **NOTHING IN THIS REPOSITORY HAS BEEN TESTED ON A REAL CNC MACHINE YET.**
> 
> Generating G-code with this software and running it on a physical lathe may result in severe machine crashes, damage to equipment, or personal injury. Do not use this in a production environment or on a real machine until **v0.1.0** is officially released. Use for software simulation and testing purposes only!

---

**LatheCadCam** is an open-source, modern, parametric "Conversational CAM" designed specifically for LinuxCNC lathes. It allows machinists to generate complex turning operations (Roughing, Finishing, Drilling, Grooving) directly at the machine controller, without needing external CAD/CAM software.

Built with a **standalone PySide6 architecture**, it runs as an independent OS process, making it perfectly compatible with any LinuxCNC interface (QtDragon, GMOCCAPY, Axis, etc.) without freezing the main machine controller.

---

## 🚧 Current Status (Road to v0.1.0)

We are rapidly moving towards our first stable milestone (`v0.1.0`). 
*   [x] **Core Domain Architecture:** Complete (Data models, Tool Library, Machine Config).
*   [x] **Plugin System:** Complete (Extensible primitive operations).
*   [x] **2D Interactive Canvas:** Complete (Real-time rendering, hit-testing, tooltips).
*   [x] **CAM Math Engine:** In Progress (PyClipper integration for tool nose compensation).
*   [ ] **G-Code Verification:** Pending (Requires extensive simulator testing).
*   [ ] **LinuxCNC Live Bridge:** Pending (Testing the `linuxcnc` Python module injection).
*   [ ] **Real Machine Testing:** Pending.

---

## 🚀 Key Features (Planned & Active)

*   **Parametric Design:** Create parts using predefined feature plug-ins (Cylinder, Taper, Chamfer, Fillet, Groove, Bore) instead of drawing vectors manually.
*   **Conversational Workflow:** Define operations assigned to specific tools in an intuitive visual tree.
*   **ISO Tool Library:** Built-in support for standard ISO inserts (CNMG, DNMG, etc.) with automatic nose radius compensation (`G41/G42` or pre-calculated offsets).
*   **Smart Toolpaths:**
    *   Custom lightweight 2D geometry engine.
    *   **PyClipper** for robust polygon offsetting and collision-free roughing passes.
*   **LinuxCNC Integration:** Instantly injects generated G-code into the running machine interpreter via the Python interface.
*   **Safe & Isolated:** Runs as a standalone subprocess—if the CAM UI crashes, your machine control stays alive and safe.

---

## 🛠️ Architecture

The project follows a strict **Clean Architecture** to ensure stability, easy testing, and future-proofing:

```text
┌──────────────────────┐      ┌──────────────────────┐      ┌──────────────────────┐
│   GUI Layer (UI)     │      │   Core Logic (CAM)   │      │   Driver Layer (IO)  │
│ -------------------- │      │ -------------------- │      │ -------------------- │
│ • PySide6 (Qt6)      │ ────►│ • Primitive Plugins  │ ────►│ • LinuxCNC Bridge    │
│ • Interactive Canvas │      │ • PyClipper (Offset) │      │ • JSON Serializer    │
│ • Tool Manager       │      │ • G-Code Generator   │      │ • OS Subprocess      │
└──────────────────────┘      └──────────────────────┘      └──────────────────────┘
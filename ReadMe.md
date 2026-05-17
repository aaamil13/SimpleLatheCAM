# SimpleLatheCAM

**SimpleLatheCAM** is a modern, parametric "Conversational CAM" designed specifically for LinuxCNC lathes. It allows machinists to generate complex turning operations (Roughing, Finishing, Threading) directly at the machine controller, without needing external CAD/CAM software.

Built with a **standalone PySide6 architecture**, it runs as an independent process, making it compatible with any LinuxCNC interface (QtDragon, GMOCCAPY, Axis, etc.).

---

## 🚀 Key Features

*   **Parametric Design:** Create parts using predefined features (Cylinder, Taper, Chamfer, Fillet) instead of drawing vectors.
*   **Conversational Workflow:** Define "Recipes" (Operations) mapped to specific tools.
*   **ISO Tool Library:** Built-in support for standard ISO inserts (CNMG, DNMG, etc.) with automatic nose radius compensation.
*   **Smart Toolpaths:**
    *   **CadQuery** engine for 3D/2D geometry generation.
    *   **Clipper (PyClipper)** for robust polygon offsetting and collision-free roughing passes.
    *   Automatic **G71/G70** cycle support (optional) or pure expanded G-code.
*   **LinuxCNC Integration:** Instantly injects generated G-code into the running machine interpreter via the Python interface.
*   **Safe & Isolated:** Runs as a subprocess—if the CAM crashes, your machine control stays alive.

---

## 🛠️ Architecture

The project follows a strict **Layered Architecture** to ensure stability and future-proofing:

```text
┌──────────────────────┐      ┌──────────────────────┐      ┌──────────────────────┐
│   GUI Layer (UI)     │      │   Core Logic (CAM)   │      │   Driver Layer (IO)  │
│ -------------------- │      │ -------------------- │      │ -------------------- │
│ • PySide6 (Qt6)      │ ────►│ • CadQuery (Geo)     │ ────►│ • LinuxCNC Module    │
│ • Visualizer         │      │ • PyClipper (Offset) │      │ • File System (JSON) │
│ • ISO Tool Manager   │      │ • G-Code Generator   │      │ • Subprocess Control │
└──────────────────────┘      └──────────────────────┘      └──────────────────────┘
```

### Tech Stack
*   **Language:** Python 3.10+
*   **UI Framework:** PySide6 (Qt for Python)
*   **Geometry Engine:** CadQuery (OpenCASCADE based)
*   **Path Planning:** PyClipper (Polygon clipping & offsetting)
*   **Controller:** LinuxCNC (via `linuxcnc` python module)

---

## 📦 Installation

Since CadQuery relies on OCP (OpenCASCADE), the recommended installation is via **Conda/Mamba** to handle binary dependencies correctly.

### 1. Prerequisites
*   LinuxCNC 2.8 or higher (Running on Debian 10/11/12)
*   Miniforge or Mambaforge (Recommended)

### 2. Setup Environment
```bash
# Create a fresh environment
mamba create -n lathe_cam python=3.10
mamba activate lathe_cam

# Install heavy dependencies
mamba install -c conda-forge cadquery

# Install UI and Logic dependencies
pip install PySide6 pyclipper
```

### 3. Clone & Run
```bash
git clone https://github.com
cd SimpleLatheCAM
python main.py
```

---

## 🔌 Integration with LinuxCNC

To launch SimpleLatheCAM directly from your machine interface, add a user button that executes the script.

**Example for QtDragon / QtVCP:**
Add a button in your UI handler script:

```python
import subprocess

def on_cam_button_clicked(self):
    # Launches the editor as a detached process
    subprocess.Popen(["/path/to/conda/env/python", "/path/to/SimpleLatheCAM/main.py"])
```

**Example for GMOCCAPY (INI file):**
```ini
[DISPLAY]
USER_COMMAND_BUTTON = name="Lathe CAM"; command=python3 /home/cnc/SimpleLatheCAM/main.py
```

---

## 📖 Usage Workflow

1.  **Open Editor:** Click the "Lathe CAM" button on your CNC screen.
2.  **Select Tool:** Choose a tool from the library (e.g., *Tool 1 - Roughing CNMG 0.8mm*).
3.  **Add Operations:** Add parametric steps (e.g., *Face Turn -> Cylinder OD 40mm -> Chamfer 2mm*).
4.  **Preview:** See the 2D profile and toolpath in real-time.
5.  **Compile:** Click **"Send to Machine"**.
    *   The software generates a `.ngc` file.
    *   It checks if LinuxCNC is IDLE.
    *   It commands LinuxCNC to load the new file immediately.
6.  **Cycle Start:** Press the physical start button on your machine.

---

## 📂 Project Structure

*   `src/ui/` - PySide6 Widgets and Main Window logic.
*   `src/cam/` - Core mathematics (CadQuery generators, Clipper offsetting).
*   `src/tools/` - JSON database of ISO inserts and holders.
*   `src/drivers/` - Isolated `linuxcnc` communication layer.
*   `assets/` - Icons and graphical resources.

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:
1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/NewCycle`).
3.  Commit your changes.
4.  Push to the branch and open a Pull Request.

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.

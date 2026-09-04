# 🚀 Pop-up AI - Universal Desktop AI Assistant & Screen Problem Solver

<p align="center">
  <img src="https://img.shields.io/badge/Version-1.0.0-blue.svg" alt="Version" />
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg" alt="Platform" />
  <img src="https://img.shields.io/badge/Engine-Ollama%20Local%20LLM-black.svg" alt="Engine" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License" />
</p>

**Pop-up AI** is a lightweight, stealthy, and powerful floating AI overlay assistant designed for Windows. It features instantaneous screen OCR problem solving, in-app Python code execution, automated IDE solution injection, SQLite solution archiving, and click-through ghost mode.

---

## 🌟 Key Features

### 🎯 1. Interactive Question Snipper (`🎯 Snip & Solve`)
- Drag a green selection box directly over any **quiz question, coding challenge, math problem, or MCQ** on your screen.
- Instantly crops, extracts text via Windows Native Media OCR, and streams the direct solution with zero background interference.

### 📸 2. Smart Fullscreen Screen Scanner (`📸 Scan Screen`)
- One-click desktop scan with intelligent noise filtering that automatically removes terminal paths, IDE menus, and system dialogs to isolate only the real question.

### ⚡ 3. Instant Solution Auto-Paste (`Ctrl + Shift + V`)
- Automatically switches focus back to your active code editor (VS Code, Cursor, LeetCode, Terminal) and **injects the clean solution or code** directly at your cursor location.

### 🧩 4. In-App Code Runner Sandbox (`▶ Run in Sandbox`)
- Directly execute and test generated Python algorithms and data structures inside an isolated sandbox subprocess.
- Live terminal console showing `stdout`, `stderr`, execution duration (`ms`), and return code status.

### 📜 5. Searchable Solution History & Markdown Export (`📜 History`)
- Every scanned question, MCQ, code solution, timestamp, and active model is persisted in a local SQLite database (`~/.universal_overlay/history.db`).
- Live search bar and one-click **`📥 Export to Markdown`** to save your exam/coding prep session into structured `.md` notes.

### 🪟 6. Click-Through "Ghost Mode" (`Ctrl + Shift + G`)
- Native Windows `WS_EX_TRANSPARENT` click-through overlay. The assistant remains visible on top with custom opacity, while all mouse clicks pass directly through to windows underneath.

### 🕶️ 7. Emergency "Boss Key" (`F1`)
- Instantly vanishes the entire widget, floating dot, and taskbar entry with 0ms delay. Pressing `F1` again restores it immediately.

### 🤖 8. Dynamic Ollama Model Auto-Discovery
- Automatically scans your local Ollama instance (`http://localhost:11434/api/tags`) on launch.
- Seamlessly switch between **Qwen 3.6**, **Phi-3**, **LLaMA 3.2**, **LLaVA**, **Mistral**, or any model installed on your PC.

---

## ⌨️ Master Global Shortcuts

| Shortcut | Action | Description |
| :--- | :--- | :--- |
| **`Ctrl + H`** | **Toggle Overlay** | Summons, hides, or reopens the Pop-up AI assistant from any app or full-screen window |
| **`Ctrl + Shift + V`** | **⚡ Auto-Paste** | Injects clean generated code/answer directly into your active window |
| **`Ctrl + Shift + G`** | **🪟 Ghost Mode** | Toggles mouse click-through overlay mode on/off |
| **`F1`** | **🕶️ Boss Key** | 0ms emergency stealth hide & restore |
| **`Ctrl + Shift + N`** | **📝 Next Typer Block** | Types the next sequential text block into external windows |
| **`Ctrl + Shift + C`** | **🧹 Clean Clipboard** | Strips invisible zero-width characters and AI watermarks |

---

## 🚀 Quick Start & Installation

### 1. Prerequisites
- **Windows 10 / 11**
- **Python 3.10+**
- **[Ollama](https://ollama.com/)** running locally

### 2. Clone Repository
```powershell
git clone https://github.com/charanyarlagadda99-afk/POPUP-AI.git
cd POPUP-AI
```

### 3. Install Dependencies
```powershell
pip install -r requirements-dev.txt
pip install winocr mss keyboard Pillow
```

### 4. Pull Your Preferred Local AI Models
```powershell
ollama pull Qwen3.6:latest
ollama pull phi3
```

### 5. Launch Pop-up AI
```powershell
python floating_widget.py
```

---

## 🧠 Adaptive Multi-Domain Problem Solver

Pop-up AI automatically detects the nature of the question on your screen and formats the response:

| Problem Type | AI Output Format |
| :--- | :--- |
| **Multiple Choice (MCQ)** | `Answer: Option X) [Text]` (Direct 1-line answer, no delay) |
| **Coding & Algorithms** | Task summary + clean working code in markdown + complexity notes |
| **Math & Logic** | Formula + step-by-step calculation + final value |
| **General & Theory** | Direct, concise, structured answer |

---

## 📁 Architecture Overview

```
POPUP-AI/
├── floating_widget.py               # Main application entry point
├── desktop_overlay/
│   ├── app.py                       # Overlay runtime coordinator
│   ├── config.py                    # Configuration and persistent settings
│   ├── agent/
│   │   ├── llm_provider.py          # Dynamic Ollama streaming client & auto-discovery
│   │   ├── engine.py                # Autonomous agent tool runner
│   │   └── tools/                   # Automation tools (clipboard, input, screen, uia)
│   ├── context/
│   │   ├── context_engine.py        # Desktop context aggregator
│   │   ├── screen.py                # High-speed OCR (winocr/MSS) & noise filter
│   │   └── active_window.py         # Windows foreground process tracker
│   ├── history/
│   │   └── history_manager.py       # SQLite database archive & Markdown exporter
│   ├── sandbox/
│   │   └── code_runner.py           # In-app Python execution engine
│   ├── platform_layer/
│   │   └── win32_api.py             # Ctypes Win32 bindings (Ghost mode, Auto-paste)
│   └── ui/
│       ├── overlay_window.py        # Master window manager (Pop-up AI)
│       ├── expanded_mode.py         # Main assistant chat & toolbar
│       ├── snipper.py               # Interactive green box question selector
│       ├── sandbox_view.py          # Code sandbox runner UI
│       ├── history_view.py          # Searchable solution history UI
│       ├── editor_view.py           # Sequential block typer
│       ├── settings_ui.py           # Opacity & appearance settings
│       └── compact_mode.py          # Floating adaptive dot launcher
└── tests/
    └── test_desktop_overlay.py      # Automated unit test suite
```

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).

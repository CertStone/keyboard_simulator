"""Tkinter-based GUI for the keyboard simulator."""

from __future__ import annotations

import logging
import sys
import threading
import time
from pathlib import Path
from typing import Optional, cast

import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from tkinterdnd2 import DND_FILES, TkinterDnD
import keyboard

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from keyboard_simulator.config import ConfigError, FileConfig, TextConfig, TargetOS
    from keyboard_simulator.tasks import build_plan
    from keyboard_simulator.simulator import KeyboardSimulator, SimulatorHooks
    from keyboard_simulator.backends.sendinput import SendInputBackend
    from keyboard_simulator.logging_config import setup_logging, disable_logging
except ModuleNotFoundError:  # pragma: no cover - fallback for direct execution without install
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))
    from keyboard_simulator.config import ConfigError, FileConfig, TextConfig, TargetOS
    from keyboard_simulator.tasks import build_plan
    from keyboard_simulator.simulator import KeyboardSimulator, SimulatorHooks
    from keyboard_simulator.backends.sendinput import SendInputBackend
    from keyboard_simulator.logging_config import setup_logging, disable_logging

# --- Conditional Logging ---
# If running from source (e.g., pyproject.toml exists) or --log is passed, enable logging.
# This prevents logging in the bundled executable by default.
if Path("pyproject.toml").exists() or "--log" in sys.argv:
    setup_logging()
else:
    disable_logging()

logger = logging.getLogger(__name__)

STATUS_MAP = {
    "idle": "状态: 空闲",
    "countdown": "状态: {seconds_left} 秒后开始...",
    "running": "状态: 运行中... 请勿操作键鼠！",
    "paused": "状态: 已暂停",
    "completed": "状态: 任务完成",
    "stopped": "状态: 用户已停止",
    "aborting": "状态: 正在中止...",
    "error": "状态: 发生错误",
}


class App(TkinterDnD.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("键盘模拟器 GUI (V2)")
        self.geometry("620x600")
        self.resizable(False, False)

        self.is_running = False
        self.is_paused = False
        self.file_path = tk.StringVar()
        self.target_os = tk.StringVar(value="linux")
        self.input_method = tk.StringVar(value="scancode")
        self.status_var = tk.StringVar(value=STATUS_MAP["idle"])
        self.simulator: Optional[KeyboardSimulator] = None
        self.simulation_thread: Optional[threading.Thread] = None

        logger.info("Initializing GUI application.")
        self._create_widgets()
        self._setup_hotkeys()
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.status_var.set(STATUS_MAP["idle"])  # Set initial status
        logger.info("GUI initialized successfully.")

    # --- UI 构建 ---
    def _create_widgets(self) -> None:
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        text_frame = ttk.Frame(self.notebook, padding="10")
        file_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(text_frame, text="文本输入模式")
        self.notebook.add(file_frame, text="文件传输模式")

        ttk.Label(text_frame, text="在此处输入或粘贴要自动键入的文本:").pack(anchor="w")
        self.text_widget = tk.Text(text_frame, wrap="word", height=10, width=60)
        self.text_widget.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        file_input_frame = ttk.Frame(file_frame)
        file_input_frame.pack(fill=tk.X, pady=(5, 10))
        ttk.Label(file_input_frame, text="文件路径:").pack(side=tk.LEFT, padx=(0, 5))
        self.file_path_entry = ttk.Entry(file_input_frame, textvariable=self.file_path)
        self.file_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.select_file_button = ttk.Button(
            file_input_frame, text="选择文件...", command=self._select_file
        )
        self.select_file_button.pack(side=tk.LEFT, padx=(5, 0))

        self.drop_target_label = ttk.Label(
            file_frame,
            text="\n\n请将文件拖拽至此\n或使用上方按钮选择文件\n\n",
            relief="solid",
            borderwidth=1,
            anchor="center",
        )
        self.drop_target_label.pack(fill=tk.BOTH, expand=True, pady=5)
        self.drop_target_label.drop_target_register(DND_FILES)  # type: ignore[attr-defined]
        self.drop_target_label.dnd_bind("<<Drop>>", self._on_drop)  # type: ignore[attr-defined]

        os_frame = ttk.Frame(file_frame)
        os_frame.pack(fill=tk.X, pady=5)
        ttk.Label(os_frame, text="目标系统:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(os_frame, text="Linux", variable=self.target_os, value="linux").pack(
            side=tk.LEFT
        )
        ttk.Radiobutton(os_frame, text="Windows", variable=self.target_os, value="windows").pack(
            side=tk.LEFT, padx=10
        )

        settings_frame = ttk.LabelFrame(main_frame, text="通用设置", padding="10")
        settings_frame.pack(fill=tk.X, pady=10)

        ttk.Label(settings_frame, text="按键延迟(秒):").grid(
            row=0, column=0, sticky="w", padx=5, pady=5
        )
        self.delay_spinbox = ttk.Spinbox(
            settings_frame, from_=0.0, to=1.0, increment=0.01, format="%.2f", width=8
        )
        self.delay_spinbox.set("0.01")
        self.delay_spinbox.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(settings_frame, text="启动倒计时(秒):").grid(
            row=0, column=2, sticky="w", padx=15, pady=5
        )
        self.countdown_spinbox = ttk.Spinbox(settings_frame, from_=1, to=60, width=8)
        self.countdown_spinbox.set("5")
        self.countdown_spinbox.grid(row=0, column=3, sticky="w", padx=5, pady=5)

        ttk.Label(settings_frame, text="输入模式:").grid(
            row=1, column=0, sticky="w", padx=5, pady=5
        )
        method_frame = ttk.Frame(settings_frame)
        method_frame.grid(row=1, column=1, columnspan=3, sticky="w")
        ttk.Radiobutton(
            method_frame,
            text="硬件扫描码 (兼容性强，不支持中文)",
            variable=self.input_method,
            value="scancode",
        ).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(
            method_frame,
            text="Unicode (速度快)",
            variable=self.input_method,
            value="unicode",
        ).pack(side=tk.LEFT, padx=5)

        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=5)

        self.start_button = ttk.Button(
            control_frame, text="开始模拟 (F9)", command=self._start_simulation
        )
        self.start_button.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)

        self.pause_button = ttk.Button(
            control_frame, text="暂停 (F11)", command=self._toggle_pause, state="disabled"
        )
        self.pause_button.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=10)

        self.stop_button = ttk.Button(
            control_frame, text="强制停止 (F10)", command=self._force_stop, state="disabled"
        )
        self.stop_button.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)

        status_bar = ttk.Frame(main_frame, relief=tk.SUNKEN, padding="5")
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))
        self.status_label = ttk.Label(
            status_bar, textvariable=self.status_var, anchor="w"
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # --- 热键 & 交互 ---
    def _setup_hotkeys(self) -> None:
        try:
            keyboard.add_hotkey("F9", self._start_simulation)
            keyboard.add_hotkey("F10", self._force_stop)
            keyboard.add_hotkey("F11", self._toggle_pause)
            logger.info("Global hotkeys (F9, F10, F11) registered successfully.")
        except Exception as e:
            logger.warning("Failed to register global hotkeys: %s", e, exc_info=True)
            messagebox.showwarning(
                "热键警告", "设置全局热键失败。\n\n如果热键无效，请尝试以管理员身份运行。"
            )

    def _select_file(self) -> None:
        logger.debug("Opening file selection dialog.")
        filepath = filedialog.askopenfilename(
            title="选择文件",
            filetypes=(("所有文件", "*.*"), ("文本文档", "*.txt")),
        )
        if filepath:
            path = Path(filepath)
            logger.info("File selected via dialog: %s", path)
            self.file_path.set(str(path))
            self.drop_target_label.config(text=f"已选择文件:\n{path.name}")

    def _on_drop(self, event) -> None:
        # The data is a string that might be wrapped in curly braces
        path_str = event.data.strip()
        if path_str.startswith("{") and path_str.endswith("}"):
            path_str = path_str[1:-1]

        try:
            path = Path(path_str)
            logger.info("File dropped onto window: %s", path)
            if path.exists():
                self.file_path.set(str(path))
                self.drop_target_label.config(text=f"已选择文件:\n{path.name}")
            else:
                logger.error("Dropped file path does not exist: %s", path_str)
                messagebox.showerror("错误", f"文件路径无效: {path_str}")
        except Exception as e:
            logger.error("Error processing dropped file path: %s", e, exc_info=True)
            messagebox.showerror("错误", f"处理路径时出错: {path_str}\n{e}")

    # --- 模拟控制 ---
    def _start_simulation(self) -> None:
        if self.is_running:
            logger.warning("Attempted to start simulation while one is already running.")
            return

        try:
            logger.info("Building configuration from UI.")
            config = self._build_config_from_ui()
            logger.debug("Built config: %s", config)
            plan = build_plan(config)
            logger.info("Built plan with %d tasks.", len(plan.tasks))
        except (ValueError, ConfigError) as exc:
            logger.error("Configuration error: %s", exc, exc_info=True)
            messagebox.showerror("配置错误", str(exc))
            return
        except Exception as exc:  # pragma: no cover - unexpected
            logger.critical("Failed to build plan: %s", exc, exc_info=True)
            messagebox.showerror("错误", f"构建任务失败:\n{exc}")
            return

        prefer_unicode = self.input_method.get() == "unicode"
        logger.info("Input method selected: %s", "unicode" if prefer_unicode else "scancode")

        def on_countdown_wrapper(left: int) -> None:
            self.after(0, self._on_countdown, left)

        def on_status_wrapper(status: str) -> None:
            self.after(0, self._on_status, status)

        hooks = SimulatorHooks(
            on_countdown=on_countdown_wrapper,
            on_status=on_status_wrapper,
        )
        self.simulator = KeyboardSimulator(SendInputBackend(), hooks)

        self.is_running = True
        self.is_paused = False
        self._update_controls(running=True)
        logger.info("Starting simulation thread.")

        def runner() -> None:
            sim = self.simulator
            if sim is None:
                logger.error("Simulator object was None when runner thread started.")
                return
            try:
                logger.info("Simulation plan execution started.")
                sim.run_plan(plan)
                logger.info("Simulation plan execution finished.")
            except Exception as exc:  # pragma: no cover - runtime failure
                logger.critical("Runtime error during simulation: %s", exc, exc_info=True)
                self.after(0, messagebox.showerror, "运行时错误", f"发生错误:\n{exc}")
                self.after(0, self._on_status, "error")

        self.simulation_thread = threading.Thread(target=runner, daemon=True)
        self.simulation_thread.start()

    def _build_config_from_ui(self):
        delay = float(self.delay_spinbox.get())
        countdown = int(self.countdown_spinbox.get())
        if delay < 0 or countdown < 0:
            raise ValueError("倒计时与延迟必须为非负数")

        if self.notebook.index("current") == 0:
            text = self.text_widget.get("1.0", tk.END).strip()
            if not text:
                raise ValueError("请输入要自动键入的文本内容")
            return TextConfig(
                text_to_type=text,
                delay_between_keystrokes=delay,
                countdown_before_start=countdown,
            )

        file_path = Path(self.file_path.get())
        if not file_path.exists():
            raise ValueError("请选择有效的文件路径")
        output_name = file_path.name
        return FileConfig(
            file_path=file_path,
            target_os=cast(TargetOS, self.target_os.get()),
            output_filename=output_name,
            delay_between_keystrokes=delay,
            countdown_before_start=countdown,
        )

    def _force_stop(self) -> None:
        if not self.is_running or self.simulator is None:
            return
        logger.info("Force stop requested by user.")
        self._on_status("aborting")
        self.simulator.stop()

        # Wait for the simulation thread to finish
        if self.simulation_thread and self.simulation_thread.is_alive():
            # Give the thread a moment to exit its loops
            self.simulation_thread.join(timeout=1.5)

        # Reset state regardless of thread termination
        self.is_running = False
        self.is_paused = False
        self._update_controls(running=False)
        
        # If status is still aborting, force it to stopped
        if self.status_var.get() == STATUS_MAP["aborting"]:
            self._on_status("stopped")

    def _toggle_pause(self) -> None:
        if not self.is_running or self.simulator is None:
            return
        self.is_paused = not self.is_paused
        if self.is_paused:
            logger.info("Simulation paused.")
            self.simulator.pause()
            self.pause_button.config(text="恢复 (F11)")
        else:
            logger.info("Simulation resumed.")
            self.simulator.resume()
            self.pause_button.config(text="暂停 (F11)")

    # --- 状态更新 ---
    def _on_countdown(self, seconds_left: int) -> None:
        logger.debug("Countdown: %d seconds left.", seconds_left)
        self.status_var.set(STATUS_MAP["countdown"].format(seconds_left=seconds_left))

    def _on_status(self, status: str) -> None:
        logger.info("Simulation status updated: %s", status)
        self.status_var.set(STATUS_MAP.get(status, f"状态: {status}"))

        if status in {"completed", "stopped", "error"}:
            self.is_running = False
            self.is_paused = False
            self.pause_button.config(text="暂停 (F11)")
            self._update_controls(running=False)

    def _update_controls(self, *, running: bool) -> None:
        self.start_button.config(state="disabled" if running else "normal")
        self.pause_button.config(state="normal" if running else "disabled")
        self.stop_button.config(state="normal" if running else "disabled")

    # --- 关闭处理 ---
    def _on_closing(self) -> None:
        logger.info("Close window requested.")
        if self.is_running:
            logger.warning("Attempting to close window while simulation is running.")
            if not messagebox.askyesno("退出", "模拟任务正在运行，确定要退出吗？"):
                logger.info("User cancelled exit.")
                return
            if self.simulator:
                logger.info("Stopping simulation before exit.")
                self.simulator.stop()
        logger.info("Destroying main window.")
        self.destroy()


if __name__ == "__main__":  # pragma: no cover
    try:
        logger.info("Application starting.")
        app = App()
        app.mainloop()
        logger.info("Application finished.")
    except Exception as e:
        logger.critical("An unhandled exception occurred at the top level: %s", e, exc_info=True)
        messagebox.showerror("严重错误", f"应用程序遇到无法恢复的错误:\n{e}")

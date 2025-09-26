# -----------------------------------------------------------------------------
# 键盘模拟器 PRO (内核驱动版)
#
# 源码修正版说明:
# - 诚挚致歉，此版本已根据您提供的 interception-python 库源码完全重写。
# - 解决了此前所有由于 API 调用方式错误导致的 AttributeError 和 TypeError。
#
# - 核心修正:
#   1. 修复了 `KeyStroke.__init__()` 的参数数量错误。现在将通过正确的
#      位操作来处理扩展键（extended keys），而不是作为第三个参数传入。
#   2. 遵循源码中的正确工作流程：使用 `context.await_input()` 等待，
#      然后用 `context.devices[device].receive()` 接收。
#   3. 彻底修复了键盘被完全劫持的致命BUG。监听线程现在可以正确地“放行”
#      所有非热键的物理按键。
# -----------------------------------------------------------------------------

import sys
import time
import os
import threading
from pathlib import Path
from typing import cast
import logging

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinterdnd2 import DND_FILES, TkinterDnD
import interception
from interception import _keycodes as keycodes  # 导入内部模块以获取扫描码

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from keyboard_simulator.config import ConfigError, FileConfig, TextConfig, TargetOS
    from keyboard_simulator.tasks import build_plan
    from keyboard_simulator.logging_config import setup_logging, disable_logging
except ModuleNotFoundError:  # pragma: no cover - fallback for direct execution without install
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))
    from keyboard_simulator.config import ConfigError, FileConfig, TextConfig, TargetOS
    from keyboard_simulator.tasks import build_plan
    from keyboard_simulator.logging_config import setup_logging, disable_logging

# --- Conditional Logging ---
if Path("pyproject.toml").exists() or "--log" in sys.argv:
    setup_logging()
else:
    disable_logging()

logger = logging.getLogger(__name__)


# --- Core Keyboard Simulator Class ---
class KeyboardSimulatorPro:
    def __init__(self, context, device):
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()  # Not paused by default
        self.keyboard_device = device
        self.context = context

    def _check_pause_and_stop(self):
        while not self.pause_event.is_set():
            if self.stop_event.is_set():
                return True
            time.sleep(0.1)
        return self.stop_event.is_set()

    def _create_and_send_stroke(self, scan_code, is_extended, state):
        """
        正确地创建并发送一个 KeyStroke 对象。
        """
        key_stroke_cls = getattr(interception, "KeyStroke")
        stroke = key_stroke_cls(scan_code, state)
        if is_extended:
            key_flag = getattr(interception, "KeyFlag")
            stroke.flags |= key_flag.KEY_E0
        self.context.send(self.keyboard_device, stroke)

    def _press_key_from_data(self, key_data, delay):
        """根据 get_key_information 返回的数据模拟按键"""
        mods_down = []
        if key_data.shift:
            mods_down.append(keycodes.get_key_information("shift"))
        if key_data.ctrl:
            mods_down.append(keycodes.get_key_information("ctrl"))
        if key_data.alt:
            mods_down.append(keycodes.get_key_information("alt"))

        # 按下修饰键
        key_flag = getattr(interception, "KeyFlag")
        for mod_data in mods_down:
            self._create_and_send_stroke(
                mod_data.scan_code, mod_data.is_extended, key_flag.KEY_DOWN
            )
            time.sleep(delay / 2)

        # 按下主键
        self._create_and_send_stroke(key_data.scan_code, key_data.is_extended, key_flag.KEY_DOWN)
        time.sleep(delay)

        # 释放主键
        self._create_and_send_stroke(key_data.scan_code, key_data.is_extended, key_flag.KEY_UP)

        # 释放修饰键
        for mod_data in reversed(mods_down):
            time.sleep(delay / 2)
            self._create_and_send_stroke(mod_data.scan_code, mod_data.is_extended, key_flag.KEY_UP)

    def type_string(self, s, delay):
        for char in s:
            if self._check_pause_and_stop():
                logger.info("Stop signal detected, halting typing.")
                return

            try:
                key_data = keycodes.get_key_information(char)
                self._press_key_from_data(key_data, delay)
            except getattr(keycodes, "UnknownKeyError", Exception):
                logger.warning("Skipping unknown key: '%s'", char)

            time.sleep(delay)

    def generate_linux_command(self, encoded_data, output_filename):
        chunk_size = 512
        chunks = [encoded_data[i : i + chunk_size] for i in range(0, len(encoded_data), chunk_size)]
        command = f"echo -n {chunks[0]}>{output_filename}.b64\n"
        for chunk in chunks[1:]:
            command += f"echo -n {chunk}>>{output_filename}.b64\n"
        command += f"base64 -d {output_filename}.b64>{output_filename}\n"
        command += f"rm {output_filename}.b64\n"
        return command

    def generate_windows_command(self, encoded_data, output_filename):
        lines = [encoded_data[i : i + 76] for i in range(0, len(encoded_data), 76)]
        command = f"echo {lines[0]}>tmp.b64\n"
        for line in lines[1:]:
            command += f"echo {line}>>tmp.b64\n"
        command += f"certutil -decode tmp.b64 {output_filename}\n"
        command += "del tmp.b64\n"
        return command


# --- GUI Application Class ---
class App(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("键盘模拟器 PRO (驱动版)")
        self.geometry("620x600")
        self.resizable(False, False)

        logger.info("Initializing PRO GUI application.")
        self.is_running = False
        self.is_paused = False
        self.file_path = tk.StringVar()
        self.target_os = tk.StringVar(value="linux")
        self.simulation_thread = None
        self.simulator = None
        self.current_plan = None

        try:
            logger.info("Initializing Interception driver context.")
            context_cls = getattr(interception, "Interception")
            self.context = context_cls()
            self.context.set_filter(
                self.context.is_keyboard, interception.FilterKeyFlag.FILTER_KEY_ALL
            )

            self.keyboard_device = None
            for i in range(20):
                if self.context.is_keyboard(i):
                    self.keyboard_device = i
                    logger.info("Found keyboard device at index: %d", i)
                    break
            if self.keyboard_device is None:
                raise RuntimeError("未找到键盘设备。")
        except Exception as e:
            logger.critical("Failed to initialize Interception driver: %s", e, exc_info=True)
            messagebox.showerror(
                "驱动错误",
                f"初始化 Interception 驱动失败！\n请确认驱动已正确安装并已重启电脑。\n\n错误详情: {e}",
            )
            self.destroy()
            return

        self.F9_SCANCODE = keycodes.get_key_information("f9").scan_code
        self.F10_SCANCODE = keycodes.get_key_information("f10").scan_code
        self.F11_SCANCODE = keycodes.get_key_information("f11").scan_code
        logger.debug("Registered hotkey scancodes: F9=%d, F10=%d, F11=%d", self.F9_SCANCODE, self.F10_SCANCODE, self.F11_SCANCODE)

        self._create_widgets()
        self.listener_thread = threading.Thread(target=self._keyboard_listener, daemon=True)
        self.listener_thread.start()
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        logger.info("PRO GUI initialized successfully.")

    def _keyboard_listener(self):
        logger.info("Keyboard listener thread started.")
        while True:
            try:
                device = self.context.await_input()
                if device is None:
                    continue

                stroke = self.context.devices[device].receive()

                if stroke is None:
                    continue

                is_hotkey = False
                if self.context.is_keyboard(device):
                    key_flag = getattr(interception, "KeyFlag")
                    flags = getattr(stroke, "flags", None)
                    code = getattr(stroke, "code", None)
                    if flags == key_flag.KEY_DOWN:
                        if code == self.F9_SCANCODE:
                            logger.debug("F9 hotkey pressed.")
                            self.after(0, self._start_simulation)
                            is_hotkey = True
                        elif code == self.F10_SCANCODE:
                            logger.debug("F10 hotkey pressed.")
                            self.after(0, self._force_stop)
                            is_hotkey = True
                        elif code == self.F11_SCANCODE:
                            logger.debug("F11 hotkey pressed.")
                            self.after(0, self._toggle_pause)
                            is_hotkey = True

                if not is_hotkey:
                    self.context.send(device, stroke)

            except Exception as e:
                logger.error("Error in keyboard listener thread: %s", e, exc_info=True)
                time.sleep(1)

    def _create_widgets(self):
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
        self.status_label = ttk.Label(
            main_frame, text="状态: 准备就绪 (驱动模式)", relief=tk.SUNKEN, anchor="w", padding=5
        )
        self.status_label.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))

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

    def _on_drop(self, event):
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

    def _start_simulation(self):
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
        except Exception as exc:
            logger.critical("Failed to build plan: %s", exc, exc_info=True)
            messagebox.showerror("错误", f"任务构建失败:\n{exc}")
            return

        self.is_running = True
        self.simulator = KeyboardSimulatorPro(self.context, self.keyboard_device)
        self.simulator.stop_event.clear()
        self.simulator.pause_event.set()
        self.current_plan = plan
        self._update_ui_for_run_state(True)
        logger.info("Starting simulation thread.")
        self.simulation_thread = threading.Thread(
            target=self._run_simulation, args=(plan,), daemon=True
        )
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

    def _run_simulation(self, plan):
        simulator = self.simulator
        if simulator is None:
            logger.error("Simulator object was None when runner thread started.")
            self.after(0, self._update_ui_on_finish, "发生错误")
            return
        try:
            logger.info("Simulation countdown started (%d seconds).", plan.countdown_before_start)
            for i in range(plan.countdown_before_start, 0, -1):
                if simulator.stop_event.is_set():
                    logger.info("Simulation stopped by user during countdown.")
                    self.after(0, self._update_ui_on_finish, "已被用户中止")
                    return
                self.after(0, self.status_label.config, {"text": f"状态: {i} 秒后开始..."})
                time.sleep(1)

            logger.info("Simulation running.")
            self.after(0, self.status_label.config, {"text": "状态: 运行中... 请勿操作键鼠！"})
            for task in plan.tasks:
                simulator.type_string(task.payload, plan.delay_between_keystrokes)

            final_status = "任务完成" if not simulator.stop_event.is_set() else "已被用户中止"
            logger.info("Simulation finished with status: %s", final_status)
            self.after(0, self._update_ui_on_finish, final_status)
        except Exception as e:
            logger.critical("Runtime error during simulation: %s", e, exc_info=True)
            self.after(0, messagebox.showerror, "运行时错误", f"发生错误:\n{e}")
            self.after(0, self._update_ui_on_finish, "发生错误")

    def _force_stop(self):
        if not self.is_running or self.simulator is None:
            return
        logger.info("Force stop requested by user.")
        self.simulator.stop_event.set()
        self.simulator.pause_event.set()
        self.status_label.config(text="状态: 正在中止...")

    def _toggle_pause(self):
        if not self.is_running or self.simulator is None:
            return
        self.is_paused = not self.is_paused
        if self.is_paused:
            logger.info("Simulation paused.")
            self.simulator.pause_event.clear()
            self.pause_button.config(text="恢复 (F11)")
            self.status_label.config(text="状态: 已暂停")
        else:
            logger.info("Simulation resumed.")
            self.simulator.pause_event.set()
            self.pause_button.config(text="暂停 (F11)")
            self.status_label.config(text="状态: 运行中... 请勿操作键鼠！")

    def _update_ui_for_run_state(self, is_starting):
        state = "disabled" if is_starting else "normal"
        self.start_button.config(state=state)
        self.pause_button.config(state="normal" if is_starting else "disabled")
        self.stop_button.config(state="normal" if is_starting else "disabled")

    def _update_ui_on_finish(self, status_text):
        self.status_label.config(text=f"状态: {status_text}")
        self._update_ui_for_run_state(False)
        self.is_running = False
        self.is_paused = False
        self.pause_button.config(text="暂停 (F11)")

    def _on_closing(self):
        logger.info("Close window requested. Destroying context and window.")
        self.context.destroy()
        self.destroy()


if __name__ == "__main__":
    try:
        logger.info("PRO application starting.")
        app = App()
        app.mainloop()
        logger.info("PRO application finished.")
    except Exception as e:
        logger.critical("An unhandled exception occurred at the top level: %s", e, exc_info=True)
        messagebox.showerror("严重错误", f"应用程序遇到无法恢复的错误:\n{e}")

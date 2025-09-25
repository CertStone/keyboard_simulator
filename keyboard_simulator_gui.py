import tkinter as tk
from tkinter import ttk, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import ctypes
from ctypes import wintypes
import time
import base64
import os
import threading
import keyboard

# --- Windows API & Constants ---
user32 = ctypes.WinDLL('user32', use_last_error=True)
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008
VK_RETURN = 0x0D
VK_SHIFT = 0x10

PUL = ctypes.POINTER(ctypes.c_ulong)
class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", PUL)]

class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD),
                ("wParamL", wintypes.WORD),
                ("wParamH", wintypes.WORD)]

class MouseInput(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG),
                ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", PUL)]

class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput),
                ("mi", MouseInput),
                ("hi", HardwareInput)]

class Input(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD),
                ("ii", Input_I)]

# --- Character to Virtual-Key Code and Shift-State Mapping (US Keyboard Layout) ---
VK_MAP = {
    'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45, 'f': 0x46, 'g': 0x47, 'h': 0x48,
    'i': 0x49, 'j': 0x4A, 'k': 0x4B, 'l': 0x4C, 'm': 0x4D, 'n': 0x4E, 'o': 0x4F, 'p': 0x50,
    'q': 0x51, 'r': 0x52, 's': 0x53, 't': 0x54, 'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58,
    'y': 0x59, 'z': 0x5A,
    '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34, '5': 0x35, '6': 0x36, '7': 0x37,
    '8': 0x38, '9': 0x39,
    ' ': 0x20, ',': 0xBC, '.': 0xBE, '/': 0xBF, ';': 0xBA, "'": 0xDE, '[': 0xDB, ']': 0xDD,
    '\\': 0xDC, '-': 0xBD, '=': 0xBB, '`': 0xC0,
}
SHIFT_MAP = {
    'A': 'a', 'B': 'b', 'C': 'c', 'D': 'd', 'E': 'e', 'F': 'f', 'G': 'g', 'H': 'h',
    'I': 'i', 'J': 'j', 'K': 'k', 'L': 'l', 'M': 'm', 'N': 'n', 'O': 'o', 'P': 'p',
    'Q': 'q', 'R': 'r', 'S': 's', 'T': 't', 'U': 'u', 'V': 'v', 'W': 'w', 'X': 'x',
    'Y': 'y', 'Z': 'z',
    '!': '1', '@': '2', '#': '3', '$': '4', '%': '5', '^': '6', '&': '7', '*': '8',
    '(': '9', ')': '0', '_': '-', '+': '=', '{': '[', '}': ']', '|': '\\', ':': ';',
    '"': "'", '<': ',', '>': '.', '?': '/', '~': '`'
}

# --- Core Keyboard Simulator Class ---
class KeyboardSimulator:
    def __init__(self, stop_event, pause_event):
        self.stop_event = stop_event
        self.pause_event = pause_event

    def _check_pause_and_stop(self):
        while not self.pause_event.is_set():
            if self.stop_event.is_set(): return True
            time.sleep(0.1)
        return self.stop_event.is_set()

    def _send_input(self, *inputs):
        nInputs = len(inputs)
        lpInput = (Input * nInputs)(*inputs)
        cbSize = ctypes.sizeof(Input)
        return user32.SendInput(nInputs, lpInput, cbSize)
    
    def _key_down(self, vk_code):
        scan_code = user32.MapVirtualKeyW(vk_code, 0)
        self._send_input(Input(type=INPUT_KEYBOARD, ii=Input_I(ki=KeyBdInput(wVk=vk_code, wScan=scan_code, dwFlags=KEYEVENTF_SCANCODE))))
    
    def _key_up(self, vk_code):
        scan_code = user32.MapVirtualKeyW(vk_code, 0)
        self._send_input(Input(type=INPUT_KEYBOARD, ii=Input_I(ki=KeyBdInput(wVk=vk_code, wScan=scan_code, dwFlags=KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP))))

    def _type_char_scancode(self, char, delay):
        needs_shift = char in SHIFT_MAP
        vk_code = VK_MAP.get(SHIFT_MAP.get(char, char))
        
        if vk_code is None:
            print(f"Warning: Character '{char}' not supported in Scan-code mode. Skipping.")
            return

        if needs_shift: self._key_down(VK_SHIFT)
        time.sleep(delay / 2)
        self._key_down(vk_code)
        time.sleep(delay)
        self._key_up(vk_code)
        if needs_shift: self._key_up(VK_SHIFT)

    def _type_char_unicode(self, char):
        self._send_input(
            Input(type=INPUT_KEYBOARD, ii=Input_I(ki=KeyBdInput(wScan=ord(char), dwFlags=KEYEVENTF_UNICODE))),
            Input(type=INPUT_KEYBOARD, ii=Input_I(ki=KeyBdInput(wScan=ord(char), dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)))
        )

    def type_string(self, s, delay, mode='scancode'):
        for char in s:
            if self._check_pause_and_stop():
                print("Detection stop/pause signal, interrupting input.")
                return

            if char == '\n':
                self._key_down(VK_RETURN)
                time.sleep(delay)
                self._key_up(VK_RETURN)
            elif mode == 'scancode':
                self._type_char_scancode(char, delay)
            else: # unicode mode
                self._type_char_unicode(char)

            time.sleep(delay)

    def generate_linux_command(self, encoded_data, output_filename):
        chunk_size = 512
        chunks = [encoded_data[i:i+chunk_size] for i in range(0, len(encoded_data), chunk_size)]
        command = f"echo -n {chunks[0]} > {output_filename}.b64\n"
        for chunk in chunks[1:]:
            command += f"echo -n {chunk} >> {output_filename}.b64\n"
        command += f"base64 -d {output_filename}.b64 > {output_filename}\n"
        command += f"rm {output_filename}.b64\n"
        return command

    def generate_windows_command(self, encoded_data, output_filename):
        lines = [encoded_data[i:i + 76] for i in range(0, len(encoded_data), 76)]
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
        self.title("键盘模拟器 GUI (V2)")
        self.geometry("620x600")
        self.resizable(False, False)

        # State variables
        self.is_running = False
        self.is_paused = False
        self.file_path = tk.StringVar()
        self.target_os = tk.StringVar(value="linux")
        self.input_method = tk.StringVar(value="scancode")
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set() # Not paused by default
        self.simulator = KeyboardSimulator(self.stop_event, self.pause_event)

        self._create_widgets()
        self._setup_hotkeys()
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        text_frame = ttk.Frame(notebook, padding="10")
        file_frame = ttk.Frame(notebook, padding="10")
        notebook.add(text_frame, text="文本输入模式")
        notebook.add(file_frame, text="文件传输模式")

        ttk.Label(text_frame, text="在此处输入或粘贴要自动键入的文本:").pack(anchor="w")
        self.text_widget = tk.Text(text_frame, wrap="word", height=10, width=60)
        self.text_widget.pack(fill=tk.BOTH, expand=True, pady=(5,0))

        self.drop_target_label = ttk.Label(file_frame, text="\n\n请将文件拖拽至此\n\n", relief="solid", borderwidth=1, anchor="center")
        self.drop_target_label.pack(fill=tk.BOTH, expand=True, pady=5)
        self.drop_target_label.drop_target_register(DND_FILES)
        self.drop_target_label.dnd_bind('<<Drop>>', self._on_drop)

        os_frame = ttk.Frame(file_frame)
        os_frame.pack(fill=tk.X, pady=5)
        ttk.Label(os_frame, text="目标系统:").pack(side=tk.LEFT, padx=(0,10))
        ttk.Radiobutton(os_frame, text="Linux", variable=self.target_os, value="linux").pack(side=tk.LEFT)
        ttk.Radiobutton(os_frame, text="Windows", variable=self.target_os, value="windows").pack(side=tk.LEFT, padx=10)

        settings_frame = ttk.LabelFrame(main_frame, text="通用设置", padding="10")
        settings_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(settings_frame, text="按键延迟(秒):").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.delay_spinbox = ttk.Spinbox(settings_frame, from_=0.0, to=1.0, increment=0.01, format="%.2f", width=8)
        self.delay_spinbox.set("0.01")
        self.delay_spinbox.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        ttk.Label(settings_frame, text="启动倒计时(秒):").grid(row=0, column=2, sticky="w", padx=15, pady=5)
        self.countdown_spinbox = ttk.Spinbox(settings_frame, from_=1, to=60, width=8)
        self.countdown_spinbox.set("5")
        self.countdown_spinbox.grid(row=0, column=3, sticky="w", padx=5, pady=5)
        
        ttk.Label(settings_frame, text="输入模式:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        method_frame = ttk.Frame(settings_frame)
        method_frame.grid(row=1, column=1, columnspan=3, sticky="w")
        ttk.Radiobutton(method_frame, text="硬件扫描码 (兼容性强，不支持中文)", variable=self.input_method, value="scancode").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(method_frame, text="Unicode (速度快)", variable=self.input_method, value="unicode").pack(side=tk.LEFT, padx=5)
        
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=5)

        self.start_button = ttk.Button(control_frame, text="开始模拟 (F9)", command=self._start_simulation)
        self.start_button.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        
        self.pause_button = ttk.Button(control_frame, text="暂停 (F11)", command=self._toggle_pause, state="disabled")
        self.pause_button.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=10)

        self.stop_button = ttk.Button(control_frame, text="强制停止 (F10)", command=self._force_stop, state="disabled")
        self.stop_button.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        
        self.status_label = ttk.Label(main_frame, text="状态: 准备就绪 (请以管理员身份运行以使用热键)", relief=tk.SUNKEN, anchor="w", padding=5)
        self.status_label.pack(fill=tk.X, side=tk.BOTTOM, pady=(5,0))

    def _on_drop(self, event):
        path = event.data.strip('{}')
        if os.path.exists(path):
            self.file_path.set(path)
            self.drop_target_label.config(text=f"已选择文件:\n{os.path.basename(path)}")
        else:
            messagebox.showerror("错误", f"文件路径无效: {path}")

    def _setup_hotkeys(self):
        try:
            keyboard.add_hotkey('F9', self._start_simulation)
            keyboard.add_hotkey('F10', self._force_stop)
            keyboard.add_hotkey('F11', self._toggle_pause)
            print("全局热键 F9, F10, F11 已设置。")
        except Exception:
            messagebox.showwarning("热键警告", "设置全局热键失败。\n\n请务必以【管理员身份】运行此程序。")

    def _start_simulation(self):
        if self.is_running: return
        self.is_running = True
        self.stop_event.clear()
        self.pause_event.set()

        config = {
            "mode": "text" if self.tk.call(self.children['!frame'].children['!notebook'], "index", "current") == 0 else "file",
            "text": self.text_widget.get("1.0", tk.END).strip(),
            "file_path": self.file_path.get(), "target_os": self.target_os.get(),
            "delay": float(self.delay_spinbox.get()), "countdown": int(self.countdown_spinbox.get()),
            "input_method": self.input_method.get()
        }
        if config['mode'] == 'file' and not config["file_path"]:
            messagebox.showerror("错误", "请先拖入一个文件再开始。")
            self.is_running = False
            return
        
        self._update_ui_for_run_state(True)
        threading.Thread(target=self._run_simulation, args=(config,)).start()

    def _run_simulation(self, config):
        try:
            for i in range(config['countdown'], 0, -1):
                if self.stop_event.is_set():
                    self.after(0, self._update_ui_on_finish, "用户已停止")
                    return
                self.after(0, self.status_label.config, {'text': f"状态: {i}秒后开始..."})
                time.sleep(1)

            self.after(0, self.status_label.config, {'text': "状态: 运行中... 请勿操作键鼠！"})
            
            string_to_type = ""
            if config['mode'] == 'text':
                string_to_type = config['text']
            else:
                file_path = config['file_path']
                with open(file_path, 'rb') as f:
                    encoded_data = base64.b64encode(f.read()).decode('ascii')
                
                gen_func = self.simulator.generate_linux_command if config['target_os'] == 'linux' else self.simulator.generate_windows_command
                string_to_type = gen_func(encoded_data, os.path.basename(file_path))

            self.simulator.type_string(string_to_type, config['delay'], config['input_method'])
            final_status = "任务完成" if not self.stop_event.is_set() else "用户已停止"
            self.after(0, self._update_ui_on_finish, final_status)
        except Exception as e:
            self.after(0, messagebox.showerror, "运行时错误", f"发生错误:\n{e}")
            self.after(0, self._update_ui_on_finish, "发生错误")

    def _force_stop(self):
        if not self.is_running: return
        self.stop_event.set()
        self.pause_event.set() # Ensure it's not stuck in a paused state
        self.status_label.config(text="状态: 正在停止...")
    
    def _toggle_pause(self):
        if not self.is_running: return
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_event.clear()
            self.pause_button.config(text="恢复 (F11)")
            self.status_label.config(text="状态: 已暂停")
        else:
            self.pause_event.set()
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
        if self.is_running:
            if messagebox.askyesno("退出", "模拟任务正在运行，确定要退出吗？"):
                self.stop_event.set()
                self.pause_event.set()
                self.destroy()
        else:
            self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()


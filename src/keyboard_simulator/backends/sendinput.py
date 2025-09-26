"""Win32 SendInput backend implementation."""

from __future__ import annotations

import ctypes
from .base import AbstractKeyboardBackend, BackendError

# 定义 Win32 API 常量
INPUT_KEYBOARD = 1
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
VK_RETURN = 0x0D

# 定义 ctypes 结构，确保与 Windows API 兼容
# 参考: https://learn.microsoft.com/en-us/windows/win32/api/winuser/
# ULONG_PTR 在 64 位上是 64 位，在 32 位上是 32 位。ctypes.c_void_p 是一个很好的映射。
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk",         ctypes.c_ushort),
                ("wScan",       ctypes.c_ushort),
                ("dwFlags",     ctypes.c_ulong),
                ("time",        ctypes.c_ulong),
                ("dwExtraInfo", ctypes.c_void_p)]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx",          ctypes.c_long),
                ("dy",          ctypes.c_long),
                ("mouseData",   ctypes.c_ulong),
                ("dwFlags",     ctypes.c_ulong),
                ("time",        ctypes.c_ulong),
                ("dwExtraInfo", ctypes.c_void_p)]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg",        ctypes.c_ulong),
                ("wParamL",     ctypes.c_ushort),
                ("wParamH",     ctypes.c_ushort)]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT),
                ("mi", MOUSEINPUT),
                ("hi", HARDWAREINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong),
                ("union", _INPUT_UNION)]


class SendInputBackend(AbstractKeyboardBackend):
    """使用 SendInput API 的后端。"""

    def __init__(self):
        super().__init__()
        try:
            # 使用 use_last_error=True 以便在调用失败时获取错误码
            self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        except OSError as e:
            raise BackendError(f"加载 user32.dll 失败: {e}") from e

        # 显式定义 SendInput 函数的参数类型和返回类型，以提高健壮性
        self.user32.SendInput.restype = ctypes.c_uint
        self.user32.SendInput.argtypes = [ctypes.c_uint,      # cInputs
                                          ctypes.POINTER(INPUT), # pInputs
                                          ctypes.c_int]       # cbSize

    def _send_input(self, inputs_data):
        """
        构建并发送 INPUT 结构数组。
        """
        if not inputs_data:
            return

        n_inputs = len(inputs_data)
        
        # 创建一个正确类型的 ctypes 数组
        input_array = (INPUT * n_inputs)()

        # 填充数组
        for i, data in enumerate(inputs_data):
            input_array[i].type = data['type']
            if data['type'] == INPUT_KEYBOARD:
                input_array[i].union.ki.wVk = data.get('wVk', 0)
                input_array[i].union.ki.wScan = data.get('wScan', 0)
                input_array[i].union.ki.dwFlags = data.get('dwFlags', 0)
                input_array[i].union.ki.time = 0  # 系统将提供时间戳
                input_array[i].union.ki.dwExtraInfo = 0 # 通常设置为0
        
        # 调用 SendInput
        sent = self.user32.SendInput(n_inputs, input_array, ctypes.sizeof(INPUT))

        # 验证结果
        if sent != n_inputs:
            error_code = ctypes.get_last_error()
            raise BackendError(f"SendInput 调用失败 (发送 {sent}/{n_inputs}, 错误码 {error_code})")

    def type_character(self, char: str, delay: float = 0.01):
        """输入单个字符。"""
        inputs = []
        # KEYDOWN
        inputs.append({
            'type': INPUT_KEYBOARD,
            'wScan': ord(char),
            'dwFlags': KEYEVENTF_UNICODE
        })
        # KEYUP
        inputs.append({
            'type': INPUT_KEYBOARD,
            'wScan': ord(char),
            'dwFlags': KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
        })
        self._send_input(inputs)

    def press_return(self, delay: float = 0.01):
        """按下并释放回车键。"""
        inputs = []
        # KEYDOWN
        inputs.append({
            'type': INPUT_KEYBOARD,
            'wVk': VK_RETURN,
            'dwFlags': 0
        })
        # KEYUP
        inputs.append({
            'type': INPUT_KEYBOARD,
            'wVk': VK_RETURN,
            'dwFlags': KEYEVENTF_KEYUP
        })
        self._send_input(inputs)

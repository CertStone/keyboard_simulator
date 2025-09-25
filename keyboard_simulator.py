import ctypes
import time
import json
import base64
import os

# --- Windows API 定义 ---

# C-like structures for SendInput
PUL = ctypes.POINTER(ctypes.c_ulong)
class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong),
                ("wParamL", ctypes.c_short),
                ("wParamH", ctypes.c_ushort)]

class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput),
                ("mi", MouseInput),
                ("hi", HardwareInput)]

class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong),
                ("ii", Input_I)]

# Constants
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

# --- 核心键盘模拟功能 ---

def press_key(scan_code):
    """
    模拟按下和释放一个键
    """
    # Key down
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(0, scan_code, KEYEVENTF_UNICODE, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(INPUT_KEYBOARD), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

    # Key up
    ii_.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
    x = Input(ctypes.c_ulong(INPUT_KEYBOARD), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

def type_string(s, delay):
    """
    输入整个字符串
    """
    print(f"开始输入文本... 共 {len(s)} 个字符。")
    for char in s:
        if char == '\n':
            # 模拟回车键 (VK_RETURN = 0x0D)
            # 使用更可靠的虚拟键码方式模拟回车
            ctypes.windll.user32.keybd_event(0x0D, 0, 0, 0)
            time.sleep(delay)
            ctypes.windll.user32.keybd_event(0x0D, 0, KEYEVENTF_KEYUP, 0)
        else:
            press_key(ord(char))
        time.sleep(delay)
    print("文本输入完成。")

# --- 文件传输逻辑 ---

def generate_linux_command(encoded_data, output_filename):
    """
    为Linux生成解码命令
    """
    # 将长字符串分块以避免命令行长度限制
    chunk_size = 512
    chunks = [encoded_data[i:i+chunk_size] for i in range(0, len(encoded_data), chunk_size)]
    
    # 第一块使用 > 创建文件，后续使用 >> 追加
    command = f"echo -n {chunks[0]} > {output_filename}.b64\n"
    for chunk in chunks[1:]:
        command += f"echo -n {chunk} >> {output_filename}.b64\n"
    
    command += f"base64 -d {output_filename}.b64 > {output_filename}\n"
    command += f"rm {output_filename}.b64\n"
    return command

def generate_windows_command(encoded_data, output_filename):
    """
    为Windows生成解码命令
    """
    # certutil 对行长度有要求，需要分行
    lines = [encoded_data[i:i + 76] for i in range(0, len(encoded_data), 76)]
    
    # 第一行使用 > 创建文件，后续使用 >> 追加
    command = f"echo {lines[0]} > tmp.b64\n"
    for line in lines[1:]:
        command += f"echo {line} >> tmp.b64\n"
        
    command += f"certutil -decode tmp.b64 {output_filename}\n"
    command += "del tmp.b64\n"
    return command

# --- 主程序 ---

def main():
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("错误: 未找到 'config.json' 文件。请确保配置文件存在于同级目录下。")
        return
    except json.JSONDecodeError:
        print("错误: 'config.json' 文件格式不正确。请检查 JSON 语法。")
        return

    mode = config.get('mode')
    delay = config.get('delay_between_keystrokes', 0.01)
    countdown = config.get('countdown_before_start', 5)

    print("--- 键盘模拟器已启动 ---")
    print(f"模式: {mode.upper()}")
    print(f"将在 {countdown} 秒后开始输入，请将鼠标焦点切换到目标窗口...")

    for i in range(countdown, 0, -1):
        print(f"{i}...")
        time.sleep(1)
    print("开始执行！请勿操作键鼠...")

    try:
        if mode == 'text':
            text = config.get('text_to_type', '')
            if not text:
                print("警告: 'text_to_type' 为空，没有内容可以输入。")
            else:
                type_string(text, delay)
        
        elif mode == 'file':
            file_path = config.get('file_path')
            target_os = config.get('target_os')
            output_filename = config.get('output_filename')

            if not all([file_path, target_os, output_filename]):
                print("错误: 文件传输模式需要 'file_path', 'target_os', 'output_filename' 均被配置。")
                return

            if not os.path.exists(file_path):
                print(f"错误: 文件不存在 -> {file_path}")
                return

            print(f"正在读取并编码文件: {file_path}")
            with open(file_path, 'rb') as f:
                binary_data = f.read()
            
            encoded_data = base64.b64encode(binary_data).decode('ascii')
            print(f"文件编码完成，Base64 字符串长度: {len(encoded_data)}")

            if target_os == 'linux':
                command_to_type = generate_linux_command(encoded_data, output_filename)
            elif target_os == 'windows':
                command_to_type = generate_windows_command(encoded_data, output_filename)
            else:
                print(f"错误: 不支持的目标操作系统 '{target_os}'。请选择 'windows' 或 'linux'。")
                return
            
            print("将要输入的解码命令已生成。准备输入...")
            type_string(command_to_type, delay)

        else:
            print(f"错误: 未知的模式 '{mode}'。请在 'config.json' 中选择 'text' 或 'file'。")

    except Exception as e:
        print(f"\n程序执行过程中发生意外错误: {e}")
    
    print("\n--- 所有任务执行完毕 ---")


if __name__ == '__main__':
    main()

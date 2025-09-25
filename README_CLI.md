跨虚拟机键盘模拟输入工具 - 说明文档1. 项目简介本项目旨在解决因虚拟化软件限制而无法直接复制粘贴的问题。通过在宿主机 (Windows) 上运行一个 Python 脚本，可以模拟真实键盘操作，将指定的文本内容或文件内容自动输入到目标虚拟机（Windows 或 Linux）中。对于二进制文件，本工具采用 Base64 编码的策略，将其转换为纯文本字符串，然后在目标虚拟机中通过命令行工具（如 base64 或 certutil）解码，从而实现文件的“传输”。2. 文件结构keyboard_simulator.py: 主程序脚本，负责读取配置、执行键盘模拟。config.json: 配置文件。 所有操作都通过修改此文件来定义。说明文档.md: 您正在阅读的这份文件。3. 环境准备操作系统: 您的操作主机必须是 Windows。Python: 需要安装 Python 3.x。您可以从 Python 官网 下载。安装时请勾选 "Add Python to PATH"。本项目无需安装任何第三方库，仅使用 Python 内置模块。4. 使用方法核心步骤：编辑 config.json 文件，根据您的需求设置模式 (mode) 和相关参数。打开一个命令行终端（如 CMD 或 PowerShell）。使用 cd 命令切换到项目文件所在的目录。运行主程序: python keyboard_simulator.py程序会显示一个倒计时（默认为 5 秒）。在这段时间内，请立刻点击目标虚拟机的窗口，确保输入焦点在虚拟机内部的命令行或编辑器上。倒计时结束后，程序将自动开始输入。请勿移动鼠标或操作键盘，直到程序完成。配置示例 (config.json)模式一：输入纯文本 (text)如果您想输入一段文字（例如一段代码、一个命令或一篇文章），请这样配置：{
  "mode": "text",
  "text_to_type": "echo 'Hello from the host machine!'\nls -la\n",
  "delay_between_keystrokes": 0.01,
  "countdown_before_start": 5
}
text_to_type: 您要输入的字符串。特殊字符 \n 会被转换成回车键。delay_between_keystrokes: 每个按键之间的延迟（秒）。如果虚拟机反应慢，可以适当增加此值。模式二：传输文件 (file)如果您想将一个文件传输到虚拟机，请这样配置：{
  "mode": "file",
  "file_path": "C:/path/to/your/program.exe",
  "target_os": "windows",
  "output_filename": "program.exe",
  "delay_between_keystrokes": 0.01,
  "countdown_before_start": 5
}
file_path: 您本机上要传输的文件的完整路径。请使用 / 作为路径分隔符。target_os: 目标虚拟机的操作系统，可以是 "windows" 或 "linux"。这非常重要，因为解码命令不同。output_filename: 文件在虚拟机中保存的名称。5. 技术原理键盘模拟: 脚本通过 Python 的 ctypes 库调用 Windows 底层的 SendInput API。此 API 可以精确模拟键盘的按下（KeyDown）和抬起（KeyUp）事件，可靠性高。文件编码: 使用标准的 Base64 编码，它能将任意二进制数据转换成由 a-z, A-Z, 0-9, +, / 组成的文本字符串，便于传输。文件解码:Linux: 生成 echo '...' | base64 -d > filename 命令。Windows: 由于 Windows 没有原生 base64 命令，我们利用 certutil -decode。脚本会先用 echo 将 Base64 字符串分块写入临时文件（如 tmp.b64），然后执行解码命令，最后删除临时文件。6. 注意事项键盘布局: 本脚本默认基于标准的美式 (US) 键盘布局。如果您的主机或虚拟机使用其他布局，某些特殊字符可能会映射错误。焦点: 运行脚本后必须将鼠标焦点切换到目标窗口，否则输入会发送到您当前激活的窗口上。稳定性: 对于非常大的文件，传输过程可能需要很长时间，且容易被意外中断。建议用于传输中小型文件（几 MB 以内）。权限: 请确保您在目标虚拟机中有权限创建文件和执行命令。
# 键盘模拟器 - 命令行界面 (CLI)

命令行界面 (CLI) 为开发者和高级用户提供了一个强大、灵活的方式来使用键盘模拟器，无需图形界面。它非常适合集成到自动化脚本或在终端环境中直接使用。

## 1. 功能概览

- **多种输入模式**：直接通过参数输入文本 (`--text`) 或指定文件 (`--file`)。
- **后端选择**：支持在标准 `sendinput` 后端和专业的 `interception` 后端之间切换。
- **参数配置**：所有 GUI 中的选项，如按键延迟、启动倒计时等，都可以通过命令行参数进行配置。
- **日志系统**：可选的日志记录功能，便于调试和追踪。
- **兼容旧版**：支持通过 `--config` 参数加载旧版的 `config.json` 文件。

## 2. 安装

如果您已经按照主 `README.md` 中的说明安装了依赖，则可跳过此步。CLI 的核心功能无需额外依赖。

```powershell
# 激活虚拟环境
.\.venv\Scripts\Activate.ps1

# 以可编辑模式安装
pip install -e .
```

## 3. 使用方法

CLI 的主入口是 `keyboard-simulator` 命令（或 `ksim` 作为别名），这是在 `pyproject.toml` 中定义的。

### 基本用法

**模拟输入一段文本：**

```bash
# 输入 "Hello, World!" 并换行
keyboard-simulator --text "Hello, World!\n"
```

**传输一个文件 (默认目标为 Linux):**

```bash
# 将 a.txt 传输到目标系统中，并命名为 remote_a.txt
keyboard-simulator --file "C:\path\to\a.txt" --output "remote_a.txt"
```

**传输文件到 Windows 虚拟机：**

```bash
# 指定 --target-os 为 windows
keyboard-simulator --file "C:\path\to\program.exe" --target-os windows --output "program.exe"
```

### 高级选项

**指定按键延迟和倒计时：**

```bash
# 设置按键延迟为 20 毫秒，启动前倒计时为 3 秒
keyboard-simulator --text "fast input" --delay 0.02 --countdown 3
```

**使用 Interception 后端 (需要预装驱动):**

```bash
# 使用 interception 后端可以更好地兼容虚拟机和游戏
keyboard-simulator --text "Hello, VMware!" --backend interception
```

**启用日志记录：**

日志对于调试非常有用。

```bash
# 启用日志，并将级别设置为 DEBUG
keyboard-simulator --text "debug session" --log --log-level DEBUG
```
日志文件将保存在 `logs/keyboard_simulator.log`。

### 所有可用参数

您可以通过 `keyboard-simulator --help` 查看所有可用选项：

- `--config FILE`: 加载 JSON 配置文件，用于兼容旧版。
- `--text TEXT`: 要模拟输入的文本字符串。
- `--file FILE`: 要传输的本地文件路径。
- `--target-os {windows,linux}`: 文件传输的目标操作系统 (默认为 `linux`)。
- `--output FILENAME`: 在目标系统上保存的文件名。
- `--delay SECONDS`: 按键之间的延迟（秒）。
- `--countdown SECONDS`: 开始模拟前的倒计时（秒）。
- `--backend {sendinput,interception}`: 选择键盘模拟后端 (默认为 `sendinput`)。
- `--log`: 启用文件和控制台日志记录。
- `--log-level LEVEL`: 设置日志级别 (如 `DEBUG`, `INFO`)。

## 4. 示例场景

### 场景一：自动化部署脚本

假设您需要自动在一个新的 Linux 虚拟机中运行一个设置脚本。

```bash
# 准备您的 setup.sh 脚本
# 然后在宿主机上运行：
keyboard-simulator --file "./setup.sh" --output "setup.sh" --countdown 5
# (在 5 秒内切换到虚拟机终端)
# 脚本传输完成后，再发送执行命令
keyboard-simulator --text "bash setup.sh\n" --countdown 2
```

### 场景二：在远程桌面中粘贴密码

由于安全策略，某些远程桌面禁止粘贴。您可以使用此工具输入一个长而复杂的密码。

```bash
# 在本地终端输入以下命令，然后迅速点击远程桌面的密码框
keyboard-simulator --text "Your-L0ng_and-C0mpl3x-P@ssw0rd!" --delay 0.05
```

---

CLI 提供了与 GUI 版本完全相同的核心功能，但方式更直接、更适合脚本化。请根据您的具体需求选择最适合的工具。
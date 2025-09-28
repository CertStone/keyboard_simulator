# 键盘模拟器 - 专业版 (Interception 驱动)


---

## 1) 打包版快速使用（推荐给普通用户）

1. 从项目的 Release 页面下载 `KeyboardSimulatorPro.exe`。
2. 首次使用需要安装 Interception 驱动：
   - 下载并解压：https://github.com/oblitum/Interception/releases/latest （`Interception.zip`）
   - 以管理员身份打开 CMD 或 PowerShell，进入解压后的 `command line installer` 目录，执行：
     ```cmd
     install-interception.exe /install
     ```
   - 看到 “Interception successfully installed.” 即表示成功，随后重启电脑。
3. 双击运行 `KeyboardSimulatorPro.exe`，即可像标准版 GUI 一样使用（拖拽文件/输入文本、F9 开始、F10 停止、F11 暂停/恢复）。
4. 如需卸载驱动，管理员身份运行：
   ```cmd
   install-interception.exe /uninstall
   ```
   然后重启电脑。

---

## 2) 源码版（开发者）

如果你需要调试、开发或从源码运行 PRO 版：

1. 克隆并安装依赖：
   ```powershell
   git clone https://github.com/CertStone/keyboard_simulator.git
   cd keyboard_simulator
   pip install -e .[pro]
   ```
2. 安装 Interception 驱动（步骤同上“打包版快速使用”的第 2 步）。
3. 运行源码入口：
   ```powershell
   python .\keyboard_simulator_pro.py
   ```
4. 其他说明：
   - 如之前误装了名为 `interception` 的旧库，请先卸载：`pip uninstall interception`，应使用 `interception-python`。
   - PRO 版热键由驱动层处理，响应更可靠，且不影响物理键盘使用。

---

## 3) 常见问题（PRO）

- 运行 EXE 提示找不到 `win32api`？
  - 请确保从 Release 下载的是最新版本。如仍有问题，请在 Issue 中附上日志与系统版本信息。
- 安装驱动后无效？
  - 请确认使用管理员权限执行安装命令，并在安装后重启电脑。
- 与标准 GUI 有何不同？
  - PRO 版本采用驱动级输入，在虚拟化/反作弊/高防护环境下更稳定。
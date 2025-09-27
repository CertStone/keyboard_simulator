# 键盘模拟器 - 专业版 (Interception 驱动)

## 1. “专业版”简介

此版本是为解决在 VMware、VirtualBox、远程桌面及各种高强度防护软件中输入无效的终极解决方案。它通过一个名为 **Interception** 的内核级驱动程序来模拟键盘输入，其模拟的真实度远超标准 API，能够应对最苛刻的虚拟化和安全环境。

**与标准 GUI 版的区别**:
- **核心技术**: 完全采用 `Interception` 驱动进行输入，兼容性最高。
- **热键实现**: 直接在驱动层面监听 F9, F10, F11 热键，无需 `keyboard` 库，响应更迅速、更可靠，且不影响物理键盘的正常使用。

## 2. 【重要】安装与设置

此版本需要一个额外的、关键的安装步骤：安装 Interception 驱动程序。

### 第一步：安装 Interception 驱动

1.  **下载**: 前往 Interception 的官方发布页面下载最新版本：
    [https://github.com/oblitum/Interception/releases/latest](https://github.com/oblitum/Interception/releases/latest)
    下载名为 `Interception.zip` 的文件。

2.  **解压**: 将 `Interception.zip` 解压到一个固定的位置，例如 `C:\Interception`。

3.  **安装**:
    - 以 **管理员身份** 打开命令提示符 (CMD) 或 PowerShell。
    - 使用 `cd` 命令进入您解压的文件夹，然后进入 `command line installer` 子目录。例如：
      ```cmd
      cd C:\Interception\"command line installer"
      ```
    - 在该目录下，运行以下安装命令：
      ```cmd
      install-interception.exe /install
      ```
    - 如果看到 "Interception successfully installed." 的提示，说明安装成功。

4.  **重启电脑**: 这是 **必须的** 步骤！驱动程序只有在重启后才能正确加载。

### 第二步：安装 Python 依赖库

如果您已按照主 `README.md` 中的说明安装了 `[pro]` 依赖，则可跳过此步。

```bash
# 安装 interception-python 和 tkinterdnd2
pip install -e .[pro]
```
> **注意**: 如果您之前根据错误的提示安装了名为 `interception` 的库，请务必先卸载它 (`pip uninstall interception`)，以避免冲突。

## 3. 使用方法

安装完成后，使用方法与标准 GUI 版本完全相同。

### 启动程序
直接运行 `keyboard_simulator_pro.py` 即可。
```bash
python keyboard_simulator_pro.py
```

### 配置与操作
1.  **拖放文件** 或 **输入文本**。
2.  设置 **延迟** 和 **倒计时**。
3.  使用 **F9** (开始), **F10** (停止), **F11** (暂停/恢复) 或界面按钮来控制模拟过程。

### 目标
在倒计时期间，将鼠标焦点切换到 VMware 虚拟机内部，程序将开始精准输入。

## 4. 卸载驱动 (如果需要)

如果您想卸载 Interception 驱动，同样以管理员身份打开 CMD，进入 `command line installer` 目录，运行：
```cmd
install-interception.exe /uninstall
```
然后重启电脑。
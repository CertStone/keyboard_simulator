# 项目架构概览

本文档概述键盘模拟器项目的目标架构，解释模块拆分逻辑与各组件之间的依赖关系，便于后续开发者快速上手并扩展功能。

## 1. 设计目标

- **模块化**: 将项目拆分为独立的、可测试的组件，如配置、任务生成、模拟器和后端。
- **可扩展性**: 轻松添加新的键盘模拟后端（如网络代理）或新的任务类型，而无需修改核心代码。
- **代码复用**: CLI、标准 GUI 和专业版 GUI 共享同一套核心逻辑，避免代码重复。
- **清晰的关注点分离**:
  - `config.py`: 负责配置的加载、解析和验证。
  - `tasks.py`: 负责将高级配置转换为具体的、可执行的模拟任务。
  - `simulator.py`: 负责协调任务的执行，管理生命周期（开始、暂停、停止）。
  - `backends/`: 负责与底层系统 API（如 `SendInput` 或 `Interception`）交互。

## 2. 包结构

```
keyboard_simulator/
├── src/keyboard_simulator/
│   ├── __init__.py           # 包入口，导出公共 API
│   ├── config.py             # 数据模型 (TextConfig, FileConfig) 及解析逻辑
│   ├── tasks.py              # 任务规划 (build_plan)
│   ├── encoding.py           # 文件编码与脚本生成 (Base64)
│   ├── simulator.py          # 核心模拟器 (KeyboardSimulator)
│   ├── logging_config.py     # 日志配置
│   └── backends/
│       ├── base.py           # 抽象基类 (AbstractKeyboardBackend)
│       ├── sendinput.py      # 标准后端 (SendInput)
│       └── interception.py   # 专业后端 (Interception)
│
├── keyboard_simulator_gui.py # GUI 入口 (标准版)
├── keyboard_simulator_pro.py # GUI 入口 (专业版)
├── keyboard_simulator.py     # 兼容旧版的 CLI 入口
│
├── tests/                    # 单元测试
│   ├── test_config.py
│   ├── test_encoding.py
│   └── test_tasks.py
│
├── build/
│   └── pyinstaller_build.py  # PyInstaller 打包脚本
│
├── docs/
│   └── ARCHITECTURE.md       # 本文档
│
├── .github/workflows/
│   └── release.yml           # GitHub Actions 自动化发布流程
│
└── pyproject.toml            # 项目元数据与依赖管理
```

## 3. 核心流程

一个完整的模拟任务遵循以下流程：

1.  **入口点 (CLI/GUI)**: 用户通过界面或命令行参数提供输入。
2.  **配置构建**: 输入被转换为一个 `Config` 对象（`TextConfig` 或 `FileConfig`）。
3.  **任务规划**: `tasks.build_plan(config)` 函数接收 `Config` 对象，生成一个 `SimulationPlan`。
    - 对于文件，`encoding.py` 会将其内容编码为 Base64，并包装成一个 shell 脚本字符串。
    - `SimulationPlan` 包含一个或多个 `TypingTask`，每个任务都有一个要输入的 `payload` 字符串。
4.  **后端初始化**: 根据用户选择或默认设置，实例化一个具体的后端（如 `SendInputBackend`）。
5.  **模拟器实例化**: 创建 `KeyboardSimulator(backend, hooks)` 实例。`hooks` 用于将内部状态（如倒计时、完成）回调给 UI。
6.  **执行计划**: 调用 `simulator.run_plan(plan)`。
    - 模拟器处理倒计时。
    - 模拟器遍历 `plan` 中的每个 `task`，并逐字符调用 `backend.type_character(char)`。
    - 模拟器通过 `threading.Event` 监听暂停和停止信号，并相应地控制执行流程。
7.  **后端执行**: 后端将字符转换为具体的系统调用（如 `ctypes.windll.user32.SendInput`）。

## 4. 关键抽象

### `AbstractKeyboardBackend`

这是所有后端必须实现的接口，定义在 `backends/base.py`。它强制实现以下核心方法：

- `type_character(char: str, delay: float)`: 输入单个字符。
- `press_return(delay: float)`: 按下回车键。

这确保了 `KeyboardSimulator` 可以与任何后端协作，而无需了解其内部实现细节。

### `SimulatorHooks`

这是一个简单的数据类，用于将模拟器的内部事件（如倒计时更新、状态变更）传递给外部调用者（主要是 GUI），实现UI与业务逻辑的解耦。

## 5. 测试策略

- **单元测试**:
  - `config.py`, `encoding.py`, `tasks.py` 的逻辑不依赖于任何外部环境，是单元测试的重点。
  - `simulator.py` 的测试通过注入一个 **mock** 的 `AbstractKeyboardBackend` 来完成，以验证其流程控制（暂停、停止等）是否正确，而不实际调用系统 API。
- **集成测试**:
  - CLI 的端到端测试可以通过子进程调用来完成。
  - 后端模块的测试较为困难，通常需要手动测试或在特定环境（如 Windows CI/CD runner）中进行。
- **UI 测试**:
  - GUI 的关键逻辑（如配置构建）被提取到独立的辅助函数中，以便进行单元测试。
  - 完整的 UI 交互流程依赖手动测试。

## 6. 构建与发布

- **构建**: 使用 `PyInstaller` 将 `keyboard_simulator_gui.py` 和 `keyboard_simulator_pro.py` 分别打包成独立的可执行文件。`build/pyinstaller_build.py` 脚本负责处理所有细节。
- **发布**: 通过 GitHub Actions 实现自动化。当一个新的 `tag` (例如 `v0.2.0`)被推送到仓库时，`release.yml` 工作流会自动触发：
  1.  检出代码。
  2.  安装 Python 和项目依赖。
  3.  运行打包脚本。
  4.  创建一个新的 GitHub Release，并将 `dist/` 目录下的可执行文件作为附件上传。
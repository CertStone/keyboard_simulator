# 项目架构概览

本文档概述键盘模拟器开源项目的目标架构，解释模块拆分逻辑与各组件之间的依赖关系，便于后续开发者快速上手并扩展功能。

## 目标

- 提供一致且可测试的键盘输入模拟核心。
- 支持多种后端实现：Win32 `SendInput` 与 Interception 驱动。
- 通过统一的高层 API 服务于 CLI 工具与 GUI/PRO 图形界面。
- 分离配置解析、任务构建、后台输入执行等关注点，降低重复代码。

## 包结构

```
src/keyboard_simulator/
├── __init__.py
├── config.py           # 配置模型 & 解析工具
├── tasks.py            # 将配置转换成输入任务 (文本/文件)
├── encoding.py         # Base64 分块、命令生成逻辑
├── simulator.py        # KeyboardSimulator，协调任务和后端
├── backends/
│   ├── __init__.py
│   ├── base.py         # AbstractKeyboardBackend 接口定义
│   ├── sendinput.py    # Win32 SendInput 实现
│   └── interception.py # Interception 驱动实现
├── cli.py              # 命令行入口 (argparse)
└── gui/
    ├── __init__.py
    ├── base.py         # GUI 共用的控件、倒计时、线程封装
    ├── standard.py     # 标准 GUI (SendInput 后端)
    └── pro.py          # 专业版 GUI (Interception 后端)
```

## 核心流程

1. **配置阶段**：从 JSON、命令行参数或 GUI 输入构造 `Config` 数据类。
2. **任务生成**：`tasks.py` 根据配置返回一系列 `TypingTask` 对象（文本派发或文件传输命令）。
3. **模拟执行**：`KeyboardSimulator` 接收 `TypingTask`，在倒计时后通过注入的 `AbstractKeyboardBackend` 逐字符发送，提供暂停/停止控制。
4. **后端抽象**：
   - `SendInputBackend` 负责调用 Win32 API。
   - `InterceptionBackend` 负责调用 `interception-python`。
   - 二者均实现 `type_character`、`press_key_combo` 等接口，供上层统一调用。

## 扩展点

- 新的键盘后端（例如网络代理、录制回放）只需继承 `AbstractKeyboardBackend`。
- 新的任务类型（如“输入快捷命令序列”）可以通过拓展 `TypingTask` 子类实现。
- GUI 可复用 `gui.base` 中的线程、安全更新逻辑，无需关注具体后端细节。

## 数据与错误处理

- 配置解析时提供详尽的错误消息，指向具体字段。
- 任务执行通过事件对象实现暂停/停止；异常会冒泡到调用者，由 CLI/GUI 展示友好提示。
- 所有文件路径与编码逻辑集中在 `encoding.py`，便于单元测试覆盖。

## 测试策略

- 使用 `pytest` 对 `encoding.py`、`tasks.py`、`config.py` 做单元测试。
- 为 CLI 提供集成测试（在 Windows 可使用 `pytest.mark.skipif` 控制）。
- GUI 逻辑的关键函数拆分至纯函数后，通过单元测试覆盖；界面交互使用手动测试清单。

该架构将逐步在后续提交中落地执行。欢迎贡献者参考本架构，在新增功能前先讨论设计以保持一致性。
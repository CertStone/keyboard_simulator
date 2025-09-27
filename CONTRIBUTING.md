# 贡献指南

非常感谢您有兴趣改进 **键盘模拟器**！我们欢迎任何形式的贡献，无论是报告错误、提出功能建议，还是直接提交代码。

## 🚀 快速开始

如果您是第一次参与贡献，请遵循以下步骤：

1.  **Fork 并克隆**：将本仓库 Fork 到您自己的 GitHub 账户，并克隆到本地。
2.  **创建分支**：从 `main` 分支创建一个新的特性分支（例如 `feature/add-new-backend`）。
3.  **安装依赖**：为了确保开发环境一致，我们强烈建议您使用虚拟环境。

    ```powershell
    # 创建虚拟环境
    python -m venv .venv

    # 激活虚拟环境
    .\.venv\Scripts\Activate.ps1

    # 以可编辑模式安装所有依赖项（开发、Pro版、构建）
    pip install -e .[dev,pro,build]
    ```

4.  **进行修改**：实现您的新功能或修复错误。
5.  **运行质量检查**：在提交前，请确保所有代码检查和测试都能通过。

    ```powershell
    # 运行格式化和静态检查工具 (Ruff)
    ruff check . --fix
    ruff format .

    # 运行单元测试 (Pytest)
    pytest
    ```

6.  **提交拉取请求 (Pull Request)**：将您的分支推送到 GitHub，并创建一个 PR。请在 PR 中清晰地描述您的改动。

## ✅ Pull Request (PR) 清单

在提交 PR 前，请确保您已经完成了以下事项：

- [ ] 所有质量检查（代码风格、单元测试）均在本地通过。
- [ ] 如果您的改动影响了软件行为，请同步更新相关文档（如 `README.md`, `docs/ARCHITECTURE.md`）。
- [ ] 对于任何用户可见的重要改动，请在 `CHANGELOG.md` 的 `[Unreleased]` 部分添加一条记录。
- [ ] 新代码应包含类型提示 (Type Hints) 和必要的文档字符串 (Docstrings)。
- [ ] 如果涉及 UI 变动，附上截图会非常有帮助。

## 🧪 测试指南

- **核心逻辑**：针对 `src/keyboard_simulator` 中模块的单元测试应放在 `tests/` 目录下。
- **模拟器测试**：在测试 `simulator.py` 时，请使用模拟的后端 (Mock Backend) 来隔离其核心调度逻辑，避免依赖具体硬件或驱动。
- **Windows API**：如果您的测试依赖于 Windows 特定的 API（如 `SendInput`），请使用 `@pytest.mark.skipif(sys.platform != "win32", reason="仅限 Windows")` 标记，以确保测试在其他平台上可以被跳过。

## 📝 编码风格

- **代码规范**：遵循 Ruff 的默认规则（基于 PEP 8, Pyflakes 等）。
- **类型提示**：所有函数签名都应包含类型提示。
- **数据结构**：优先使用 `dataclasses` 来定义以数据为中心的对象。
- **平台隔离**：将平台相关的逻辑（如 Windows API 调用）严格限制在 `backends` 模块内部。

## 📄 文档更新

- **用户可见的改动**：请更新 `README.md` 和 `README_PRO.md`。
- **架构性决策**：请更新 `docs/ARCHITECTURE.md`，说明您的设计思路。
- **版本发布相关**：请在 `CHANGELOG.md` 中添加更新日志。

## 🙏 需要帮助？

如果您在开发过程中遇到任何问题，特别是与驱动程序或 `ctypes` 相关的棘手问题，请随时开启一个草稿 PR (Draft PR) 或发起一个讨论 (Discussion)。我们非常乐意提供帮助！

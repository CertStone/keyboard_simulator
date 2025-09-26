# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- `build/pyinstaller_build.py` 脚本，可一键调用 PyInstaller 打包 GUI/PRO 可执行程序。
- README 新增 PyInstaller 打包指南，说明依赖安装与构建命令。

### Changed
- 构建选项切换到 PyInstaller，默认清理临时目录并自动收集 GUI/PRO 所需依赖。

### Removed
- 旧的 `build/nuitka_build.py` 脚本及相关 Nuitka 指南。

## [0.1.0] - 2025-09-25
### Added
- Modular `src/keyboard_simulator` package with configuration, encoding, tasks, and simulator orchestration modules.
- New command-line interface with argparse, backend selection, and reusable configuration loader.
- Shared SendInput backend supporting Unicode and scancode modes.
- Interception backend wrapper with defensive guards.
- Comprehensive unit tests for config parsing, encoding, and task planning.
- Project metadata (`pyproject.toml`), MIT license, and contributor guidelines.
- Refreshed documentation and architecture overview.

### Changed
- GUI 和 PRO 工具均复用新的核心逻辑，移除重复的编码/倒计时实现。
- README 全面改版，覆盖 CLI/GUI/PRO 场景与开发流程。

### Removed
- Legacy monolithic logic embedded in `keyboard_simulator.py`.

"""Command line interface for the keyboard simulator."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Optional

from . import config as cfg
from .config import ConfigError
from .backends.sendinput import SendInputBackend
from .simulator import KeyboardSimulator, SimulatorHooks
from .tasks import build_plan
from .logging_config import setup_logging, disable_logging

try:  # pragma: no cover - optional dependency
    from .backends.interception import InterceptionBackend
except Exception:  # pragma: no cover
    InterceptionBackend = None  # type: ignore[assignment]


def _positive_float(value: str) -> float:
    result = float(value)
    if result < 0:
        raise argparse.ArgumentTypeError("必须是非负数值")
    return result


def _positive_int(value: str) -> int:
    result = int(value)
    if result < 0:
        raise argparse.ArgumentTypeError("必须是非负整数")
    return result


def _build_config_from_args(args: argparse.Namespace) -> cfg.Config:
    if args.config:
        return cfg.load(Path(args.config))

    delay = args.delay if args.delay is not None else 0.01
    countdown = args.countdown if args.countdown is not None else 5

    if args.text is not None:
        return cfg.TextConfig(
            text_to_type=args.text,
            delay_between_keystrokes=delay,
            countdown_before_start=countdown,
        )

    if args.file is not None:
        if not args.output:
            output = Path(args.file).name
        else:
            output = args.output
        return cfg.FileConfig(
            file_path=Path(args.file),
            target_os=args.target_os,
            output_filename=output,
            delay_between_keystrokes=delay,
            countdown_before_start=countdown,
        )

    raise argparse.ArgumentError(None, "必须提供 --config 或 --text / --file")


def _create_backend(name: str):
    if name == "sendinput":
        return SendInputBackend()
    if name == "interception":
        if InterceptionBackend is None:
            raise SystemExit("未安装 interception-python，无法使用 interception 后端")
        return InterceptionBackend()
    raise SystemExit(f"未知的后端: {name}")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="跨虚拟机键盘模拟输入工具")
    parser.add_argument("--config", type=str, help="配置文件路径 (JSON)")
    parser.add_argument("--text", type=str, help="直接输入要模拟的文本")
    parser.add_argument("--file", type=str, help="要传输的文件路径")
    parser.add_argument(
        "--target-os",
        type=str,
        choices=["windows", "linux"],
        default="linux",
        help="文件传输目标操作系统",
    )
    parser.add_argument("--output", type=str, help="目标机器上的输出文件名")
    parser.add_argument("--delay", type=_positive_float, help="按键间隔 (秒)")
    parser.add_argument("--countdown", type=_positive_int, help="启动前倒计时 (秒)")
    parser.add_argument(
        "--backend",
        choices=["sendinput", "interception"],
        default="sendinput",
        help="选择键盘后端实现",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="设置日志记录级别",
    )
    parser.add_argument(
        "--log", action="store_true", help="启用文件和控制台日志记录"
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    args = parse_args(argv)
    if args.log:
        setup_logging(log_level=args.log_level)
    else:
        disable_logging()
    
    logger = logging.getLogger(__name__)

    try:
        logger.info("正在从参数构建配置...")
        config = _build_config_from_args(args)
        logger.debug("构建的配置: %s", config)

        logger.info("正在构建任务计划...")
        plan = build_plan(config)
        logger.debug("构建的计划包含 %d 个任务", len(plan.tasks))

        logger.info("正在创建后端: %s", args.backend)
        backend = _create_backend(args.backend)

        hooks = SimulatorHooks(
            on_countdown=lambda s: logger.info("%d 秒后开始...", s),
            on_status=lambda s: logger.info("状态更新: %s", s),
        )

        simulator = KeyboardSimulator(backend, hooks)

        logger.info("开始执行模拟...")
        simulator.run_plan(plan)
        logger.info("模拟执行完毕。")

    except (ConfigError, argparse.ArgumentError, ValueError) as e:
        logger.error("配置或参数错误: %s", e, exc_info=True)
        raise SystemExit(f"错误: {e}")
    except Exception as e:
        logger.critical("发生未预料的严重错误: %s", e, exc_info=True)
        raise SystemExit(f"严重错误: {e}")


if __name__ == "__main__":  # pragma: no cover
    main()

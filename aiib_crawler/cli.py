"""命令行入口、交互式引导与退出码处理。"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable, Sequence

from aiib_crawler.config import (
    TAB_LABELS,
    VALID_TABS,
    Config,
    ConfigError,
    load_config,
)
from aiib_crawler.crawler import AIIBCrawler
from aiib_crawler.storage import CheckpointState, Storage, StorageError

logger = logging.getLogger(__name__)


def setup_logging(*, verbose: bool = False) -> None:
    """初始化统一格式的控制台日志。"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


def select_tabs(input_fn: Callable[[str], str] = input) -> tuple[str, ...]:
    """交互式询问用户要抓取的 AIIB 数据模块。"""
    print("\n" + "=" * 64)
    print("请选择要抓取的亚投行 (AIIB) 研究数据模块:")
    for idx, tab in enumerate(VALID_TABS, start=1):
        print(f"  [{idx}] {tab:<15} - {TAB_LABELS[tab]}")
    print(f"  [{len(VALID_TABS) + 1}] all             - 全部抓取（默认）")
    print("  （支持多选，例如输入 1,3 或直接回车选择全部）")
    print("=" * 64)

    mapping = {str(idx): tab for idx, tab in enumerate(VALID_TABS, start=1)}
    all_key = str(len(VALID_TABS) + 1)

    while True:
        choice = input_fn(f"请输入序号 (1-{all_key}，默认 {all_key}): ").strip().lower()
        if not choice or choice in (all_key, "all"):
            return VALID_TABS

        parts = [p.strip() for p in choice.replace("，", ",").split(",") if p.strip()]
        selected: list[str] = []
        valid = True
        for part in parts:
            if part in mapping:
                tab = mapping[part]
            elif part in VALID_TABS:
                tab = part
            else:
                valid = False
                break
            if tab not in selected:
                selected.append(tab)

        if valid and selected:
            return tuple(selected)
        print("输入无效，请重新输入有效序号或模块名。")


def select_resume_mode(state: CheckpointState, input_fn: Callable[[str], str] = input) -> str:
    """发现历史数据时，交互式询问继续抓取还是备份重置。"""
    done_str = ", ".join(sorted(state.completed_tabs)) if state.completed_tabs else "无"
    print("\n" + "=" * 64)
    print("[!] 检测到本地已存在历史抓取进度！")
    print(f"    - 已记录的去重条目/文件数: {len(state.seen_ids)} 条")
    print(f"    - 已完成的模块: {done_str}")
    if state.updated_at:
        print(f"    - 上次更新时间: {state.updated_at}")
    print("=" * 64)
    print("请选择操作模式:")
    print("  [1] 继续上次的进度抓取 (Resume) —— 推荐")
    print("  [2] 备份旧数据并重新开始 (Reset)")

    while True:
        choice = input_fn("请输入序号 (1 或 2，默认 1): ").strip().lower()
        if choice in ("", "1", "resume"):
            return "resume"
        if choice in ("2", "reset"):
            return "reset"
        print("输入无效，请输入 1 或 2。")


def prepare(config: Config, input_fn: Callable[[str], str] = input) -> tuple[Config, Storage, CheckpointState]:
    """根据配置与磁盘状态完成运行前准备（模块选择、断点恢复或安全备份重置）。"""
    if not config.tabs_explicit:
        tabs = select_tabs(input_fn=input_fn)
        config = config.with_overrides(tabs=tabs, tabs_explicit=True)

    storage = Storage(config.data_dir, config.tabs)
    mode = config.mode

    if storage.has_previous_run():
        existing_state = storage.load_state()
        if mode is None:
            mode = select_resume_mode(existing_state, input_fn=input_fn)

        if mode == "reset":
            storage.backup_and_reset()
            state = storage.load_state()
        else:
            state = existing_state
            logger.info(
                "[*] 已加载历史进度：已记录 %d 个条目/附件，已完成模块 %s",
                len(state.seen_ids),
                sorted(state.completed_tabs),
            )
    else:
        mode = mode or "resume"
        state = CheckpointState()

    config = config.with_overrides(mode=mode)
    return config, storage, state


def run(argv: Sequence[str] | None = None) -> int:
    """执行完整爬虫流程并返回进程退出码。"""
    config = load_config(argv)
    setup_logging(verbose=config.verbose)

    config, storage, state = prepare(config)
    logger.info(
        "[*] 目标数据模块: %s | 重点国家过滤: %s | PDF下载策略: %s",
        ", ".join(config.tabs),
        config.country_filter,
        config.download_pdfs,
    )
    if config.since or config.until:
        since_str = config.since.astimezone(config.tz).strftime("%Y-%m-%d") if config.since else "不限"
        until_str = config.until.astimezone(config.tz).strftime("%Y-%m-%d") if config.until else "不限"
        logger.info("[*] 时间过滤范围 (%s): %s ~ %s", config.tz_label, since_str, until_str)

    crawler = AIIBCrawler(config, storage)
    counts = crawler.run(state)

    summary = ", ".join(f"{tab}={count}" for tab, count in counts.items())
    logger.info("[+] 全部采集任务已完成！数据保存在 %s (%s)", config.data_dir, summary)
    return 0


def main(argv: Sequence[str] | None = None) -> None:
    """CLI 主入口，统一处理配置错误、存储错误与 Ctrl+C 中断。"""
    try:
        code = run(argv)
    except ConfigError as e:
        print(f"[!] 配置错误: {e}", file=sys.stderr)
        sys.exit(2)
    except StorageError as e:
        print(f"[!] 存储错误: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[!] 用户中断运行，当前进度与已采集数据已安全保存。", file=sys.stderr)
        sys.exit(130)
    sys.exit(code)

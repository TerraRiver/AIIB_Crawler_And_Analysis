"""配置加载与校验模块。"""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta, timezone, tzinfo
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv

BASE_URL = "https://www.aiib.org"
VALID_TABS = ("projects", "procurement", "governance", "accountability")
VALID_MODES = ("resume", "reset")
VALID_PDF_SCOPES = ("none", "india", "all")

TAB_LABELS = {
    "projects": "常规项目主表与详情页 (Projects)",
    "procurement": "项目采购、招标公告与中标合同 (Procurement & Contract Awards)",
    "governance": "治理结构、投票权、理事会与董事会会议纪要 (Governance & Board Records)",
    "accountability": "问责机制(PPM)、独立评估(CEIU)与制裁名单 (Accountability & Debarment)",
}


class ConfigError(ValueError):
    """配置参数不合法。"""


@dataclass(frozen=True)
class Config:
    """运行配置（不可变）。"""

    data_dir: Path
    profile_dir: Path
    headless: bool = False
    tabs: tuple[str, ...] = VALID_TABS
    tabs_explicit: bool = False
    mode: str | None = None
    country_filter: str = "ALL"
    download_pdfs: str = "india"
    max_detail_pages: int = 0  # 0 表示不限制，全量抓取项目详情页
    since: datetime | None = None
    until: datetime | None = None
    tz: tzinfo = UTC
    tz_label: str = "UTC"
    verbose: bool = False

    def with_overrides(self, **kwargs: object) -> Config:
        """返回覆盖指定字段后的新配置对象。"""
        return replace(self, **kwargs)


def parse_tabs(raw: str) -> tuple[str, ...]:
    """解析并校验数据类型列表（去重保序）。"""
    value = raw.strip().lower()
    if not value or value == "all":
        return VALID_TABS

    seen: list[str] = []
    for part in value.split(","):
        tab = part.strip()
        if not tab:
            continue
        if tab not in VALID_TABS:
            valid = ", ".join((*VALID_TABS, "all"))
            raise ConfigError(f"无效的数据模块 '{tab}'，可选值: {valid}")
        if tab not in seen:
            seen.append(tab)

    if not seen:
        raise ConfigError("至少需要指定一个数据模块")
    return tuple(seen)


def parse_pdf_scope(raw: str) -> str:
    """解析 PDF 附件下载范围。"""
    value = raw.strip().lower()
    if not value:
        return "india"
    if value not in VALID_PDF_SCOPES:
        valid = ", ".join(VALID_PDF_SCOPES)
        raise ConfigError(f"无效的 PDF 下载范围 '{raw}'，可选值: {valid}")
    return value


def parse_timezone(raw: str | None) -> tuple[tzinfo, str]:
    """解析时区配置，支持 UTC、±HH:MM、±HH 或 IANA 时区名。"""
    value = (raw or "UTC").strip()
    if not value or value.upper() == "UTC" or value == "Z":
        return UTC, "UTC"

    normalized = value[3:].strip() if value.upper().startswith("UTC") and len(value) > 3 else value
    if normalized and normalized[0] in ("+", "-"):
        sign = 1 if normalized[0] == "+" else -1
        rest = normalized[1:]
        try:
            if ":" in rest:
                hours_str, minutes_str = rest.split(":", 1)
                hours, minutes = int(hours_str), int(minutes_str)
            elif len(rest) <= 2:
                hours, minutes = int(rest), 0
            elif len(rest) == 4:
                hours, minutes = int(rest[:2]), int(rest[2:])
            else:
                raise ValueError
        except ValueError as e:
            raise ConfigError(f"无效的时区偏移 '{raw}'，示例: +08:00, -05:00, UTC, Asia/Shanghai") from e

        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ConfigError(f"时区偏移超出范围 '{raw}'")
        offset = timedelta(minutes=sign * (hours * 60 + minutes))
        label = f"UTC{'+' if sign > 0 else '-'}{hours:02d}:{minutes:02d}"
        return timezone(offset), label

    try:
        return ZoneInfo(value), value
    except ZoneInfoNotFoundError as e:
        raise ConfigError(f"未知的时区 '{raw}'，示例: UTC, +08:00, Asia/Shanghai") from e


def parse_bound_datetime(raw: str | None, *, is_end_bound: bool, default_tz: tzinfo) -> datetime | None:
    """解析时间边界字符串并统一转换为 UTC。"""
    if raw is None or not raw.strip():
        return None
    value = raw.strip()

    if len(value) == 4 and value.isdigit():
        year = int(value)
        if is_end_bound:
            local_dt = datetime(year, 12, 31, 23, 59, 59, 999999, tzinfo=default_tz)
        else:
            local_dt = datetime(year, 1, 1, 0, 0, 0, tzinfo=default_tz)
        return local_dt.astimezone(UTC)

    if len(value) == 10 and value[4] == "-" and value[7] == "-":
        try:
            dt = datetime.strptime(value, "%Y-%m-%d")
        except ValueError as e:
            raise ConfigError(f"无效的日期格式 '{raw}'，期望 YYYY 或 YYYY-MM-DD") from e
        if is_end_bound:
            dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        return dt.replace(tzinfo=default_tz).astimezone(UTC)

    iso_val = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    try:
        dt = datetime.fromisoformat(iso_val)
    except ValueError as e:
        raise ConfigError(f"无效的时间格式 '{raw}'，期望 YYYY、YYYY-MM-DD 或 ISO 8601") from e

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=default_tz)
    return dt.astimezone(UTC)


def build_arg_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="aiib-crawler",
        description="亚洲基础设施投资银行 (AIIB) 印度参与度、态度与偏好策略全量研究数据采集工具",
    )
    parser.add_argument(
        "--types",
        metavar="LIST",
        help="要抓取的数据模块，逗号分隔: projects,procurement,governance,accountability 或 all",
    )
    parser.add_argument(
        "--mode",
        choices=VALID_MODES,
        help="断点处理模式: resume(继续上次进度) 或 reset(备份旧数据并重新开始)",
    )
    parser.add_argument(
        "--country",
        metavar="NAME",
        help="重点过滤或优先标记的成员国（默认 ALL 抓取全行数据作为基准对照，可设 India）",
    )
    parser.add_argument(
        "--download-pdfs",
        choices=VALID_PDF_SCOPES,
        help="PDF 原始文件下载范围: none(仅元数据+Excel), india(下载印度项目PDF+治理与评估核心PDF), all(全量PDF)",
    )
    parser.add_argument(
        "--max-detail-pages",
        type=int,
        metavar="N",
        help="最大抓取的项目详情页数量（0 表示不限制，全量抓取所有项目详情页）",
    )
    parser.add_argument(
        "--since",
        metavar="TIME",
        help="起始时间下界（含），支持 YYYY 或 YYYY-MM-DD",
    )
    parser.add_argument(
        "--until",
        metavar="TIME",
        help="截止时间上界（含），支持 YYYY 或 YYYY-MM-DD",
    )
    parser.add_argument(
        "--tz",
        metavar="TZ",
        help="解析无时区时间以及输出展示使用的时区（如 UTC, +08:00, Asia/Shanghai）",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        metavar="PATH",
        help="数据存储目录（默认 ./data）",
    )
    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="是否使用无头浏览器模式 (--headless / --no-headless)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="输出调试级别日志",
    )
    return parser


def load_config(argv: Sequence[str] | None = None, env_file: Path | None = None) -> Config:
    """合并环境变量与命令行参数（CLI 优先），返回校验后的 Config。"""
    load_dotenv(dotenv_path=env_file)
    args = build_arg_parser().parse_args(argv)

    data_dir = (args.data_dir or Path(os.getenv("DATA_DIR", "./data"))).expanduser().resolve()

    profile_env = os.getenv("BROWSER_PROFILE_DIR", "").strip()
    profile_dir = Path(profile_env).expanduser().resolve() if profile_env else data_dir / "browser_profile"

    headless = args.headless if args.headless is not None else os.getenv("HEADLESS", "true").strip().lower() in ("1", "true", "yes")

    raw_types = args.types if args.types is not None else os.getenv("CRAWL_TYPES", "").strip()
    tabs_explicit = bool(raw_types)
    tabs = parse_tabs(raw_types) if tabs_explicit else VALID_TABS

    raw_mode = args.mode or os.getenv("RESUME_MODE", "").strip().lower() or None
    if raw_mode is not None and raw_mode not in VALID_MODES:
        raise ConfigError(f"无效的断点模式 '{raw_mode}'，可选值: {', '.join(VALID_MODES)}")

    country_filter = (args.country or os.getenv("COUNTRY_FILTER", "ALL")).strip() or "ALL"

    raw_pdf_scope = args.download_pdfs or os.getenv("DOWNLOAD_PDFS", "india").strip()
    download_pdfs = parse_pdf_scope(raw_pdf_scope)

    if args.max_detail_pages is not None:
        max_detail_pages = max(0, args.max_detail_pages)
    else:
        raw_max_pages = os.getenv("MAX_DETAIL_PAGES", "0").strip()
        try:
            max_detail_pages = max(0, int(raw_max_pages))
        except ValueError as e:
            raise ConfigError(f"无效的 MAX_DETAIL_PAGES '{raw_max_pages}'，应为非负整数") from e

    raw_tz = args.tz if args.tz is not None else os.getenv("TIMEZONE", "UTC")
    tz, tz_label = parse_timezone(raw_tz)

    raw_since = args.since if args.since is not None else os.getenv("SINCE")
    raw_until = args.until if args.until is not None else os.getenv("UNTIL")
    since = parse_bound_datetime(raw_since, is_end_bound=False, default_tz=tz)
    until = parse_bound_datetime(raw_until, is_end_bound=True, default_tz=tz)

    if since and until and since > until:
        raise ConfigError(f"起始时间 ({since.isoformat()}) 不能晚于截止时间 ({until.isoformat()})")

    return Config(
        data_dir=data_dir,
        profile_dir=profile_dir,
        headless=headless,
        tabs=tabs,
        tabs_explicit=tabs_explicit,
        mode=raw_mode,
        country_filter=country_filter,
        download_pdfs=download_pdfs,
        max_detail_pages=max_detail_pages,
        since=since,
        until=until,
        tz=tz,
        tz_label=tz_label,
        verbose=bool(args.verbose),
    )

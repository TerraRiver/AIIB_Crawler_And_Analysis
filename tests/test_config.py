"""Config 模块参数解析与校验测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from aiib_crawler.config import (
    VALID_TABS,
    ConfigError,
    load_config,
    parse_bound_datetime,
    parse_pdf_scope,
    parse_tabs,
    parse_timezone,
)


def test_parse_tabs_all_and_subsets() -> None:
    assert parse_tabs("all") == VALID_TABS
    assert parse_tabs("") == VALID_TABS
    assert parse_tabs("projects,governance,projects") == ("projects", "governance")


def test_parse_tabs_invalid_raises() -> None:
    with pytest.raises(ConfigError):
        parse_tabs("projects,invalid_module")


def test_parse_pdf_scope() -> None:
    assert parse_pdf_scope("india") == "india"
    assert parse_pdf_scope("ALL") == "all"
    assert parse_pdf_scope("none") == "none"
    with pytest.raises(ConfigError):
        parse_pdf_scope("unknown")


def test_parse_timezone_variants() -> None:
    tz_utc, label_utc = parse_timezone("UTC")
    assert label_utc == "UTC"

    tz_offset, label_offset = parse_timezone("+08:00")
    assert label_offset == "UTC+08:00"

    tz_iana, label_iana = parse_timezone("Asia/Shanghai")
    assert label_iana == "Asia/Shanghai"

    with pytest.raises(ConfigError):
        parse_timezone("Invalid/Zone")


def test_parse_bound_datetime_year_and_date() -> None:
    tz, _ = parse_timezone("UTC")
    dt_start = parse_bound_datetime("2020", is_end_bound=False, default_tz=tz)
    dt_end = parse_bound_datetime("2020", is_end_bound=True, default_tz=tz)
    assert dt_start is not None and dt_start.year == 2020 and dt_start.month == 1 and dt_start.day == 1
    assert dt_end is not None and dt_end.year == 2020 and dt_end.month == 12 and dt_end.day == 31


def test_load_config_cli_precedence(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("CRAWL_TYPES=projects\nCOUNTRY_FILTER=China\n", encoding="utf-8")

    cfg = load_config(
        [
            "--types",
            "governance,accountability",
            "--country",
            "India",
            "--download-pdfs",
            "none",
            "--since",
            "2018",
            "--until",
            "2025",
            "--data-dir",
            str(tmp_path / "out"),
        ],
        env_file=env_file,
    )
    assert cfg.tabs == ("governance", "accountability")
    assert cfg.tabs_explicit is True
    assert cfg.country_filter == "India"
    assert cfg.download_pdfs == "none"
    assert cfg.since is not None and cfg.since.year == 2018
    assert cfg.until is not None and cfg.until.year == 2025


def test_load_config_since_after_until_raises(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(["--since", "2025", "--until", "2020"], env_file=env_file)

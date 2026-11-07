"""CLI 交互选择与运行前准备逻辑测试。"""

from __future__ import annotations

from pathlib import Path

from aiib_crawler.cli import prepare, select_resume_mode, select_tabs
from aiib_crawler.config import VALID_TABS, Config
from aiib_crawler.storage import CheckpointState, Storage


def test_select_tabs_interactive() -> None:
    inputs = iter(["invalid", "1,3"])
    selected = select_tabs(input_fn=lambda _: next(inputs))
    assert selected == ("projects", "governance")

    assert select_tabs(input_fn=lambda _: "") == VALID_TABS


def test_select_resume_mode_interactive() -> None:
    state = CheckpointState(seen_ids={"a"}, completed_tabs={"projects"})
    assert select_resume_mode(state, input_fn=lambda _: "1") == "resume"
    assert select_resume_mode(state, input_fn=lambda _: "2") == "reset"


def test_prepare_handles_reset_and_resume(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    storage.save_state(CheckpointState(seen_ids={"id1"}, completed_tabs={"governance"}))

    cfg_resume = Config(
        data_dir=tmp_path,
        profile_dir=tmp_path / "profile",
        tabs=("governance",),
        tabs_explicit=True,
        mode="resume",
    )
    _, _, state_resumed = prepare(cfg_resume)
    assert "id1" in state_resumed.seen_ids

    cfg_reset = cfg_resume.with_overrides(mode="reset")
    _, _, state_reset = prepare(cfg_reset)
    assert len(state_reset.seen_ids) == 0

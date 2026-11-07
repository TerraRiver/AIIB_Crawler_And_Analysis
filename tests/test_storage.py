"""Storage 模块原子写入、断点保存、增量日志重放与备份重置测试。"""

from __future__ import annotations

import json
from pathlib import Path

from aiib_crawler.storage import CheckpointState, Storage, atomic_write_json


def test_atomic_write_json_and_checkpoint_roundtrip(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    assert storage.has_previous_run() is False

    state = CheckpointState(
        seen_ids={"url:1", "url:2"},
        completed_tabs={"governance"},
    )
    storage.save_state(state)
    assert storage.has_previous_run() is True

    loaded = storage.load_state()
    assert loaded.seen_ids == {"url:1", "url:2"}
    assert loaded.completed_tabs == {"governance"}
    assert loaded.updated_at is not None


def test_journal_replay_merges_and_cleans_up(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    storage.save_tab_records("projects", [{"record_id": "p1", "title": "Project 1"}])
    storage.append_journal("projects", {"record_id": "p1", "title": "Project 1 duplicate"})
    storage.append_journal("projects", {"record_id": "p2", "title": "Project 2 new"})
    assert storage.journal_file.exists()

    # 重新实例化 Storage 应自动重放 .journal.jsonl 并去重合并到 projects.json
    storage2 = Storage(tmp_path)
    assert not storage2.journal_file.exists()
    records = storage2.load_tab_records("projects")
    assert len(records) == 2
    assert {r["record_id"] for r in records} == {"p1", "p2"}


def test_backup_and_reset_moves_files_safely(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    storage.save_state(CheckpointState(seen_ids={"a"}, completed_tabs={"projects"}))
    storage.save_tab_records("projects", [{"record_id": "p1"}])
    storage.save_dataset("projects", "india_projects_summary", [{"record_id": "p1"}])

    backup_dir = storage.backup_and_reset()
    assert backup_dir is not None and backup_dir.exists()
    assert (backup_dir / "state.json").exists()
    assert (backup_dir / "projects.json").exists()
    assert not storage.state_file.exists()
    assert not storage.tab_file("projects").exists()

    # 测试 atomic_write_json 写入字典
    sample_path = tmp_path / "sample.json"
    atomic_write_json(sample_path, {"ok": True})
    assert json.loads(sample_path.read_text(encoding="utf-8")) == {"ok": True}

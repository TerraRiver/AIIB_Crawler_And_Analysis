"""持久化存储、断点状态与增量日志管理。"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aiib_crawler.config import VALID_TABS

logger = logging.getLogger(__name__)


class StorageError(RuntimeError):
    """数据读写或结构校验失败。"""


def atomic_write_json(path: Path, payload: Any) -> None:
    """通过同目录临时文件 + fsync + os.replace 原子写入 JSON，防止中断损坏。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


@dataclass
class CheckpointState:
    """断点续传状态。"""

    seen_ids: set[str] = field(default_factory=set)
    completed_tabs: set[str] = field(default_factory=set)
    updated_at: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> CheckpointState:
        if not isinstance(raw, dict):
            raise StorageError("state.json 顶层必须是 JSON 对象")
        seen = raw.get("seen_ids", [])
        completed = raw.get("completed_tabs", [])
        if not isinstance(seen, list) or not isinstance(completed, list):
            raise StorageError("state.json 中的 seen_ids 与 completed_tabs 必须是数组")
        return cls(
            seen_ids={str(x) for x in seen if x},
            completed_tabs={str(x) for x in completed if x},
            updated_at=raw.get("updated_at"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "seen_ids": sorted(self.seen_ids),
            "completed_tabs": sorted(self.completed_tabs),
            "updated_at": datetime.now(UTC).isoformat(),
        }


class Storage:
    """管理 state.json、各模块 JSON 数据集、增量 journal 以及安全备份重置。"""

    def __init__(self, data_dir: Path, tabs: tuple[str, ...] = VALID_TABS) -> None:
        self.data_dir = data_dir
        self.tabs = tabs
        self.state_file = data_dir / "state.json"
        self.journal_file = data_dir / ".journal.jsonl"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._replay_journal_if_present()

    def tab_dir(self, tab: str) -> Path:
        """返回指定模块的子目录路径。"""
        d = self.data_dir / tab
        d.mkdir(parents=True, exist_ok=True)
        return d

    def tab_file(self, tab: str) -> Path:
        """返回指定模块的主汇总 JSON 文件路径。"""
        return self.data_dir / f"{tab}.json"

    def dataset_file(self, tab: str, name: str) -> Path:
        """返回模块子目录下的具名 JSON 数据集路径。"""
        return self.tab_dir(tab) / f"{name}.json"

    def has_previous_run(self) -> bool:
        """检查是否存在历史抓取记录或断点文件。"""
        if self.state_file.exists():
            return True
        if any(self.tab_file(t).exists() for t in VALID_TABS):
            return True
        return any((self.data_dir / t).exists() and any((self.data_dir / t).iterdir()) for t in VALID_TABS)

    def load_state(self) -> CheckpointState:
        """加载断点状态；若文件不存在则返回空状态。"""
        if not self.state_file.exists():
            return CheckpointState()
        try:
            raw = json.loads(self.state_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise StorageError(f"断点文件 {self.state_file} JSON 解析失败: {e}") from e
        return CheckpointState.from_dict(raw)

    def save_state(self, state: CheckpointState) -> None:
        """原子保存断点状态。"""
        atomic_write_json(self.state_file, state.to_dict())

    def load_records(self, path: Path) -> list[dict[str, Any]]:
        """读取指定 JSON 列表文件。"""
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise StorageError(f"数据文件 {path} JSON 解析失败: {e}") from e
        if not isinstance(data, list):
            raise StorageError(f"数据文件 {path} 顶层结构必须是数组")
        return data

    def save_records(self, path: Path, records: list[dict[str, Any]]) -> None:
        """原子保存 JSON 列表文件。"""
        atomic_write_json(path, records)

    def load_tab_records(self, tab: str) -> list[dict[str, Any]]:
        """读取指定模块主汇总 JSON 文件。"""
        return self.load_records(self.tab_file(tab))

    def save_tab_records(self, tab: str, records: list[dict[str, Any]]) -> None:
        """保存指定模块主汇总 JSON 文件并清理对应的增量日志。"""
        atomic_write_json(self.tab_file(tab), records)

    def save_dataset(self, tab: str, name: str, payload: Any) -> Path:
        """原子保存模块子目录下的具名 JSON 数据集。"""
        target = self.dataset_file(tab, name)
        atomic_write_json(target, payload)
        return target

    def append_journal(self, tab: str, record: dict[str, Any]) -> None:
        """将单条抓取结果追加到增量日志（Write-Ahead Log），防止进程中断丢失未落盘数据。"""
        entry = json.dumps({"tab": tab, "record": record}, ensure_ascii=False)
        with self.journal_file.open("a", encoding="utf-8") as f:
            f.write(entry + "\n")
            f.flush()
            os.fsync(f.fileno())

    def clear_journal(self) -> None:
        """清理已完成合并的增量日志。"""
        self.journal_file.unlink(missing_ok=True)

    def _replay_journal_if_present(self) -> None:
        """启动时若发现未合并的增量日志，自动重放并合并进对应的模块 JSON 文件。"""
        if not self.journal_file.exists():
            return

        by_tab: dict[str, list[dict[str, Any]]] = {}
        try:
            lines = self.journal_file.read_text(encoding="utf-8").splitlines()
        except OSError as e:
            logger.warning("读取增量日志失败，跳过恢复: %s", e)
            return

        for line in lines:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                tab = item.get("tab")
                record = item.get("record")
                if tab in VALID_TABS and isinstance(record, dict):
                    by_tab.setdefault(tab, []).append(record)
            except json.JSONDecodeError:
                logger.warning("忽略损坏的增量日志行")

        for tab, journal_records in by_tab.items():
            existing = self.load_tab_records(tab)
            existing_keys = {self._record_key(r) for r in existing}
            added = 0
            for rec in journal_records:
                key = self._record_key(rec)
                if key not in existing_keys:
                    existing.append(rec)
                    existing_keys.add(key)
                    added += 1
            if added:
                atomic_write_json(self.tab_file(tab), existing)
                logger.info("[*] 从增量日志恢复了 %d 条 [%s] 记录", added, tab)

        self.journal_file.unlink(missing_ok=True)

    @staticmethod
    def _record_key(record: dict[str, Any]) -> str:
        """生成记录去重唯一键。"""
        for field_name in ("record_id", "project_id", "url", "id", "no"):
            val = record.get(field_name)
            if val:
                return f"{field_name}:{val}"
        return json.dumps(record, sort_keys=True, ensure_ascii=False)

    def backup_and_reset(self) -> Path | None:
        """将当前目标模块（self.tabs）的现有数据文件移入带时间戳的备份目录，而非直接删除。"""
        is_full_reset = set(self.tabs) >= set(VALID_TABS)
        targets: list[Path] = []
        if is_full_reset and self.state_file.exists():
            targets.append(self.state_file)
        if self.journal_file.exists():
            targets.append(self.journal_file)
        for tab in self.tabs:
            tf = self.tab_file(tab)
            if tf.exists():
                targets.append(tf)
            td = self.data_dir / tab
            if td.exists() and any(td.iterdir()):
                targets.append(td)

        if not targets and not self.state_file.exists():
            return None

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.data_dir / "backups" / stamp
        backup_dir.mkdir(parents=True, exist_ok=True)

        for path in targets:
            shutil.move(str(path), str(backup_dir / path.name))

        if not is_full_reset and self.state_file.exists():
            shutil.copy2(str(self.state_file), str(backup_dir / self.state_file.name))
            state = self.load_state()
            for tab in self.tabs:
                state.completed_tabs.discard(tab)
                # 清理属于该模块的已记录条目与附件键，以便重新拉取与下载
                prefixes = self._tab_key_prefixes(tab)
                state.seen_ids = {k for k in state.seen_ids if not any(k.startswith(p) or p in k for p in prefixes)}
            if not state.completed_tabs:
                state.seen_ids.clear()
            self.save_state(state)

        logger.info("[*] 已将 %s 旧数据备份至: %s", ",".join(self.tabs), backup_dir)
        return backup_dir

    @staticmethod
    def _tab_key_prefixes(tab: str) -> tuple[str, ...]:
        mapping: dict[str, tuple[str, ...]] = {
            "projects": ("/en/projects/details/", "project_number:"),
            "procurement": ("ppo:", "/project-procurement/"),
            "governance": ("member:", "governor:", "resolution:", "bog_proceedings:", "constituency:", "bod_minutes:", "/governance/"),
            "accountability": (
                "ppm:",
                "ceiu_plr:",
                "ceiu_dialogue:",
                "debarment:",
                "/project-affected-peoples-mechanism/",
                "/complaints-resolution-evaluation-integrity-unit/",
                "PLR-GUJARAT",
            ),
        }
        return mapping.get(tab, (tab,))

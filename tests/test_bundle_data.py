from __future__ import annotations

import unicodedata
import zipfile
from pathlib import Path

import pytest

from scripts.bundle_data import (
    BUNDLE_SPECS,
    BundleSpec,
    decode_member_name,
    pack_bundle,
    unpack_archive,
    verify_archive,
)


def test_pack_and_unpack_chinese_filenames_utf8_nfc(tmp_path: Path) -> None:
    src_root = tmp_path / "src_repo"
    out_dir = tmp_path / "dist"
    dst_root = tmp_path / "dst_repo"
    dst_root.mkdir()

    # 含中文、全角标点与 NFD 分解字符的文件名，模拟 macOS 常见场景
    nfd_name = unicodedata.normalize("NFD", "café_亚投行制度与“一带一路”分析.md")
    (src_root / "papers" / "知网论文").mkdir(parents=True)
    (src_root / "papers" / "知网论文" / "“亚投行”研究报告.pdf").write_bytes(b"%PDF-1.4 fake pdf")
    (src_root / "papers" / "知网论文" / nfd_name).write_text("测试中文内容", encoding="utf-8")
    # 垃圾文件应自动跳过
    (src_root / "papers" / ".DS_Store").write_bytes(b"junk")
    (src_root / "papers" / "知网论文" / "._hidden.pdf").write_bytes(b"junk")
    # procurement 目录仅打包 .pdf，跳过已进 Git 的 .xlsx
    (src_root / "data" / "procurement" / "files").mkdir(parents=True)
    (src_root / "data" / "procurement" / "files" / "2025-report.pdf").write_bytes(b"%PDF-1.4 proc")
    (src_root / "data" / "procurement" / "files" / "List-of-Contract-Awards_2016-2025.xlsx").write_bytes(b"xlsx")

    archive = pack_bundle(src_root, out_dir, BUNDLE_SPECS["core"])
    assert archive.is_file()
    assert verify_archive(archive) is True

    # 验证所有非 ASCII 条目均设置了 UTF-8 标志位 (0x800) 且全部规范化为 NFC，无垃圾文件和 xlsx
    with zipfile.ZipFile(archive, "r") as zf:
        infos = zf.infolist()
        names = [zi.filename for zi in infos]
        non_ascii_infos = [zi for zi in infos if not zi.filename.isascii()]
        assert len(non_ascii_infos) == 2
        assert all(zi.flag_bits & 0x800 for zi in non_ascii_infos)
        assert all(name == unicodedata.normalize("NFC", name) for name in names)
        assert "papers/知网论文/“亚投行”研究报告.pdf" in names
        assert f"papers/知网论文/{unicodedata.normalize('NFC', nfd_name)}" in names
        assert "data/procurement/files/2025-report.pdf" in names
        assert not any(".DS_Store" in n or "._hidden" in n or n.endswith(".xlsx") for n in names)

    # 首次解压
    stats1 = unpack_archive(archive, dst_root)
    assert stats1["extracted"] == 3
    assert stats1["skipped"] == 0
    assert (dst_root / "papers" / "知网论文" / "“亚投行”研究报告.pdf").read_bytes() == b"%PDF-1.4 fake pdf"
    assert (
        dst_root / "papers" / "知网论文" / unicodedata.normalize("NFC", nfd_name)
    ).read_text(encoding="utf-8") == "测试中文内容"
    assert (dst_root / "data" / "procurement" / "files" / "2025-report.pdf").read_bytes() == b"%PDF-1.4 proc"

    # 幂等二次解压（默认跳过已存在且大小一致的文件）
    stats2 = unpack_archive(archive, dst_root)
    assert stats2["extracted"] == 0
    assert stats2["skipped"] == 3


def test_unpack_blocks_zip_slip(tmp_path: Path) -> None:
    malicious_zip = tmp_path / "evil.zip"
    dst_root = tmp_path / "safe_root"
    dst_root.mkdir()

    with zipfile.ZipFile(malicious_zip, "w") as zf:
        zf.writestr("../escaped.txt", "boom")

    with pytest.raises(ValueError, match="非法路径穿越"):
        unpack_archive(malicious_zip, dst_root)


def test_decode_legacy_gbk_member_name() -> None:
    """即使遇到旧版 Windows 未设 0x800 标志位、以 GBK 写入的压缩包条目，也能正确还原中文文件名。"""
    chinese_name = "papers/测试中文路径.txt"
    gbk_as_cp437 = chinese_name.encode("gbk").decode("cp437")
    zinfo = zipfile.ZipInfo(filename=gbk_as_cp437)
    zinfo.flag_bits = 0  # 模拟旧版 Windows 未设 UTF-8 标志位
    assert decode_member_name(zinfo) == chinese_name


def test_pack_custom_spec_missing_dir_raises_when_empty(tmp_path: Path) -> None:
    empty_spec = BundleSpec(
        key="empty",
        archive_name="empty.zip",
        description="empty",
        include_paths=(("does_not_exist", None),),
    )
    with pytest.raises(RuntimeError, match="未找到任何可打包文件"):
        pack_bundle(tmp_path, tmp_path / "out", empty_spec)

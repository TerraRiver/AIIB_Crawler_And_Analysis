"""一键打包与解压缩跨平台协作数据包（支持 macOS / Windows 无乱码查看与解压）。

设计要点：
1. 仅使用 Python 标准库，无需额外安装第三方包即可运行（同学克隆后可直接用 python3 / python 解压）。
2. 所有归档条目路径统一规范为 Unicode NFC + POSIX 斜杠，并显式写入 ZIP UTF-8 标志位 (flag_bits |= 0x800)，
   确保 macOS Finder、Windows 10/11 资源管理器、7-Zip、WinRAR 等图形工具与命令行查看/解压中文文件名均不乱码。
3. 自动过滤 .DS_Store、Thumbs.db、._* 等系统垃圾文件，开启 ZIP64 支持 2GB+ 大包。
4. 对已压缩二进制格式（PDF/DOCX/PNG/JPG 等）采用 STORE 直存、对文本格式（MD/EBT/JSON 等）采用 DEFLATE 压缩，
   兼顾极速打包与高兼容性。
5. 元数据写入 ZIP 文件注释区（archive comment），不向项目根目录额外写入多余文件，支持直接双击解压至项目根目录。

常用命令：
  # 一键打包全部（核心资料包 + 印度项目 PDF 扩展包）至 dist_bundles/
  uv run python scripts/bundle_data.py pack

  # 仅打核心资料包（~229 MB）或仅打项目附件包（~2.0 GB）
  uv run python scripts/bundle_data.py pack --only core
  uv run python scripts/bundle_data.py pack --only projects

  # 一键解压 dist_bundles/（或指定 zip 文件）到项目根目录
  python scripts/bundle_data.py unpack
  python scripts/bundle_data.py unpack dist_bundles/aiib_core_materials.zip

  # 校验压缩包完整性与 UTF-8 跨平台兼容性
  python scripts/bundle_data.py verify dist_bundles/aiib_core_materials.zip
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUT_DIR = ROOT_DIR / "dist_bundles"

# 已高度压缩的扩展名直接 STORE，避免无意义耗时压缩且保持 100% 标准 ZIP 兼容
PRECOMPRESSED_SUFFIXES = frozenset(
    {
        ".pdf",
        ".docx",
        ".xlsx",
        ".pptx",
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".gif",
        ".zip",
        ".gz",
        ".7z",
        ".rar",
        ".mp4",
        ".mp3",
    }
)

IGNORED_FILENAMES = frozenset({".DS_Store", "Thumbs.db", "desktop.ini"})
WINDOWS_INVALID_CHARS = re.compile(r'[<>:"|?*\x00-\x1f]')


@dataclass(frozen=True)
class BundleSpec:
    key: str
    archive_name: str
    description: str
    include_paths: tuple[tuple[str, tuple[str, ...] | None], ...]
    # 每项为 (相对路径, 允许的后缀元组或 None 表示全部)


BUNDLE_SPECS: dict[str, BundleSpec] = {
    "core": BundleSpec(
        key="core",
        archive_name="aiib_core_materials.zip",
        description="核心资料包（知网论文 + 57篇智库媒体 + 亚投行38份制度PDF/MD + 治理纪要 + 采购年报 + 问责PDF）",
        include_paths=(
            ("papers", None),
            ("data/institutions/pdfs", None),
            ("data/institutions/markdown", None),
            ("data/governance/pdfs", None),
            ("data/procurement/files", (".pdf",)),
            ("data/accountability/pdfs", None),
            ("data/cnki_selected_export.ebt", None),
        ),
    ),
    "projects": BundleSpec(
        key="projects",
        archive_name="aiib_india_project_pdfs.zip",
        description="印度项目全量 PDF 附件扩展包（740 份 PSI/PD/PIMR/环评/贷款协议）",
        include_paths=(("data/projects/pdfs", None),),
    ),
}


def format_size(num_bytes: int) -> str:
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024.0 or unit == "TB":
            return f"{value:.2f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024.0
    return f"{num_bytes} B"


def is_junk_path(path: Path) -> bool:
    return any(part in IGNORED_FILENAMES or part == "__MACOSX" or part.startswith("._") for part in path.parts)


def validate_windows_compat(rel_posix: str) -> str | None:
    parts = rel_posix.split("/")
    for part in parts:
        if WINDOWS_INVALID_CHARS.search(part):
            return f"包含 Windows 非法字符: {rel_posix}"
        if part.endswith(" ") or part.endswith("."):
            return f"目录或文件名以空格/句点结尾（Windows 不支持）: {rel_posix}"
    return None


def collect_bundle_files(root: Path, spec: BundleSpec) -> list[tuple[Path, str]]:
    """收集目标分包的全部文件，返回 (本地绝对路径, NFC 规范化的 POSIX 相对路径) 列表。"""
    collected: list[tuple[Path, str]] = []
    seen_arcnames: set[str] = set()

    for rel_str, allowed_suffixes in spec.include_paths:
        target = root / rel_str
        if not target.exists():
            print(f"[!] 提示：路径不存在，已跳过: {rel_str}")
            continue

        candidates = [target] if target.is_file() else sorted(p for p in target.rglob("*") if p.is_file())
        for file_path in candidates:
            rel_path = file_path.relative_to(root)
            if is_junk_path(rel_path):
                continue
            if allowed_suffixes is not None and file_path.suffix.lower() not in allowed_suffixes:
                continue

            arcname = unicodedata.normalize("NFC", rel_path.as_posix())
            if arcname in seen_arcnames:
                continue
            seen_arcnames.add(arcname)
            collected.append((file_path, arcname))

    collected.sort(key=lambda item: item[1])
    return collected


def build_zip_info(file_path: Path, arcname: str) -> tuple[zipfile.ZipInfo, int]:
    """构造显式启用 UTF-8 标志位 (0x800) 且跨平台兼容的 ZipInfo。"""
    st = file_path.stat()
    mtime = time.localtime(st.st_mtime)
    # ZIP 格式支持的最早年份为 1980
    date_time = (
        max(mtime.tm_year, 1980),
        mtime.tm_mon,
        mtime.tm_mday,
        mtime.tm_hour,
        mtime.tm_min,
        mtime.tm_sec,
    )
    zinfo = zipfile.ZipInfo(filename=arcname, date_time=date_time)
    # 显式标记 UTF-8 文件名（General Purpose Bit Flag bit 11），防止 Windows / macOS 中文乱码
    zinfo.flag_bits |= 0x800
    zinfo.create_system = 3  # Unix 兼容属性，同时保留普通文件权限
    zinfo.external_attr = (0o100644 & 0xFFFF) << 16

    compress_type = (
        zipfile.ZIP_STORED if file_path.suffix.lower() in PRECOMPRESSED_SUFFIXES else zipfile.ZIP_DEFLATED
    )
    zinfo.compress_type = compress_type
    return zinfo, compress_type


def pack_bundle(
    root: Path,
    out_dir: Path,
    spec: BundleSpec,
    *,
    force_deflate: bool = False,
) -> Path:
    """将指定分包打包为跨平台 UTF-8 ZIP 归档。"""
    files = collect_bundle_files(root, spec)
    if not files:
        raise RuntimeError(f"分包 '{spec.key}' 未找到任何可打包文件！")

    warnings = [msg for _, arc in files if (msg := validate_windows_compat(arc))]
    if warnings:
        print(f"[!] 检测到 {len(warnings)} 个潜在 Windows 文件名兼容性问题：")
        for w in warnings[:10]:
            print(f"    - {w}")

    out_dir.mkdir(parents=True, exist_ok=True)
    archive_path = out_dir / spec.archive_name
    tmp_path = archive_path.with_suffix(".zip.part")

    total_raw_bytes = sum(p.stat().st_size for p, _ in files)
    print(f"\n[*] 开始打包 [{spec.key}] -> {archive_path}")
    print(f"    说明: {spec.description}")
    print(f"    文件数: {len(files)} 个 | 原始总大小: {format_size(total_raw_bytes)}")

    start_ts = time.monotonic()
    written_bytes = 0
    last_print_ts = start_ts

    try:
        with zipfile.ZipFile(
            tmp_path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            allowZip64=True,
            compresslevel=6,
        ) as zf:
            for idx, (file_path, arcname) in enumerate(files, start=1):
                zinfo, compress_type = build_zip_info(file_path, arcname)
                if force_deflate:
                    compress_type = zipfile.ZIP_DEFLATED
                    zinfo.compress_type = compress_type

                # 使用流式分块写入，避免大文件一次性占满内存
                with file_path.open("rb") as src, zf.open(zinfo, "w", force_zip64=True) as dst:
                    while chunk := src.read(1024 * 1024):
                        dst.write(chunk)
                        written_bytes += len(chunk)

                now = time.monotonic()
                if idx == len(files) or now - last_print_ts >= 1.5:
                    pct = (written_bytes / total_raw_bytes * 100.0) if total_raw_bytes else 100.0
                    print(
                        f"    进度: {idx}/{len(files)} ({pct:5.1f}%) | "
                        f"{format_size(written_bytes)} / {format_size(total_raw_bytes)}",
                        flush=True,
                    )
                    last_print_ts = now

            metadata: dict[str, Any] = {
                "bundle_key": spec.key,
                "description": spec.description,
                "created_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "file_count": len(files),
                "total_raw_bytes": total_raw_bytes,
                "encoding": "UTF-8 (NFC, ZIP flag 0x800)",
            }
            zf.comment = json.dumps(metadata, ensure_ascii=False).encode("utf-8")

        tmp_path.replace(archive_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise

    elapsed = time.monotonic() - start_ts
    final_size = archive_path.stat().st_size
    print(
        f"[+] 打包完成: {archive_path.name} | 体积: {format_size(final_size)} | "
        f"耗时: {elapsed:.1f}s"
    )
    return archive_path


def decode_member_name(zinfo: zipfile.ZipInfo) -> str:
    """稳健解码归档文件名：优先信任 UTF-8 标志位，同时兼容旧版 Windows GBK 打包文件。"""
    raw_name = zinfo.filename
    if zinfo.flag_bits & 0x800:
        return unicodedata.normalize("NFC", raw_name)
    try:
        raw_bytes = raw_name.encode("cp437")
        for enc in ("utf-8", "gb18030", "gbk"):
            try:
                return unicodedata.normalize("NFC", raw_bytes.decode(enc))
            except UnicodeDecodeError:
                continue
    except UnicodeEncodeError:
        pass
    return unicodedata.normalize("NFC", raw_name)


def to_fs_path(path: Path) -> Path:
    """在 Windows 上当路径接近 MAX_PATH (260) 时自动启用 \\\\?\\ 长路径前缀。"""
    if os.name == "nt":
        abs_str = str(path.resolve())
        if len(abs_str) >= 240 and not abs_str.startswith("\\\\?\\"):
            if abs_str.startswith("\\\\"):
                return Path("\\\\?\\UNC\\" + abs_str.lstrip("\\"))
            return Path("\\\\?\\" + abs_str)
    return path


def safe_resolve_target(root: Path, member_name: str) -> Path:
    """防止 Zip Slip 路径穿越攻击，确保所有解压路径严格落在项目根目录内。"""
    normalized = member_name.replace("\\", "/").lstrip("/")
    if not normalized or normalized.endswith("/"):
        raise ValueError(f"非文件条目: {member_name}")
    parts = [p for p in normalized.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise ValueError(f"检测到非法路径穿越条目，已拒绝解压: {member_name}")

    root_resolved = root.resolve()
    dest = (root_resolved / Path(*parts)).resolve()
    try:
        dest.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"解压目标超出根目录边界: {member_name}") from exc
    return dest


def unpack_archive(
    archive_path: Path,
    target_root: Path,
    *,
    overwrite: bool = False,
) -> dict[str, int]:
    """将跨平台 ZIP 归档安全解压至目标项目根目录。"""
    if not archive_path.is_file():
        raise FileNotFoundError(f"找不到压缩包: {archive_path}")

    print(f"\n[*] 开始解压: {archive_path} -> {target_root}")
    extracted = 0
    skipped = 0
    junk_skipped = 0
    bytes_written = 0

    with zipfile.ZipFile(archive_path, mode="r") as zf:
        if zf.comment:
            try:
                meta = json.loads(zf.comment.decode("utf-8"))
                print(
                    f"    包信息: [{meta.get('bundle_key', '?')}] "
                    f"{meta.get('file_count', '?')} 个文件 | "
                    f"打包时间: {meta.get('created_at_utc', '?')}"
                )
            except Exception:
                pass

        members = [zi for zi in zf.infolist() if not zi.is_dir()]
        total = len(members)
        last_print_ts = time.monotonic()

        for idx, zinfo in enumerate(members, start=1):
            member_name = decode_member_name(zinfo)
            rel_path = Path(*[p for p in member_name.replace("\\", "/").split("/") if p not in ("", ".")])
            if is_junk_path(rel_path):
                junk_skipped += 1
                continue

            dest = safe_resolve_target(target_root, member_name)
            dest_fs = to_fs_path(dest)

            if dest_fs.exists() and not overwrite and dest_fs.stat().st_size == zinfo.file_size:
                skipped += 1
            else:
                dest_fs.parent.mkdir(parents=True, exist_ok=True)
                tmp_fs = to_fs_path(dest.with_name(dest.name + ".unpack.tmp"))
                with zf.open(zinfo, "r") as src, tmp_fs.open("wb") as dst:
                    while chunk := src.read(1024 * 1024):
                        dst.write(chunk)
                        bytes_written += len(chunk)
                tmp_fs.replace(dest_fs)

                # 还原修改时间
                try:
                    ts = time.mktime((*zinfo.date_time, 0, 0, -1))
                    os.utime(dest_fs, (ts, ts))
                except Exception:
                    pass
                extracted += 1

            now = time.monotonic()
            if idx == total or now - last_print_ts >= 1.5:
                print(
                    f"    进度: {idx}/{total} | 新解压: {extracted} | 已存在跳过: {skipped}",
                    flush=True,
                )
                last_print_ts = now

    print(
        f"[+] 解压完成: {archive_path.name} | 新写入 {extracted} 个文件 ({format_size(bytes_written)})，"
        f"跳过已存在 {skipped} 个，过滤垃圾文件 {junk_skipped} 个"
    )
    return {"extracted": extracted, "skipped": skipped, "junk_skipped": junk_skipped}


def verify_archive(archive_path: Path) -> bool:
    """检查 ZIP 完整性（CRC 校验）、UTF-8 标志位与 Windows 路径兼容性。"""
    if not archive_path.is_file():
        print(f"[-] 文件不存在: {archive_path}")
        return False

    print(f"\n[*] 正在校验压缩包: {archive_path} ({format_size(archive_path.stat().st_size)})")
    with zipfile.ZipFile(archive_path, mode="r") as zf:
        bad_file = zf.testzip()
        if bad_file is not None:
            print(f"[-] CRC 校验失败，损坏条目: {bad_file}")
            return False

        infos = [zi for zi in zf.infolist() if not zi.is_dir()]
        non_ascii_infos = [zi for zi in infos if not zi.filename.isascii()]
        non_utf8 = [zi.filename for zi in non_ascii_infos if not (zi.flag_bits & 0x800)]
        win_issues = [msg for zi in infos if (msg := validate_windows_compat(decode_member_name(zi)))]
        nfd_issues = [
            zi.filename for zi in infos if zi.filename != unicodedata.normalize("NFC", zi.filename)
        ]

        if zf.comment:
            try:
                meta = json.loads(zf.comment.decode("utf-8"))
                print(f"    元数据: {json.dumps(meta, ensure_ascii=False)}")
            except Exception:
                pass

        print(f"    总文件数: {len(infos)}（其中含非 ASCII/中文路径 {len(non_ascii_infos)} 个）")
        print("    CRC 完整性校验: 通过")
        print(
            f"    非 ASCII 条目 UTF-8 标志位 (0x800) 覆盖率: "
            f"{len(non_ascii_infos) - len(non_utf8)}/{len(non_ascii_infos)}"
        )
        print(f"    Unicode NFC 规范检查: {'通过' if not nfd_issues else f'发现 {len(nfd_issues)} 个 NFD 条目'}")
        print(
            f"    Windows 文件名兼容性: {'通过' if not win_issues else f'发现 {len(win_issues)} 个问题'}"
        )
        return not non_utf8 and not win_issues and not nfd_issues


def resolve_archives_for_unpack(paths: list[Path], out_dir: Path) -> list[Path]:
    if not paths:
        candidates = sorted(out_dir.glob("aiib_*.zip")) if out_dir.is_dir() else []
        if not candidates:
            candidates = sorted(ROOT_DIR.glob("aiib_*.zip"))
        return candidates

    resolved: list[Path] = []
    for p in paths:
        if p.is_dir():
            resolved.extend(sorted(p.glob("*.zip")))
        else:
            resolved.append(p)
    return resolved


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AIIB 协作数据包一键打包 / 解压 / 校验工具（macOS & Windows 中文无乱码）"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_pack = sub.add_parser("pack", help="打包本地被 Git 忽略的数据与文献文件")
    p_pack.add_argument(
        "--only",
        choices=("all", "core", "projects"),
        default="all",
        help="选择打包范围: all (默认，打两个包) | core (核心资料包 ~229MB) | projects (印度项目PDF包 ~2GB)",
    )
    p_pack.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"压缩包输出目录（默认: {DEFAULT_OUT_DIR.relative_to(ROOT_DIR)}）",
    )
    p_pack.add_argument(
        "--force-deflate",
        action="store_true",
        help="对 PDF/图片也强制启用 DEFLATE 压缩（耗时更长、体积几乎无明显缩小）",
    )

    p_unpack = sub.add_parser("unpack", help="一键解压压缩包到项目根目录")
    p_unpack.add_argument(
        "archives",
        nargs="*",
        type=Path,
        help="要解压的 .zip 文件或目录路径（留空则自动扫描 dist_bundles/ 下的 aiib_*.zip）",
    )
    p_unpack.add_argument(
        "--target-dir",
        type=Path,
        default=ROOT_DIR,
        help="解压目标根目录（默认为当前项目根目录）",
    )
    p_unpack.add_argument(
        "--overwrite",
        action="store_true",
        help="覆盖本地已存在的同名文件（默认跳过大小相同的已有文件）",
    )

    p_verify = sub.add_parser("verify", help="校验压缩包完整性与 macOS/Windows 文件名兼容性")
    p_verify.add_argument(
        "archives",
        nargs="*",
        type=Path,
        help="要校验的 .zip 文件路径（留空则自动扫描 dist_bundles/ 下的 aiib_*.zip）",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "pack":
        keys = ("core", "projects") if args.only == "all" else (args.only,)
        out_dir = args.out_dir if args.out_dir.is_absolute() else (ROOT_DIR / args.out_dir)
        for key in keys:
            pack_bundle(ROOT_DIR, out_dir, BUNDLE_SPECS[key], force_deflate=args.force_deflate)
        print(f"\n[✓] 全部打包任务完成，输出目录: {out_dir}")
        return 0

    if args.command == "unpack":
        archives = resolve_archives_for_unpack(args.archives, DEFAULT_OUT_DIR)
        if not archives:
            print(
                "[-] 未找到任何可解压的 .zip 文件。请把压缩包放入 dist_bundles/ 或在命令后指定路径。",
                file=sys.stderr,
            )
            return 1
        target_root = args.target_dir.resolve()
        for arc in archives:
            unpack_archive(arc, target_root, overwrite=args.overwrite)
        print("\n[✓] 全部解压完成！")
        return 0

    if args.command == "verify":
        archives = resolve_archives_for_unpack(args.archives, DEFAULT_OUT_DIR)
        if not archives:
            print("[-] 未找到可校验的 .zip 文件。", file=sys.stderr)
            return 1
        ok = all(verify_archive(arc) for arc in archives)
        return 0 if ok else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

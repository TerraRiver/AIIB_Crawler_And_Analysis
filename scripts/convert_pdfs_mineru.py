"""调用 MinerU 官方云端 v4 批量 API，将 data/institutions/pdfs/ 下的 PDF 批量解析转换为高质量 Markdown (.md)。

使用方式:
  1. 在项目根目录 .env 文件中填入 MINERU_API_TOKEN=eyJ...
  2. 运行:
     uv run python -m scripts.convert_pdfs_mineru
"""

from __future__ import annotations

import argparse
import io
import logging
import os
import re
import time
import zipfile
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

MINERU_BATCH_URLS_API = "https://mineru.net/api/v4/file-urls/batch"
MINERU_BATCH_RESULTS_API = "https://mineru.net/api/v4/extract-results/batch/{batch_id}"


def load_mineru_token() -> str:
    """从 .env 或环境变量加载 MINERU_API_TOKEN，并自动清理多余前缀或引号。"""
    load_dotenv(override=True)
    raw = os.getenv("MINERU_API_TOKEN", "").strip().strip("'").strip('"')
    if raw.lower().startswith("bearer "):
        raw = raw[7:].strip()
    if not raw:
        raise RuntimeError(
            "未检测到 MINERU_API_TOKEN！请在项目根目录的 .env 文件第 2 行填入您的 MinerU API Token。"
        )
    return raw


def save_mineru_zip_to_markdown(
    zip_bytes: bytes,
    pdf_stem: str,
    md_out_dir: Path,
    raw_out_dir: Path,
    title_header: str = "",
) -> Path:
    """解压 MinerU 返回的结果 zip 包，提取 .md 与 images/ 并写入目标目录。"""
    md_out_dir.mkdir(parents=True, exist_ok=True)
    doc_raw_dir = raw_out_dir / pdf_stem
    doc_raw_dir.mkdir(parents=True, exist_ok=True)

    doc_images_dir = md_out_dir / "images" / pdf_stem
    md_content = ""

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        zf.extractall(doc_raw_dir)
        for member in zf.namelist():
            if member.endswith("/"):
                continue
            member_path = Path(member)
            if member_path.suffix.lower() == ".md" and not md_content:
                md_content = zf.read(member).decode("utf-8", errors="replace")
            elif "images/" in member or member_path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                doc_images_dir.mkdir(parents=True, exist_ok=True)
                img_dest = doc_images_dir / member_path.name
                img_dest.write_bytes(zf.read(member))

    if not md_content:
        raise RuntimeError(f"MinerU 压缩包中未找到 .md 文件: {pdf_stem}")

    # 将 Markdown 中的默认图片路径 ![](images/xxx.jpg) 重写为 ![](images/<pdf_stem>/xxx.jpg)
    md_content = re.sub(
        r"(!\[[^\]]*\]\()(?:\./)?images/([^)]+\))",
        rf"\1images/{pdf_stem}/\2",
        md_content,
    )

    if title_header and not md_content.lstrip().startswith("# "):
        md_content = f"# {title_header}\n\n{md_content}"

    target_md = md_out_dir / f"{pdf_stem}.md"
    tmp_md = target_md.with_suffix(".md.tmp")
    tmp_md.write_text(md_content, encoding="utf-8")
    tmp_md.replace(target_md)
    return target_md


def process_batch(
    api_client: httpx.Client,
    oss_client: httpx.Client,
    pdf_files: list[Path],
    md_out_dir: Path,
    raw_out_dir: Path,
    title_map: dict[str, str],
    model_version: str = "vlm",
) -> None:
    """对一组本地 PDF 执行：申请上传链接 -> PUT 上传 -> 轮询解析进度 -> 下载解压保存 .md。"""
    files_payload = []
    for p in pdf_files:
        is_cn = "_CN" in p.stem or p.stem.startswith("01_") or p.stem.startswith("29_")
        files_payload.append(
            {
                "name": p.name,
                "is_ocr": False,
                "data_id": p.stem[:64],
                "language": "ch" if is_cn else "en",
            }
        )

    req_body: dict[str, Any] = {
        "enable_formula": True,
        "enable_table": True,
        "model_version": model_version,
        "files": files_payload,
    }

    logger.info("[*] 正在向 MinerU 申请 %d 个 PDF 文件的批量上传链接...", len(pdf_files))
    resp = api_client.post(MINERU_BATCH_URLS_API, json=req_body)
    resp.raise_for_status()
    resp_json = resp.json()
    if resp_json.get("code") != 0:
        raise RuntimeError(f"MinerU 申请上传链接失败: {resp_json}")

    batch_id = resp_json["data"]["batch_id"]
    file_urls: list[str] = resp_json["data"]["file_urls"]
    logger.info("[+] 已获取 Batch ID: %s，开始上传本地 PDF 文件...", batch_id)

    # 注意：向阿里云 OSS 预签名 URL 执行 PUT 上传时不能附带额外的 Authorization 或 Content-Type 头
    for idx, pdf_path in enumerate(pdf_files):
        upload_url = file_urls[idx]
        size_kb = pdf_path.stat().st_size / 1024.0
        logger.info("  -> 正在上传 (%d/%d) %s (%.1f KB)...", idx + 1, len(pdf_files), pdf_path.name, size_kb)
        pdf_bytes = pdf_path.read_bytes()
        put_resp = oss_client.put(upload_url, content=pdf_bytes)
        if put_resp.status_code not in (200, 201):
            raise RuntimeError(
                f"上传文件 {pdf_path.name} 至 OSS 失败 (HTTP {put_resp.status_code}): {put_resp.text[:300]}"
            )

    logger.info("[+] 批次 %s 全部文件上传完毕，系统已自动触发云端解析，开始轮询进度...", batch_id)
    completed_stems: set[str] = set()
    failed_stems: set[str] = set()
    stem_by_name = {p.name: p.stem for p in pdf_files}

    poll_url = MINERU_BATCH_RESULTS_API.format(batch_id=batch_id)
    while len(completed_stems) + len(failed_stems) < len(pdf_files):
        time.sleep(5.0)
        poll_resp = api_client.get(poll_url)
        poll_resp.raise_for_status()
        poll_data = poll_resp.json()
        if poll_data.get("code") != 0:
            logger.warning("[!] 轮询返回非 0 状态: %s", poll_data)
            continue

        extract_list: list[dict[str, Any]] = poll_data.get("data", {}).get("extract_result", [])
        status_counts: dict[str, int] = {}

        for item in extract_list:
            fname = item.get("file_name", "")
            stem = item.get("data_id") or stem_by_name.get(fname, Path(fname).stem)
            state = item.get("state", "unknown")
            status_counts[state] = status_counts.get(state, 0) + 1

            if stem in completed_stems or stem in failed_stems:
                continue

            if state == "done":
                zip_url = item.get("full_zip_url", "")
                if not zip_url:
                    continue
                logger.info("[*] [%s] 云端解析完成，正在下载结果压缩包...", stem)
                zip_resp = oss_client.get(zip_url)
                zip_resp.raise_for_status()
                md_path = save_mineru_zip_to_markdown(
                    zip_resp.content,
                    pdf_stem=stem,
                    md_out_dir=md_out_dir,
                    raw_out_dir=raw_out_dir,
                    title_header=title_map.get(stem, ""),
                )
                completed_stems.add(stem)
                logger.info(
                    "[+] [%d/%d] 已生成 Markdown: %s",
                    len(completed_stems),
                    len(pdf_files),
                    md_path,
                )
            elif state == "failed":
                err_msg = item.get("err_msg", "未知错误")
                failed_stems.add(stem)
                logger.error("[-] [%s] 解析失败: %s", stem, err_msg)

        if len(completed_stems) + len(failed_stems) < len(pdf_files):
            logger.info(
                "    ... 批次 [%s] 进度: 已完成 %d/%d | 状态分布: %s",
                batch_id[:10],
                len(completed_stems),
                len(pdf_files),
                status_counts,
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="使用 MinerU 官方 API 将制度 PDF 批量转换为 Markdown")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/institutions/pdfs"),
        help="输入 PDF 目录 (默认: data/institutions/pdfs)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/institutions/markdown"),
        help="输出 Markdown 目录 (默认: data/institutions/markdown)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=15,
        help="每批上传的 PDF 数量 (默认: 15)",
    )
    parser.add_argument(
        "--model-version",
        type=str,
        default="vlm",
        choices=["vlm", "pipeline"],
        help="MinerU 解析模型版本 (默认: vlm)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新转换已存在的 .md 文件",
    )
    args = parser.parse_args()

    token = load_mineru_token()
    pdf_all = sorted(args.input_dir.glob("*.pdf"))
    if not pdf_all:
        raise RuntimeError(f"在 {args.input_dir} 下未找到任何 PDF 文件！")

    # 加载标题映射（若存在 institutions_index.json）
    title_map: dict[str, str] = {}
    index_path = args.input_dir.parent / "institutions_index.json"
    if index_path.exists():
        import json

        for rec in json.loads(index_path.read_text(encoding="utf-8")):
            stem = Path(rec["filename"]).stem
            title_map[stem] = f"{rec.get('title_cn', '')} ({rec.get('title_en', '')})"

    pending_pdfs: list[Path] = []
    for p in pdf_all:
        target_md = args.output_dir / f"{p.stem}.md"
        if not args.force and target_md.exists() and target_md.stat().st_size > 0:
            logger.info("[*] 跳过已转换文件: %s", target_md.name)
        else:
            pending_pdfs.append(p)

    if not pending_pdfs:
        logger.info("[+] 全部 %d 份 PDF 均已转换为 Markdown，无需重复处理！输出目录: %s", len(pdf_all), args.output_dir)
        return

    logger.info(
        "[*] 待转换 PDF 共 %d 份（总计 %d 份），每批 %d 份，输出目录: %s",
        len(pending_pdfs),
        len(pdf_all),
        args.batch_size,
        args.output_dir,
    )

    raw_out_dir = args.input_dir.parent / "mineru_raw"
    api_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    with (
        httpx.Client(headers=api_headers, follow_redirects=True, timeout=60.0) as api_client,
        httpx.Client(follow_redirects=True, timeout=180.0) as oss_client,
    ):
        for start in range(0, len(pending_pdfs), args.batch_size):
            batch_files = pending_pdfs[start : start + args.batch_size]
            logger.info(
                "=== 开始处理第 %d/%d 批 (文件 %d ~ %d) ===",
                start // args.batch_size + 1,
                (len(pending_pdfs) + args.batch_size - 1) // args.batch_size,
                start + 1,
                start + len(batch_files),
            )
            process_batch(
                api_client=api_client,
                oss_client=oss_client,
                pdf_files=batch_files,
                md_out_dir=args.output_dir,
                raw_out_dir=raw_out_dir,
                title_map=title_map,
                model_version=args.model_version,
            )

    logger.info("[+] 全部 %d 份 PDF 已成功转换为 Markdown！保存在: %s", len(pending_pdfs), args.output_dir)


if __name__ == "__main__":
    main()

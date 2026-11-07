"""四个核心数据模块 (projects, procurement, governance, accountability) 的采集与附件下载实现。"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import httpx
from pypdf import PdfReader

from aiib_crawler.config import Config
from aiib_crawler.parser import (
    parse_ceiu_evaluation_html,
    parse_debarment_list_js,
    parse_directors_json,
    parse_governors_annual_meetings_html,
    parse_governors_json,
    parse_governors_resolutions_js,
    parse_meeting_minutes_html,
    parse_ppm_html_tables,
    parse_ppm_submissions_js,
    parse_ppo_data_js,
    parse_procurement_overview_html,
    parse_project_detail_html,
    parse_projects_js,
    parse_voting_power_js,
)
from aiib_crawler.stealth import RequestPacer, compute_backoff_wait
from aiib_crawler.storage import CheckpointState, Storage

logger = logging.getLogger(__name__)

_PACER = RequestPacer(base_min=0.2, base_max=0.6, burst_size=15, burst_pause=(1.5, 3.0))

DEFAULT_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

ENDPOINTS = {
    "projects_js": "https://www.aiib.org/en/projects/list/.content/all-projects-data.js",
    "procurement_overview": "https://www.aiib.org/en/opportunities/business/project-procurement/index.html",
    "ppo_data_all_js": "https://www.aiib.org/en/opportunities/business/project-procurement/_common/ppo-data-all.js",
    "voting_power_js": "https://www.aiib.org/en/about-aiib/governance/members-of-bank/.content/voting-power.js",
    "governors_json": "https://www.aiib.org/en/about-aiib/governance/board-governors/.content/index/governors.json",
    "governors_res_js": "https://www.aiib.org/en/about-aiib/governance/board-governors/.content/index/resData.js",
    "governors_index_html": "https://www.aiib.org/en/about-aiib/governance/board-governors/index.html",
    "directors_json": "https://www.aiib.org/en/about-aiib/governance/board-directors/board-members/.content/all-directors.json",
    "meeting_minutes_html": "https://www.aiib.org/en/about-aiib/governance/board-directors/meeting-minutes/index.html",
    "ppm_main_js": "https://www.aiib.org/en/about-aiib/who-we-are/project-affected-peoples-mechanism/submission/_common/main.js",
    "ppm_track_html": "https://www.aiib.org/en/about-aiib/who-we-are/project-affected-peoples-mechanism/submission/track-all-submission.html",
    "ceiu_eval_html": "https://www.aiib.org/en/about-aiib/who-we-are/complaints-resolution-evaluation-integrity-unit/evaluation/index.html",
    "debarment_js": "https://www.aiib.org/en/about-aiib/who-we-are/debarment-list/_common/js/debarment-list.js",
}


def sanitize_filename(name: str) -> str:
    """将文件名中的非法字符替换为安全下划线。"""
    cleaned = re.sub(r"[^\w.\-]+", "_", name.strip())
    return cleaned[:160] or "document"


def fetch_text_with_retry(client: httpx.Client, url: str, *, retries: int = 3, referer: str | None = None) -> str:
    """带指数退避重试与上下文 Referer 头的文本/HTML/JS 请求函数。"""
    import time

    last_err: Exception | None = None
    headers = _PACER.build_headers(referer)
    for attempt in range(1, retries + 1):
        try:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            _PACER.last_url = url
            return resp.text
        except Exception as e:
            last_err = e
            wait_sec = compute_backoff_wait(attempt)
            logger.warning("[!] 请求失败 (%d/%d) %s: %s，等待 %.1fs 后重试", attempt, retries, url, e, wait_sec)
            time.sleep(wait_sec)
    raise RuntimeError(f"无法获取 {url}: {last_err}") from last_err


def download_binary_file(
    client: httpx.Client,
    url: str,
    dest_path: Path,
    state: CheckpointState,
    storage: Storage,
    *,
    referer: str | None = None,
) -> bool:
    """下载 PDF / Excel 二进制附件（支持断点跳过、上下文 Referer、批次节流与原子落盘）。"""
    if not url:
        return False
    file_seen_key = f"file:{url}"
    if file_seen_key in state.seen_ids and dest_path.exists() and dest_path.stat().st_size > 0:
        logger.debug("跳过已下载附件: %s", dest_path.name)
        return True

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest_path.with_suffix(dest_path.suffix + ".part")
    headers = _PACER.build_headers(referer)
    try:
        with client.stream("GET", url, headers=headers) as resp:
            resp.raise_for_status()
            with tmp_path.open("wb") as f:
                for chunk in resp.iter_bytes(chunk_size=65536):
                    f.write(chunk)
        tmp_path.replace(dest_path)
        state.seen_ids.add(file_seen_key)
        storage.save_state(state)
        logger.info("[+] 已下载附件: %s", dest_path.relative_to(storage.data_dir))
        _PACER.wait(reason=dest_path.name)
        return True
    except Exception as e:
        tmp_path.unlink(missing_ok=True)
        logger.warning("[!] 下载附件失败 %s: %s", url, e)
        return False


def _filter_by_year(year: int | None, config: Config) -> bool:
    """根据配置的 since / until 年份边界过滤记录。"""
    if year is None:
        return True
    if config.since and year < config.since.year:
        return False
    return not (config.until and year > config.until.year)


def extract_india_mentions_from_pdf(pdf_path: Path) -> list[dict[str, Any]]:
    """从 PDF 文件（如理事会年会纪要或董事会纪要）中检索包含 'India' 的页面与段落摘录。"""
    if not pdf_path.exists():
        return []
    mentions: list[dict[str, Any]] = []
    try:
        reader = PdfReader(str(pdf_path))
        for page_idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if not re.search(r"\bIndia\b", text, re.I):
                continue
            snippets: list[str] = []
            for para in re.split(r"\n\s*\n", text):
                cleaned = re.sub(r"\s+", " ", para).strip()
                if re.search(r"\bIndia\b", cleaned, re.I):
                    snippets.append(cleaned[:600])
            mentions.append(
                {
                    "page": page_idx,
                    "snippets": snippets[:5],
                }
            )
    except Exception as e:
        logger.debug("解析 PDF 文本失败 %s: %s", pdf_path.name, e)
    return mentions


# ==============================================================================
# 模块 1: Projects 采集（常规项目主表与详情页）
# ==============================================================================


def collect_projects_tab(
    client: httpx.Client,
    config: Config,
    storage: Storage,
    state: CheckpointState,
) -> list[dict[str, Any]]:
    """抓取全行常规项目列表、各项目详情页以及印度项目核心 PDF 文件。"""
    logger.info("[*] 正在拉取 AIIB 全量常规项目列表数据源...")
    projects_js = fetch_text_with_retry(client, ENDPOINTS["projects_js"])
    all_projects = parse_projects_js(projects_js)
    all_projects = [p for p in all_projects if _filter_by_year(p.get("approval_year"), config)]

    india_projects = [p for p in all_projects if p.get("economy", "").lower() == "india"]

    storage.save_dataset("projects", "all_projects_summary", all_projects)
    storage.save_dataset("projects", "india_projects_summary", india_projects)
    logger.info(
        "[+] 常规项目主表解析完成: 全行项目 %d 个 (其中印度项目 %d 个)",
        len(all_projects),
        len(india_projects),
    )

    # 加载已持久化的项目详情列表并建立索引
    existing_details = storage.load_tab_records("projects")
    details_by_url: dict[str, dict[str, Any]] = {str(r.get("url")): r for r in existing_details if r.get("url")}

    # 决定需要抓取详情页的项目列表：若指定 --country India 则只抓印度详情页，否则优先抓印度项目详情页再抓其余成员国
    if config.country_filter.lower() == "india":
        target_projects = india_projects
    else:
        non_india_projects = [p for p in all_projects if p.get("economy", "").lower() != "india"]
        target_projects = india_projects + non_india_projects

    if config.max_detail_pages > 0:
        target_projects = target_projects[: config.max_detail_pages]

    total_targets = len(target_projects)
    newly_scraped = 0

    for idx, proj in enumerate(target_projects, start=1):
        detail_url = proj.get("detail_url", "")
        if not detail_url:
            continue

        if detail_url in state.seen_ids and detail_url in details_by_url:
            detail_record = details_by_url[detail_url]
        else:
            try:
                html = fetch_text_with_retry(client, detail_url)
                detail_record = parse_project_detail_html(html, url=detail_url)
                # 合并主表里的列表字段（如列表页的 approved_funding / project_type）
                detail_record["list_project_type"] = proj.get("project_type", "")
                detail_record["list_approval_year"] = proj.get("approval_year")
                detail_record["list_effective_funding_usd_millions"] = proj.get("effective_funding_usd_millions")

                # 先写增量日志，再更新内存与 state.json
                storage.append_journal("projects", detail_record)
                details_by_url[detail_url] = detail_record
                state.seen_ids.add(detail_url)
                newly_scraped += 1

                if newly_scraped % 10 == 0:
                    storage.save_tab_records("projects", list(details_by_url.values()))
                    storage.clear_journal()
                    storage.save_state(state)
                    logger.info(
                        "[*] 项目详情页抓取进度: %d/%d (本次新增 %d 条)",
                        idx,
                        total_targets,
                        newly_scraped,
                    )
                _PACER.wait(reason="项目详情页")
            except Exception as e:
                logger.warning("[!] 抓取项目详情页失败 (%d/%d) %s: %s", idx, total_targets, detail_url, e)
                continue

        # 按需下载项目的核心 PDF 文档（默认仅下载印度项目的 PSI / PD / PIMR / 贷款协议）
        economy_name = (detail_record.get("economy") or proj.get("economy") or "").strip()
        should_download_pdf = config.download_pdfs == "all" or (config.download_pdfs == "india" and economy_name.lower() == "india")
        if should_download_pdf:
            proj_num = detail_record.get("project_number") or f"proj_{idx:03d}"
            folder_name = sanitize_filename(f"{proj_num}_{economy_name}")
            pdf_dir = storage.tab_dir("projects") / "pdfs" / folder_name
            for doc in detail_record.get("documents", []):
                raw_doc_url = doc.get("url", "")
                doc_url = raw_doc_url.split("#", 1)[0].strip()
                if not doc_url or not doc_url.lower().endswith(".pdf"):
                    continue
                fname = sanitize_filename(doc_url.rsplit("/", 1)[-1])
                dest = pdf_dir / fname
                if download_binary_file(client, doc_url, dest, state, storage, referer=detail_url):
                    doc["local_path"] = str(dest.relative_to(storage.data_dir))

    all_detail_records = list(details_by_url.values())
    india_detail_records = [r for r in all_detail_records if str(r.get("economy") or "").lower() == "india"]
    storage.save_tab_records("projects", all_detail_records)
    storage.save_dataset("projects", "project_details_all", all_detail_records)
    storage.save_dataset("projects", "india_project_details", india_detail_records)
    storage.clear_journal()
    storage.save_state(state)

    logger.info(
        "[+] [projects] 模块完成: 累计详情页 %d 条 (其中印度项目详情 %d 条)",
        len(all_detail_records),
        len(india_detail_records),
    )
    return all_detail_records


# ==============================================================================
# 模块 2: Procurement & Contract Awards 采集
# ==============================================================================


def collect_procurement_tab(
    client: httpx.Client,
    config: Config,
    storage: Storage,
    state: CheckpointState,
) -> list[dict[str, Any]]:
    """抓取项目采购公告、采购计划、合同授予记录，并下载 2016-2025 全量中标合同 Excel 与年度采购报告 PDF。"""
    logger.info("[*] 正在拉取 AIIB 项目采购与合同授予全量数据...")
    overview_html = fetch_text_with_retry(client, ENDPOINTS["procurement_overview"])
    overview_info = parse_procurement_overview_html(overview_html)

    ppo_js = fetch_text_with_retry(client, ENDPOINTS["ppo_data_all_js"])
    ppo_records = parse_ppo_data_js(ppo_js)
    ppo_records = [r for r in ppo_records if _filter_by_year(r.get("published_year"), config)]

    india_ppo = [r for r in ppo_records if r.get("economy", "").lower() == "india" or "india" in r.get("contractor", "").lower()]
    contract_awards = [r for r in ppo_records if r.get("category") == "Contract Awards"]
    india_contract_awards = [r for r in india_ppo if r.get("category") == "Contract Awards"]

    files_dir = storage.tab_dir("procurement") / "files"

    # 始终下载全量中标合同主表 Excel（体积小、研究价值极高）
    xlsx_url = overview_info.get("contract_awards_xlsx_url", "")
    if xlsx_url:
        xlsx_name = sanitize_filename(xlsx_url.rsplit("/", 1)[-1])
        xlsx_dest = files_dir / xlsx_name
        if download_binary_file(client, xlsx_url, xlsx_dest, state, storage):
            overview_info["contract_awards_xlsx_local_path"] = str(xlsx_dest.relative_to(storage.data_dir))

    # 下载年度运营采购报告 PDF (2021-2025)
    if config.download_pdfs in ("india", "all"):
        for rep in overview_info.get("annual_procurement_reports", []):
            rep_url = rep.get("url", "")
            if not rep_url:
                continue
            rep_dest = files_dir / sanitize_filename(rep_url.rsplit("/", 1)[-1])
            if download_binary_file(client, rep_url, rep_dest, state, storage):
                rep["local_path"] = str(rep_dest.relative_to(storage.data_dir))

    storage.save_dataset("procurement", "procurement_overview_files", overview_info)
    storage.save_dataset("procurement", "procurement_all_records", ppo_records)
    storage.save_dataset("procurement", "contract_awards_notices", contract_awards)
    storage.save_dataset("procurement", "india_procurement_records", india_ppo)
    storage.save_dataset("procurement", "india_contract_awards", india_contract_awards)
    storage.save_tab_records("procurement", ppo_records)

    for r in ppo_records:
        state.seen_ids.add(str(r["record_id"]))
    storage.save_state(state)

    logger.info(
        "[+] [procurement] 模块完成: 全量采购记录 %d 条 (其中合同授予 %d 条，涉印采购记录 %d 条)",
        len(ppo_records),
        len(contract_awards),
        len(india_ppo),
    )
    return ppo_records


# ==============================================================================
# 模块 3: Governance (Voting Power, Governors, Directors, Board Minutes) 采集
# ==============================================================================


def collect_governance_tab(
    client: httpx.Client,
    config: Config,
    storage: Storage,
    state: CheckpointState,
) -> list[dict[str, Any]]:
    """抓取成员国认缴股本与投票权、理事会成员与历年决议、年会纪要、12个董事会选区及历次董事会会议纪要。"""
    logger.info("[*] 正在拉取 AIIB 治理结构、投票权、理事会与董事会会议纪要数据...")

    voting_js = fetch_text_with_retry(client, ENDPOINTS["voting_power_js"])
    voting_data = parse_voting_power_js(voting_js)

    gov_json = fetch_text_with_retry(client, ENDPOINTS["governors_json"])
    governors = parse_governors_json(gov_json)

    res_js = fetch_text_with_retry(client, ENDPOINTS["governors_res_js"])
    resolutions = parse_governors_resolutions_js(res_js)
    resolutions = [r for r in resolutions if _filter_by_year(r.get("year"), config)]

    gov_html = fetch_text_with_retry(client, ENDPOINTS["governors_index_html"])
    annual_proceedings = parse_governors_annual_meetings_html(gov_html)

    dir_json = fetch_text_with_retry(client, ENDPOINTS["directors_json"])
    constituencies = parse_directors_json(dir_json)

    minutes_html = fetch_text_with_retry(client, ENDPOINTS["meeting_minutes_html"])
    board_minutes = parse_meeting_minutes_html(minutes_html)
    board_minutes = [m for m in board_minutes if _filter_by_year(m.get("meeting_year"), config)]

    india_Pages_extracts: list[dict[str, Any]] = []

    # 下载历届理事会年会纪要 (Summary Proceedings) PDF 并自动检索涉印段落
    if config.download_pdfs in ("india", "all"):
        proc_dir = storage.tab_dir("governance") / "pdfs" / "annual_proceedings"
        for proc in annual_proceedings:
            pdf_url = proc.get("pdf_url", "")
            if not pdf_url:
                continue
            dest = proc_dir / sanitize_filename(pdf_url.rsplit("/", 1)[-1])
            if download_binary_file(client, pdf_url, dest, state, storage):
                proc["local_path"] = str(dest.relative_to(storage.data_dir))
                mentions = extract_india_mentions_from_pdf(dest)
                if mentions:
                    india_Pages_extracts.append(
                        {
                            "source_type": "Board of Governors Annual Meeting Proceedings",
                            "year": proc.get("year"),
                            "title": proc.get("title"),
                            "pdf_url": pdf_url,
                            "local_path": proc["local_path"],
                            "india_mentions": mentions,
                        }
                    )

    if config.download_pdfs in ("india", "all"):
        min_dir = storage.tab_dir("governance") / "pdfs" / "board_minutes"
        for bm in board_minutes:
            pdf_url = bm.get("pdf_url", "")
            if not pdf_url:
                continue
            dest = min_dir / sanitize_filename(pdf_url.rsplit("/", 1)[-1])
            if download_binary_file(client, pdf_url, dest, state, storage):
                bm["local_path"] = str(dest.relative_to(storage.data_dir))

    storage.save_dataset("governance", "members_voting_power", voting_data)
    storage.save_dataset("governance", "board_of_governors", governors)
    storage.save_dataset("governance", "governors_resolutions", resolutions)
    storage.save_dataset("governance", "governors_annual_proceedings", annual_proceedings)
    storage.save_dataset("governance", "board_of_directors_constituencies", constituencies)
    storage.save_dataset("governance", "board_of_directors_meeting_minutes", board_minutes)
    storage.save_dataset("governance", "india_governor_proceedings_mentions", india_Pages_extracts)

    summary_records: list[dict[str, Any]] = [
        *voting_data.get("members", []),
        *constituencies,
        *resolutions,
        *board_minutes,
    ]
    storage.save_tab_records("governance", summary_records)
    for rec in summary_records:
        if rec.get("record_id"):
            state.seen_ids.add(str(rec["record_id"]))
    storage.save_state(state)

    logger.info(
        "[+] [governance] 模块完成: 成员国投票权 %d 国, 选区 %d 个, 理事会决议 %d 项, 董事会会议纪要 %d 份",
        len(voting_data.get("members", [])),
        len(constituencies),
        len(resolutions),
        len(board_minutes),
    )
    return summary_records


# ==============================================================================
# 模块 4: Accountability (PPM, CEIU Evaluations, Debarment List) 采集
# ==============================================================================


def collect_accountability_tab(
    client: httpx.Client,
    config: Config,
    storage: Storage,
    state: CheckpointState,
) -> list[dict[str, Any]]:
    """抓取 PPM 受影响民众机制申诉案件、联合融资 IAM 案件、CEIU 独立评估学习报告与廉洁制裁名单。"""
    logger.info("[*] 正在拉取 AIIB 问责机制 (PPM)、独立评估 (CEIU) 与制裁名单数据...")

    ppm_js = fetch_text_with_retry(client, ENDPOINTS["ppm_main_js"])
    ppm_cases = parse_ppm_submissions_js(ppm_js)
    ppm_cases = [c for c in ppm_cases if _filter_by_year(c.get("year"), config)]
    india_ppm_cases = [c for c in ppm_cases if c.get("economy", "").lower() == "india"]

    ppm_html = fetch_text_with_retry(client, ENDPOINTS["ppm_track_html"])
    ppm_tables = parse_ppm_html_tables(ppm_html)

    ceiu_html = fetch_text_with_retry(client, ENDPOINTS["ceiu_eval_html"])
    ceiu_data = parse_ceiu_evaluation_html(ceiu_html)

    debarment_js = fetch_text_with_retry(client, ENDPOINTS["debarment_js"])
    debarment_list = parse_debarment_list_js(debarment_js)

    pdf_dir = storage.tab_dir("accountability") / "pdfs"

    # 下载联合融资项目与适用 IAM 清单 PDF、PPM 案件关联 PDF 以及涉印 CEIU 评估报告 PDF
    if config.download_pdfs in ("india", "all"):
        cofin_pdf_url = ppm_tables.get("cofinanced_projects_pdf_url", "")
        if cofin_pdf_url:
            dest = pdf_dir / sanitize_filename(cofin_pdf_url.rsplit("/", 1)[-1])
            if download_binary_file(client, cofin_pdf_url, dest, state, storage):
                ppm_tables["cofinanced_projects_pdf_local_path"] = str(dest.relative_to(storage.data_dir))

        target_ppm_cases = ppm_cases if config.download_pdfs == "all" else india_ppm_cases
        for case in target_ppm_cases:
            local_paths: list[str] = []
            for p_url in case.get("project_urls", []):
                clean_u = p_url.split("#", 1)[0]
                if clean_u.lower().endswith(".pdf"):
                    dest = pdf_dir / sanitize_filename(clean_u.rsplit("/", 1)[-1])
                    if download_binary_file(client, clean_u, dest, state, storage):
                        local_paths.append(str(dest.relative_to(storage.data_dir)))
            if local_paths:
                case["local_pdf_paths"] = local_paths

        for plr in ceiu_data.get("plr_reports", []):
            proj_name = str(plr.get("project_name") or "")
            is_india_plr = "gujarat" in proj_name.lower() or "india" in proj_name.lower()
            if config.download_pdfs == "all" or is_india_plr:
                for doc in plr.get("evaluation_documents", []):
                    raw_doc_url = doc.get("url", "")
                    doc_url = raw_doc_url.split("#", 1)[0]
                    if not doc_url or not doc_url.lower().endswith(".pdf"):
                        continue
                    dest = pdf_dir / sanitize_filename(doc_url.rsplit("/", 1)[-1])
                    if download_binary_file(client, doc_url, dest, state, storage):
                        doc["local_path"] = str(dest.relative_to(storage.data_dir))

    storage.save_dataset("accountability", "ppm_submissions_all", ppm_cases)
    storage.save_dataset("accountability", "india_ppm_submissions", india_ppm_cases)
    storage.save_dataset("accountability", "ppm_cofinancier_iam_cases", ppm_tables)
    storage.save_dataset("accountability", "ceiu_evaluation_reports", ceiu_data)
    storage.save_dataset("accountability", "debarment_list", debarment_list)

    combined_records: list[dict[str, Any]] = [
        *ppm_cases,
        *ceiu_data.get("plr_reports", []),
        *debarment_list,
    ]
    storage.save_tab_records("accountability", combined_records)
    for rec in combined_records:
        if rec.get("record_id"):
            state.seen_ids.add(str(rec["record_id"]))
    storage.save_state(state)

    logger.info(
        "[+] [accountability] 模块完成: PPM 申诉 %d 件 (其中涉印 %d 件), CEIU 评估报告 %d 份, 制裁名单 %d 条",
        len(ppm_cases),
        len(india_ppm_cases),
        len(ceiu_data.get("plr_reports", [])),
        len(debarment_list),
    )
    return combined_records

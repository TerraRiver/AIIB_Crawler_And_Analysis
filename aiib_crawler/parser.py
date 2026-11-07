"""AIIB 官网静态 JS 数据源与 HTML DOM 纯函数解析器（与网络/浏览器解耦，便于单元测试）。"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

from bs4 import BeautifulSoup, Tag

from aiib_crawler.config import BASE_URL

# 印度 28 个邦、8 个联邦属地及主要城市映射表（用于提取次国家层面的空间分布）
INDIAN_STATES_MAP: dict[str, str] = {
    "andhra pradesh": "Andhra Pradesh",
    "amaravati": "Andhra Pradesh",
    "visakhapatnam": "Andhra Pradesh",
    "arunachal pradesh": "Arunachal Pradesh",
    "assam": "Assam",
    "guwahati": "Assam",
    "bihar": "Bihar",
    "patna": "Bihar",
    "chhattisgarh": "Chhattisgarh",
    "goa": "Goa",
    "gujarat": "Gujarat",
    "ahmedabad": "Gujarat",
    "surat": "Gujarat",
    "gift city": "Gujarat",
    "haryana": "Haryana",
    "gurugram": "Haryana",
    "gurgaon": "Haryana",
    "himachal pradesh": "Himachal Pradesh",
    "jharkhand": "Jharkhand",
    "karnataka": "Karnataka",
    "bangalore": "Karnataka",
    "bengaluru": "Karnataka",
    "kerala": "Kerala",
    "kochi": "Kerala",
    "madhya pradesh": "Madhya Pradesh",
    "indore": "Madhya Pradesh",
    "bhopal": "Madhya Pradesh",
    "maharashtra": "Maharashtra",
    "mumbai": "Maharashtra",
    "pune": "Maharashtra",
    "manipur": "Manipur",
    "meghalaya": "Meghalaya",
    "mizoram": "Mizoram",
    "nagaland": "Nagaland",
    "odisha": "Odisha",
    "bhubaneswar": "Odisha",
    "punjab": "Punjab",
    "amritsar": "Punjab",
    "ludhiana": "Punjab",
    "rajasthan": "Rajasthan",
    "jaipur": "Rajasthan",
    "sikkim": "Sikkim",
    "tamil nadu": "Tamil Nadu",
    "chennai": "Tamil Nadu",
    "telangana": "Telangana",
    "hyderabad": "Telangana",
    "tripura": "Tripura",
    "uttar pradesh": "Uttar Pradesh",
    "uttarakhand": "Uttarakhand",
    "west bengal": "West Bengal",
    "kolkata": "West Bengal",
    "delhi": "Delhi (NCT)",
    "jammu and kashmir": "Jammu and Kashmir",
    "ladakh": "Ladakh",
    "puducherry": "Puducherry",
}

COFINANCIER_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("World Bank", re.compile(r"\b(?:World Bank|IBRD|International Bank for Reconstruction and Development|IDA)\b", re.I)),
    ("ADB", re.compile(r"\b(?:Asian Development Bank|ADB)\b", re.I)),
    ("IFC", re.compile(r"\b(?:International Finance Corporation|IFC)\b", re.I)),
    ("EBRD", re.compile(r"\b(?:European Bank for Reconstruction and Development|EBRD)\b", re.I)),
    ("EIB", re.compile(r"\b(?:European Investment Bank|EIB)\b", re.I)),
    ("IsDB", re.compile(r"\b(?:Islamic Development Bank|IsDB)\b", re.I)),
    ("NDB", re.compile(r"\b(?:New Development Bank|NDB)\b", re.I)),
    ("KfW", re.compile(r"\bKfW\b", re.I)),
    ("AFD", re.compile(r"\b(?:Agence Fran[cç]aise de D[eé]veloppement|AFD)\b", re.I)),
    ("JICA", re.compile(r"\b(?:Japan International Cooperation Agency|JICA)\b", re.I)),
]


def normalize_url(href: str | None) -> str:
    """将相对路径规范化为完整 AIIB URL。"""
    if not href:
        return ""
    val = href.strip()
    if not val:
        return ""
    if val.startswith(("http://", "https://")):
        return val
    if val.startswith("//"):
        return f"https:{val}"
    if not val.startswith("/"):
        val = "/" + val
    return f"{BASE_URL}{val}"


def clean_html_text(raw_html: str | None) -> str:
    """剥离 HTML 标签并合并多余空白。"""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    text = soup.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def parse_usd_millions(raw: str | None) -> float | None:
    """从类似 'USD140.61 million'、'USD 1,250.00 million'、'USD5.00 million' 中提取百万美元浮点数。"""
    if not raw:
        return None
    text = raw.strip()
    if not text:
        return None
    m_billion = re.search(r"([0-9][0-9,]*(?:\.[0-9]+)?)\s*billion", text, re.I)
    if m_billion:
        return round(float(m_billion.group(1).replace(",", "")) * 1000.0, 4)
    m_million = re.search(r"([0-9][0-9,]*(?:\.[0-9]+)?)\s*million", text, re.I)
    if m_million:
        return round(float(m_million.group(1).replace(",", "")), 4)
    m_num = re.search(r"USD\s*([0-9][0-9,]*(?:\.[0-9]+)?)", text, re.I)
    if m_num:
        val = float(m_num.group(1).replace(",", ""))
        return round(val / 1_000_000.0, 4) if val >= 1000 else round(val, 4)
    return None


def parse_flexible_date(raw: str | None) -> datetime | None:
    """解析 AIIB 常见日期字符串（如 'October 28, 2021', 'Jan 11, 2016', '2025'）并返回 UTC datetime。"""
    if not raw:
        return None
    cleaned = re.sub(r"\s+", " ", raw.strip()).rstrip(".")
    if not cleaned or cleaned in ("-", "N/A", "NULL", "TBD"):
        return None
    # 替换常见缩写句点，如 'Aug. 28, 2026' -> 'Aug 28, 2026'
    cleaned = re.sub(r"\b([A-Za-z]{3,4})\.\s+", r"\1 ", cleaned)
    cleaned = re.sub(r"\bSept\b", "Sep", cleaned, flags=re.I)

    formats = (
        "%B %d, %Y",
        "%b %d, %Y",
        "%B %Y",
        "%b %Y",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%Y",
    )
    for fmt in formats:
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def extract_js_array_json(raw_js: str, var_name: str = "data") -> list[Any]:
    """从形如 'var data = [...];' 的 JS 文件中提取指定变量的 JSON 数组并解析。"""
    pattern = re.compile(rf"var\s+{re.escape(var_name)}\s*=\s*\[")
    m = pattern.search(raw_js)
    start_idx = m.end() - 1 if m else raw_js.find("[")
    if start_idx == -1:
        return []

    sub = re.sub(r",\s*\]", "]", raw_js[start_idx:])
    decoder = json.JSONDecoder()
    obj, _ = decoder.raw_decode(sub)
    return obj if isinstance(obj, list) else []


def extract_indian_states(text: str) -> list[str]:
    """从印度项目标题、描述、借款人或执行机构文本中提取涉及的邦/直辖区列表。"""
    if not text:
        return []
    lowered = text.lower()
    found: list[str] = []
    for keyword, state_name in INDIAN_STATES_MAP.items():
        if re.search(rf"\b{re.escape(keyword)}\b", lowered) and state_name not in found:
            found.append(state_name)
    if not found:
        return ["Nationwide / Multi-State"]
    return found


def extract_cofinanciers(text: str) -> list[str]:
    """从项目文本与环境社会政策说明中提取联合融资伙伴机构（如 World Bank, ADB 等）。"""
    if not text:
        return []
    found: list[str] = []
    for name, pattern in COFINANCIER_PATTERNS:
        if pattern.search(text) and name not in found:
            found.append(name)
    return found


# ==============================================================================
# 模块 1: Projects & Special Funds 解析器
# ==============================================================================


def parse_projects_js(raw_js: str) -> list[dict[str, Any]]:
    """解析 all-projects-data.js，返回结构化项目列表。"""
    items = extract_js_array_json(raw_js, "data")
    results: list[dict[str, Any]] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "").strip()
        detail_url = normalize_url(path)
        name = clean_html_text(str(item.get("name") or ""))
        economy = str(item.get("economy") or "").strip()
        year_str = str(item.get("date") or "").strip()
        approval_year = int(year_str) if year_str.isdigit() else None

        approved_raw = str(item.get("approved_funding") or "").strip()
        proposed_raw = str(item.get("proposed_funding") or "").strip()
        committed_raw = str(item.get("committed_funding") or "").strip()
        special_raw = str(item.get("special_funding") or "").strip()

        approved_usd = parse_usd_millions(approved_raw)
        proposed_usd = parse_usd_millions(proposed_raw)
        funding_usd = approved_usd if approved_usd is not None else proposed_usd

        project_type = str(item.get("project_type") or "").strip()
        if project_type.upper() == "NULL":
            project_type = ""

        record_id = path if path else f"project:{year_str}:{economy}:{name}:{idx}"
        results.append(
            {
                "record_id": record_id,
                "approval_year": approval_year,
                "date_raw": year_str,
                "economy": economy,
                "sector": str(item.get("sector") or "").strip(),
                "financing_type": str(item.get("financing_type") or "").strip(),
                "project_type": project_type,
                "name": name,
                "status": str(item.get("status") or "").strip(),
                "approved_funding_raw": approved_raw,
                "approved_funding_usd_millions": approved_usd,
                "committed_funding_raw": committed_raw,
                "proposed_funding_raw": proposed_raw,
                "proposed_funding_usd_millions": proposed_usd,
                "effective_funding_usd_millions": funding_usd,
                "special_funding_raw": special_raw,
                "detail_path": path,
                "detail_url": detail_url,
            }
        )
    return results


def classify_document_type(title: str, category: str) -> str:
    """根据文档标题与分类归纳文档类型（PSI, PD, PIMR, ESMP, Loan Agreement, Other）。"""
    lowered = f"{title} {category}".lower()
    if "monitoring report" in lowered or "pimr" in lowered:
        return "PIMR"
    if "project document" in lowered or re.search(r"\bpd\b", lowered):
        return "PD"
    if "project summary" in lowered or re.search(r"\bpsi\b", lowered):
        return "PSI"
    if "loan agreement" in lowered or "project agreement" in lowered or "guarantee agreement" in lowered:
        return "Loan/Project Agreement"
    if any(k in lowered for k in ("environmental", "social", "esmp", "esia", "resettlement", "indigenous")):
        return "E&S Document"
    if "procurement" in lowered or "contract award" in lowered:
        return "Procurement Document"
    return "Other"


def parse_project_detail_html(html: str, url: str = "") -> dict[str, Any]:
    """解析单个 AIIB 项目详情页 HTML，提取完整元数据、段落文本、文档链接与衍生研究指标。"""
    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.select_one("h1.title-page") or soup.select_one("title")
    title = title_el.get_text(" ", strip=True) if title_el else ""
    if ":" in title and title.lower().startswith(("approved projects", "proposed projects")):
        title = title.split(":", 1)[1].strip()

    # 1. 解析顶部 Summary 卡片项 (.summary-item)
    summary_map: dict[str, str] = {}
    for item in soup.select(".summary-item"):
        name_el = item.select_one(".summary-item-name")
        val_el = item.select_one(".summary-item-value")
        if not name_el or not val_el:
            continue
        key = name_el.get_text(" ", strip=True).upper().rstrip(":")
        val = val_el.get_text(" ", strip=True)
        if key:
            summary_map[key] = val

    project_number = summary_map.get("PROJECT NUMBER", "")
    status = summary_map.get("STATUS", "")
    economy = summary_map.get("MEMBER", "")
    sector = summary_map.get("SECTOR", "")
    es_category = summary_map.get("E&S CATEGORY", "")
    approved_funding_raw = summary_map.get("APPROVED FUNDING", "")
    proposed_funding_raw = summary_map.get("PROPOSED FUNDING", "")
    financing_type = summary_map.get("FINANCING TYPE", "")
    concept_review_raw = summary_map.get("CONCEPT REVIEW", "")
    financing_approval_raw = summary_map.get("FINANCING APPROVAL", "")
    latest_field_visit = summary_map.get("LATEST FIELD VISIT", "")
    loan_closing_raw = summary_map.get("LOAN CLOSING / LAST DISBURSEMENT", "") or summary_map.get("LOAN CLOSING", "")

    concept_dt = parse_flexible_date(concept_review_raw)
    approval_dt = parse_flexible_date(financing_approval_raw)
    approval_lag_days: int | None = None
    if concept_dt and approval_dt and approval_dt >= concept_dt:
        approval_lag_days = (approval_dt - concept_dt).days

    # 2. 解析正文段落 (.project-paragraph .paragraph)
    paragraphs: dict[str, str] = {}
    for para in soup.select(".project-paragraph .paragraph"):
        h2 = para.find("h2")
        if not h2:
            continue
        heading = h2.get_text(" ", strip=True).upper()
        # 移除标题本身后提取正文
        h2_copy_text = h2.get_text(" ", strip=True)
        full_text = para.get_text(" ", strip=True)
        body = full_text[len(h2_copy_text) :].strip() if full_text.startswith(h2_copy_text) else full_text
        paragraphs[heading] = body

    objective = paragraphs.get("OBJECTIVE", "")
    description = paragraphs.get("DESCRIPTION", "")
    es_info = paragraphs.get("ENVIRONMENTAL AND SOCIAL INFORMATION", "")
    project_team_leader = paragraphs.get("PROJECT TEAM LEADER", "")
    borrower = paragraphs.get("BORROWER", "")
    implementing_entity = paragraphs.get("IMPLEMENTING ENTITY", "")

    # 3. 解析项目关联 PDF 与披露文档 (.feature-documents .doc)
    documents: list[dict[str, str]] = []
    for doc_group in soup.select(".feature-documents .doc"):
        cat_el = doc_group.select_one(".project-sub-title")
        doc_category = cat_el.get_text(" ", strip=True) if cat_el else "DOCUMENTS"
        for link_wrap in doc_group.select(".link"):
            a_el = link_wrap.find("a", href=True)
            if not a_el:
                continue
            doc_url = normalize_url(a_el.get("href"))
            doc_title = a_el.get_text(" ", strip=True)
            date_el = link_wrap.select_one(".date")
            doc_date = date_el.get_text(" ", strip=True) if date_el else ""
            documents.append(
                {
                    "category": doc_category,
                    "title": doc_title,
                    "date": doc_date,
                    "url": doc_url,
                    "doc_type": classify_document_type(doc_title, doc_category),
                }
            )

    # 4. 计算研究衍生指标（联合融资伙伴、环境社会政策适用、金融中介转贷、印度次国家邦分布）
    combined_text = " ".join([title, financing_type, objective, description, es_info, borrower, implementing_entity])
    cofinanciers = extract_cofinanciers(combined_text)
    is_cofinanced = bool(cofinanciers) or ("cofinanc" in combined_text.lower()) or ("co-financ" in combined_text.lower())

    if cofinanciers and any(
        phrase in es_info.lower()
        for phrase in (
            "world bank's environmental",
            "world bank’s environmental",
            "adb's safeguard",
            "adb’s safeguard",
            "ebrd's environmental",
            "ebrd’s environmental",
            "co-financier's",
            "cofinancier's",
            "cofinancier’s",
            "applicable environmental and social",
        )
    ):
        applicable_es_policy = f"Cofinancier Policy ({', '.join(cofinanciers)})"
    else:
        applicable_es_policy = "AIIB ESP"

    is_fi_onlending = (es_category.upper() == "FI") or any(
        kw in combined_text.lower()
        for kw in ("financial intermediary", "on-lending", "onlending", "sub-project", "subproject", "alternative investment fund")
    )

    indian_states = extract_indian_states(combined_text) if economy.lower() == "india" else []

    approved_usd = parse_usd_millions(approved_funding_raw)
    proposed_usd = parse_usd_millions(proposed_funding_raw)

    return {
        "record_id": url or f"project_number:{project_number}",
        "url": url,
        "project_number": project_number,
        "title": title,
        "status": status,
        "economy": economy,
        "sector": sector,
        "es_category": es_category,
        "financing_type": financing_type,
        "approved_funding_raw": approved_funding_raw,
        "approved_funding_usd_millions": approved_usd,
        "proposed_funding_raw": proposed_funding_raw,
        "proposed_funding_usd_millions": proposed_usd,
        "concept_review_date": concept_review_raw,
        "financing_approval_date": financing_approval_raw,
        "approval_lag_days": approval_lag_days,
        "latest_field_visit": latest_field_visit,
        "loan_closing_date": loan_closing_raw,
        "objective": objective,
        "description": description,
        "environmental_and_social_info": es_info,
        "project_team_leader": project_team_leader,
        "borrower": borrower,
        "implementing_entity": implementing_entity,
        "is_cofinanced": is_cofinanced,
        "cofinanciers": cofinanciers,
        "applicable_es_policy": applicable_es_policy,
        "is_fi_onlending": is_fi_onlending,
        "indian_states": indian_states,
        "documents_count": len(documents),
        "pimr_count": sum(1 for d in documents if d["doc_type"] == "PIMR"),
        "documents": documents,
        "raw_summary_fields": summary_map,
    }


# ==============================================================================
# 模块 2: Procurement & Contract Awards 解析器
# ==============================================================================


def parse_contract_price(raw_price: str | None) -> tuple[str, float | None]:
    """解析合同金额字符串（如 'USD 84,000.00' 或 'INR 2,078,489,885.00'），返回 (币种, 数值)。"""
    if not raw_price:
        return "", None
    text = raw_price.strip()
    if not text:
        return "", None
    m = re.match(r"^([A-Za-z]{3})\s*([0-9][0-9,]*(?:\.[0-9]+)?)", text)
    if m:
        currency = m.group(1).upper()
        try:
            amount = float(m.group(2).replace(",", ""))
            return currency, amount
        except ValueError:
            return currency, None
    return "", None


def parse_ppo_data_js(raw_js: str) -> list[dict[str, Any]]:
    """解析 ppo-data-all.js 中的 var ppoData = [...] 采购与合同授予记录。"""
    idx = raw_js.find("[")
    ridx = raw_js.rfind("]")
    if idx == -1 or ridx == -1 or ridx <= idx:
        return []
    body = raw_js[idx : ridx + 1]
    # 将未加引号的 JS 属性键名转换为合法 JSON 键名
    normalized = re.sub(
        r"(?<=[{,])\s*(id|cd|mb|pj|ds|cr|sd|pc|st|ct|tp|dc)\s*:",
        r'"\1":',
        body,
    )
    normalized = re.sub(r",\s*\]", "]", normalized)
    raw_items = json.loads(normalized)

    results: list[dict[str, Any]] = []
    for i, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        pub_date = str(item.get("id") or "").strip()
        dt = parse_flexible_date(pub_date)
        raw_price = str(item.get("pc") or "").strip()
        currency, amount = parse_contract_price(raw_price)
        doc_path = str(item.get("dc") or "").strip()
        results.append(
            {
                "record_id": f"ppo:{i}:{pub_date}:{doc_path}",
                "published_date": pub_date,
                "published_year": dt.year if dt else None,
                "closing_date": str(item.get("cd") or "").strip(),
                "economy": str(item.get("mb") or "").strip(),
                "project_name": clean_html_text(str(item.get("pj") or "")),
                "description": clean_html_text(str(item.get("ds") or "")),
                "contractor": clean_html_text(str(item.get("cr") or "")),
                "signature_date": str(item.get("sd") or "").strip(),
                "contract_amount_raw": raw_price,
                "contract_currency": currency,
                "contract_amount": amount,
                "sector": str(item.get("st") or "").strip(),
                "category": str(item.get("ct") or "").strip(),
                "notice_type": str(item.get("tp") or "").strip(),
                "document_path": doc_path,
                "document_url": normalize_url(doc_path),
            }
        )
    return results


def parse_procurement_overview_html(html: str) -> dict[str, Any]:
    """从 project-procurement/index.html 中提取中标合同全量 Excel 与年度运营采购报告 PDF 链接。"""
    soup = BeautifulSoup(html, "html.parser")
    contract_awards_xlsx_url = ""
    annual_reports: list[dict[str, str]] = []

    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        full_url = normalize_url(href)
        text = a.get_text(" ", strip=True)
        if "List-of-Contract-Awards" in href and href.lower().endswith(".xlsx"):
            contract_awards_xlsx_url = full_url
        elif "Annual-Operational-Procurement-Report" in href and href.lower().endswith(".pdf"):
            m_year = re.search(r"(20\d{2})", href)
            annual_reports.append(
                {
                    "year": m_year.group(1) if m_year else "",
                    "title": text or href.rsplit("/", 1)[-1],
                    "url": full_url,
                }
            )

    return {
        "contract_awards_xlsx_url": contract_awards_xlsx_url,
        "annual_procurement_reports": annual_reports,
    }


# ==============================================================================
# 模块 3: Governance (Voting Power, Governors, Directors, Board Minutes) 解析器
# ==============================================================================


def _parse_number(val: str) -> float | None:
    cleaned = val.replace(",", "").replace("%", "").replace("*", "").strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_voting_power_js(raw_js: str) -> dict[str, Any]:
    """解析 voting-power.js，提取域内成员、域外成员、准成员的认缴股本与投票权份额。"""
    update_match = re.search(r"var\s+update_date\s*=\s*\[\s*\"([^\"]+)\"\s*\]", raw_js)
    update_date = update_match.group(1).strip() if update_match else ""

    regional_raw = extract_js_array_json(raw_js, "regional_members")
    nonregional_raw = extract_js_array_json(raw_js, "nonregional_members")
    prospective_raw = extract_js_array_json(raw_js, "prospective_members")

    members: list[dict[str, Any]] = []
    totals: dict[str, dict[str, Any]] = {}

    for group_name, rows in (("Regional", regional_raw), ("Non-Regional", nonregional_raw)):
        for row in rows:
            if not isinstance(row, str):
                continue
            parts = [p.strip() for p in row.split("|")]
            if len(parts) < 6:
                continue
            raw_economy = parts[0]
            economy = raw_economy.replace("*", "").strip()
            entry = {
                "record_id": f"member:{economy}",
                "economy": economy,
                "member_group": group_name,
                "join_date": parts[1],
                "subscription_amount_usd_millions": _parse_number(parts[2]),
                "subscription_percent": _parse_number(parts[3]),
                "voting_power_votes": int(_parse_number(parts[4]) or 0),
                "voting_power_percent": _parse_number(parts[5]),
            }
            if economy.lower().startswith(("total ", "grand total")):
                totals[economy] = entry
            else:
                members.append(entry)

    prospective_members = [str(x).replace("*", "").strip() for x in prospective_raw if str(x).strip()]

    return {
        "update_date": update_date,
        "members_count": len(members),
        "regional_count": sum(1 for m in members if m["member_group"] == "Regional"),
        "non_regional_count": sum(1 for m in members if m["member_group"] == "Non-Regional"),
        "totals": totals,
        "prospective_members": prospective_members,
        "members": members,
    }


def parse_governors_json(raw_json: str) -> list[dict[str, Any]]:
    """解析 governors.json，提取各国理事与副理事姓名及职务（如印度财政部长）。"""
    payload = json.loads(raw_json)
    content = payload.get("content", [])
    results: list[dict[str, Any]] = []

    for item in content:
        if not isinstance(item, dict):
            continue
        member_list = item.get("member", [])
        country_html = member_list[0].get("country", "") if member_list and isinstance(member_list[0], dict) else ""
        economy = clean_html_text(country_html).replace("*", "").strip()

        gov_soup = BeautifulSoup(str(item.get("governor") or ""), "html.parser")
        gov_name_el = gov_soup.select_one(".sort-governor")
        gov_title_el = gov_soup.select_one(".sub")

        alt_soup = BeautifulSoup(str(item.get("alertnate") or item.get("alternate") or ""), "html.parser")
        alt_name_el = alt_soup.select_one(".sort-alternate")
        alt_title_el = alt_soup.select_one(".sub")

        results.append(
            {
                "record_id": f"governor:{economy}",
                "economy": economy,
                "governor_name": gov_name_el.get_text(" ", strip=True) if gov_name_el else "",
                "governor_title": gov_title_el.get_text(" ", strip=True) if gov_title_el else "",
                "alternate_name": alt_name_el.get_text(" ", strip=True) if alt_name_el else "",
                "alternate_title": alt_title_el.get_text(" ", strip=True) if alt_title_el else "",
            }
        )
    return results


def _extract_js_field(block: str, key: str) -> str:
    """从 JS 对象文本块中提取指定字段的值（支持单引号、双引号与反引号模板字符串）。"""
    pattern = re.compile(
        rf"['\"]?{re.escape(key)}['\"]?\s*:\s*(?:`([^`]*)`|'((?:\\.|[^'])*)'|\"((?:\\.|[^\"])*)\")",
        re.S,
    )
    m = pattern.search(block)
    if not m:
        return ""
    val = m.group(1) if m.group(1) is not None else (m.group(2) if m.group(2) is not None else (m.group(3) or ""))
    return val.strip()


def parse_governors_resolutions_js(raw_js: str) -> list[dict[str, Any]]:
    """解析理事会决议 resData.js（支持反引号多行模板字符串）。"""
    start_match = re.search(r"\"content\"\s*:\s*\[", raw_js)
    if not start_match:
        return []
    sub = raw_js[start_match.end() :]
    blocks = re.split(r"\}\s*,\s*\{", sub)
    results: list[dict[str, Any]] = []

    for block in blocks:
        res_title = _extract_js_field(block, "title")
        if not res_title:
            continue
        text_tit = _extract_js_field(block, "text_tit")
        copy_html = _extract_js_field(block, "text_copy")
        date_raw = _extract_js_field(block, "date")
        dt = parse_flexible_date(date_raw)

        soup = BeautifulSoup(copy_html, "html.parser")
        a_el = soup.find("a", href=True)
        pdf_url = normalize_url(a_el.get("href")) if a_el else ""
        resolution_text = clean_html_text(f"{text_tit} {copy_html}")

        results.append(
            {
                "record_id": f"resolution:{res_title}",
                "resolution_no": res_title,
                "date": date_raw,
                "year": dt.year if dt else None,
                "title": res_title,
                "resolution_text": resolution_text,
                "pdf_url": pdf_url,
            }
        )
    return results


def parse_governors_annual_meetings_html(html: str) -> list[dict[str, Any]]:
    """从 board-governors/index.html 中提取历年理事会年会纪要 (Summary Proceedings) PDF 链接。"""
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        if not href.lower().endswith(".pdf"):
            continue
        if "proceedings" not in href.lower() and "annual-meeting" not in href.lower():
            continue
        full_url = normalize_url(href)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)
        text = a.get_text(" ", strip=True) or href.rsplit("/", 1)[-1]
        m_year = re.search(r"(20\d{2})", f"{text} {href}")
        results.append(
            {
                "record_id": f"bog_proceedings:{full_url}",
                "year": int(m_year.group(1)) if m_year else None,
                "title": text,
                "pdf_url": full_url,
            }
        )
    return results


def parse_directors_json(raw_json: str) -> list[dict[str, Any]]:
    """解析 all-directors.json，提取 12 个董事会选区（含印度独立选区）的董事、副董事及所代表成员国。"""
    payload = json.loads(raw_json)
    content = payload.get("content", [])
    results: list[dict[str, Any]] = []

    for idx, item in enumerate(content, start=1):
        if not isinstance(item, dict):
            continue
        dir_list = item.get("dir", [])
        dir_html = dir_list[0].get("name", "") if dir_list and isinstance(dir_list[0], dict) else ""
        dir_soup = BeautifulSoup(dir_html, "html.parser")
        dir_name_el = dir_soup.select_one(".name")
        dir_nat_el = dir_soup.select_one(".nationality")
        dir_link_el = dir_soup.select_one("a[href]")

        director_name = dir_name_el.get_text(" ", strip=True) if dir_name_el else ""
        director_nat = (dir_nat_el.get_text(" ", strip=True) if dir_nat_el else "").strip("() ")
        constituency_url = normalize_url(dir_link_el.get("href")) if dir_link_el else ""

        nates_soup = BeautifulSoup(str(item.get("nates") or ""), "html.parser")
        nate_names = [el.get_text(" ", strip=True) for el in nates_soup.select(".font-copy-16-black")]
        nate_nats = [el.get_text(" ", strip=True).strip("() ") for el in nates_soup.select(".font-copy-14-black")]
        alternates = [{"name": n, "nationality": nat} for n, nat in zip(nate_names, nate_nats, strict=False)]

        members_text = clean_html_text(str(item.get("members") or ""))
        constituency_members = [m.strip() for m in members_text.split(";") if m.strip()]

        results.append(
            {
                "record_id": f"constituency:{idx}:{director_nat or director_name}",
                "constituency_index": idx,
                "director_name": director_name,
                "director_nationality": director_nat,
                "constituency_url": constituency_url,
                "alternates": alternates,
                "constituency_members": constituency_members,
                "constituency_members_count": len(constituency_members),
                "is_single_country_constituency": len(constituency_members) == 1,
            }
        )
    return results


def parse_meeting_minutes_html(html: str) -> list[dict[str, Any]]:
    """解析 board-directors/meeting-minutes/index.html，提取历次董事会会议纪要日期与 PDF 链接。"""
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for row in soup.select(".members-table .table-pc .table-body ul.table-row"):
        lis = row.find_all("li", recursive=False)
        if not lis:
            continue
        meeting_date = lis[0].get_text(" ", strip=True)
        a_el = row.select_one("a[href]")
        if not a_el:
            continue
        pdf_url = normalize_url(a_el.get("href"))
        if not pdf_url or pdf_url in seen_urls:
            continue
        seen_urls.add(pdf_url)
        m_year = re.search(r"(20\d{2})", f"{meeting_date} {pdf_url}")
        results.append(
            {
                "record_id": f"bod_minutes:{pdf_url}",
                "meeting_date": meeting_date,
                "meeting_year": int(m_year.group(1)) if m_year else None,
                "pdf_url": pdf_url,
            }
        )
    return results


# ==============================================================================
# 模块 4: Accountability (PPM, CEIU Evaluations, Debarment List) 解析器
# ==============================================================================


def parse_ppm_submissions_js(raw_js: str) -> list[dict[str, Any]]:
    """解析 PPM 申诉案件数据源 submission/_common/main.js 中的 var baseData = [...]。"""
    start_match = re.search(r"var\s+baseData\s*=\s*\[", raw_js)
    if not start_match:
        return []
    sub = raw_js[start_match.end() :]
    end_idx = sub.find("];")
    if end_idx != -1:
        sub = sub[:end_idx]

    blocks = re.split(r"\}\s*,\s*\{", sub)
    results: list[dict[str, Any]] = []

    for block in blocks:
        case_no = _extract_js_field(block, "no")
        if not case_no:
            continue
        year_str = _extract_js_field(block, "year")
        economy = _extract_js_field(block, "member")
        pname_html = _extract_js_field(block, "pname")
        ppm_stage = _extract_js_field(block, "ppm")
        submission_html = _extract_js_field(block, "submission")
        status = _extract_js_field(block, "status")
        remarks_html = _extract_js_field(block, "remarks")

        pname_soup = BeautifulSoup(pname_html, "html.parser")
        project_links = [normalize_url(a.get("href")) for a in pname_soup.find_all("a", href=True)]
        project_name = pname_soup.get_text(" ", strip=True)

        submission_text = clean_html_text(submission_html)
        remarks_text = clean_html_text(remarks_html)

        delegated_cofinancier = extract_cofinanciers(remarks_text)
        is_dropped_pipeline = "dropped from aiib" in remarks_text.lower()

        results.append(
            {
                "record_id": f"ppm:{case_no}",
                "case_no": case_no,
                "year": int(year_str) if year_str.isdigit() else None,
                "economy": economy,
                "project_name": project_name,
                "project_urls": project_links,
                "ppm_function": ppm_stage,
                "status": status,
                "submission_summary": submission_text,
                "remarks": remarks_text,
                "delegated_to_cofinancier_iam": delegated_cofinancier,
                "is_project_dropped_from_pipeline": is_dropped_pipeline,
            }
        )
    return results


def _parse_int_cell(text: str) -> int:
    m = re.search(r"(\d+)", text or "")
    return int(m.group(1)) if m else 0


def parse_ppm_html_tables(html: str) -> dict[str, Any]:
    """解析 track-all-submission.html 中的联合融资机构 IAM 案件统计表 (.table-2) 与共融项目清单 PDF。"""
    soup = BeautifulSoup(html, "html.parser")
    cofinancier_iam_cases: list[dict[str, Any]] = []
    subtotal: dict[str, int] = {}

    for ul in soup.select(".table-2 .table-body ul.table-row"):
        lis = ul.find_all("li", recursive=False)
        if len(lis) < 8:
            continue

        def _col_text(li_el: Tag) -> str:
            con = li_el.select_one(".col-con")
            return con.get_text(" ", strip=True) if con else li_el.get_text(" ", strip=True)

        no_str = _col_text(lis[0])
        title_str = _col_text(lis[1])
        adb_cnt = _parse_int_cell(_col_text(lis[2]))
        ebrd_cnt = _parse_int_cell(_col_text(lis[3]))
        eib_cnt = _parse_int_cell(_col_text(lis[4]))
        ifc_cnt = _parse_int_cell(_col_text(lis[5]))
        wb_cnt = _parse_int_cell(_col_text(lis[6]))
        total_cnt = _parse_int_cell(_col_text(lis[7]))

        if "subtotal" in (ul.get("class") or []) or title_str.lower().startswith("sub-total"):
            subtotal = {
                "adb_am_count": adb_cnt,
                "ebrd_ipam_count": ebrd_cnt,
                "eib_cm_count": eib_cnt,
                "ifc_cao_count": ifc_cnt,
                "world_bank_am_count": wb_cnt,
                "total_count": total_cnt,
            }
            continue

        economy = ""
        project_name = title_str
        if ":" in title_str:
            econ_part, proj_part = title_str.split(":", 1)
            economy = econ_part.strip()
            project_name = proj_part.strip()

        proj_a = lis[1].find("a", href=True)
        cofinancier_iam_cases.append(
            {
                "no": _parse_int_cell(no_str),
                "economy": economy,
                "project_name": project_name,
                "project_url": normalize_url(proj_a.get("href")) if proj_a else "",
                "adb_am_count": adb_cnt,
                "ebrd_ipam_count": ebrd_cnt,
                "eib_cm_count": eib_cnt,
                "ifc_cao_count": ifc_cnt,
                "world_bank_am_count": wb_cnt,
                "total_count": total_cnt,
            }
        )

    cofinanced_list_pdf = ""
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if "Approved-Co-Financed-Projects" in href and href.lower().endswith(".pdf"):
            cofinanced_list_pdf = normalize_url(href)
            break

    return {
        "cofinanced_projects_pdf_url": cofinanced_list_pdf,
        "subtotal": subtotal,
        "cofinancier_iam_cases": cofinancier_iam_cases,
    }


def _extract_links_from_cell(td: Tag) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for a in td.find_all("a", href=True):
        links.append(
            {
                "title": a.get_text(" ", strip=True),
                "url": normalize_url(a.get("href")),
            }
        )
    return links


def parse_ceiu_evaluation_html(html: str) -> dict[str, Any]:
    """解析 CEIU 独立评估页面 evaluation/index.html，提取所有项目学习评估报告 (PLR) 与管理层回应 PDF。"""
    soup = BeautifulSoup(html, "html.parser")
    plr_reports: list[dict[str, Any]] = []

    for idx, tr in enumerate(soup.select("#table-1 tbody tr"), start=1):
        tds = tr.find_all("td")
        if len(tds) == 2:
            doc_links = _extract_links_from_cell(tds[0])
            date_str = tds[1].get_text(" ", strip=True)
            first_title = doc_links[0]["title"] if doc_links else tds[0].get_text(" ", strip=True)
            project_name = first_title.split(":", 1)[1].strip() if ":" in first_title else first_title
            plr_reports.append(
                {
                    "record_id": f"ceiu_plr:{idx}:{date_str}:{project_name}",
                    "date": date_str,
                    "sector": "",
                    "project_name": project_name,
                    "project_url": doc_links[0]["url"] if doc_links else "",
                    "evaluation_documents": doc_links,
                }
            )
        elif len(tds) >= 4:
            date_str = tds[0].get_text(" ", strip=True)
            sector = tds[1].get_text(" ", strip=True)
            doc_links = _extract_links_from_cell(tds[2])
            proj_links = _extract_links_from_cell(tds[3])
            project_name = tds[3].get_text(" ", strip=True)
            plr_reports.append(
                {
                    "record_id": f"ceiu_plr:{idx}:{date_str}:{project_name}",
                    "date": date_str,
                    "sector": sector,
                    "project_name": project_name,
                    "project_url": proj_links[0]["url"] if proj_links else "",
                    "evaluation_documents": doc_links,
                }
            )

    dialogues: list[dict[str, Any]] = []
    for idx, tr in enumerate(soup.select("#table-2 tbody tr"), start=1):
        tds = tr.find_all("td")
        if len(tds) == 2:
            dialogues.append(
                {
                    "record_id": f"ceiu_dialogue:{idx}",
                    "date": tds[1].get_text(" ", strip=True),
                    "topic": tds[0].get_text(" ", strip=True),
                    "links": _extract_links_from_cell(tds[0]),
                }
            )
        elif len(tds) >= 3:
            dialogues.append(
                {
                    "record_id": f"ceiu_dialogue:{idx}",
                    "date": tds[0].get_text(" ", strip=True),
                    "topic": tds[1].get_text(" ", strip=True),
                    "summary": tds[2].get_text(" ", strip=True),
                    "links": _extract_links_from_cell(tds[2]),
                }
            )

    return {
        "plr_reports": plr_reports,
        "practitioner_dialogues": dialogues,
    }


def parse_debarment_list_js(raw_js: str) -> list[dict[str, Any]]:
    """解析 debarment-list.js，提取被制裁实体与廉洁合规交叉违规名单。"""
    items = extract_js_array_json(raw_js, "data")
    results: list[dict[str, Any]] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        name = clean_html_text(str(item.get("NAME") or ""))
        economy = clean_html_text(str(item.get("ECONOMY") or ""))
        results.append(
            {
                "record_id": f"debarment:{idx}:{economy}:{name}",
                "entity_name": name,
                "address": clean_html_text(str(item.get("ADDRESS") or "")),
                "economy": economy,
                "debarred_by": clean_html_text(str(item.get("DEBARRED BY") or "")),
                "prohibited_practice": clean_html_text(str(item.get("PROHIBITED PRACTICE") or "")),
                "from_date": clean_html_text(str(item.get("FROM") or "")),
                "to_date": clean_html_text(str(item.get("TO") or "")),
                "date_added_by_aiib": clean_html_text(str(item.get("DATE ADDED BY AIIB") or "")),
                "other_notes": clean_html_text(str(item.get("OTHER NOTES") or "")),
            }
        )
    return results

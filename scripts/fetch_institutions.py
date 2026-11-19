"""下载亚投行（AIIB）官方核心制度、治理、业务政策与财务募资 PDF 原件至 data/institutions/pdfs/。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import time
import httpx
from pypdf import PdfReader

from aiib_crawler.collector import DEFAULT_HEADERS
from aiib_crawler.stealth import compute_backoff_wait
from aiib_crawler.storage import atomic_write_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)


def atomic_write_bytes(dest: Path, content: bytes) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest.with_suffix(dest.suffix + ".part")
    tmp_path.write_bytes(content)
    tmp_path.replace(dest)


def fetch_bytes_with_retry(client: httpx.Client, url: str, *, retries: int = 3) -> bytes:
    """带指数退避重试的二进制文件请求函数。"""
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            last_err = e
            wait_sec = compute_backoff_wait(attempt)
            logger.warning("[!] 下载失败 (%d/%d) %s: %s，等待 %.1fs 后重试", attempt, retries, url, e, wait_sec)
            time.sleep(wait_sec)
    raise RuntimeError(f"无法下载 {url}: {last_err}") from last_err

# 38 份核心制度与财务募资官方 PDF 清单
INSTITUTIONAL_DOCUMENTS: list[dict[str, str]] = [
    # 一、基础宪章与法律框架 (Charter & Legal Hierarchy)
    {
        "id": "01",
        "filename": "01_Articles_of_Agreement_CN.pdf",
        "category": "01_Charter_and_Legal_Framework",
        "title_cn": "《亚洲基础设施投资银行协定》（官方中文版）",
        "title_en": "Articles of Agreement (Chinese Version)",
        "url": "https://www.aiib.org/en/about-aiib/basic-documents/_download/articles-of-agreement/basic_document_chinese_bank_articles_of_agreement.pdf",
    },
    {
        "id": "02",
        "filename": "02_Articles_of_Agreement_EN.pdf",
        "category": "01_Charter_and_Legal_Framework",
        "title_cn": "《亚洲基础设施投资银行协定》（官方英文版）",
        "title_en": "Articles of Agreement (English Version)",
        "url": "https://www.aiib.org/en/about-aiib/basic-documents/_download/articles-of-agreement/basic_document_english-bank_articles_of_agreement.pdf",
    },
    {
        "id": "03",
        "filename": "03_Chief_Negotiators_Report.pdf",
        "category": "01_Charter_and_Legal_Framework",
        "title_cn": "《首席谈判代表关于亚投行协定的报告》",
        "title_en": "Chief Negotiators' Report on the Articles of Agreement",
        "url": "https://www.aiib.org/en/about-aiib/basic-documents/_download/articles-of-agreement/basic_document_report_on_the_articles_of_agreement.pdf",
    },
    {
        "id": "04",
        "filename": "04_Internal_Legal_Framework_Directive.pdf",
        "category": "01_Charter_and_Legal_Framework",
        "title_cn": "《内部法律框架指令》",
        "title_en": "Directive on the Internal Legal Framework",
        "url": "https://www.aiib.org/en/about-aiib/who-we-are/role-of-law/.content/index/_download/AIIB-Directive-on-the-Internal-Legal-Framework-20241016.pdf",
    },
    {
        "id": "05",
        "filename": "05_AIIB_Organizational_Structure.pdf",
        "category": "01_Charter_and_Legal_Framework",
        "title_cn": "《亚投行官方组织架构图》",
        "title_en": "AIIB Organizational Structure",
        "url": "https://www.aiib.org/en/about-aiib/governance/_common/_download/AIIB_organizational_structure.pdf",
    },
    # 二、治理架构、理事会与董事会职权及问责框架 (Governance, Boards & Accountability Framework)
    {
        "id": "06",
        "filename": "06_By_Laws_of_AIIB.pdf",
        "category": "02_Governance_and_Boards",
        "title_cn": "《亚投行附例》",
        "title_en": "By-Laws of the AIIB",
        "url": "https://www.aiib.org/en/about-aiib/basic-documents/_download/by-laws-of-the-asian/basic_document_by_laws_of_aiib.pdf",
    },
    {
        "id": "07",
        "filename": "07_Rules_of_Procedure_Governors.pdf",
        "category": "02_Governance_and_Boards",
        "title_cn": "《理事会议事规则》",
        "title_en": "Rules of Procedure of the Board of Governors",
        "url": "https://www.aiib.org/en/about-aiib/basic-documents/_download/rules-of-procedure/basic_document_rules_of_procedure_governors.pdf",
    },
    {
        "id": "08",
        "filename": "08_Rules_of_Procedure_Directors.pdf",
        "category": "02_Governance_and_Boards",
        "title_cn": "《董事会议事规则》",
        "title_en": "Rules of Procedure of the Board of Directors",
        "url": "https://www.aiib.org/en/about-aiib/basic-documents/_download/rules-of-procedure/rules-of-procedure-of-the-board-of-directors.pdf",
    },
    {
        "id": "09",
        "filename": "09_Rules_Election_of_President.pdf",
        "category": "02_Governance_and_Boards",
        "title_cn": "《行长选举规则》",
        "title_en": "Rules for the Election of the President",
        "url": "https://www.aiib.org/en/news-events/news/2020/_download/Rules-for-the-Election-of-the-President-adopted-Dec-2019.pdf",
    },
    {
        "id": "10",
        "filename": "10_Preparation_of_Board_Documents_Directive.pdf",
        "category": "02_Governance_and_Boards",
        "title_cn": "《董事会文件准备指令》",
        "title_en": "Directive on the Preparation of Board Documents",
        "url": "https://www.aiib.org/en/about-aiib/who-we-are/role-of-law/.content/index/_download/Directive-on-the-Preparation-of-Board-Documents.pdf",
    },
    {
        "id": "11",
        "filename": "11_Board_Policy_Strategy_Committee_TOR.pdf",
        "category": "02_Governance_and_Boards",
        "title_cn": "《董事会政策与战略委员会职权范围》",
        "title_en": "Terms of Reference for the Policy and Strategy Committee",
        "url": "https://www.aiib.org/en/about-aiib/basic-documents/_download/rules-of-directors/Asian-Infrastructure-Investment-Bank-Terms-of-Reference-for-the-Policy-and-Strategy-Committee.pdf",
    },
    {
        "id": "12",
        "filename": "12_Board_Audit_Risk_Committee_TOR.pdf",
        "category": "02_Governance_and_Boards",
        "title_cn": "《董事会审计与风险委员会职权范围》",
        "title_en": "Terms of Reference for the Audit and Risk Committee",
        "url": "https://www.aiib.org/en/about-aiib/basic-documents/_download/rules-of-directors/Asian-Infrastructure-Investment-Bank-Terms-of-Reference-for-the-Audit-and-Risk-Committee.pdf",
    },
    {
        "id": "13",
        "filename": "13_Accountability_Framework_Regulation.pdf",
        "category": "02_Governance_and_Boards",
        "title_cn": "《问责框架更新条例（Sec2022-100）》",
        "title_en": "Updated Regulation on the Accountability Framework",
        "url": "https://www.aiib.org/en/about-aiib/governance/_common/_download/Updated-Regulation-on-the-Accountability-Framework_Sec2022-100.pdf",
    },
    {
        "id": "14",
        "filename": "14_Accountability_Framework_Paper.pdf",
        "category": "02_Governance_and_Boards",
        "title_cn": "《问责框架说明文件》",
        "title_en": "Paper on the Accountability Framework",
        "url": "https://www.aiib.org/en/about-aiib/governance/_common/_download/paper-on-the-accountabilty-framework.pdf",
    },
    {
        "id": "15",
        "filename": "15_Oversight_Mechanism_Paper.pdf",
        "category": "02_Governance_and_Boards",
        "title_cn": "《监督机制说明文件》",
        "title_en": "Paper on the Oversight Mechanism",
        "url": "https://www.aiib.org/en/about-aiib/governance/_common/_download/paper-on-the-oversight-mechanism-public.pdf",
    },
    # 三、企业战略与业务边界 (Strategies & Mandate Boundaries)
    {
        "id": "16",
        "filename": "16_Corporate_Strategy.pdf",
        "category": "03_Strategies_and_Mandate",
        "title_cn": "《亚投行企业战略：为明日基础设施融资》",
        "title_en": "AIIB Corporate Strategy: Financing Infrastructure for Tomorrow",
        "url": "https://www.aiib.org/en/policies-strategies/strategies/.content/index/_download/AIIB-Corporate-Strategy.pdf",
    },
    {
        "id": "17",
        "filename": "17_Nonregional_Members_Financing_Strategy.pdf",
        "category": "03_Strategies_and_Mandate",
        "title_cn": "《非域内成员融资业务战略》",
        "title_en": "Strategy on Financing Operations in Nonregional Members",
        "url": "https://www.aiib.org/en/policies-strategies/_download/financing-operations/NRM-Strategy_Sep-BOD-Approved_For-Public-Website.pdf",
    },
    {
        "id": "18",
        "filename": "18_Mobilizing_Private_Capital_Strategy.pdf",
        "category": "03_Strategies_and_Mandate",
        "title_cn": "《动员私人资本基础设施战略》",
        "title_en": "Strategy on Mobilizing Private Capital for Infrastructure",
        "url": "https://www.aiib.org/en/policies-strategies/_download/mobilizing_private/Strategy-on-Mobilizing-Private-Capital-for-Infrastructure.pdf",
    },
    {
        "id": "19",
        "filename": "19_Investing_in_Equity_Strategy.pdf",
        "category": "03_Strategies_and_Mandate",
        "title_cn": "《股权投资战略》",
        "title_en": "Strategy on Investing in Equity",
        "url": "https://www.aiib.org/en/policies-strategies/_download/strategy-investing-equity/Strategy-on-Investing-in-Equity.pdf",
    },
    {
        "id": "20",
        "filename": "20_International_Relations_Policy.pdf",
        "category": "03_Strategies_and_Mandate",
        "title_cn": "《国际关系业务政策》",
        "title_en": "Operational Policy on International Relations",
        "url": "https://www.aiib.org/en/policies-strategies/_download/operational-policy-on-international-relations/operational-policy-on-international-relations.pdf",
    },
    {
        "id": "21",
        "filename": "21_Partnerships_Report_2025.pdf",
        "category": "03_Strategies_and_Mandate",
        "title_cn": "《2025 伙伴关系与联合融资报告》",
        "title_en": "AIIB Partnerships Report 2025",
        "url": "https://www.aiib.org/en/publications/partnerships-reports/2025/pdf/AIIB-partnerships-report-2025.pdf",
    },
    # 四、项目周期、采购、环评与问责流程 (Project Cycle, Procurement, ESF & PPM)
    {
        "id": "22",
        "filename": "22_Operational_Policy_on_Financing.pdf",
        "category": "04_Project_Cycle_and_Operations",
        "title_cn": "《融资业务政策 (OPF)》",
        "title_en": "Operational Policy on Financing (OPF)",
        "url": "https://www.aiib.org/en/policies-strategies/_download/operation-policy/AIIB-Operational-Policy-on-Financing_OPF.pdf",
    },
    {
        "id": "23",
        "filename": "23_Directive_on_OPF.pdf",
        "category": "04_Project_Cycle_and_Operations",
        "title_cn": "《融资业务政策执行指令（含项目周期全流程）》",
        "title_en": "Revised Directive on the Operational Policy on Financing",
        "url": "https://www.aiib.org/en/about-aiib/who-we-are/role-of-law/.content/index/_download/Revised-Directive-on-the-Operational-Policy-on-Financing.pdf",
    },
    {
        "id": "24",
        "filename": "24_Climate_Policy_Based_Financing_Paper.pdf",
        "category": "04_Project_Cycle_and_Operations",
        "title_cn": "《气候导向政策性融资文件》",
        "title_en": "Paper on AIIB Climate-Focused Policy-Based Financing",
        "url": "https://www.aiib.org/en/what-we-do/Climate-Focused-Policy-Based-Financing/pdf/Paper-on-AIIB-Climate-PBF_For-disclosure_July-10-2024-final.pdf",
    },
    {
        "id": "25",
        "filename": "25_General_Conditions_Sovereign_Loans.pdf",
        "category": "04_Project_Cycle_and_Operations",
        "title_cn": "《主权贷款通则》",
        "title_en": "General Conditions for Sovereign-backed Loans",
        "url": "https://www.aiib.org/en/policies-strategies/_download/sovereign-backed/General-Conditions-for-Sovereign-backed-Loans-October-22-2021.pdf",
    },
    {
        "id": "26",
        "filename": "26_Procurement_Policy.pdf",
        "category": "04_Project_Cycle_and_Operations",
        "title_cn": "《采购政策》",
        "title_en": "Procurement Policy",
        "url": "https://www.aiib.org/en/opportunities/business/.content/index/_download/AIIB-PROCUREMENT-POLICY.pdf",
    },
    {
        "id": "27",
        "filename": "27_Directive_Procurement_Recipients.pdf",
        "category": "04_Project_Cycle_and_Operations",
        "title_cn": "《受款人采购指令》",
        "title_en": "Directive on Procurement Instructions for Recipients",
        "url": "https://www.aiib.org/en/policies-strategies/_download/operational-directive/AIIB-Directive-on-Procurement-Instructions-for-Recipients-July-26-2024.pdf",
    },
    {
        "id": "28",
        "filename": "28_Directive_on_ESF.pdf",
        "category": "04_Project_Cycle_and_Operations",
        "title_cn": "《环境与社会框架执行指令》",
        "title_en": "Directive on the Environmental and Social Framework",
        "url": "https://www.aiib.org/en/policies-strategies/_download/project-affected/Directive-on-the-Environmental-and-Social-Framework.pdf",
    },
    {
        "id": "29",
        "filename": "29_PPM_Policy_2026_CN.pdf",
        "category": "04_Project_Cycle_and_Operations",
        "title_cn": "《受影响民众机制（PPM）政策 2026 官方中文版》",
        "title_en": "2026 AIIB Policy on the Project-affected People's Mechanism (Chinese)",
        "url": "https://www.aiib.org/en/policies-strategies/_download/project-affected/Translation-of-Policy/2026-AIIB-Policy-on-the-PPM_Translation-in-Chinese.pdf",
    },
    # 五、资金池、资本充足率、发债募资与财务报表 (Capital Pool, Treasury & Financials)
    {
        "id": "30",
        "filename": "30_ALM_Policy.pdf",
        "category": "05_Capital_Pool_and_Treasury",
        "title_cn": "《资产负债管理政策》",
        "title_en": "Asset Liability Management Policy",
        "url": "https://www.aiib.org/en/policies-strategies/_download/alm-policy/asset-liability-management-policy.pdf",
    },
    {
        "id": "31",
        "filename": "31_Directive_Capital_Adequacy.pdf",
        "category": "05_Capital_Pool_and_Treasury",
        "title_cn": "《资本充足率与压力测试指令》",
        "title_en": "Directive on Capital Adequacy and Stress Testing",
        "url": "https://www.aiib.org/en/about-aiib/who-we-are/role-of-law/.content/index/_download/AIIB-Directive-on-Capital-Adequacy-and-Stress-Testing.pdf",
    },
    {
        "id": "32",
        "filename": "32_Sovereign_Loan_Pricing_Policy.pdf",
        "category": "05_Capital_Pool_and_Treasury",
        "title_cn": "《主权担保产品定价政策》",
        "title_en": "Pricing Policy for Sovereign-Backed Products",
        "url": "https://www.aiib.org/en/policies-strategies/_download/operation-policy/Pricing-Policy-for-Sovereign-Backed-Products.pdf",
    },
    {
        "id": "33",
        "filename": "33_Sovereign_Financing_FactSheet.pdf",
        "category": "05_Capital_Pool_and_Treasury",
        "title_cn": "《主权融资情况说明书》",
        "title_en": "Sovereign-backed Financing Fact Sheet",
        "url": "https://www.aiib.org/en/treasury/_common/_download/AIIB_Sovereign-backed-Financing-SBF-FactSheet.pdf",
    },
    {
        "id": "34",
        "filename": "34_Directive_Special_Funds.pdf",
        "category": "05_Capital_Pool_and_Treasury",
        "title_cn": "《特别基金管理指令》",
        "title_en": "Directive on the Administration of AIIB Special Funds",
        "url": "https://www.aiib.org/en/about-aiib/who-we-are/role-of-law/.content/index/_download/AIIB-Directive-on-the-Administration-of-AIIB-Special-Funds.pdf",
    },
    {
        "id": "35",
        "filename": "35_Investor_Presentation.pdf",
        "category": "05_Capital_Pool_and_Treasury",
        "title_cn": "《投资者演示报告（含资金池与发债募资结构）》",
        "title_en": "AIIB Investor Presentation",
        "url": "https://www.aiib.org/en/treasury/_common/_download/AIIB-Investor-Presentation.pdf",
    },
    {
        "id": "36",
        "filename": "36_AIIB_Fact_Sheet.pdf",
        "category": "05_Capital_Pool_and_Treasury",
        "title_cn": "《亚投行财务与评级情况说明书》",
        "title_en": "AIIB Fact Sheet",
        "url": "https://www.aiib.org/en/treasury/_common/_download/AIIB_FACT-SHEET.pdf",
    },
    {
        "id": "37",
        "filename": "37_Financial_Statements_2025_Final.pdf",
        "category": "05_Capital_Pool_and_Treasury",
        "title_cn": "《2025 年度经审计财务报表》",
        "title_en": "AIIB Audited Financial Statements 2025",
        "url": "https://www.aiib.org/en/about-aiib/financial-statements/.content/index/pdf/AIIB-Financial-Statements-2025-Final.pdf",
    },
    {
        "id": "38",
        "filename": "38_Business_Plan_and_Budget_2026.pdf",
        "category": "05_Capital_Pool_and_Treasury",
        "title_cn": "《2026 年业务计划与预算摘要》",
        "title_en": "Summary of AIIB 2026 Business Plan and Budget",
        "url": "https://www.aiib.org/en/policies-strategies/_download/business-plan-2026/Summary-of-AIIB-2026-Business-Plan-and-Budget.pdf",
    },
]


def download_all_institutional_pdfs(base_dir: Path = Path("data/institutions")) -> list[dict[str, Any]]:
    pdfs_dir = base_dir / "pdfs"
    pdfs_dir.mkdir(parents=True, exist_ok=True)
    index_records: list[dict[str, Any]] = []

    with httpx.Client(headers=DEFAULT_HEADERS, follow_redirects=True, timeout=45.0) as client:
        for doc in INSTITUTIONAL_DOCUMENTS:
            dest = pdfs_dir / doc["filename"]
            if dest.exists() and dest.stat().st_size > 0:
                logger.info("[*] 已存在跳过: %s (%d KB)", doc["filename"], dest.stat().st_size // 1024)
            else:
                logger.info("[*] 正在下载 [%s/38] %s -> %s", doc["id"], doc["title_cn"], doc["filename"])
                content = fetch_bytes_with_retry(client, doc["url"])
                atomic_write_bytes(dest, content)

            page_count = 0
            try:
                reader = PdfReader(str(dest))
                page_count = len(reader.pages)
            except Exception as e:
                logger.warning("[!] 无法读取 PDF 页数 %s: %s", dest.name, e)

            index_records.append(
                {
                    **doc,
                    "local_path": f"institutions/pdfs/{doc['filename']}",
                    "size_bytes": dest.stat().st_size,
                    "size_kb": round(dest.stat().st_size / 1024.0, 1),
                    "pages": page_count,
                }
            )

    index_path = base_dir / "institutions_index.json"
    atomic_write_json(index_path, index_records)
    logger.info("[+] 全部 %d 份制度文件已下载完毕！索引文件: %s", len(index_records), index_path)
    return index_records


if __name__ == "__main__":
    download_all_institutional_pdfs()

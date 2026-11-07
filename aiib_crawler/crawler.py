"""爬虫主流程编排与印度参与度/偏好量化指标汇总生成。"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

import httpx

from aiib_crawler.collector import (
    DEFAULT_HEADERS,
    collect_accountability_tab,
    collect_governance_tab,
    collect_procurement_tab,
    collect_projects_tab,
)
from aiib_crawler.config import Config
from aiib_crawler.storage import CheckpointState, Storage

logger = logging.getLogger(__name__)


class AIIBCrawler:
    """管理 HTTP 会话、断点状态与多模块顺序抓取。"""

    def __init__(self, config: Config, storage: Storage) -> None:
        self.config = config
        self.storage = storage

    def run(self, state: CheckpointState) -> dict[str, int]:
        """按配置顺序抓取各模块，并在结束后生成印度参与度与策略偏好量化画像。"""
        counts: dict[str, int] = {}

        with httpx.Client(
            headers=DEFAULT_HEADERS,
            follow_redirects=True,
            timeout=35.0,
        ) as client:
            for tab in self.config.tabs:
                if (
                    tab != "projects"
                    and tab in state.completed_tabs
                    and self.config.mode == "resume"
                    and self.config.download_pdfs == "none"
                ):
                    existing = self.storage.load_tab_records(tab)
                    counts[tab] = len(existing)
                    logger.info("[*] 模块 [%s] 在上次运行中已完成（共 %d 条记录），跳过", tab, len(existing))
                    continue

                if tab == "projects":
                    records = collect_projects_tab(client, self.config, self.storage, state)
                elif tab == "procurement":
                    records = collect_procurement_tab(client, self.config, self.storage, state)
                elif tab == "governance":
                    records = collect_governance_tab(client, self.config, self.storage, state)
                elif tab == "accountability":
                    records = collect_accountability_tab(client, self.config, self.storage, state)
                else:
                    logger.warning("[!] 未知模块 [%s]，跳过", tab)
                    continue

                counts[tab] = len(records)
                state.completed_tabs.add(tab)
                self.storage.save_state(state)

        self._build_india_quantitative_profile()
        return counts

    def _build_india_quantitative_profile(self) -> None:
        """基于已采集的四维数据集，自动计算印度在亚投行的参与度、态度与偏好策略核心量化指标。"""
        profile: dict[str, Any] = {}

        # 1. 项目与资金维度 (Projects & Financing)
        all_projects_path = self.storage.dataset_file("projects", "all_projects_summary")
        if all_projects_path.exists():
            all_projects = self.storage.load_records(all_projects_path)
            approved_all = [p for p in all_projects if str(p.get("status")).lower() == "approved"]
            india_approved = [p for p in approved_all if str(p.get("economy")).lower() == "india"]

            total_approved_usd = sum(float(p.get("approved_funding_usd_millions") or 0.0) for p in approved_all)
            india_approved_usd = sum(float(p.get("approved_funding_usd_millions") or 0.0) for p in india_approved)

            by_year: dict[str, dict[str, Any]] = {}
            for p in india_approved:
                yr = str(p.get("approval_year") or "Unknown")
                entry = by_year.setdefault(
                    yr, {"project_count": 0, "approved_usd_millions": 0.0, "sovereign_count": 0, "nonsovereign_count": 0}
                )
                entry["project_count"] += 1
                entry["approved_usd_millions"] = round(
                    entry["approved_usd_millions"] + float(p.get("approved_funding_usd_millions") or 0.0), 2
                )
                if str(p.get("financing_type")).lower() == "sovereign":
                    entry["sovereign_count"] += 1
                else:
                    entry["nonsovereign_count"] += 1

            sector_dist: dict[str, dict[str, Any]] = {}
            for p in india_approved:
                sec = str(p.get("sector") or "Other")
                s_entry = sector_dist.setdefault(sec, {"project_count": 0, "approved_usd_millions": 0.0})
                s_entry["project_count"] += 1
                s_entry["approved_usd_millions"] = round(
                    s_entry["approved_usd_millions"] + float(p.get("approved_funding_usd_millions") or 0.0), 2
                )

            profile["projects_overview"] = {
                "bank_total_approved_projects": len(approved_all),
                "bank_total_approved_usd_millions": round(total_approved_usd, 2),
                "india_approved_projects": len(india_approved),
                "india_approved_usd_millions": round(india_approved_usd, 2),
                "india_project_count_share_percent": round(len(india_approved) * 100.0 / max(1, len(approved_all)), 2),
                "india_funding_share_percent": round(india_approved_usd * 100.0 / max(1.0, total_approved_usd), 2),
                "india_sovereign_projects": sum(1 for p in india_approved if str(p.get("financing_type")).lower() == "sovereign"),
                "india_nonsovereign_projects": sum(1 for p in india_approved if str(p.get("financing_type")).lower() != "sovereign"),
                "india_standalone_projects": sum(1 for p in india_approved if str(p.get("project_type")).lower() == "stand-alone"),
                "india_cofinanced_projects_in_list": sum(1 for p in india_approved if str(p.get("project_type")).lower() == "cofinanced"),
                "india_annual_trend": dict(sorted(by_year.items())),
                "india_sector_distribution": sector_dist,
            }

        # 2. 印度项目详情页深度指标（联合融资伙伴、环境社会政策适用、转贷比例、次国家邦分布、审批周期）
        india_details_path = self.storage.dataset_file("projects", "india_project_details")
        if india_details_path.exists():
            india_details = self.storage.load_records(india_details_path)
            if india_details:
                state_counter: Counter[str] = Counter()
                cofin_counter: Counter[str] = Counter()
                es_cat_counter: Counter[str] = Counter()
                policy_counter: Counter[str] = Counter()
                lags: list[int] = []

                for d in india_details:
                    for st in d.get("indian_states", []):
                        state_counter[st] += 1
                    for cf in d.get("cofinanciers", []):
                        cofin_counter[cf] += 1
                    es_cat = str(d.get("es_category") or "Unspecified")
                    es_cat_counter[es_cat] += 1
                    policy_counter[str(d.get("applicable_es_policy") or "AIIB ESP")] += 1
                    lag = d.get("approval_lag_days")
                    if isinstance(lag, int) and lag >= 0:
                        lags.append(lag)

                profile["india_project_details_analysis"] = {
                    "analyzed_india_detail_pages": len(india_details),
                    "fi_or_onlending_count": sum(1 for d in india_details if d.get("is_fi_onlending")),
                    "cofinanced_detected_count": sum(1 for d in india_details if d.get("is_cofinanced")),
                    "cofinancier_breakdown": dict(cofin_counter.most_common()),
                    "es_category_breakdown": dict(es_cat_counter.most_common()),
                    "applicable_es_policy_breakdown": dict(policy_counter.most_common()),
                    "indian_states_distribution": dict(state_counter.most_common()),
                    "approval_lag_days_avg": round(sum(lags) / len(lags), 1) if lags else None,
                    "approval_lag_days_median": sorted(lags)[len(lags) // 2] if lags else None,
                    "approval_lag_sample_size": len(lags),
                }

        # 3. 治理与投票权维度 (Governance & Leverage Ratio)
        voting_path = self.storage.dataset_file("governance", "members_voting_power")
        if voting_path.exists():
            import json

            voting_data = json.loads(voting_path.read_text(encoding="utf-8"))
            members = voting_data.get("members", [])
            top_5 = sorted(members, key=lambda m: float(m.get("voting_power_percent") or 0.0), reverse=True)[:5]
            india_member = next((m for m in members if str(m.get("economy")).lower() == "india"), None)
            if india_member:
                sub_pct = float(india_member.get("subscription_percent") or 0.0)
                vote_pct = float(india_member.get("voting_power_percent") or 0.0)
                fund_pct = float(profile.get("projects_overview", {}).get("india_funding_share_percent") or 0.0)
                profile["governance_and_leverage"] = {
                    "voting_power_update_date": voting_data.get("update_date"),
                    "india_subscription_usd_millions": india_member.get("subscription_amount_usd_millions"),
                    "india_subscription_share_percent": sub_pct,
                    "india_voting_power_votes": india_member.get("voting_power_votes"),
                    "india_voting_power_share_percent": vote_pct,
                    "india_loan_to_equity_leverage_ratio": round(fund_pct / sub_pct, 3) if sub_pct > 0 else None,
                    "india_loan_to_voting_power_ratio": round(fund_pct / vote_pct, 3) if vote_pct > 0 else None,
                    "top_5_shareholders": top_5,
                }

        # 4. 问责机制与评估维度 (Accountability & PPM)
        ppm_path = self.storage.dataset_file("accountability", "ppm_submissions_all")
        if ppm_path.exists():
            ppm_all = self.storage.load_records(ppm_path)
            ppm_india = [c for c in ppm_all if str(c.get("economy")).lower() == "india"]
            ppm_by_member = Counter(str(c.get("economy") or "Unknown") for c in ppm_all)
            profile["accountability_and_es_friction"] = {
                "bank_total_ppm_submissions": len(ppm_all),
                "india_ppm_submissions": len(ppm_india),
                "india_ppm_share_percent": round(len(ppm_india) * 100.0 / max(1, len(ppm_all)), 2),
                "ppm_submissions_by_economy": dict(ppm_by_member.most_common()),
                "india_dropped_pipeline_projects_in_ppm": [
                    c.get("project_name") for c in ppm_india if c.get("is_project_dropped_from_pipeline")
                ],
            }

        if profile:
            from aiib_crawler.storage import atomic_write_json

            target = self.storage.data_dir / "india_quantitative_profile.json"
            atomic_write_json(target, profile)
            logger.info("[+] 已生成印度参与度与策略偏好量化画像: %s", target)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成第三章《印度在亚投行制度与治理中的影响力》全部图表 (300 DPI)
严格遵循精简视觉规范：
1. 多子图一律采用上下垂直排列 (nrows=2, ncols=1)；
2. 剔除图表内的长句文字解释，仅保留核心数据标签与极简机制节点（标题 + 简短关键词/指标 + 判定菱形 + 箭头）；
3. 禁用 matplotlib 默认的 $...$ 数学公式解析 (text.parse_math = False)。
"""

import os
import json
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

# 全局字体与渲染配置
matplotlib.rcParams["font.sans-serif"] = [
    "PingFang SC",
    "Heiti TC",
    "STHeiti",
    "Songti SC",
    "Arial Unicode MS",
    "DejaVu Sans",
]
matplotlib.rcParams["axes.unicode_minus"] = False
matplotlib.rcParams["text.parse_math"] = False
matplotlib.rcParams["figure.dpi"] = 300
matplotlib.rcParams["savefig.dpi"] = 300

OUT_DIR = "reports/figures"
os.makedirs(OUT_DIR, exist_ok=True)

# 统一学术配色方案
C_NAVY = "#1B365D"       # 深海蓝
C_BLUE = "#2874A6"       # 中海蓝
C_RED = "#C0392B"        # 砖红（突出印度）
C_TEAL = "#2E8B57"       # 森林绿
C_AMBER = "#D68910"      # 琥珀金
C_PURPLE = "#6C3483"     # 深紫
C_SLATE = "#5D6D7E"      # 蓝灰
C_CARD_BLUE = "#EFF6FF"
C_CARD_RED = "#FDEDEC"
C_CARD_GREEN = "#E8F8F5"
C_CARD_GOLD = "#FEF9E7"
C_CARD_PURPLE = "#F5EEF8"
C_BORDER = "#CBD5E1"


def draw_card(ax, x, y, w, h, title, body="", header_fc=C_NAVY, body_fc="#F8FAFC",
              ec=C_NAVY, lw=1.5, title_fs=11.2, body_fs=10.0, header_ratio=0.38,
              title_color="white", body_color="#0F172A"):
    """绘制与第一章风格一致的精简标题卡片（居中短词，无长句段落）"""
    if not body:
        box = FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.003,rounding_size=0.012",
            facecolor=header_fc, edgecolor=ec, linewidth=lw, zorder=3
        )
        ax.add_patch(box)
        ax.text(
            x + w / 2, y + h / 2, title,
            ha="center", va="center", fontsize=title_fs,
            fontweight="bold", color=title_color, linespacing=1.25, zorder=4
        )
        return

    hh = h * header_ratio
    bh = h - hh

    body_box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.002,rounding_size=0.012",
        facecolor=body_fc, edgecolor=ec, linewidth=lw, zorder=2
    )
    ax.add_patch(body_box)

    header_box = FancyBboxPatch(
        (x, y + bh), w, hh,
        boxstyle="round,pad=0.002,rounding_size=0.012",
        facecolor=header_fc, edgecolor=ec, linewidth=lw, zorder=3
    )
    ax.add_patch(header_box)

    ax.text(
        x + w / 2, y + bh + hh / 2, title,
        ha="center", va="center", fontsize=title_fs,
        fontweight="bold", color=title_color, linespacing=1.18, zorder=4
    )
    ax.text(
        x + w / 2, y + bh / 2, body,
        ha="center", va="center", fontsize=body_fs,
        color=body_color, linespacing=1.32, zorder=4
    )


def draw_zone(ax, x, y, w, h, label="", fc="#F8FAFC", ec="#94A3B8", lw=1.2, ls="--",
              label_color="#1E293B", fontsize=11.0):
    """绘制浅色虚线分区背景框"""
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.004,rounding_size=0.015",
        facecolor=fc, edgecolor=ec, linewidth=lw, linestyle=ls, zorder=1
    )
    ax.add_patch(box)
    if label:
        ax.text(
            x + w / 2, y + h - 0.028, label,
            ha="center", va="center", fontsize=fontsize,
            fontweight="bold", color=label_color, zorder=2
        )


def draw_diamond(ax, cx, cy, w, h, text, fc="#FEF3C7", ec="#B45309", lw=1.6,
                 fontsize=10.2, textcolor="#78350F"):
    """绘制决策判定菱形节点"""
    pts = [(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)]
    poly = Polygon(pts, closed=True, facecolor=fc, edgecolor=ec, linewidth=lw, zorder=3)
    ax.add_patch(poly)
    ax.text(
        cx, cy, text,
        ha="center", va="center", fontsize=fontsize,
        fontweight="bold", color=textcolor, linespacing=1.22, zorder=4
    )


def draw_arrow(ax, x1, y1, x2, y2, color="#334155", lw=1.8, style="-|>",
               linestyle="-", label="", label_pos=None, fontsize=9.5):
    """绘制简洁连接箭头"""
    ax.annotate(
        "", xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(
            arrowstyle=style, color=color, lw=lw, linestyle=linestyle,
            shrinkA=0, shrinkB=0, mutation_scale=13
        ),
        zorder=5
    )
    if label:
        lx, ly = label_pos if label_pos else ((x1 + x2) / 2, (y1 + y2) / 2)
        ax.text(
            lx, ly, label,
            ha="center", va="center", fontsize=fontsize, color=color, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.18", fc="white", ec=color, lw=0.8, alpha=0.96),
            zorder=6
        )


# ==============================================================================
# 图 3-1：亚投行前十大股东股本投票权对比与董事会12个选区结构图（上下排列，极简标签）
# ==============================================================================
def generate_fig3_1():
    with open("data/governance/members_voting_power.json") as f:
        mvp = json.load(f)
    with open("data/governance/board_of_directors_constituencies.json") as f:
        bdc = json.load(f)

    cn_name_map = {
        "China": "中国 (域内)",
        "India": "印度 (域内)",
        "Russia": "俄罗斯 (域内)",
        "Germany": "德国 (域外)",
        "Korea": "韩国 (域内)",
        "Australia": "澳大利亚 (域内)",
        "France": "法国 (域外)",
        "Indonesia": "印度尼西亚 (域内)",
        "United Kingdom": "英国 (域外)",
        "Türkiye": "土耳其 (域内)",
    }
    members_sorted = sorted(
        mvp["members"],
        key=lambda x: x["subscription_amount_usd_millions"] or 0,
        reverse=True
    )[:10]

    member_map = {m["economy"]: m for m in mvp["members"]}
    const_list = []
    const_label_map = {
        5: "第5选区 (中国等)",
        9: "第9选区 (德/法/意等)",
        4: "第4选区 (俄/哈/伊等)",
        10: "第10选区 (印度独占)",
        8: "第8选区 (英/波/丹等)",
        7: "第7选区 (澳/新/新等)",
        12: "第12选区 (韩/乌/以等)",
        1: "第1选区 (沙/阿/卡等)",
        2: "第2选区 (土/巴/阿等)",
        6: "第6选区 (埃/巴/阿等)",
        11: "第11选区 (印/柬/孟等)",
        3: "第3选区 (菲/马/泰等)",
    }
    for c in bdc:
        idx = c["constituency_index"]
        m_list = c["constituency_members"]
        sub_cap = sum(member_map.get(m, {}).get("subscription_amount_usd_millions") or 0 for m in m_list)
        vp_pct = sum(member_map.get(m, {}).get("voting_power_percent") or 0 for m in m_list)
        const_list.append({
            "idx": idx,
            "label": const_label_map.get(idx, f"第{idx}选区"),
            "members_count": len(m_list),
            "sub_cap": sub_cap,
            "vp_pct": vp_pct,
            "is_india": (idx == 10),
            "is_china": (idx == 5),
        })
    const_list.sort(key=lambda x: x["vp_pct"], reverse=True)

    fig, (ax1, ax2) = plt.subplots(
        nrows=2, ncols=1, figsize=(12.5, 13.0),
        gridspec_kw={"height_ratios": [1.0, 1.12], "hspace": 0.28}
    )
    fig.patch.set_facecolor("#FFFFFF")

    # ---- 子图 (a)：前十大成员认缴股本占比 vs 投票权占比 ----
    y1 = np.arange(len(members_sorted))[::-1]
    labels1 = [cn_name_map.get(m["economy"], m["economy"]) for m in members_sorted]
    cap_pcts = [m["subscription_percent"] for m in members_sorted]
    vp_pcts = [m["voting_power_percent"] for m in members_sorted]

    bar_h = 0.36
    ax1.barh(
        y1 + bar_h / 2, cap_pcts, height=bar_h,
        color=["#E74C3C" if m["economy"] == "India" else "#5499C7" for m in members_sorted],
        alpha=0.88, label="认缴股本占比 (%)"
    )
    ax1.barh(
        y1 - bar_h / 2, vp_pcts, height=bar_h,
        color=[C_RED if m["economy"] == "India" else C_NAVY for m in members_sorted],
        label="投票权占比 (%)"
    )

    for i, (cp, vp, m) in enumerate(zip(cap_pcts, vp_pcts, members_sorted)):
        yi = y1[i]
        is_ind = (m["economy"] == "India")
        fw = "bold" if is_ind or m["economy"] == "China" else "normal"
        col = C_RED if is_ind else "#1C2833"
        ax1.text(
            max(cp, vp) + 0.4, yi,
            f"股本 {cp:.2f}%  |  投票权 {vp:.2f}%",
            va="center", ha="left", fontsize=10.5, fontweight=fw, color=col
        )

    ax1.axvline(15.0, color=C_AMBER, linestyle="--", linewidth=1.8, zorder=2)
    ax1.text(15.25, 0.6, "15% 超级多数否决线", color="#9A6309", fontsize=10.2, fontweight="bold")

    ax1.axvline(25.0, color=C_RED, linestyle=":", linewidth=1.8, zorder=2)
    ax1.text(25.25, 0.6, "25% 特定多数否决线", color=C_RED, fontsize=10.2, fontweight="bold")

    ax1.set_yticks(y1)
    ax1.set_yticklabels(labels1, fontsize=11.2, fontweight="bold")
    for tick_label, m in zip(ax1.get_yticklabels(), members_sorted):
        if m["economy"] == "India":
            tick_label.set_color(C_RED)
    ax1.set_xlim(0, 39.5)
    ax1.set_xlabel("占全行总额比例 (%)", fontsize=11.2, fontweight="bold")
    ax1.set_title(
        "(a) 亚投行前十大股东成员认缴股本占比与投票权占比",
        fontsize=13.2, fontweight="bold", color=C_NAVY, pad=10, loc="left"
    )
    ax1.grid(axis="x", linestyle="--", alpha=0.4)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.legend(loc="lower right", fontsize=10.8, frameon=True, facecolor="#FFFFFF", edgecolor=C_BORDER)

    # ---- 子图 (b)：董事会12个选区合并投票权占比与成员数量 ----
    y2 = np.arange(len(const_list))[::-1]
    c_labels = [c["label"] for c in const_list]
    c_vp = [c["vp_pct"] for c in const_list]
    c_colors = [C_RED if c["is_india"] else (C_NAVY if c["is_china"] else C_SLATE) for c in const_list]

    ax2.barh(y2, c_vp, height=0.60, color=c_colors, alpha=0.92)

    for i, c in enumerate(const_list):
        yi = y2[i]
        vp = c["vp_pct"]
        mc = c["members_count"]
        if c["is_india"]:
            txt = f"{vp:.2f}%  |  1个成员国 ★ 全行唯一单一主权国家选区（永久独立委派正副董事）"
            ax2.text(vp + 0.4, yi, txt, va="center", ha="left", fontsize=10.5, fontweight="bold", color=C_RED)
        elif c["is_china"]:
            txt = f"{vp:.2f}%  |  {mc}个成员（中国大陆、中国香港）"
            ax2.text(vp + 0.4, yi, txt, va="center", ha="left", fontsize=10.5, fontweight="bold", color=C_NAVY)
        else:
            txt = f"{vp:.2f}%  |  {mc}个成员国（多国轮值）"
            ax2.text(vp + 0.4, yi, txt, va="center", ha="left", fontsize=10.3, color="#2C3E50")

    ax2.set_yticks(y2)
    ax2.set_yticklabels(c_labels, fontsize=11.0, fontweight="bold")
    for tick_label, c in zip(ax2.get_yticklabels(), const_list):
        if c["is_india"]:
            tick_label.set_color(C_RED)
        elif c["is_china"]:
            tick_label.set_color(C_NAVY)

    ax2.set_xlim(0, 39.5)
    ax2.set_xlabel("选区合并投票权占比 (%)", fontsize=11.2, fontweight="bold")
    ax2.set_title(
        "(b) 亚投行董事会 12 个选区（Constituencies）合并投票权占比与包含成员数量",
        fontsize=13.2, fontweight="bold", color=C_NAVY, pad=10, loc="left"
    )
    ax2.grid(axis="x", linestyle="--", alpha=0.4)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    out_path = os.path.join(OUT_DIR, "fig3_1_voting_and_constituencies.png")
    plt.savefig(out_path, bbox_inches="tight", facecolor="#FFFFFF")
    plt.close(fig)
    print("Saved:", out_path)


# ==============================================================================
# 图 3-2：印度在亚投行三层治理架构中的席位配置与副行长任期对照图（上下双面板，极简流程图+时间轴）
# ==============================================================================
def generate_fig3_2():
    fig = plt.figure(figsize=(13.0, 12.5), facecolor="#FFFFFF")
    gs = fig.add_gridspec(nrows=2, ncols=1, height_ratios=[0.92, 1.15], hspace=0.25)

    # ---- 面板 (a)：印度在亚投行三层治理架构中的席位配置与立项闭环（极简节点流程图） ----
    ax1 = fig.add_subplot(gs[0])
    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis("off")

    ax1.text(
        0.0, 0.96,
        "(a) 印度在亚投行三层治理架构中的席位嵌入与业务传导机制",
        fontsize=13.5, fontweight="bold", color=C_NAVY, ha="left", va="top"
    )

    draw_zone(ax1, 0.01, 0.04, 0.28, 0.84, "印度国内主管机关", fc="#F8FAFC", ec="#94A3B8", fontsize=11.0)
    draw_zone(ax1, 0.33, 0.04, 0.66, 0.84, "亚投行三层治理与业务部门（印度席位配置）", fc="#F8FAFC", ec="#94A3B8", fontsize=11.0)

    # 左侧：印度财政部节点
    draw_card(
        ax1, 0.03, 0.48, 0.24, 0.28,
        "印度联邦财政部\n(经济事务署 DEA)",
        "筛选国内基建项目库\n直接委派理事与执董\n推荐高管候选人",
        header_fc=C_RED, body_fc=C_CARD_RED, ec=C_RED, header_ratio=0.38, title_fs=11.0, body_fs=9.8
    )
    draw_card(
        ax1, 0.03, 0.10, 0.24, 0.24,
        "印度本土实施机构\n(PGCIL / 各邦地铁局)",
        "负责项目申报、编制标书\n与主导采购评标授标",
        header_fc="#922B21", body_fc=C_CARD_RED, ec="#922B21", header_ratio=0.40, title_fs=10.5, body_fs=9.6
    )
    draw_arrow(ax1, 0.15, 0.48, 0.15, 0.34, label="转贷/监管", color=C_RED, fontsize=9.0)

    # 右侧三层卡片
    draw_card(
        ax1, 0.36, 0.62, 0.28, 0.20,
        "第一层：理事会席位",
        "印度财长任理事 · 7.53% 投票权\n2017–2018主席国 · 2018孟买年会",
        header_fc=C_NAVY, body_fc=C_CARD_BLUE, ec=C_NAVY, header_ratio=0.38, title_fs=11.0, body_fs=9.5
    )
    draw_card(
        ax1, 0.68, 0.62, 0.28, 0.20,
        "第二层：董事会第10选区",
        "唯一“一国一区”（成员数=1）\n常驻正副执董 · 无需多国轮值",
        header_fc=C_RED, body_fc=C_CARD_RED, ec=C_RED, header_ratio=0.38, title_fs=11.0, body_fs=9.5
    )
    draw_card(
        ax1, 0.36, 0.34, 0.60, 0.20,
        "第三层：管理层核心业务副行长（2016—2026 连续十年占位）",
        "D. J. Pandian (CIO/第一区域) → Urjit Patel (第一区域) → R. Misra → A. B. Pandey (投资方案)\n直管南亚/东南亚投资立项、行业方案及环境社会与采购受托合规",
        header_fc=C_TEAL, body_fc=C_CARD_GREEN, ec=C_TEAL, header_ratio=0.38, title_fs=11.0, body_fs=9.5
    )
    draw_card(
        ax1, 0.36, 0.08, 0.28, 0.18,
        "第一区域投资业务局 (DG)",
        "负责南亚项目初筛、尽调\n与贷款谈判（印籍局长）",
        header_fc=C_BLUE, body_fc=C_CARD_BLUE, ec=C_BLUE, header_ratio=0.40, title_fs=10.5, body_fs=9.3
    )
    draw_card(
        ax1, 0.68, 0.08, 0.28, 0.18,
        "可持续与受托局 / CEIU",
        "环社框架(ESF)、采购审查\n及 PPM 问责机制分流",
        header_fc=C_PURPLE, body_fc=C_CARD_PURPLE, ec=C_PURPLE, header_ratio=0.40, title_fs=10.5, body_fs=9.3
    )

    # 连接箭头
    draw_arrow(ax1, 0.27, 0.68, 0.36, 0.72, label="委派理事", color=C_NAVY, fontsize=8.8)
    draw_arrow(ax1, 0.64, 0.72, 0.68, 0.72, label="授权", color=C_NAVY, fontsize=8.8)
    draw_arrow(ax1, 0.82, 0.62, 0.82, 0.54, label="共识审批", color=C_RED, fontsize=8.8)
    draw_arrow(ax1, 0.50, 0.34, 0.50, 0.26, label="分管直辖", color=C_TEAL, fontsize=8.8)
    draw_arrow(ax1, 0.27, 0.20, 0.36, 0.17, label="项目对接", color=C_BLUE, fontsize=8.8)

    # ---- 面板 (b)：2016—2026年印度籍副行长任期甘特条 vs 年度获批规模 ----
    ax2 = fig.add_subplot(gs[1])

    years = np.arange(2016, 2027)
    ind_amt = [100.0, 1279.0, 955.0, 625.0, 2100.0, 2642.51, 1694.50, 1836.0, 882.22, 1344.50, 992.0]
    ind_cnt = [1, 4, 3, 4, 8, 12, 5, 5, 6, 8, 4]

    ax2.bar(
        years, ind_amt, width=0.55,
        color=[C_NAVY if y <= 2021 else (C_TEAL if y <= 2023 else C_AMBER if y == 2024 else C_RED) for y in years],
        alpha=0.86, edgecolor="#1C2833", linewidth=0.8, zorder=3
    )

    for y, amt, cnt in zip(years, ind_amt, ind_cnt):
        ax2.text(
            y, amt + 55, f"${amt:,.0f}M\n({cnt}项)",
            ha="center", va="bottom", fontsize=9.8, fontweight="bold", color="#1C2833", zorder=5
        )

    # 顶部单排甘特时间轴带 (y: 3100 -> 3950)，仅放精简人名、任期与职务，严丝合缝对应年份轴！
    gantt_bands = [
        (2015.55, 2021.48, "D. J. Pandian (2016.02–2022.01)\n副行长兼CIO / 第一区域副行长\n[任内获批 32 项 · $7,701.5M]", C_NAVY, C_CARD_BLUE),
        (2021.52, 2023.48, "Urjit Patel\n(2022.02–2024.01)\n第一区域副行长\n[10项 · $3,530.5M]", C_TEAL, C_CARD_GREEN),
        (2023.52, 2024.48, "R. Misra\n(2024–25.03)\n代副行长\n[6项·$882M]", C_AMBER, C_CARD_GOLD),
        (2024.52, 2026.45, "A. B. Pandey\n(2025.04–至今)\n投资方案副行长\n[12项 · $2,336.5M]", C_RED, C_CARD_RED),
    ]
    for x0, x1, txt, col, fill in gantt_bands:
        w = x1 - x0
        box = FancyBboxPatch(
            (x0, 3100), w, 920,
            boxstyle="round,pad=0.01,rounding_size=0.06",
            facecolor=fill, edgecolor=col, linewidth=1.6, zorder=4
        )
        ax2.add_patch(box)
        ax2.text(
            x0 + w / 2, 3100 + 460, txt,
            ha="center", va="center", fontsize=9.6, fontweight="bold",
            color=col, linespacing=1.28, zorder=5
        )

    for xv in [2021.5, 2023.5, 2024.5]:
        ax2.axvline(xv, color="#64748B", linestyle="--", linewidth=1.3, ymin=0, ymax=0.75, zorder=2)

    ax2.set_xticks(years)
    ax2.set_xticklabels([f"{y}年" if y < 2026 else "2026年\n(1-3月)" for y in years], fontsize=10.8, fontweight="bold")
    ax2.set_xlim(2015.4, 2026.6)
    ax2.set_ylim(0, 4250)
    ax2.set_yticks([0, 1000, 2000, 3000])
    ax2.set_ylabel("印度年度获批金额 ($M)", fontsize=11.2, fontweight="bold")
    ax2.set_title(
        "(b) 2016—2026 年印度籍副行长连续任期时间轴与印度项目年度获批规模",
        fontsize=13.2, fontweight="bold", color=C_NAVY, pad=10, loc="left"
    )
    ax2.grid(axis="y", linestyle="--", alpha=0.4)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    out_path = os.path.join(OUT_DIR, "fig3_2_governance_and_vp_timeline.png")
    plt.savefig(out_path, bbox_inches="tight", facecolor="#FFFFFF")
    plt.close(fig)
    print("Saved:", out_path)


# ==============================================================================
# 图 3-3：亚投行项目受影响人群机制（PPM）案件国别占比与印度案件分流机制图（上下双面板，极简流程图）
# ==============================================================================
def generate_fig3_3():
    fig = plt.figure(figsize=(12.8, 11.2), facecolor="#FFFFFF")
    gs = fig.add_gridspec(nrows=2, ncols=1, height_ratios=[0.72, 1.28], hspace=0.28)

    # ---- 子图 (a)：PPM 申诉案件中印度的占比对比 ----
    ax1 = fig.add_subplot(gs[0])

    categories = [
        "公开登记案件\n(共 7 起)",
        "收到直接申诉\n(共 45 起)"
    ]
    y = np.arange(len(categories))
    india_shares = [5 / 7 * 100.0, 14 / 45 * 100.0]
    other_shares = [2 / 7 * 100.0, 31 / 45 * 100.0]
    india_counts = [5, 14]
    other_counts = [2, 31]

    bar_h = 0.44
    ax1.barh(y, india_shares, height=bar_h, color=C_RED, alpha=0.92, label="印度项目申诉")
    ax1.barh(y, other_shares, left=india_shares, height=bar_h, color=C_SLATE, alpha=0.82, label="其他成员国项目申诉")

    for i in range(len(categories)):
        ax1.text(
            india_shares[i] / 2, y[i],
            f"印度: {india_counts[i]} 起 ({india_shares[i]:.1f}%)",
            ha="center", va="center", color="#FFFFFF", fontsize=11.2, fontweight="bold"
        )
        other_label = (
            f"其他成员国: {other_counts[i]} 起 ({other_shares[i]:.1f}%)\n[孟加拉国 1 起、印尼 1 起]"
            if i == 0 else
            f"其他成员国及多国项目: {other_counts[i]} 起 ({other_shares[i]:.1f}%)"
        )
        ax1.text(
            india_shares[i] + other_shares[i] / 2, y[i],
            other_label,
            ha="center", va="center", color="#FFFFFF", fontsize=10.8, fontweight="bold"
        )

    ax1.set_yticks(y)
    ax1.set_yticklabels(categories, fontsize=11.5, fontweight="bold", color=C_NAVY)
    ax1.set_xlim(0, 100)
    ax1.set_xlabel("占全行问责申诉总数比例 (%)", fontsize=11.2, fontweight="bold")
    ax1.set_title(
        "(a) 亚投行项目受影响人群机制（PPM）历史申诉中的印度占比（2019—2025年）",
        fontsize=13.2, fontweight="bold", color=C_NAVY, pad=10, loc="left"
    )
    ax1.grid(axis="x", linestyle="--", alpha=0.4)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.legend(loc="upper right", fontsize=10.8, frameon=True, facecolor="#FFFFFF", edgecolor=C_BORDER)

    # ---- 子图 (b)：印度 5 起公开登记案件的制度过滤与分流机制流程图（菱形判定 + 极简卡片） ----
    ax2 = fig.add_subplot(gs[1])
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    ax2.axis("off")

    ax2.text(
        0.0, 0.96,
        "(b) 印度项目 PPM 申诉双重过滤与联合融资移交分流机制",
        fontsize=13.2, fontweight="bold", color=C_NAVY, ha="left", va="top"
    )

    # 输入节点
    draw_card(
        ax2, 0.02, 0.36, 0.20, 0.30,
        "印度项目登记申诉\n（共 5 起案件）",
        "• 安得拉邦供水 (000078)\n• 安得拉邦道路 (000085)\n• 亚穆纳河运河太阳能\n• 钦奈地铁二期 (2023)\n• 钦奈地铁二期 (2025)",
        header_fc=C_NAVY, body_fc=C_CARD_BLUE, ec=C_NAVY, header_ratio=0.32, title_fs=10.8, body_fs=9.3
    )

    # 第一道判定菱形：是否联合融资
    draw_diamond(
        ax2, 0.36, 0.52, 0.22, 0.32,
        "第一道过滤\n世行/亚开行\n牵头联合融资？\n(政策第2.1.1条)",
        fc=C_CARD_GOLD, ec=C_AMBER, fontsize=9.5
    )
    draw_arrow(ax2, 0.22, 0.52, 0.25, 0.52, color=C_NAVY)

    # 分支 1：是 -> 移交牵头行（右上卡片）
    draw_card(
        ax2, 0.66, 0.66, 0.32, 0.22,
        "分流路径一：移交牵头行（3起 / 60%）",
        "适用世行检验组规则 · 亚投行免于调查\n[安得拉供水、安得拉道路、亚穆纳太阳能]",
        header_fc=C_TEAL, body_fc=C_CARD_GREEN, ec=C_TEAL, header_ratio=0.38, title_fs=10.8, body_fs=9.5
    )
    draw_arrow(ax2, 0.36, 0.68, 0.66, 0.77, label="是 (联合融资)", color=C_TEAL, fontsize=9.3)

    # 第二道判定菱形：是否完成事先真诚沟通
    draw_diamond(
        ax2, 0.50, 0.23, 0.22, 0.32,
        "第二道过滤\n已完成项目GRM\n与管理层事先沟通？\n(前置受理条件)",
        fc=C_CARD_GOLD, ec=C_AMBER, fontsize=9.5
    )
    draw_arrow(ax2, 0.36, 0.36, 0.39, 0.23, label="否 (独立融资)", color=C_RED, fontsize=9.3)

    # 分支 2：否 -> 驳回不予受理（右中卡片）
    draw_card(
        ax2, 0.66, 0.36, 0.32, 0.22,
        "分流路径二：裁定不受理（1起 / 20%）",
        "未履行前置沟通程序 · 直接驳回\n[2023年钦奈地铁二期首次申诉]",
        header_fc=C_AMBER, body_fc=C_CARD_GOLD, ec=C_AMBER, header_ratio=0.38, title_fs=10.8, body_fs=9.5
    )
    draw_arrow(ax2, 0.61, 0.28, 0.66, 0.47, label="未完成", color=C_AMBER, fontsize=9.2)

    # 分支 3：是 -> 进入正式合规审查（右下卡片）
    draw_card(
        ax2, 0.66, 0.06, 0.32, 0.22,
        "分流路径三：正式合规审查（1起 / 20%）",
        "独立主权贷款 · 2025年10月启动审查\n[2025年钦奈地铁二期二次申诉 · 未停工]",
        header_fc=C_RED, body_fc=C_CARD_RED, ec=C_RED, header_ratio=0.38, title_fs=10.8, body_fs=9.5
    )
    draw_arrow(ax2, 0.61, 0.18, 0.66, 0.17, label="已完成", color=C_RED, fontsize=9.2)

    out_path = os.path.join(OUT_DIR, "fig3_3_ppm_accountability_india.png")
    plt.savefig(out_path, bbox_inches="tight", facecolor="#FFFFFF")
    plt.close(fig)
    print("Saved:", out_path)


# ==============================================================================
# 图 3-4：亚投行制度规则塑造印度参与结果的六大传导机制图（极简三列节点流向图，无长句）
# ==============================================================================
def generate_fig3_4():
    fig, ax = plt.subplots(figsize=(13.8, 12.2), facecolor="#FFFFFF")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.5, 0.975,
        "亚投行制度条款与治理机制塑造印度参与结果的传导路径图",
        fontsize=14.2, fontweight="bold", color=C_NAVY, ha="center", va="top"
    )

    draw_zone(ax, 0.01, 0.02, 0.30, 0.91, "第一列：亚投行法定制度条款", fc="#F8FAFC", ec="#94A3B8", fontsize=11.2)
    draw_zone(ax, 0.35, 0.02, 0.30, 0.91, "第二列：治理与执行传导机制", fc="#F8FAFC", ec="#94A3B8", fontsize=11.2)
    draw_zone(ax, 0.69, 0.02, 0.30, 0.91, "第三列：第二章实证参与结果", fc="#F8FAFC", ec="#94A3B8", fontsize=11.2)

    rows = [
        (
            "《协定》第11/13条 · 国别限额",
            "出资与贷款配额脱钩（申请驱动）\n超大域内成员享最高档敞口上限",
            "人事占位 + 大股东借款克制",
            "独占第10选区 + 印籍副行长直管\n中国主动克制借款释放信贷空间",
            "稳居第一大借款国（撬动比最高）",
            "获批 60 项 · $144.51亿 (18.42%)\n认缴撬动 1.73倍 · 实缴撬动 8.64倍",
            C_NAVY, C_CARD_BLUE
        ),
        (
            "《协定》第27/31条 · 采购第5.3条",
            "禁止政治干预 · 仅考量经济标准\n联合融资直接适用牵头行规则",
            "无记名共识制 + 牵头行委托脱敏",
            "26.37%否决权不适用日常项目审批\n委托世行/亚开行监管消除双边摩擦",
            "2020年后逆势达峰 · 92%联合融资",
            "2020–2022获批 $57.60亿 (占39.9%)\n2020–2021联合融资占比达 92.19%",
            C_RED, C_CARD_RED
        ),
        (
            "《协定》第13条 · 《问责框架》",
            "允许无主权担保私营与基金投资\n董事会下放“行长授权审批权”",
            "免除DEA主权担保与董事会排期",
            "绕开联邦与邦财政繁琐预算审批\n管理层授权直接签批非主权项目",
            "非主权项目反超 · 审批提速 54%",
            "非主权审批 205.4天 vs 主权 447.2天\n2023–2026非主权(16项)超主权(9项)",
            C_TEAL, C_CARD_GREEN
        ),
        (
            "《协定》第13条第3款 · 属地原则",
            "成员国领土业务“主权无异议权”\n多边银行争议领土规避惯例",
            "概念初筛阶段前置过滤争议区",
            "印巴克什米尔与中印东段争议区过滤\n无争议区按纯经济技术标准立项",
            "避开争议领土 · 阿萨姆邦密集立项",
            "克什米尔及藏南争议区立项数为 0\n阿萨姆邦获批 5 项 · $8.95亿",
            C_BLUE, C_CARD_BLUE
        ),
        (
            "《采购政策》 · 第5.4条商业采购",
            "借款国实施机构主导编标与评标\n允许国内招标(NOCT)与商业惯例",
            "本土业主评标 + 印国内安全审查",
            "PGCIL/地铁局评标利好本土承包商\n印 GFR 144(xi) 签证与清关阻断中资",
            "印企垄断 95.35% 合同 · 中资归零",
            "印企本国中标 $98.11亿 · 全球第一\n中资在印仅 2.21% · 2022–2025归零",
            C_AMBER, C_CARD_GOLD
        ),
        (
            "《PPM政策》第2.1.1条 · 前置程序",
            "联合融资案件移交牵头行豁免规则\n强制要求事先与GRM/管理层沟通",
            "世行检验组分流 + 前置驳回机制",
            "60%登记案件移交世行免于重复审查\n20%因未履行事先沟通被直接驳回",
            "申诉最密集但极少阻断项目推进",
            "占全行直接申诉 31.1% · 登记案 71.4%\n仅1起独立融资案进入审查 · 0停工",
            C_PURPLE, C_CARD_PURPLE
        ),
    ]

    card_h = 0.122
    gap = 0.020
    start_y = 0.755

    for i, (t1, b1, t2, b2, t3, b3, col, fill) in enumerate(rows):
        y = start_y - i * (card_h + gap)
        draw_card(ax, 0.025, y, 0.27, card_h, t1, b1, header_fc=col, body_fc=fill, ec=col, header_ratio=0.36, title_fs=10.4, body_fs=9.2)
        draw_card(ax, 0.365, y, 0.27, card_h, t2, b2, header_fc=col, body_fc="#FFFFFF", ec=col, header_ratio=0.36, title_fs=10.4, body_fs=9.2)
        draw_card(ax, 0.705, y, 0.27, card_h, t3, b3, header_fc=col, body_fc=fill, ec=col, header_ratio=0.36, title_fs=10.4, body_fs=9.2)

        cy = y + card_h / 2
        draw_arrow(ax, 0.295, cy, 0.365, cy, color=col, lw=2.0)
        draw_arrow(ax, 0.635, cy, 0.705, cy, color=col, lw=2.0)

    out_path = os.path.join(OUT_DIR, "fig3_4_findings_to_institutions_mapping.png")
    plt.savefig(out_path, bbox_inches="tight", facecolor="#FFFFFF")
    plt.close(fig)
    print("Saved:", out_path)


if __name__ == "__main__":
    generate_fig3_1()
    generate_fig3_2()
    generate_fig3_3()
    generate_fig3_4()
    print("All 4 concise Chapter 3 figures generated successfully.")

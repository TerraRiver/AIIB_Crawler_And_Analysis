"""Generate 7 high-resolution academic statistical, geographic, and heatmap figures for Chapter 2:
India's Substantive Participation in AIIB Projects and Procurement (2016-2026).

Figure lineup per user refinements:
- fig2_1_india_projects_trend.png: 2016-2026 India approved project amount (SBF/NSBF stacked) & project count (Single panel).
- fig2_2_india_share_in_aiib.png: 3 vertically stacked subfigures (a, b, c):
    (a) Top 10 AIIB borrowers donut chart + full ranking table;
    (b) 2016-2026 annual share of India in AIIB approved amount & count;
    (c) All-member Subscribed Capital vs. Approved Financing scatter plot (formerly scatter panel a).
- fig2_3_india_cofinancing_trend.png: 2017-2026 Co-financed vs. Standalone amount & share evolution (Single panel, former subfigure b removed).
- fig2_4_india_sbf_nsbf_and_lag.png: 2 vertically stacked subfigures (a, b):
    (a) 2017-2026 SBF vs. NSBF count evolution & Proposed pipeline;
    (b) 2x2 Financing Matrix average project size & approval lag days.
- fig2_5_sector_and_map_combined.png: 2 vertically stacked subfigures merging former Fig 5B and Fig 6A (with Fig 5A & 6B removed):
    (a) Sector project count & average single-project size (former Fig 5B);
    (b) Real administrative map of India (GeoJSON Choropleth + proportional bubbles, former Fig 6A).
- fig2_6_procurement_nationality_comparison.png: 2 vertically stacked subfigures (former Fig 2-7):
    (a) Contractor nationality & procurement method in India's 1,110 contracts ($102.89B);
    (b) Bank-wide top 10 contractor nationalities across 3,311 contracts ($266.00B).
- fig2_7_procurement_heatmap_and_annual.png: 2 vertically stacked subfigures (replacing former Fig 2-8a with a 2D Heatmap and pairing with Fig 2-8b):
    (a) 2D Heatmap of Top Borrower Members x Contractor Nationality (share % & amount $100M);
    (b) 2016-2025 annual contract award value in India vs. bank-wide, and Chinese wins in India dropping to $0 (former Fig 2-8b).
"""

import json
from pathlib import Path
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Polygon as MplPolygon
import numpy as np

# Disable matplotlib TeX math parsing on '$' so currency strings like '$144.51亿 ... $784.71亿' render literally
matplotlib.rcParams["text.parse_math"] = False

# Configure Chinese font and publication-grade styling
plt.rcParams["font.sans-serif"] = ["PingFang SC", "Heiti TC", "STHeiti", "Arial Unicode MS", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 300
plt.rcParams["savefig.dpi"] = 300
plt.rcParams["axes.titlesize"] = 14
plt.rcParams["axes.labelsize"] = 12
plt.rcParams["xtick.labelsize"] = 11
plt.rcParams["ytick.labelsize"] = 11
plt.rcParams["legend.fontsize"] = 10.5

OUT_DIR = Path("reports/figures")
OUT_DIR.mkdir(parents=True, exist_ok=True)
GEOJSON_PATH = Path("data/india_states_telangana.geojson")

# Color palette
C_NAVY = "#1E3A8A"
C_BLUE = "#2563EB"
C_SKY = "#0284C7"
C_LIGHT_BLUE = "#93C5FD"
C_TEAL = "#0D9488"
C_AMBER = "#D97706"
C_ORANGE = "#EA580C"
C_RED = "#DC2626"
C_SLATE = "#475569"
C_LIGHT_SLATE = "#CBD5E1"
C_BG_GRAY = "#F8FAFC"
C_TEXT = "#0F172A"
C_MUTED = "#475569"
C_PURPLE = "#7C3AED"


def setup_ax(ax, title="", xlabel="", ylabel="", grid_axis="y"):
    """Apply clean academic styling to an axes object with large readable fonts."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#64748B")
    ax.spines["bottom"].set_color("#64748B")
    ax.spines["left"].set_linewidth(0.9)
    ax.spines["bottom"].set_linewidth(0.9)
    ax.tick_params(colors=C_TEXT, labelsize=11)
    if grid_axis:
        ax.grid(axis=grid_axis, linestyle="--", alpha=0.45, color="#CBD5E1", zorder=0)
    if title:
        ax.set_title(title, fontsize=13.5, fontweight="bold", color=C_TEXT, pad=14, loc="left")
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=11.5, fontweight="bold", color=C_TEXT, labelpad=8)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=11.5, fontweight="bold", color=C_TEXT, labelpad=8)


# ==============================================================================
# Figure 2-1: 2016–2026年印度在亚投行获批项目数量与融资金额年度演变图 (Single Panel)
# ==============================================================================
def make_fig2_1():
    years = ["2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026*"]
    sbf_amt = np.array([0.0, 9.24, 9.95, 6.45, 17.50, 18.9067, 17.19, 9.0175, 6.7472, 12.4061, 10.00])
    nsbf_amt = np.array([0.0, 1.50, 1.50, 1.75, 2.00, 0.50, 1.50, 2.03, 3.835, 3.99, 8.50])
    tot_amt = sbf_amt + nsbf_amt
    counts = np.array([0, 5, 5, 4, 4, 9, 8, 6, 8, 6, 5])
    sbf_cnt = [0, 4, 3, 2, 3, 8, 6, 3, 3, 2, 1]
    nsbf_cnt = [0, 1, 2, 2, 1, 1, 2, 3, 5, 4, 4]

    fig, ax1 = plt.subplots(figsize=(12.5, 6.8))
    x = np.arange(len(years))
    width = 0.54

    phases = [
        (-0.45, 3.45, "#EFF6FF", "第一阶段：启动与联合融资探索期\n(2016–2019：累计14项 / 30.39亿美元)"),
        (3.55, 6.45, "#FEF3C7", "第二阶段：疫情应急与主权贷款高峰期\n(2020–2022：累计21项 / 57.60亿美元)"),
        (6.55, 10.45, "#ECFDF5", "第三阶段：常态化与非主权融资转型期\n(2023–2026*：累计25项 / 56.53亿美元)"),
    ]
    for xmin, xmax, bg_col, label in phases:
        ax1.axvspan(xmin, xmax, color=bg_col, alpha=0.48, zorder=0)
        ax1.text(
            (xmin + xmax) / 2,
            26.2,
            label,
            ha="center",
            va="top",
            fontsize=10.5,
            fontweight="bold",
            color="#1E293B",
            bbox=dict(boxstyle="round,pad=0.35", facecolor="white", edgecolor="#CBD5E1", alpha=0.94),
        )

    ax1.bar(x, sbf_amt, width=width, color=C_NAVY, alpha=0.90, label="主权担保融资额 (SBF，累计117.41亿美元，35项)", zorder=3)
    ax1.bar(x, nsbf_amt, width=width, bottom=sbf_amt, color=C_SKY, alpha=0.90, label="非主权融资额 (NSBF，累计27.11亿美元，25项)", zorder=3)

    setup_ax(ax1, title="2016—2026年印度在亚投行获批项目融资金额（主权/非主权堆叠）与项目数量演变", xlabel="批准年份（*2026年数据截至2026年3月）", ylabel="年度获批融资金额（亿美元）")
    ax1.set_xticks(x)
    ax1.set_xticklabels(years, fontsize=11, fontweight="bold")
    ax1.set_ylim(0, 29.5)
    ax1.set_xlim(-0.6, 10.6)

    ax2 = ax1.twinx()
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_color(C_RED)
    ax2.spines["right"].set_linewidth(1.1)
    ax2.tick_params(axis="y", colors=C_RED, labelsize=11)
    ax2.set_ylabel("年度获批项目数量（个）", fontsize=11.5, fontweight="bold", color=C_RED, labelpad=10)
    ax2.set_ylim(0, 15.5)

    ax2.plot(
        x, counts, color=C_RED, marker="o", markersize=8.5, linewidth=2.6,
        markerfacecolor="white", markeredgewidth=2.2, label="年度获批项目总数（右轴，累计60项）", zorder=6
    )

    bar_y_extra = [0.0, 0.35, 0.35, 0.35, 0.35, 0.35, 0.35, 1.45, 0.35, 0.35, 0.35]
    for i in range(len(years)):
        if tot_amt[i] > 0:
            ax1.text(
                x[i],
                tot_amt[i] + bar_y_extra[i],
                f"${tot_amt[i]:.2f}亿\n({sbf_cnt[i]}主+{nsbf_cnt[i]}非)",
                ha="center",
                va="bottom",
                fontsize=9.5,
                fontweight="bold",
                color=C_NAVY,
                zorder=5,
            )
        else:
            ax1.text(x[i], 0.5, "$0.00亿\n(0项)", ha="center", va="bottom", fontsize=9.5, color=C_MUTED, zorder=5)

    count_offsets = [12, -16, -16, -16, -16, 12, 12, -16, 12, -16, -16]
    for i, c in enumerate(counts):
        if c > 0:
            ax2.annotate(
                f"{c}项",
                (x[i], c),
                xytext=(0, count_offsets[i]),
                textcoords="offset points",
                ha="center",
                va="center",
                fontsize=9.8,
                fontweight="bold",
                color="white",
                bbox=dict(boxstyle="round,pad=0.22", facecolor=C_RED, edgecolor="none", alpha=0.92),
                zorder=7,
            )

    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(
        handles1 + handles2, labels1 + labels2,
        loc="upper center", bbox_to_anchor=(0.48, 0.995),
        frameon=True, facecolor="white", edgecolor="#CBD5E1", fontsize=10.0, ncol=3
    )

    fig.text(
        0.01, 0.01,
        "数据来源：亚洲基础设施投资银行（AIIB）项目数据库（截至2026年3月）。注：全行累计批准印度项目60个（总额144.51亿美元），另有8个拟议项目（22.17亿美元）及4个已终止项目。",
        fontsize=9.5, color=C_MUTED
    )
    plt.tight_layout(rect=[0, 0.03, 1, 1])
    out = OUT_DIR / "fig2_1_india_projects_trend.png"
    plt.savefig(out)
    plt.close(fig)
    print("Saved", out)


# ==============================================================================
# Figure 2-2: 3个子图上下排列 (a) 前十大借款国份额 + (b) 印度历年占比 + (c) 认缴股本vs获批金额散点图
# ==============================================================================
def make_fig2_2():
    fig = plt.figure(figsize=(12.5, 18.2))
    gs = gridspec.GridSpec(
        3, 2,
        height_ratios=[1.0, 0.92, 1.05],
        width_ratios=[0.95, 1.35],
        hspace=0.38,
        wspace=0.05
    )

    ax_pie = fig.add_subplot(gs[0, 0])
    ax_tbl = fig.add_subplot(gs[0, 1])
    ax2 = fig.add_subplot(gs[1, :])
    ax3 = fig.add_subplot(gs[2, :])

    # --- Panel (a): Donut + Ranking Table ---
    countries = [
        "印度 (India)", "土耳其 (Türkiye)", "印度尼西亚 (Indonesia)", "孟加拉国 (Bangladesh)",
        "多国区域项目 (Multicountry)", "中国 (China)", "乌兹别克斯坦 (Uzbekistan)",
        "菲律宾 (Philippines)", "哈萨克斯坦 (Kazakhstan)", "巴基斯坦 (Pakistan)", "其余31个成员合计"
    ]
    amounts = [144.5125, 107.136, 60.263, 52.790, 52.570, 52.250, 47.7747, 41.8978, 38.406, 34.8681, 152.2319]
    counts = [60, 43, 18, 27, 38, 26, 23, 12, 12, 14, 113]
    shares = [a / 784.71 * 100 for a in amounts]

    colors = [
        "#1E3A8A", "#2563EB", "#0284C7", "#0D9488", "#10B981",
        "#F59E0B", "#EA580C", "#8B5CF6", "#EC4899", "#6366F1", "#94A3B8"
    ]
    explode = [0.06] + [0.0] * 10

    wedges, _ = ax_pie.pie(
        amounts,
        explode=explode,
        colors=colors,
        startangle=140,
        radius=1.08,
        wedgeprops=dict(width=0.44, edgecolor="white", linewidth=1.8),
    )
    ax_pie.text(
        0.0, 0.0,
        "亚投行全球获批总额\n$784.71亿\n(386个项目)\n\n印度稳居第一\n金额占比 18.42%\n数量占比 15.54%",
        ha="center", va="center", fontsize=10.2, fontweight="bold", color=C_NAVY
    )
    for i, w in enumerate(wedges):
        ang = (w.theta2 + w.theta1) / 2.0
        rad = np.deg2rad(ang)
        r_mid = 0.86 + (0.06 if i == 0 else 0.0)
        wx = r_mid * np.cos(rad)
        wy = r_mid * np.sin(rad)
        if shares[i] >= 4.8:
            ax_pie.text(
                wx, wy, f"{shares[i]:.1f}%",
                ha="center", va="center", fontsize=9.2, fontweight="bold",
                color="white" if i not in (4, 5, 10) else "#0F172A"
            )
    ax_pie.set_title("(a) 亚投行累计获批金额前十大借款成员结构（784.71亿美元，386项）", fontsize=13.0, fontweight="bold", color=C_TEXT, pad=10, loc="left")

    ax_tbl.set_xlim(0, 10.0)
    ax_tbl.set_ylim(0, 10.0)
    ax_tbl.axis("off")

    ax_tbl.text(0.1, 9.15, "前十大借款成员累计获批规模与份额明细（2016—2026.03）", fontsize=11.0, fontweight="bold", color=C_NAVY)
    ax_tbl.text(0.45, 8.45, "排名与借款成员", fontsize=10.0, fontweight="bold", color=C_SLATE)
    ax_tbl.text(5.35, 8.45, "获批金额", fontsize=10.0, fontweight="bold", color=C_SLATE, ha="right")
    ax_tbl.text(7.10, 8.45, "金额占比", fontsize=10.0, fontweight="bold", color=C_SLATE, ha="right")
    ax_tbl.text(9.80, 8.45, "项目数 (数量占比)", fontsize=10.0, fontweight="bold", color=C_SLATE, ha="right")
    ax_tbl.plot([0.1, 9.85], [8.12, 8.12], color="#94A3B8", lw=1.2)

    for idx, (c_name, amt, cnt, sh, col) in enumerate(zip(countries, amounts, counts, shares, colors)):
        ry = 7.55 - idx * 0.70
        if idx == 0:
            rect = FancyBboxPatch((0.08, ry - 0.28), 9.78, 0.56, boxstyle="round,pad=0.04", facecolor="#EFF6FF", edgecolor="#93C5FD", lw=1.0)
            ax_tbl.add_patch(rect)
        swatch = FancyBboxPatch((0.15, ry - 0.16), 0.22, 0.34, boxstyle="round,pad=0.02", facecolor=col, edgecolor="none")
        ax_tbl.add_patch(swatch)
        rank_prefix = f"#{idx+1} " if idx < 10 else "— "
        fw = "bold" if idx in (0, 1, 5) else "normal"
        tc = C_NAVY if idx == 0 else C_TEXT
        ax_tbl.text(0.48, ry, f"{rank_prefix}{c_name}", fontsize=10.0, fontweight=fw, color=tc, va="center")
        ax_tbl.text(5.35, ry, f"${amt:.2f}亿", fontsize=10.0, fontweight=fw, color=tc, va="center", ha="right")
        ax_tbl.text(7.10, ry, f"{sh:.2f}%", fontsize=10.0, fontweight=fw, color=tc, va="center", ha="right")
        ax_tbl.text(9.80, ry, f"{cnt}项 ({cnt/386*100:.1f}%)", fontsize=10.0, fontweight=fw, color=tc, va="center", ha="right")

    # --- Panel (b): Annual percentage share of India in AIIB total (2016-2026) ---
    years = ["2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026*"]
    cnt_share = [0.0, 33.33, 41.67, 15.38, 10.00, 19.15, 18.60, 12.50, 17.02, 10.71, 11.36]
    amt_share = [0.0, 42.91, 34.66, 20.09, 20.98, 20.89, 28.25, 9.82, 13.08, 15.96, 15.32]
    ind_cnt_tot = ["0/8", "5/15", "5/12", "4/26", "4/40", "9/47", "8/43", "6/48", "8/47", "6/56", "5/44"]

    x = np.arange(len(years))
    w = 0.38
    ax2.bar(x - w / 2, amt_share, width=w, color=C_NAVY, alpha=0.92, label="印度获批金额占全行年度总额比例 (%)", zorder=3)
    ax2.bar(x + w / 2, cnt_share, width=w, color=C_AMBER, alpha=0.88, label="印度获批项目数占全行年度总数比例 (%)", zorder=3)

    ax2.axhline(18.42, color=C_NAVY, linestyle="--", linewidth=1.5, alpha=0.8, label="十年累计金额占比均值 (18.42%，$144.51亿/$784.71亿)")
    ax2.axhline(15.54, color=C_AMBER, linestyle=":", linewidth=1.6, alpha=0.9, label="十年累计数量占比均值 (15.54%，60项/386项)")

    setup_ax(ax2, title="(b) 2016—2026年印度在亚投行年度获批金额与项目数量中的占比演变（顶峰42.9% → 常态化13%–16%）", xlabel="批准年份（括号内为“印度获批数/全行获批总数”）", ylabel="印度占全行年度比重 (%)")
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"{y}\n({c})" for y, c in zip(years, ind_cnt_tot)], fontsize=10.2)
    ax2.set_ylim(0, 52)

    for i in range(len(years)):
        if amt_share[i] > 0:
            ax2.text(x[i] - w / 2 - 0.03, amt_share[i] + 0.8, f"{amt_share[i]:.1f}%", ha="center", va="bottom", fontsize=9.2, fontweight="bold", color=C_NAVY)
        if cnt_share[i] > 0:
            y_bump = 1.6 if i == 8 else 0.8
            ax2.text(x[i] + w / 2 + 0.03, cnt_share[i] + y_bump, f"{cnt_share[i]:.1f}%", ha="center", va="bottom", fontsize=9.2, fontweight="bold", color="#B45309")

    ax2.legend(loc="upper right", frameon=True, facecolor="white", edgecolor="#CBD5E1", fontsize=10.0, ncol=2)

    # --- Panel (c): All-Member Subscribed Capital vs. Approved Financing Scatter Plot ---
    with open("data/governance/members_voting_power.json", "r", encoding="utf-8") as f:
        mvp = json.load(f)
    with open("data/projects/all_projects_summary.json", "r", encoding="utf-8") as f:
        projs = json.load(f)

    app_amt = {}
    app_cnt = {}
    for p in projs:
        if p.get("status") == "Approved":
            ec = p.get("economy")
            amt = float(p.get("approved_funding_usd_millions") or 0.0)
            app_amt[ec] = app_amt.get(ec, 0.0) + amt
            app_cnt[ec] = app_cnt.get(ec, 0) + 1

    pts = []
    for m in mvp["members"]:
        ec = m["economy"]
        sub_100m = float(m["subscription_amount_usd_millions"] or 0.0) / 100.0
        app_100m = app_amt.get(ec, 0.0) / 100.0
        cnt = app_cnt.get(ec, 0)
        grp = m["member_group"]
        pts.append((ec, grp, sub_100m, app_100m, cnt))

    x_line = np.linspace(0, 165, 200)
    ax3.plot(x_line, x_line, color=C_TEAL, linestyle="--", linewidth=1.5, alpha=0.8, label="1:1 等额参考线（累计获批金额 = 认缴股本，即1.0倍认缴额）", zorder=2)
    x_line2 = np.linspace(0, 315, 200)
    ax3.plot(x_line2, 0.2 * x_line2, color=C_AMBER, linestyle=":", linewidth=1.6, alpha=0.85, label="实缴股本平衡线（累计获批金额 = 20%实缴股本，即1.0倍实缴额）", zorder=2)

    for ec, grp, sub, app, cnt in pts:
        if ec == "India":
            col, alp, sz, z = "#DC2626", 1.0, 280, 7
        elif ec == "China":
            col, alp, sz, z = "#D97706", 0.95, 260, 7
        elif app > 0:
            col, alp, sz, z = (C_NAVY if grp == "Regional" else C_PURPLE), 0.85, max(cnt * 6.5 + 38, 42), 5
        else:
            col, alp, sz, z = "#64748B", 0.55, 38, 3
        ax3.scatter(sub, app, s=sz, color=col, alpha=alp, edgecolors="white", linewidth=1.2, zorder=z)

    setup_ax(
        ax3,
        title="(c) 全行106个成员累计认缴股本与累计获批融资金额全景对比（第一大股东中国与第一大借款国印度的位置对比）",
        xlabel="累计认缴股本金额（亿美元，Subscribed Capital）",
        ylabel="累计获批融资金额（亿美元）",
        grid_axis="both"
    )
    ax3.set_xlim(-8, 322)
    ax3.set_ylim(-12, 168)

    ann_c = [
        ("印度 (India，第2大股东 / 第1大借款国)\n认缴 $83.67亿 (8.57%) | 获批 $144.51亿 (60项)\n获批/认缴 = 1.73倍 | 获批/实缴 = 8.64倍", (83.673, 144.5125), (96.0, 122.0), "#DC2626", "#FEF2F2"),
        ("中国 (China，第1大股东 / 第5大借款国)\n认缴 $297.80亿 (30.50%) | 获批 $52.25亿 (26项)\n获批/认缴 = 0.18倍 | 获批/实缴 = 0.88倍", (297.804, 52.25), (205.0, 88.0), "#B45309", "#FFFBEB"),
        ("土耳其：认缴$26.10亿 / 获批$107.14亿 (4.10倍)", (26.099, 107.136), (45.0, 105.0), C_NAVY, "white"),
        ("印度尼西亚：认缴$33.61亿 / 获批$60.26亿 (1.79倍)", (33.607, 60.263), (58.0, 68.0), C_NAVY, "white"),
        ("孟加拉/乌兹别克/菲律宾/哈萨克/巴基斯坦\n高杠杆借款国集群（认缴$2亿–$10亿，获批$35亿–$53亿）", (7.293, 45.0), (42.0, 38.0), C_NAVY, "#EFF6FF"),
        ("纯出资非借款大股东集群（获批 $0.00亿）：\n俄罗斯($65.4亿)、德国($44.8亿)、韩国($37.4亿)、澳大利亚($36.9亿)、法国($33.8亿)、英国($30.5亿)", (44.842, 0.0), (88.0, 9.0), "#475569", "#F8FAFC"),
    ]
    for txt, xy, xytext, ec_col, bg_col in ann_c:
        ax3.annotate(
            txt, xy=xy, xytext=xytext,
            fontsize=9.4, fontweight="bold" if xy[0] > 80 else "normal", color=ec_col,
            bbox=dict(boxstyle="round,pad=0.25", facecolor=bg_col, edgecolor=ec_col, lw=1.0, alpha=0.95),
            arrowprops=dict(arrowstyle="->", color=ec_col, lw=1.1, alpha=0.85),
            zorder=8
        )

    ax3.legend(loc="upper right", frameon=True, facecolor="white", edgecolor="#CBD5E1", fontsize=9.8)

    fig.text(
        0.01, 0.008,
        "数据来源：根据亚投行项目数据库（386项已批准项目、总额784.71亿美元）及《成员认缴股本与投票权表》（认缴总股本976.32亿美元）统计计算。*2026年数据截至2026年3月。",
        fontsize=9.5, color=C_MUTED
    )
    plt.tight_layout(rect=[0, 0.02, 1, 1])
    out = OUT_DIR / "fig2_2_india_share_in_aiib.png"
    plt.savefig(out)
    plt.close(fig)
    print("Saved", out)


# ==============================================================================
# Figure 2-3: 印度获批项目融资模式（联合融资 vs 独立融资）年度金额及占比演变 (Single Panel, 子图b已移除)
# ==============================================================================
def make_fig2_3():
    fig, ax1 = plt.subplots(figsize=(12.5, 6.6))

    years = ["2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026*"]
    cofin_amt = np.array([7.39, 4.75, 0.00, 17.50, 18.3667, 5.79, 8.7975, 3.375, 1.99, 1.50])
    stand_amt = np.array([3.35, 6.70, 8.20, 2.00, 1.04, 12.90, 2.25, 7.2072, 14.4061, 17.00])
    tot_amt = cofin_amt + stand_amt
    cofin_share = np.where(tot_amt > 0, cofin_amt / tot_amt * 100, 0)
    cofin_cnt = [3, 2, 0, 4, 8, 2, 5, 4, 3, 2]
    stand_cnt = [2, 3, 4, 0, 1, 6, 1, 4, 3, 3]

    x = np.arange(len(years))
    w = 0.50
    ax1.bar(x, cofin_amt, width=w, color=C_TEAL, alpha=0.90, label="多边联合融资项目金额 (Co-financed，累计69.46亿美元，33项：世行13项/亚行11项/IFC 9项/EIB 1项)", zorder=3)
    ax1.bar(x, stand_amt, width=w, bottom=cofin_amt, color=C_NAVY, alpha=0.90, label="亚投行独立融资项目金额 (Standalone，累计75.05亿美元，27项：主权15项/非主权12项)", zorder=3)

    setup_ax(ax1, title="2017—2026年印度项目多边联合融资与亚投行独立融资年度金额及占比演变", xlabel="批准年份（括号内为“联合融资项数 : 独立融资项数”）", ylabel="年度获批融资金额（亿美元）")
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"{y}\n({c}:{s})" for y, c, s in zip(years, cofin_cnt, stand_cnt)], fontsize=10.8, fontweight="bold")
    ax1.set_ylim(0, 26.5)

    bar_top_pad = [0.35, 0.35, 0.35, 1.45, 1.65, 0.35, 0.35, 0.35, 0.35, 0.35]
    for i in range(len(years)):
        ax1.text(x[i], tot_amt[i] + bar_top_pad[i], f"${tot_amt[i]:.2f}亿", ha="center", va="bottom", fontsize=10.2, fontweight="bold", color=C_TEXT)

    ax1_r = ax1.twinx()
    ax1_r.spines["top"].set_visible(False)
    ax1_r.spines["right"].set_color(C_ORANGE)
    ax1_r.tick_params(axis="y", colors=C_ORANGE, labelsize=11)
    ax1_r.set_ylabel("联合融资金额占年度总额比例 (%)", fontsize=11.5, fontweight="bold", color=C_ORANGE)
    ax1_r.set_ylim(-6, 122)

    ax1_r.plot(
        x, cofin_share, color=C_ORANGE, marker="s", markersize=8.0, linewidth=2.6,
        markerfacecolor="white", markeredgewidth=2.1, label="联合融资金额占年度总额比例 (%)", zorder=6
    )
    label_y_offsets = [12, -16, 12, -16, -16, -16, 12, -16, 12, 12]
    for i, sh in enumerate(cofin_share):
        ax1_r.annotate(
            f"{sh:.1f}%",
            (x[i], sh),
            xytext=(0, label_y_offsets[i]),
            textcoords="offset points",
            ha="center", va="center",
            fontsize=9.8, fontweight="bold", color="white",
            bbox=dict(boxstyle="round,pad=0.22", facecolor=C_ORANGE, edgecolor="none", alpha=0.92),
            zorder=7
        )

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax1_r.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", frameon=True, facecolor="white", edgecolor="#CBD5E1", fontsize=10.0)

    fig.text(
        0.01, 0.01,
        "数据来源：根据亚投行印度获批项目融资结构文本与政策适用披露整理。注：2020—2021年联合融资额占比达92.2%（35.87亿/38.91亿美元）；2025—2026年独立融资额占比升至90.0%。",
        fontsize=9.5, color=C_MUTED
    )
    plt.tight_layout(rect=[0, 0.03, 1, 1])
    out = OUT_DIR / "fig2_3_india_cofinancing_trend.png"
    plt.savefig(out)
    plt.close(fig)
    print("Saved", out)


# ==============================================================================
# Figure 2-4: 印度主权与非主权融资（SBF vs NSBF）转型及审批周期对比图 (2x1 上下排列)
# ==============================================================================
def make_fig2_4():
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12.5, 12.8), gridspec_kw={"height_ratios": [1.05, 0.95]})

    periods = ["2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026*", "拟议在审\n(Proposed)"]
    sbf_c = np.array([4, 3, 2, 3, 8, 6, 3, 3, 2, 1, 3])
    nsbf_c = np.array([1, 2, 2, 1, 1, 2, 3, 5, 4, 4, 5])
    tot_c = sbf_c + nsbf_c
    nsbf_ratio = nsbf_c / tot_c * 100

    x = np.arange(len(periods))
    w = 0.50
    ax1.bar(x, sbf_c, width=w, color=C_NAVY, alpha=0.90, label="主权担保融资项目数 (SBF：已批35项 / 拟议3项)", zorder=3)
    ax1.bar(x, nsbf_c, width=w, bottom=sbf_c, color=C_SKY, alpha=0.90, label="非主权融资项目数 (NSBF：已批25项 / 拟议5项)", zorder=3)
    ax1.axvspan(9.5, 10.5, color="#FEF3C7", alpha=0.55, zorder=1)

    setup_ax(ax1, title="(a) 2017—2026年印度主权与非主权项目数量演变及在审项目储备（2023年起非主权数量反超）", xlabel="批准年份及拟议在审项目池", ylabel="项目数量（个）")
    ax1.set_xticks(x)
    ax1.set_xticklabels(periods, fontsize=10.5, fontweight="bold")
    ax1.set_ylim(0, 12.2)

    for i in range(len(periods)):
        ax1.text(x[i], tot_c[i] + 0.25, f"共{tot_c[i]}项\n({sbf_c[i]}主+{nsbf_c[i]}非)", ha="center", va="bottom", fontsize=9.5, fontweight="bold", color=C_TEXT)

    ax1_r = ax1.twinx()
    ax1_r.spines["top"].set_visible(False)
    ax1_r.spines["right"].set_color(C_RED)
    ax1_r.tick_params(axis="y", colors=C_RED, labelsize=11)
    ax1_r.set_ylabel("非主权项目数量占比 (%)", fontsize=11.5, fontweight="bold", color=C_RED)
    ax1_r.set_ylim(0, 108)

    ax1_r.plot(
        x, nsbf_ratio, color=C_RED, marker="D", markersize=7.5, linewidth=2.4,
        markerfacecolor="white", markeredgewidth=2.0, label="非主权项目数量占比 (%)", zorder=6
    )
    nsbf_offsets = [-15, -15, -16, -15, -15, -15, -16, 12, 12, 12, 12]
    for i, r in enumerate(nsbf_ratio):
        ax1_r.annotate(
            f"{r:.0f}%",
            (x[i], r),
            xytext=(0, nsbf_offsets[i]),
            textcoords="offset points",
            ha="center", va="center", fontsize=9.5, fontweight="bold", color="white",
            bbox=dict(boxstyle="round,pad=0.2", facecolor=C_RED, edgecolor="none", alpha=0.9),
            zorder=7
        )

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax1_r.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", frameon=True, facecolor="white", edgecolor="#CBD5E1", fontsize=10.2, ncol=2)

    quadrants = [
        "主权 × 独立融资\n(15项，总额60.00亿美元，占41.5%)",
        "主权 × 多边联合融资\n(20项，总额57.40亿美元，占39.7%)",
        "非主权 × 独立融资\n(12项，总额15.05亿美元，占10.4%)",
        "非主权 × 多边联合融资\n(13项，总额12.06亿美元，占8.3%)",
    ]
    avg_size_musd = [400.02, 287.02, 125.42, 92.73]
    avg_lag_days = [480.2, 419.8, 264.0, 171.2]

    x2 = np.arange(len(quadrants))
    w2 = 0.34
    ax2.bar(x2 - w2 / 2, avg_size_musd, width=w2, color=C_NAVY, alpha=0.90, label="平均单项融资规模（百万美元，左轴）", zorder=3)
    setup_ax(ax2, title="(b) 四类融资模式组合的平均单项规模与立项至获批筹备周期对比（2×2交叉矩阵）", xlabel="融资模式交叉组合类别（括号内为项目数、累计金额及占印度总额比重）", ylabel="平均单项融资规模（百万美元）")
    ax2.set_xticks(x2)
    ax2.set_xticklabels(quadrants, fontsize=10.5, fontweight="bold")
    ax2.set_ylim(0, 560)

    ax2_r = ax2.twinx()
    ax2_r.spines["top"].set_visible(False)
    ax2_r.spines["right"].set_color(C_AMBER)
    ax2_r.tick_params(axis="y", colors="#B45309", labelsize=11)
    ax2_r.set_ylabel("平均筹备审批周期（天：概念审查至批准）", fontsize=11.5, fontweight="bold", color="#B45309")
    ax2_r.set_ylim(0, 620)

    ax2_r.bar(x2 + w2 / 2, avg_lag_days, width=w2, color=C_AMBER, alpha=0.88, label="平均立项至批准周期（天，右轴）", zorder=3)

    for i in range(len(quadrants)):
        ax2.text(
            x2[i] - w2 / 2, avg_size_musd[i] + 10,
            f"${avg_size_musd[i]:.1f}M\n(约{avg_size_musd[i]/100:.2f}亿美元)",
            ha="center", va="bottom", fontsize=10, fontweight="bold", color=C_NAVY
        )
        ax2_r.text(
            x2[i] + w2 / 2, avg_lag_days[i] + 10,
            f"{avg_lag_days[i]:.0f}天\n(约{avg_lag_days[i]/30:.1f}个月)",
            ha="center", va="bottom", fontsize=10, fontweight="bold", color="#B45309"
        )

    h2_1, l2_1 = ax2.get_legend_handles_labels()
    h2_2, l2_2 = ax2_r.get_legend_handles_labels()
    ax2.legend(h2_1 + h2_2, l2_1 + l2_2, loc="upper right", frameon=True, facecolor="white", edgecolor="#CBD5E1", fontsize=10.2, ncol=2)

    fig.text(
        0.01, 0.01,
        "数据来源：根据亚投行印度项目档案中披露的概念审查日（Concept Review）与董事会/行长批准日（Approval）计算（共52个具完整双日期的获批项目：主权33项均值447.2天，非主权19项均值205.4天）。",
        fontsize=9.5, color=C_MUTED
    )
    plt.tight_layout(rect=[0, 0.025, 1, 1], h_pad=2.2)
    out = OUT_DIR / "fig2_4_india_sbf_nsbf_and_lag.png"
    plt.savefig(out)
    plt.close(fig)
    print("Saved", out)


# ==============================================================================
# Figure 2-5: 原图5B（分行业项目数与单均规模）与 原图6A（印度真实行政区划地图）上下合并 (2x1 上下排列)
# ==============================================================================
def make_fig2_5():
    fig, (ax_sec, ax_map) = plt.subplots(
        2, 1, figsize=(12.5, 15.6), gridspec_kw={"height_ratios": [0.88, 1.35]}
    )

    # --- Top Panel (a): Sector Project Count & Average Single-Project Size (former Fig 5B) ---
    sec_short = [
        "交通运输\n(Transport)",
        "能源电力\n(Energy)",
        "多行业金融\n中介与基金",
        "新冠危机\n恢复机制 (CRF)",
        "水务与\n防洪灌溉",
        "城市发展\n与市政",
        "教育与\n科研基建",
    ]
    cnt_rev = np.array([20, 14, 12, 4, 4, 5, 1])
    tot_rev = np.array([49.4214, 28.5411, 25.80, 22.50, 9.20, 6.55, 2.50])
    avg_rev = (tot_rev * 100.0) / cnt_rev  # in million USD

    x2 = np.arange(len(sec_short))
    w2 = 0.44

    ax_sec.bar(x2, cnt_rev, width=w2, color=C_TEAL, alpha=0.88, label="行业获批项目数量（个，左轴，共60项、总额144.51亿美元）", zorder=3)
    setup_ax(ax_sec, title="(a) 印度获批项目各行业数量、累计金额与平均单项融资规模对比（交通数量居首，CRF单均体量最大）", xlabel="行业类别", ylabel="获批项目数量（个）")
    ax_sec.set_xticks(x2)
    ax_sec.set_xticklabels(sec_short, fontsize=10.5, fontweight="bold")
    ax_sec.set_ylim(0, 26.5)

    cnt_y_bump = [0.5, 0.5, 0.5, 0.5, 0.5, 1.5, 0.5]
    for i, (c, tot_v) in enumerate(zip(cnt_rev, tot_rev)):
        ax_sec.text(
            x2[i], c + cnt_y_bump[i],
            f"{c}项 (${tot_v:.2f}亿)\n占数量{c/60*100:.1f}%",
            ha="center", va="bottom", fontsize=9.5, fontweight="bold", color=C_TEAL
        )

    ax_sec_r = ax_sec.twinx()
    ax_sec_r.spines["top"].set_visible(False)
    ax_sec_r.spines["right"].set_color(C_ORANGE)
    ax_sec_r.tick_params(axis="y", colors=C_ORANGE, labelsize=11)
    ax_sec_r.set_ylabel("平均单项融资规模（百万美元/项）", fontsize=11.5, fontweight="bold", color=C_ORANGE)
    ax_sec_r.set_ylim(0, 680)

    ax_sec_r.plot(
        x2, avg_rev, color=C_ORANGE, marker="D", markersize=8, linewidth=2.5,
        markerfacecolor="white", markeredgewidth=2.0, label="平均单项融资规模（百万美元/项，右轴）", zorder=6
    )
    avg_offsets = [12, -16, 12, 12, 12, -16, 12]
    for i, av in enumerate(avg_rev):
        ax_sec_r.annotate(
            f"${av:.1f}M",
            (x2[i], av),
            xytext=(0, avg_offsets[i]),
            textcoords="offset points",
            ha="center", va="center", fontsize=9.8, fontweight="bold", color="white",
            bbox=dict(boxstyle="round,pad=0.22", facecolor=C_ORANGE, edgecolor="none", alpha=0.92),
            zorder=7
        )

    h1, l1 = ax_sec.get_legend_handles_labels()
    h2, l2 = ax_sec_r.get_legend_handles_labels()
    ax_sec.legend(h1 + h2, l1 + l2, loc="upper right", frameon=True, facecolor="white", edgecolor="#CBD5E1", fontsize=10.0, ncol=2)

    # --- Bottom Panel (b): Real Administrative Map of India (former Fig 6A) ---
    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        geo = json.load(f)

    tier1_states = {"Maharashtra", "Tamil Nadu", "Andhra Pradesh", "Assam"}
    tier2_states = {"Gujarat", "Kerala", "Manipur", "Karnataka", "Delhi", "West Bengal", "Uttar Pradesh"}
    tier3_states = {"Madhya Pradesh", "Punjab", "Haryana", "Rajasthan", "Chhattisgarh", "Orissa", "Meghalaya", "Telangana"}
    excluded_features = {"Arunachal Pradesh", "Jammu and Kashmir", "Andaman and Nicobar", "Lakshadweep"}

    for feat in geo["features"]:
        st_name = feat["properties"].get("NAME_1", "")
        if st_name in excluded_features:
            continue
        if st_name in tier1_states:
            fc, ec, lw, z = "#93C5FD", "#1E40AF", 1.15, 2
        elif st_name in tier2_states:
            fc, ec, lw, z = "#BFDBFE", "#2563EB", 1.0, 2
        elif st_name in tier3_states:
            fc, ec, lw, z = "#DBEAFE", "#3B82F6", 0.9, 2
        else:
            fc, ec, lw, z = "#F1F5F9", "#94A3B8", 0.75, 1

        geom_type = feat["geometry"]["type"]
        coords = feat["geometry"]["coordinates"]
        polys = [coords] if geom_type == "Polygon" else coords
        for poly in polys:
            ext_ring = np.array(poly[0])
            patch = MplPolygon(ext_ring, closed=True, facecolor=fc, edgecolor=ec, linewidth=lw, zorder=z)
            ax_map.add_patch(patch)

    states_data = [
        ("旁遮普邦", 1.00, 1, 75.41, 30.84, 3, 68.0, 31.4, "right"),
        ("哈里亚纳邦", 0.89, 2, 76.33, 29.20, 3, 68.0, 29.5, "right"),
        ("德里国家首都辖区", 3.14, 2, 77.11, 28.65, 2, 68.0, 27.6, "right"),
        ("拉贾斯坦邦", 0.75, 2, 73.85, 26.58, 3, 68.0, 25.7, "right"),
        ("中央邦", 1.75, 3, 78.29, 23.54, 3, 68.0, 23.8, "right"),
        ("古吉拉特邦", 6.925, 4, 71.61, 22.69, 2, 66.8, 21.6, "right"),
        ("马哈拉施特拉邦", 19.69, 7, 76.11, 19.45, 1, 67.8, 18.8, "right"),
        ("卡纳塔克邦", 3.45, 2, 76.17, 14.71, 2, 69.2, 14.8, "right"),
        ("喀拉拉邦", 4.1065, 5, 76.41, 10.45, 2, 71.0, 11.2, "right"),
        ("北方邦", 2.60, 2, 80.56, 26.93, 2, 84.5, 30.5, "left"),
        ("阿萨姆邦", 11.5061, 4, 92.83, 26.36, 1, 96.2, 28.5, "left"),
        ("梅加拉亚邦", 0.25, 1, 91.28, 25.54, 3, 96.2, 26.5, "left"),
        ("曼尼普尔邦", 3.774, 2, 93.88, 24.74, 2, 96.2, 24.5, "left"),
        ("西孟加拉邦", 2.80, 2, 87.95, 23.90, 2, 92.0, 22.3, "left"),
        ("奥里萨邦", 0.50, 2, 84.41, 20.51, 3, 89.2, 20.2, "left"),
        ("恰蒂斯加尔邦", 0.5833, 2, 82.04, 21.26, 3, 89.2, 18.2, "left"),
        ("特伦甘纳邦", 0.10, 1, 79.06, 17.79, 3, 86.2, 16.3, "left"),
        ("安得拉邦", 11.82, 5, 79.93, 15.71, 1, 84.8, 14.2, "left"),
        ("泰米尔纳德邦", 13.8175, 6, 78.40, 11.01, 1, 83.2, 11.5, "left"),
    ]

    tier_bubble_colors = {1: "#1E3A8A", 2: "#0284C7", 3: "#F59E0B"}
    for name, amt, cnt, lon, lat, tier, l_lon, l_lat, ha in states_data:
        b_size = max(amt * 36, 52)
        col = tier_bubble_colors[tier]
        ax_map.scatter(lon, lat, s=b_size, color=col, alpha=0.88, edgecolors="white", linewidth=1.6, zorder=5)
        ax_map.annotate(
            f"{name}：${amt:.2f}亿 ({cnt}项)",
            xy=(lon, lat),
            xytext=(l_lon, l_lat),
            ha=ha, va="center",
            fontsize=9.8,
            fontweight="bold" if tier <= 2 else "normal",
            color=C_NAVY if tier == 1 else (C_TEXT if tier == 2 else "#334155"),
            bbox=dict(
                boxstyle="round,pad=0.22",
                facecolor="white",
                edgecolor=col if tier <= 2 else "#CBD5E1",
                linewidth=1.1 if tier == 1 else 0.8,
                alpha=0.95,
            ),
            arrowprops=dict(arrowstyle="-", color=col, lw=0.95, alpha=0.75),
            zorder=6,
        )

    ax_map.set_xlim(53.5, 111.5)
    ax_map.set_ylim(4.2, 33.8)
    ax_map.set_aspect(1.08)
    ax_map.axis("off")
    ax_map.set_title(
        "(b) 印度获批项目真实行政区划分布图（Choropleth分级填色 + 气泡规模标注，覆盖19个邦/中央直辖区）",
        fontsize=13.5, fontweight="bold", color=C_TEXT, pad=10, loc="left"
    )

    leg_elements = [
        mpatches.Patch(facecolor="#93C5FD", edgecolor="#1E40AF", label="第一梯队（>10亿美元：马哈拉施特拉等4邦，共56.83亿美元）"),
        mpatches.Patch(facecolor="#BFDBFE", edgecolor="#2563EB", label="第二梯队（2亿—7亿美元：古吉拉特等7邦区，共26.80亿美元）"),
        mpatches.Patch(facecolor="#DBEAFE", edgecolor="#3B82F6", label="第三梯队（<2亿美元：中央邦等8邦，共5.82亿美元）"),
        mpatches.Patch(facecolor="#F1F5F9", edgecolor="#94A3B8", label="其他行政邦（无地方专项项目，受全国性/跨邦项目辐射）"),
    ]
    ax_map.legend(
        handles=leg_elements, loc="lower left", bbox_to_anchor=(0.0, 0.01),
        frameon=True, facecolor="white", edgecolor="#CBD5E1", fontsize=9.0
    )

    nat_box = FancyBboxPatch(
        (80.6, 4.6), 30.4, 4.3,
        boxstyle="round,pad=0.3", facecolor="#FFFBEB", edgecolor=C_AMBER, linewidth=1.4, zorder=4
    )
    ax_map.add_patch(nat_box)
    ax_map.text(
        95.8, 6.75,
        "全印跨区域 / 全国性项目（共23项，总额55.06亿美元，占38.10%）\n"
        "• 主权全国项目（5项，32.50亿美元）：新冠应急与疫苗（22.50亿）、国家绿电走廊（10.00亿）\n"
        "• 非主权全国/多邦金融中介与新能源平台（18项，22.56亿美元）：NIIF基金、HDFC、L&T绿贷",
        ha="center", va="center", fontsize=8.8, fontweight="bold", color="#92400E", zorder=5
    )

    fig.text(
        0.01, 0.008,
        "数据来源：根据亚投行60个获批印度项目的行业分类与实施地点统计。注：底图采用印度邦级行政边界GeoJSON数据绘制，严格遵循中国标准地图规范，且亚投行在边界争议地区无任何项目分布。",
        fontsize=9.5, color=C_MUTED
    )
    plt.tight_layout(rect=[0, 0.02, 1, 1], h_pad=1.8)
    out = OUT_DIR / "fig2_5_sector_and_map_combined.png"
    plt.savefig(out)
    plt.close(fig)
    print("Saved", out)


# ==============================================================================
# Figure 2-6: 印度项目与亚投行全行采购合同中标方国籍分布对比图 (原图2-7，2x1 上下排列)
# ==============================================================================
def make_fig2_6():
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12.5, 13.0), gridspec_kw={"height_ratios": [1.0, 1.0]})

    ind_cats = [
        "印度本土企业独立中标 (India)",
        "中国企业独立中标 (China)",
        "土耳其企业独立中标 (Türkiye)",
        "新加坡企业独立中标 (Singapore)",
        "德国企业独立中标 (Germany)",
        "印外联合体中标 (含印中合资2笔)",
        "西班牙与瑞士企业独立中标",
        "其他国家企业 (印尼/美/日/英等)",
    ][::-1]
    ind_ioct = np.array([50.6168, 1.5272, 0.9221, 0.4819, 0.3449, 0.1750, 0.3274, 0.0608])[::-1]
    ind_nct_dir = np.array([47.4978, 0.7519, 0.00, 0.00, 0.00, 0.1361, 0.00, 0.0524])[::-1]
    ind_tot = ind_ioct + ind_nct_dir
    ind_cnts = [1083, 3, 1, 1, 3, 8, 3, 8][::-1]
    ind_notes = [
        "工程施工91.8%，涵盖IOCT国际招标与NCT国内招标",
        "2020年德里快轨隧道1笔($1.53亿) + 抗疫物资直接采购2笔($0.75亿)",
        "卡纳塔克邦班加罗尔地铁供电系统国际招标合同",
        "基础设施设备与技术服务国际招标合同",
        "轨道交通信号与控制系统国际招标合同",
        "含迅达/奥的斯印中电梯联合体2笔($0.175亿)及印韩/印法咨询6笔",
        "工程设计、监理与专业设备供应合同",
        "技术咨询服务及专项设备合同",
    ][::-1]

    y1 = np.arange(len(ind_cats))
    h = 0.56
    ax1.barh(y1, ind_ioct, height=h, color=C_NAVY, alpha=0.90, label="国际公开竞争性招标 (IOCT/IOCS，合计56.18亿美元)", zorder=3)
    ax1.barh(y1, ind_nct_dir, height=h, left=ind_ioct, color=C_SKY, alpha=0.90, label="国内竞争性招标与直接采购等 (NCT/Direct，合计46.71亿美元)", zorder=3)

    setup_ax(ax1, title="(a) 印度项目项下中标承包商国籍与招标方式结构（1,110份合同，总额102.89亿美元）", xlabel="中标合同金额（亿美元）", ylabel="", grid_axis="x")
    ax1.set_yticks(y1)
    ax1.set_yticklabels(ind_cats, fontsize=10.5, fontweight="bold")
    ax1.set_xlim(0, 225)

    for i in range(len(ind_cats)):
        pct = ind_tot[i] / 102.8943 * 100
        ax1.text(
            ind_tot[i] + 1.2, y1[i],
            f"${ind_tot[i]:.2f}亿 ({pct:.2f}%，{ind_cnts[i]}份)  —  {ind_notes[i]}",
            va="center", ha="left", fontsize=9.8, fontweight="bold" if i >= 6 else "normal", color=C_TEXT
        )

    ax1.legend(loc="lower right", bbox_to_anchor=(0.99, 0.04), frameon=True, facecolor="white", edgecolor="#CBD5E1", fontsize=10.0)

    bw_countries = [
        "1. 印度承包商 (India，独立中标)",
        "2. 中国承包商 (China，独立中标)",
        "3. 土耳其承包商 (Türkiye)",
        "4. 孟加拉国承包商 (Bangladesh)",
        "5. 印度尼西亚承包商 (Indonesia)",
        "6. 巴基斯坦承包商 (Pakistan)",
        "7. 埃及承包商 (Egypt)",
        "8. 菲律宾承包商 (Philippines)",
        "9. 阿塞拜疆承包商 (Azerbaijan)",
        "10. 意大利承包商 (Italy)",
        "其余国家及跨国联合体合计",
    ][::-1]
    bw_amts = [102.1040, 50.7669, 25.0044, 15.6540, 9.7540, 6.2389, 5.4517, 5.1460, 4.9228, 3.6352, 37.3249][::-1]
    bw_cnts = [1116, 197, 179, 369, 174, 34, 17, 7, 14, 15, 1189][::-1]
    bw_notes = [
        "本国中标1,083份($98.11亿) + 赴孟加拉等海外8国中标33份($3.99亿)",
        "全行第二大中标国，主要集中于孟加拉、巴基斯坦、乌兹别克及本国项目",
        "主要集中于土耳其本国及中亚基础设施项目",
        "主要集中于孟加拉国本国配电网、水务与交通项目",
        "主要集中于印尼本国灌溉、城市基建与能源项目",
        "主要集中于巴基斯坦本国水电站与城市交通项目",
        "主要集中于埃及本国农村环境与轨道交通项目",
        "主要集中于菲律宾防洪与马尼拉交通走廊项目",
        "主要集中于跨安纳托利亚天然气管道等能源项目",
        "欧洲主要工程与设备中标国",
        "含中外合资联合体（其中中国参与联合体约$13.10亿）及其他成员企业",
    ][::-1]
    bw_cols = [C_NAVY if "印度承包商" in c else (C_RED if "中国承包商" in c else C_TEAL) for c in bw_countries]
    bw_cols[0] = "#94A3B8"

    y2 = np.arange(len(bw_countries))
    ax2.barh(y2, bw_amts, height=0.60, color=bw_cols, alpha=0.90, zorder=3)
    setup_ax(ax2, title="(b) 亚投行全行采购合同前十大中标国别对比（3,311份合同，总额266.00亿美元：印度居全行第一）", xlabel="全行累计中标合同金额（亿美元）", ylabel="", grid_axis="x")
    ax2.set_yticks(y2)
    ax2.set_yticklabels(bw_countries, fontsize=10.5, fontweight="bold")
    ax2.set_xlim(0, 275)

    for i, (amt, cnt, note) in enumerate(zip(bw_amts, bw_cnts, bw_notes)):
        pct = amt / 266.0028 * 100
        ax2.text(
            amt + 1.2, y2[i],
            f"${amt:.2f}亿 ({pct:.2f}%，{cnt}份)  —  {note}",
            va="center", ha="left", fontsize=9.8,
            fontweight="bold" if i in (9, 10) else "normal",
            color=C_NAVY if i == 10 else (C_RED if i == 9 else C_TEXT)
        )

    fig.text(
        0.01, 0.01,
        "数据来源：根据亚投行《2016—2025年项目采购合同授予总表》（List of Contract Awards 2016–2025，共3,311条合同记录）统计计算。",
        fontsize=9.5, color=C_MUTED
    )
    plt.tight_layout(rect=[0, 0.025, 1, 1], h_pad=2.2)
    out = OUT_DIR / "fig2_6_procurement_nationality_comparison.png"
    plt.savefig(out)
    plt.close(fig)
    print("Saved", out)


# ==============================================================================
# Figure 2-7: (a) 主要借款成员×主要中标方国籍二维热力图 + (b) 2016-2025年度授标与中资在印中标演变 (2x1 上下排列)
# ==============================================================================
def make_fig2_7():
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12.8, 14.2), gridspec_kw={"height_ratios": [1.18, 0.92]})

    # --- Top Panel (a): 2D Heatmap of Borrower Country (Rows) x Contractor Nationality (Columns) ---
    borrowers = [
        "1. 印度项目 ($102.89亿)",
        "2. 土耳其项目 ($26.62亿)",
        "3. 中国项目 ($25.47亿)",
        "4. 孟加拉国项目 ($20.26亿)",
        "5. 巴基斯坦项目 ($18.92亿)",
        "6. 印度尼西亚项目 ($16.86亿)",
        "7. 埃及项目 ($11.66亿)",
        "8. 乌兹别克斯坦项目 ($8.48亿)",
        "9. 菲律宾项目 ($6.47亿)",
        "其余31个借款国合计 ($28.37亿)",
    ]
    contractor_cols = [
        "印度企业\n(含牵头合资)",
        "中国企业\n(独立中标)",
        "中外合资联合体\n(中土/中巴/中孟等)",
        "土耳其企业\n(独立及牵头)",
        "借款国本土企业\n(除印/中/土外)",
        "欧洲企业及\n欧外联合体",
        "日韩新及其他\n外资/国际机构",
    ]

    # Exact USD 100M (亿美元) matrix (10 rows x 7 cols) computed from List-of-Contract-Awards_2016-2025.xlsx
    amt_mat = np.array([
        [98.25,  2.28,  0.18,  0.92,  0.00,  0.68,  0.59],  # India ($102.89B)
        [ 0.00,  0.00, 11.34, 15.12,  0.00,  0.15,  0.00],  # Türkiye ($26.62B)
        [ 0.00, 25.47,  0.00,  0.00,  0.00,  0.00,  0.00],  # China ($25.47B)
        [ 4.77,  7.40,  3.52,  0.00,  3.32,  0.13,  1.12],  # Bangladesh ($20.26B)
        [ 0.00,  6.99,  7.54,  0.27,  1.69,  0.09,  2.33],  # Pakistan ($18.92B)
        [ 0.00,  0.39,  0.07,  0.00, 11.58,  4.74,  0.08],  # Indonesia ($16.86B)
        [ 0.00,  0.00,  0.00,  0.00,  0.00, 11.66,  0.00],  # Egypt ($11.66B)
        [ 0.02,  1.64,  0.00,  0.59,  3.20,  0.16,  2.86],  # Uzbekistan ($8.48B)
        [ 0.00,  3.24,  0.00,  0.00,  1.62,  0.01,  1.60],  # Philippines ($6.47B)
        [ 1.07,  3.36,  0.86,  4.16, 12.57,  5.11,  1.26],  # Other 31 Members ($28.37B)
    ])
    row_totals = np.array([102.8943, 26.6158, 25.4745, 20.2584, 18.9155, 16.8648, 11.6644, 8.4780, 6.4674, 28.3697])
    pct_mat = (amt_mat.T / row_totals).T * 100.0

    im = ax1.imshow(pct_mat, cmap="YlGnBu", aspect="auto", vmin=0, vmax=100)

    ax1.set_xticks(np.arange(len(contractor_cols)))
    ax1.set_yticks(np.arange(len(borrowers)))
    ax1.set_xticklabels(contractor_cols, fontsize=10.2, fontweight="bold", color=C_TEXT)
    ax1.set_yticklabels(borrowers, fontsize=10.5, fontweight="bold", color=C_TEXT)
    ax1.tick_params(top=False, bottom=True, labeltop=False, labelbottom=True)

    # White gridlines between heatmap cells
    ax1.set_xticks(np.arange(len(contractor_cols) + 1) - 0.5, minor=True)
    ax1.set_yticks(np.arange(len(borrowers) + 1) - 0.5, minor=True)
    ax1.grid(which="minor", color="white", linestyle="-", linewidth=2.2)
    ax1.tick_params(which="minor", bottom=False, left=False)
    for sp in ax1.spines.values():
        sp.set_visible(False)

    # Annotate every cell with Share % and ($Amount 亿)
    for i in range(len(borrowers)):
        for j in range(len(contractor_cols)):
            val_amt = amt_mat[i, j]
            val_pct = pct_mat[i, j]
            if val_amt >= 0.01:
                txt_col = "white" if val_pct >= 45.0 else "#0F172A"
                fw = "bold" if val_pct >= 15.0 or (i == 0 and j in (0, 1)) else "normal"
                cell_str = f"{val_pct:.1f}%\n(${val_amt:.2f}亿)"
            else:
                txt_col = "#94A3B8"
                fw = "normal"
                cell_str = "—"
            ax1.text(j, i, cell_str, ha="center", va="center", fontsize=9.2, fontweight=fw, color=txt_col)

    cbar = fig.colorbar(im, ax=ax1, fraction=0.025, pad=0.02)
    cbar.ax.tick_params(labelsize=10)
    cbar.set_label("占该借款成员采购合同总额比例 (%)", fontsize=10.5, fontweight="bold", color=C_TEXT)

    ax1.set_title(
        "(a) 亚投行主要借款成员×中标承包商国籍二维热力图（格内为占该国采购额比重与金额，对比印度95.5%本国中标与他国流向）",
        fontsize=13.0, fontweight="bold", color=C_TEXT, pad=12, loc="left"
    )

    # --- Bottom Panel (b): Annual Contract Awards in India vs Bank-wide, and Chinese Wins in India (2016-2025) ---
    years = ["2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"]
    ind_yr_amt = np.array([0.0007, 1.5475, 4.9188, 5.1997, 11.4256, 36.2804, 21.8169, 9.7541, 10.6986, 1.2521])
    tot_yr_amt = np.array([0.0080, 1.8323, 2.3832, 8.8595, 22.9056, 51.0691, 45.2849, 44.3666, 61.9690, 27.3247])
    rest_yr_amt = np.maximum(tot_yr_amt - ind_yr_amt, 0.0)
    chn_in_ind = np.array([0.0, 0.0, 0.0, 0.0, 2.1181, 0.3360, 0.0, 0.0, 0.0, 0.0])

    x2 = np.arange(len(years))
    w2 = 0.50
    ax2.bar(x2, ind_yr_amt, width=w2, color=C_NAVY, alpha=0.90, label="印度项目年度授标金额（累计102.89亿美元，占全行38.68%）", zorder=3)
    ax2.bar(x2, rest_yr_amt, width=w2, bottom=ind_yr_amt, color="#CBD5E1", alpha=0.80, label="全行其余成员项目年度授标金额（累计163.11亿美元）", zorder=3)

    setup_ax(ax2, title="(b) 2016—2025年印度项目年度合同授标规模及中资企业在印中标额演变（2022—2025年归零）", xlabel="合同签署年份", ylabel="年度合同授标金额（亿美元）")
    ax2.set_xticks(x2)
    ax2.set_xticklabels(years, fontsize=11, fontweight="bold")
    ax2.set_ylim(0, 74)

    for i in range(1, len(years)):
        top_y = ind_yr_amt[i] + rest_yr_amt[i]
        y_pad = 4.2 if i == 1 else (2.2 if i == 2 else 0.9)
        ax2.text(
            x2[i], top_y + y_pad,
            f"印${ind_yr_amt[i]:.1f}亿",
            ha="center", va="bottom", fontsize=9.2, fontweight="bold", color=C_NAVY, zorder=5
        )

    ax2_r = ax2.twinx()
    ax2_r.spines["top"].set_visible(False)
    ax2_r.spines["right"].set_color(C_RED)
    ax2_r.tick_params(axis="y", colors=C_RED, labelsize=11)
    ax2_r.set_ylabel("中资企业在印项目中标金额（亿美元）", fontsize=11.5, fontweight="bold", color=C_RED)
    ax2_r.set_ylim(-0.18, 3.2)

    ax2_r.plot(
        x2, chn_in_ind, color=C_RED, marker="o", markersize=8, linewidth=2.6,
        markerfacecolor="white", markeredgewidth=2.2, label="中资企业在印中标额（含合资，右轴）", zorder=6
    )

    ax2_r.annotate(
        "2020年：$2.12亿\n• 上海隧道工程德里快轨 $1.53亿\n• 新冠抗疫医疗物资采购 $0.59亿",
        xy=(4, 2.1181), xytext=(0.4, 2.32),
        fontsize=9.5, fontweight="bold", color=C_RED,
        bbox=dict(boxstyle="round,pad=0.28", facecolor="#FEF2F2", edgecolor=C_RED, lw=1.0),
        arrowprops=dict(arrowstyle="->", color=C_RED, lw=1.2), zorder=8
    )
    ax2_r.annotate(
        "2021年：$0.34亿\n• 抗疫物资采购 $0.16亿\n• 印中电梯联合体2笔 $0.18亿",
        xy=(5, 0.3360), xytext=(5.35, 1.25),
        fontsize=9.5, fontweight="bold", color=C_RED,
        bbox=dict(boxstyle="round,pad=0.28", facecolor="#FEF2F2", edgecolor=C_RED, lw=1.0),
        arrowprops=dict(arrowstyle="->", color=C_RED, lw=1.2), zorder=8
    )
    ax2_r.annotate(
        "2022—2025年连续4年\n中资在印中标额 = $0.00亿 (0份)",
        xy=(7.5, 0.0), xytext=(6.15, 0.45),
        fontsize=9.5, fontweight="bold", color="#991B1B",
        bbox=dict(boxstyle="round,pad=0.25", facecolor="#FEE2E2", edgecolor="#DC2626", lw=1.0),
        zorder=8
    )

    h1, l1 = ax2.get_legend_handles_labels()
    h2, l2 = ax2_r.get_legend_handles_labels()
    ax2.legend(h1 + h2, l1 + l2, loc="upper left", frameon=True, facecolor="white", edgecolor="#CBD5E1", fontsize=10, ncol=2)

    fig.text(
        0.01, 0.008,
        "数据来源：根据亚投行《2016—2025年项目采购合同授予总表》（3,311份合同、总额266.00亿美元）交叉统计。注：印度企业除在本国项目中标98.25亿美元外，还在孟加拉国（4.77亿美元）等8国中标5.86亿美元。",
        fontsize=9.5, color=C_MUTED
    )
    plt.tight_layout(rect=[0, 0.02, 1, 1], h_pad=2.0)
    out = OUT_DIR / "fig2_7_procurement_heatmap_and_annual.png"
    plt.savefig(out)
    plt.close(fig)
    print("Saved", out)


if __name__ == "__main__":
    make_fig2_1()
    make_fig2_2()
    make_fig2_3()
    make_fig2_4()
    make_fig2_5()
    make_fig2_6()
    make_fig2_7()
    print("All 7 Chapter 2 figures generated successfully.")

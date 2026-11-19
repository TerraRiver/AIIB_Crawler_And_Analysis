"""Generate 5 card-based institutional flowcharts with large, readable typography for Chapter 1."""

from __future__ import annotations

from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

# Configure Chinese font on macOS
plt.rcParams["font.sans-serif"] = [
    "PingFang SC",
    "Heiti TC",
    "STHeiti",
    "Arial Unicode MS",
    "SimHei",
]
plt.rcParams["axes.unicode_minus"] = False

OUT_DIR = Path(__file__).resolve().parent.parent / "reports" / "figures"


def draw_card(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    body: str = "",
    *,
    header_fc: str = "#1F4E78",
    body_fc: str = "#F8FAFC",
    ec: str = "#1F4E78",
    lw: float = 1.5,
    title_fs: float = 11.2,
    body_fs: float = 10.0,
    header_ratio: float = 0.36,
    title_color: str = "white",
    body_color: str = "#0F172A",
):
    """Draw a titled card with a colored header bar and a concise body area."""
    if not body:
        box = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.003,rounding_size=0.012",
            facecolor=header_fc,
            edgecolor=ec,
            linewidth=lw,
            zorder=3,
        )
        ax.add_patch(box)
        ax.text(
            x + w / 2,
            y + h / 2,
            title,
            ha="center",
            va="center",
            fontsize=title_fs,
            fontweight="bold",
            color=title_color,
            linespacing=1.25,
            zorder=4,
        )
        return

    hh = h * header_ratio
    bh = h - hh

    body_box = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.002,rounding_size=0.012",
        facecolor=body_fc,
        edgecolor=ec,
        linewidth=lw,
        zorder=2,
    )
    ax.add_patch(body_box)

    header_box = FancyBboxPatch(
        (x, y + bh),
        w,
        hh,
        boxstyle="round,pad=0.002,rounding_size=0.012",
        facecolor=header_fc,
        edgecolor=ec,
        linewidth=lw,
        zorder=3,
    )
    ax.add_patch(header_box)

    ax.text(
        x + w / 2,
        y + bh + hh / 2,
        title,
        ha="center",
        va="center",
        fontsize=title_fs,
        fontweight="bold",
        color=title_color,
        linespacing=1.18,
        zorder=4,
    )
    ax.text(
        x + w / 2,
        y + bh / 2,
        body,
        ha="center",
        va="center",
        fontsize=body_fs,
        color=body_color,
        linespacing=1.32,
        zorder=4,
    )


def draw_zone(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    label: str = "",
    *,
    fc: str = "#F1F5F9",
    ec: str = "#94A3B8",
    lw: float = 1.2,
    ls: str = "--",
    label_color: str = "#1E293B",
    fontsize: float = 11.0,
):
    """Draw a background container zone."""
    box = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.004,rounding_size=0.015",
        facecolor=fc,
        edgecolor=ec,
        linewidth=lw,
        linestyle=ls,
        zorder=1,
    )
    ax.add_patch(box)
    if label:
        ax.text(
            x + 0.015,
            y + h - 0.025,
            label,
            ha="left",
            va="center",
            fontsize=fontsize,
            fontweight="bold",
            color=label_color,
            zorder=2,
        )


def draw_diamond(
    ax,
    cx: float,
    cy: float,
    w: float,
    h: float,
    text: str,
    *,
    fc: str = "#FEF3C7",
    ec: str = "#B45309",
    lw: float = 1.6,
    fontsize: float = 10.2,
    textcolor: str = "#78350F",
):
    """Draw a decision diamond centered at (cx, cy)."""
    pts = [
        (cx, cy + h / 2),
        (cx + w / 2, cy),
        (cx, cy - h / 2),
        (cx - w / 2, cy),
    ]
    poly = Polygon(pts, closed=True, facecolor=fc, edgecolor=ec, linewidth=lw, zorder=3)
    ax.add_patch(poly)
    ax.text(
        cx,
        cy,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight="bold",
        color=textcolor,
        linespacing=1.25,
        zorder=4,
    )


def draw_arrow(
    ax,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    color: str = "#334155",
    lw: float = 1.7,
    style: str = "-|>",
    linestyle: str = "-",
    label: str = "",
    label_pos: tuple[float, float] | None = None,
    fontsize: float = 9.5,
):
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops=dict(
            arrowstyle=style,
            color=color,
            lw=lw,
            linestyle=linestyle,
            shrinkA=0,
            shrinkB=0,
            mutation_scale=13,
        ),
        zorder=5,
    )
    if label:
        lx, ly = label_pos if label_pos else ((x1 + x2) / 2, (y1 + y2) / 2)
        ax.text(
            lx,
            ly,
            label,
            ha="center",
            va="center",
            fontsize=fontsize,
            color=color,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.20", fc="white", ec=color, lw=0.8, alpha=0.97),
            zorder=6,
        )


def draw_polyline_arrow(
    ax,
    points: list[tuple[float, float]],
    *,
    color: str = "#334155",
    lw: float = 1.7,
    linestyle: str = "-",
    label: str = "",
    label_pos: tuple[float, float] | None = None,
    fontsize: float = 9.5,
):
    for i in range(len(points) - 2):
        p1, p2 = points[i], points[i + 1]
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=color, lw=lw, linestyle=linestyle, zorder=4)
    p_prev, p_last = points[-2], points[-1]
    draw_arrow(
        ax,
        p_prev[0],
        p_prev[1],
        p_last[0],
        p_last[1],
        color=color,
        lw=lw,
        linestyle=linestyle,
        label=label,
        label_pos=label_pos,
        fontsize=fontsize,
    )


def save_clean(fig, out_path: Path) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    fig.savefig(out_path, facecolor="white", dpi=300)
    plt.close(fig)
    return out_path


def fig1_1_legal_and_governance() -> Path:
    """图1-1：亚洲基础设施投资银行内部法律框架层级与治理组织架构关系图"""
    fig, ax = plt.subplots(figsize=(11.5, 6.8), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.5, 0.965,
        "图 1-1  亚洲基础设施投资银行法律层级与治理架构关系图",
        ha="center", va="center", fontsize=14.5, fontweight="bold", color="#0F172A"
    )

    draw_zone(ax, 0.015, 0.03, 0.31, 0.89, "内部法律框架（按效力由高至低）", fc="#F8FAFC", ec="#94A3B8", fontsize=11.0)
    draw_zone(ax, 0.355, 0.03, 0.63, 0.89, "三层治理与日常执行架构（《协定》第21–31条）", fc="#F8FAFC", ec="#94A3B8", fontsize=11.0)

    l_cards = [
        (0.725, "第一层级：基础国际条约", "《亚投行协定》（60条及附件）\n修改须 ≥2/3 理事且 ≥75% 投票权", "#1E3A8A", "#EFF6FF"),
        (0.505, "第二层级：规章与政策", "《附例》《议事规则》《问责框架》\n《融资政策》《环社框架》等", "#1D4ED8", "#EFF6FF"),
        (0.285, "第三层级：行长指令", "《内部法律框架指令》《员工规则》\n《OPF指令》《采购指令》等", "#0369A1", "#F0F9FF"),
        (0.055, "第四层级：细则与指南", "副行长签发《作业细则》（强制）\n《业务指南》（参考适用）", "#475569", "#F8FAFC"),
    ]
    for idx, (y, title, body, h_fc, b_fc) in enumerate(l_cards):
        draw_card(ax, 0.03, y, 0.28, 0.145, title, body, header_fc=h_fc, body_fc=b_fc, ec=h_fc, header_ratio=0.35, title_fs=11.0, body_fs=9.6)
        if idx < len(l_cards) - 1:
            next_y = l_cards[idx + 1][0]
            draw_arrow(ax, 0.17, y, 0.17, next_y + 0.145, label="上位法约束", color="#475569", fontsize=9.0)

    # Right Cards
    draw_card(
        ax, 0.48, 0.725, 0.38, 0.145,
        "理事会（Board of Governors）",
        "106个成员各派1名理事 · 最高权力机关\n保留接纳新成员、增资、选任行长等11项专属权",
        header_fc="#1E3A8A", body_fc="#EFF6FF", ec="#1E3A8A", header_ratio=0.35, title_fs=11.2, body_fs=9.6
    )

    draw_card(
        ax, 0.505, 0.505, 0.33, 0.145,
        "非常驻董事会（Board of Directors）",
        "12名董事（域内9席 + 非域内3席）\n制定重大政策（≥75%票）· 批准战略与预算",
        header_fc="#1D4ED8", body_fc="#EFF6FF", ec="#1D4ED8", header_ratio=0.35, title_fs=10.8, body_fs=9.5
    )
    draw_card(
        ax, 0.368, 0.505, 0.122, 0.145,
        "4个常设委员会",
        "• 审计与风险\n• 预算与人事\n• 政策与战略\n• 道德委员会",
        header_fc="#3B82F6", body_fc="#FFFFFF", ec="#3B82F6", header_ratio=0.30, title_fs=9.5, body_fs=9.0
    )
    draw_card(
        ax, 0.85, 0.505, 0.122, 0.145,
        "独立监督 CEIU",
        "投诉解决、评估\n与廉政局\n（含 PPM 机制）\n向董事会报告",
        header_fc="#7C3AED", body_fc="#F5F3FF", ec="#7C3AED", header_ratio=0.30, title_fs=9.5, body_fs=8.8
    )

    draw_card(
        ax, 0.48, 0.285, 0.38, 0.145,
        "行长（President）与管理层委员会",
        "任期5年 · 兼任董事会主席 · 授权审批项目\n下设：执委会(ExCom) / 初筛委(SC) / 投委会(IC)",
        header_fc="#0369A1", body_fc="#F0F9FF", ec="#0369A1", header_ratio=0.35, title_fs=11.0, body_fs=9.5
    )

    dept_cards = [
        (0.368, "投资业务局\n(IC Groups)", "项目发起、尽调\n与执行监测"),
        (0.520, "政策与战略辖区\n(PSVP / PSG)", "跨部门审查(IDR)\n与政策合规确认"),
        (0.672, "可持续与受托局\n(SFD)", "环评(ESF)审查\n与采购合规监督"),
        (0.824, "财务、司库与风险\n(CFO/TRE/RMD)", "国际发债筹资、\n资金拨付与风控"),
    ]
    for dx, d_title, d_body in dept_cards:
        draw_card(
            ax, dx, 0.055, 0.142, 0.15,
            d_title, d_body,
            header_fc="#0F766E", body_fc="#F0FDFA", ec="#0F766E",
            header_ratio=0.44, title_fs=9.2, body_fs=9.0
        )

    draw_arrow(ax, 0.67, 0.725, 0.67, 0.65, label="授权（除11项保留权）", color="#1E3A8A", fontsize=9.0)
    draw_arrow(ax, 0.49, 0.577, 0.505, 0.577, style="<->", color="#3B82F6")
    draw_arrow(ax, 0.85, 0.577, 0.835, 0.577, style="-|>", color="#7C3AED")
    draw_arrow(ax, 0.67, 0.505, 0.67, 0.43, label="《问责框架》授权", color="#1D4ED8", fontsize=9.0)

    ax.plot([0.439, 0.895], [0.24, 0.24], color="#0369A1", lw=1.6, zorder=4)
    ax.plot([0.67, 0.67], [0.285, 0.24], color="#0369A1", lw=1.6, zorder=4)
    for dx, _, _ in dept_cards:
        cx = dx + 0.071
        draw_arrow(ax, cx, 0.24, cx, 0.205, color="#0369A1", lw=1.5)

    draw_arrow(ax, 0.31, 0.797, 0.48, 0.797, style="<->", linestyle=":", label="缔约", color="#64748B", fontsize=8.8)
    draw_arrow(ax, 0.31, 0.577, 0.368, 0.577, style="<->", linestyle=":", label="制定", color="#64748B", fontsize=8.8)
    draw_arrow(ax, 0.31, 0.357, 0.48, 0.357, style="<->", linestyle=":", label="签发", color="#64748B", fontsize=8.8)
    draw_arrow(ax, 0.31, 0.13, 0.368, 0.13, style="<->", linestyle=":", label="适用", color="#64748B", fontsize=8.8)

    return save_clean(fig, OUT_DIR / "fig1_1_legal_governance_framework.png")


def fig1_2_project_cycle() -> Path:
    """图1-2：亚洲基础设施投资银行项目从初筛到完工评估的六阶段流程图"""
    fig, ax = plt.subplots(figsize=(11.8, 6.8), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.5, 0.965,
        "图 1-2  亚洲基础设施投资银行项目周期六阶段流程与信息披露节点图",
        ha="center", va="center", fontsize=14.5, fontweight="bold", color="#0F172A"
    )

    draw_zone(ax, 0.012, 0.55, 0.976, 0.37, "一、项目周期六阶段主流程与审查主体（ILF-2025-013）", fc="#F8FAFC", ec="#94A3B8", fontsize=10.8)
    draw_zone(ax, 0.012, 0.285, 0.976, 0.235, "二、主权担保融资项目（SBF）信息披露时限", fc="#FFFBEB", ec="#F59E0B", fontsize=10.8)
    draw_zone(ax, 0.012, 0.03, 0.976, 0.225, "三、非主权融资项目（NSBF）披露节点与独立申诉机制", fc="#F0FDF4", ec="#10B981", fontsize=10.8)

    stages = [
        (0.022, "1. 立项初筛", "投资局 + 初筛委(SC)\n• 环社风险初评\n• 纳入滚动储备库", "#1E3A8A"),
        (0.182, "2. 尽调与审查", "多部门 + 投委会(IC)\n• 概念审查→最终审查\n• 或单次合并审查", "#1D4ED8"),
        (0.342, "3. 合规确认", "政策与战略群组(PSG)\n• 核验OPF/ESF合规\n• 偏离须报董事会", "#0284C7"),
        (0.502, "4. 项目审批", "董事会 或 行长授权\n• 董事14日Call-In权\n• 签署《贷款协议》", "#0F766E"),
        (0.662, "5. 采购与执行", "受款人 + 司库 + PMD\n• 全球无国别限制招标\n• 追溯融资≤20%", "#047857"),
        (0.822, "6. 完工与评估", "项目组 + 监督局(CEIU)\n• 编制《完工说明PCN》\n• CEIU独立后评估", "#374151"),
    ]

    for idx, (x, title, body, color) in enumerate(stages):
        draw_card(
            ax, x, 0.575, 0.146, 0.285,
            title, body,
            header_fc=color, body_fc="#FFFFFF", ec=color,
            header_ratio=0.28, title_fs=10.5, body_fs=9.2
        )
        if idx < len(stages) - 1:
            nx = stages[idx + 1][0]
            draw_arrow(ax, x + 0.146, 0.717, nx, 0.717, color="#1E293B", lw=1.7)

    sbf_cards = [
        (0.022, "储备库按季通报", "向董事会通报储备库\n董事可启动Call-In", 0.095),
        (0.182, "概念审查后≤10工作日", "官网首次公开\n《项目摘要（PSI）》", 0.255),
        (0.502, "获批后≤10个工作日", "公开更新版《PSI》\n及《项目文件（PD）》", 0.575),
        (0.662, "分发后≤10个工作日", "官网定期公开\n《监测报告（PIMR）》", 0.735),
        (0.822, "关账后≤10个工作日", "公开《完工说明PCN》\n及CEIU评估报告", 0.895),
    ]
    for x, title, body, arrow_x in sbf_cards:
        draw_card(
            ax, x, 0.305, 0.146, 0.165,
            title, body,
            header_fc="#D97706", body_fc="#FFFFFF", ec="#D97706",
            header_ratio=0.35, title_fs=9.3, body_fs=9.0
        )
        draw_arrow(ax, arrow_x, 0.575, arrow_x, 0.47, color="#D97706", linestyle="--", lw=1.5)

    nsbf_cards = [
        (0.10, "NSBF：最终审查后≤10工作日", "官网首次公开《PSI》\n（晚于SBF概念审查节点）", "#059669"),
        (0.41, "NSBF：获批后≤10个工作日", "仅公开更新版《PSI》\n（因商业保密不公开PD）", "#059669"),
        (0.71, "受影响民众申诉与救济双通道", "项目级申诉机制（GRM）\n亚投行受影响民众机制（PPM）", "#7C3AED"),
    ]
    for x, title, body, color in nsbf_cards:
        draw_card(
            ax, x, 0.048, 0.25, 0.155,
            title, body,
            header_fc=color, body_fc="#FFFFFF", ec=color,
            header_ratio=0.35, title_fs=9.8, body_fs=9.2
        )
    draw_polyline_arrow(ax, [(0.255, 0.575), (0.255, 0.52), (0.174, 0.52), (0.174, 0.203)], color="#059669", linestyle=":")
    draw_polyline_arrow(ax, [(0.52, 0.575), (0.52, 0.52), (0.485, 0.52), (0.485, 0.203)], color="#059669", linestyle=":")
    draw_polyline_arrow(ax, [(0.815, 0.575), (0.815, 0.203)], color="#7C3AED", linestyle=":")

    return save_clean(fig, OUT_DIR / "fig1_2_project_cycle.png")


def fig1_3_accountability_call_in() -> Path:
    """图1-3：《问责框架》项目审批分权与董事“提请审议（Call-In）”判定流程图"""
    fig, ax = plt.subplots(figsize=(11.5, 6.8), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.5, 0.965,
        "图 1-3  《问责框架更新条例》项目审批分权与董事“提请审议（Call-In）”流程图",
        ha="center", va="center", fontsize=14.2, fontweight="bold", color="#0F172A"
    )

    draw_card(
        ax, 0.25, 0.84, 0.50, 0.085,
        "拟议项目完成跨部门审查（IDR）与政策合规确认（PSG）",
        "进入《问责框架更新条例（Sec2022-100）》审批权限判定程序",
        header_fc="#1E3A8A", body_fc="#EFF6FF", ec="#1E3A8A", header_ratio=0.48, title_fs=10.5, body_fs=9.5
    )

    draw_zone(ax, 0.02, 0.525, 0.63, 0.27, "第一步判定：是否触发三类董事会保留事项之一（第2.1条）？", fc="#F8FAFC", ec="#64748B", fontsize=10.5)

    cat_cards = [
        (0.035, "第 I 类：开创先例", "• 成员国首例项目\n• 新行业战略前3例\n• 新金融工具首例\n• 新伙伴政策首例", "#1D4ED8"),
        (0.240, "第 II 类：战略与政策", "• 非域内成员项目\n• 无行业战略项目\n• 需偏离现行政策\n• 国际关系敏感项目", "#1D4ED8"),
        (0.445, "第 III 类：超风险限额", "• 经济资本 > 3,750万\n• 主权融资 > 3亿美元\n• 非主权债 > 1.5亿美元\n• 股权投资 > 3,500万", "#1D4ED8"),
    ]
    for cx, ctitle, cbody, ccolor in cat_cards:
        draw_card(
            ax, cx, 0.54, 0.19, 0.20,
            ctitle, cbody,
            header_fc=ccolor, body_fc="#FFFFFF", ec=ccolor,
            header_ratio=0.28, title_fs=10.0, body_fs=9.1
        )

    draw_arrow(ax, 0.50, 0.84, 0.335, 0.795, color="#1E3A8A", lw=1.7)

    draw_diamond(
        ax, 0.835, 0.66, 0.25, 0.21,
        "第二步判定：\nWB/ADB/EBRD/EIB牵头\n联合融资 且 亚投行\n出资 ≤ 5亿美元？",
        fc="#FEF3C7", ec="#D97706", fontsize=9.5
    )
    draw_arrow(ax, 0.65, 0.66, 0.71, 0.66, label="是", label_pos=(0.68, 0.69), color="#DC2626", fontsize=9.5)

    draw_diamond(
        ax, 0.335, 0.33, 0.39, 0.185,
        "第三步判定：董事“提请审议（Call-In）”\n收到最终摘要后 14个日历日 内，\n任一董事是否书面要求提交董事会？",
        fc="#E0F2FE", ec="#0284C7", textcolor="#0C4A6E", fontsize=9.6
    )
    draw_arrow(ax, 0.335, 0.525, 0.335, 0.422, label="否（未触发）", label_pos=(0.335, 0.475), color="#059669", fontsize=9.2)
    draw_polyline_arrow(
        ax, [(0.71, 0.66), (0.68, 0.66), (0.68, 0.455), (0.335, 0.455), (0.335, 0.422)],
        color="#059669", label="是（联合融资豁免，授权行长）", label_pos=(0.525, 0.482), fontsize=9.0
    )

    draw_card(
        ax, 0.67, 0.245, 0.31, 0.165,
        "归属董事会审议批准（Board）",
        "• 提前至少14天向全体董事提交文件\n• 正式会议或无异议表决（>50%通过）",
        header_fc="#B91C1C", body_fc="#FEF2F2", ec="#B91C1C", header_ratio=0.35, title_fs=10.2, body_fs=9.2
    )
    draw_arrow(ax, 0.835, 0.555, 0.835, 0.41, label="否（非豁免）", label_pos=(0.835, 0.482), color="#B91C1C", fontsize=9.2)
    draw_arrow(ax, 0.53, 0.33, 0.67, 0.33, label="是（Call-In）", label_pos=(0.60, 0.365), color="#B91C1C", fontsize=9.2)

    draw_card(
        ax, 0.11, 0.035, 0.44, 0.145,
        "行长行使授权批准项目（President）",
        "• 14日窗口期满无异议，由行长正式签批\n• 与董事会直接批准具有同等法律效力",
        header_fc="#047857", body_fc="#ECFDF5", ec="#047857", header_ratio=0.35, title_fs=10.2, body_fs=9.3
    )
    draw_arrow(ax, 0.335, 0.237, 0.335, 0.18, label="否（14日无异议）", label_pos=(0.335, 0.208), color="#047857", fontsize=9.2)

    draw_card(
        ax, 0.67, 0.035, 0.31, 0.145,
        "董事会事后监督与问责闭环",
        "• 每次董事会例会集中报备已批项目\n• 年度《问责报告》与行长绩效考评",
        header_fc="#6D28D9", body_fc="#F5F3FF", ec="#6D28D9", header_ratio=0.35, title_fs=10.2, body_fs=9.2
    )
    draw_arrow(ax, 0.55, 0.107, 0.67, 0.107, style="<->", label="报备与考评", label_pos=(0.61, 0.14), color="#6D28D9", fontsize=9.0)
    draw_arrow(ax, 0.825, 0.245, 0.825, 0.18, style="<->", color="#6D28D9")

    return save_clean(fig, OUT_DIR / "fig1_3_accountability_call_in.png")


def fig1_4_capital_pool_funding() -> Path:
    """图1-4：亚洲基础设施投资银行双资金池隔离架构与资金循环图"""
    fig, ax = plt.subplots(figsize=(11.8, 7.0), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.5, 0.965,
        "图 1-4  亚洲基础设施投资银行双资金池隔离架构与资金循环图（2026年6月末）",
        ha="center", va="center", fontsize=14.2, fontweight="bold", color="#0F172A"
    )

    draw_zone(ax, 0.012, 0.44, 0.976, 0.49, "第一资金池：普通资本资源（OCR，第8–9条 · 总资产 692.25 亿美元）", fc="#F8FAFC", ec="#1E3A8A", fontsize=10.8)

    draw_card(
        ax, 0.025, 0.695, 0.215, 0.165,
        "实缴股本（20%）",
        "实收 195.21 亿美元\n可自由兑换货币入账\n无付息成本核心权益",
        header_fc="#1E3A8A", body_fc="#FFFFFF", ec="#1E3A8A", header_ratio=0.32, title_fs=10.2, body_fs=9.2
    )
    draw_card(
        ax, 0.025, 0.475, 0.215, 0.165,
        "待缴股本（80%）",
        "已认缴 781.11 亿美元\n日常不缴现、不放贷\n第五顺位偿债担保",
        header_fc="#3B82F6", body_fc="#FFFFFF", ec="#3B82F6", header_ratio=0.32, title_fs=10.2, body_fs=9.2
    )

    draw_card(
        ax, 0.275, 0.475, 0.215, 0.165,
        "AAA 最高信用评级",
        "优先债权人地位(PCS)\n巴塞尔 0% 风险权重\n法定放贷 ≤ 100%权益",
        header_fc="#D97706", body_fc="#FFFBEB", ec="#D97706", header_ratio=0.32, title_fs=10.2, body_fs=9.2
    )
    draw_card(
        ax, 0.275, 0.695, 0.215, 0.165,
        "国际债券市场发债",
        "存续余额 434.14 亿美元\n美元全球债 / 熊猫债等\n2026额度 110 亿美元",
        header_fc="#047857", body_fc="#ECFDF5", ec="#047857", header_ratio=0.32, title_fs=10.2, body_fs=9.2
    )

    draw_card(
        ax, 0.525, 0.555, 0.19, 0.26,
        "OCR 核心资金池\n（692.25 亿美元）",
        "• 发债：434.14亿\n  （占 62.7%）\n• 权益：240.48亿\n  （占 34.7%）\n• 其他：17.63亿",
        header_fc="#6D28D9", body_fc="#F5F3FF", ec="#6D28D9", header_ratio=0.32, title_fs=10.0, body_fs=9.2
    )

    ocr_assets = [
        (0.75, 0.75, "司库流动性资金池", "333.24 亿美元（占 48.1%）\n存款与高评级债 · 覆盖≥40%现金流", "#0284C7"),
        (0.75, 0.59, "项目贷款投资净额", "310.90 亿美元（占 44.9%）\n美元可变利差 = SOFR+0.92%~1.42%", "#0F766E"),
        (0.75, 0.455, "债券与股权投资等", "48.11 亿美元（占 7.0%）\n固定收益组合与私募股权基金", "#475569"),
    ]
    for ax_x, ax_y, atitle, abody, acolor in ocr_assets:
        draw_card(
            ax, ax_x, ax_y, 0.225, 0.12,
            atitle, abody,
            header_fc=acolor, body_fc="#FFFFFF", ec=acolor,
            header_ratio=0.35, title_fs=9.8, body_fs=8.7
        )

    draw_arrow(ax, 0.24, 0.557, 0.275, 0.557, color="#3B82F6")
    draw_arrow(ax, 0.382, 0.64, 0.382, 0.695, label="发债", label_pos=(0.42, 0.667), color="#D97706", fontsize=9.0)
    draw_arrow(ax, 0.49, 0.777, 0.525, 0.73, color="#047857")
    draw_polyline_arrow(ax, [(0.24, 0.777), (0.257, 0.777), (0.257, 0.88), (0.62, 0.88), (0.62, 0.815)], label="实缴股本直接注入", label_pos=(0.53, 0.88), color="#1E3A8A", fontsize=9.0)
    draw_arrow(ax, 0.715, 0.75, 0.75, 0.81, color="#6D28D9")
    draw_arrow(ax, 0.715, 0.68, 0.75, 0.65, color="#6D28D9")
    draw_arrow(ax, 0.715, 0.61, 0.75, 0.515, color="#6D28D9")

    ax.plot([0.012, 0.988], [0.395, 0.395], color="#B91C1C", lw=2.0, linestyle="--", zorder=5)
    ax.text(
        0.50, 0.395,
        " 《协定》第10条隔离规定：普通资本资源（OCR）与特别基金资源（SFR）分别立账、独立核算，不得以 OCR 弥补 SFR 亏损 ",
        ha="center", va="center", fontsize=9.5, fontweight="bold", color="#B91C1C",
        bbox=dict(boxstyle="round,pad=0.22", fc="#FEF2F2", ec="#B91C1C", lw=1.2), zorder=6
    )

    draw_zone(ax, 0.012, 0.14, 0.976, 0.22, "第二资金池：特别基金资源（SFR，第17条 · 独立赠款与贴息池）", fc="#F0FDF4", ec="#059669", fontsize=10.8)

    sfr_cards = [
        (0.025, "捐资人自愿无偿捐资", "主权捐资 + 外部伙伴委托资金\n（不计入股本、不产生投票权）", "#059669"),
        (0.365, "五大特别基金窗口", "内部：项目准备(PPSF) / 贴息窗口(SFW)\n外部：MCDF / GIF / 大流行病基金", "#0F766E"),
        (0.705, "前期技术援助与贷款贴息", "无偿技术援助赠款（可研、环评等）\n欠发达成员主权贷款利差减免", "#D97706"),
    ]
    for sx, stitle, sbody, scolor in sfr_cards:
        draw_card(
            ax, sx, 0.158, 0.27, 0.142,
            stitle, sbody,
            header_fc=scolor, body_fc="#FFFFFF", ec=scolor,
            header_ratio=0.35, title_fs=10.0, body_fs=9.0
        )
    draw_arrow(ax, 0.295, 0.23, 0.365, 0.23, label="注入", color="#059669", fontsize=9.0)
    draw_arrow(ax, 0.635, 0.23, 0.705, 0.23, label="拨付", color="#0F766E", fontsize=9.0)

    steps = [
        (0.012, "1. 贷款损失拨备", "ECL拨备 2.69亿美元"),
        (0.210, "2. 当期净收入", "2025净收入 12.23亿"),
        (0.408, "3. 储备与留存收益", "留存收益 45.27亿美元"),
        (0.606, "4. 未动用实缴股本", "实收股本 195.21亿"),
        (0.804, "5. 催缴待缴股本", "向106国催缴 781.11亿"),
    ]
    for idx, (wx, wtitle, wbody) in enumerate(steps):
        draw_card(
            ax, wx, 0.018, 0.184, 0.098,
            wtitle, wbody,
            header_fc="#991B1B" if idx == 4 else "#334155",
            body_fc="#FEF2F2" if idx == 4 else "#F8FAFC",
            ec="#991B1B" if idx == 4 else "#475569",
            header_ratio=0.44, title_fs=9.2, body_fs=8.8
        )
        if idx < len(steps) - 1:
            draw_arrow(ax, wx + 0.184, 0.067, steps[idx + 1][0], 0.067, color="#475569", lw=1.4)

    return save_clean(fig, OUT_DIR / "fig1_4_capital_pool_funding.png")


def fig1_5_voting_power_thresholds() -> Path:
    """图1-5：亚洲基础设施投资银行投票权三元构成与多级表决机制关系图"""
    fig, ax = plt.subplots(figsize=(11.8, 6.8), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.5, 0.965,
        "图 1-5  亚洲基础设施投资银行投票权三元构成、董事选举门槛与四级表决机制图",
        ha="center", va="center", fontsize=14.2, fontweight="bold", color="#0F172A"
    )

    draw_zone(ax, 0.012, 0.03, 0.265, 0.89, "一、投票权三元构成（第28条）", fc="#F8FAFC", ec="#94A3B8", fontsize=10.8)

    v_cards = [
        (0.655, "1. 股份投票权（85.89%）", "每 1 股（10万美元）= 1 票\n全行合计 976,322 票\n对应成员国认缴出资额", "#1E3A8A"),
        (0.365, "2. 基本投票权（12.00%）", "106 个成员平均分配\n每成员固定 1,286 票\n固定稀释大股东权重", "#0F766E"),
        (0.075, "3. 创始成员票（2.11%）", "每个创始成员固定 600 票\n后续新加入成员为 0 票\n体现早期发起缔约贡献", "#D97706"),
    ]
    for vy, vtitle, vbody, vcolor in v_cards:
        draw_card(
            ax, 0.025, vy, 0.238, 0.205,
            vtitle, vbody,
            header_fc=vcolor, body_fc="#FFFFFF", ec=vcolor,
            header_ratio=0.30, title_fs=10.0, body_fs=9.2
        )

    draw_card(
        ax, 0.315, 0.30, 0.215, 0.35,
        "成员国总投票权\n（全行 1,136,676 票）",
        "股本与投票权占比：\n\n"
        "• 中国：股本 30.50%\n  → 投票权 26.37%\n"
        "• 印度：股本 8.57%\n  → 投票权 7.53%\n"
        "• 俄罗斯：股本 6.69%\n  → 投票权 5.91%\n"
        "• 德国：股本 4.60%\n  → 投票权 4.15%",
        header_fc="#1E293B", body_fc="#F8FAFC", ec="#1E293B",
        header_ratio=0.25, title_fs=10.2, body_fs=9.1
    )

    draw_arrow(ax, 0.263, 0.757, 0.315, 0.55, color="#1E3A8A", lw=1.6)
    draw_arrow(ax, 0.263, 0.467, 0.315, 0.467, color="#0F766E", lw=1.6)
    draw_arrow(ax, 0.263, 0.177, 0.315, 0.39, color="#D97706", lw=1.6)

    draw_zone(ax, 0.565, 0.62, 0.422, 0.30, "二、选区董事选举门槛（《协定》附件二）", fc="#F5F3FF", ec="#7C3AED", fontsize=10.8)

    draw_card(
        ax, 0.58, 0.645, 0.19, 0.205,
        "域内董事（9席）\n门槛：域内票 ≥ 6%",
        "中(36.3%)、印(10.4%)、\n俄(8.1%) 均超 6%，\n各自组建单一国家选区\n并直接指派执行董事",
        header_fc="#6D28D9", body_fc="#FFFFFF", ec="#6D28D9",
        header_ratio=0.35, title_fs=9.5, body_fs=8.8
    )
    draw_card(
        ax, 0.785, 0.645, 0.19, 0.205,
        "非域内董事（3席）\n门槛：非域内票 ≥ 15%",
        "无单一非域内国达15%，\n均须联合组建多国选区\n并轮流派任正副董事",
        header_fc="#7C3AED", body_fc="#FFFFFF", ec="#7C3AED",
        header_ratio=0.35, title_fs=9.5, body_fs=8.8
    )

    draw_zone(ax, 0.565, 0.03, 0.422, 0.56, "三、四级多数决表决门槛（《协定》第28条）", fc="#F8FAFC", ec="#94A3B8", fontsize=10.8)

    t_cards = [
        (0.58, 0.315, "1. 简单多数（>50%所投票）", "适用：常规项目审批、年度预算\n日常采取协商一致或无异议程序\n任何单一国均无常规项目否决权", "#2563EB"),
        (0.785, 0.315, "2. 理事会特别多数", "门槛：>1/2理事 且 ≥50%总票数\n适用：接纳新成员、新增融资工具\n溢价增发新股、设立附属机构", "#0D9488"),
        (0.58, 0.055, "3. 董事会四分之三多数", "门槛：代表全行 ≥75% 总投票权\n适用：制定重大业务与财务政策\n按《问责框架》向行长授予审批权", "#D97706"),
        (0.785, 0.055, "4. 理事会超级多数", "门槛：≥2/3理事 且 ≥75%总票数\n适用：增资、下调域内75%下限、\n选任/罢免行长、修改协定等11项", "#B91C1C"),
    ]
    for tx, ty, ttitle, tbody, tcolor in t_cards:
        draw_card(
            ax, tx, ty, 0.19, 0.215,
            ttitle, tbody,
            header_fc=tcolor, body_fc="#FFFFFF", ec=tcolor,
            header_ratio=0.30, title_fs=9.5, body_fs=8.7
        )

    draw_arrow(ax, 0.53, 0.56, 0.565, 0.75, label="选区组阁", color="#6D28D9", fontsize=9.0)
    draw_arrow(ax, 0.53, 0.41, 0.565, 0.31, label="议事表决", color="#1E293B", fontsize=9.0)

    return save_clean(fig, OUT_DIR / "fig1_5_voting_power_thresholds.png")


def main() -> None:
    for fn in (
        fig1_1_legal_and_governance,
        fig1_2_project_cycle,
        fig1_3_accountability_call_in,
        fig1_4_capital_pool_funding,
        fig1_5_voting_power_thresholds,
    ):
        p = fn()
        print(f"Generated: {p} ({p.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()

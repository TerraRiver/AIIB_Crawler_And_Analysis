"""Playwright 页面拟人交互（贝塞尔鼠标轨迹、变速滚轮、指读停顿）与 HTTP 请求节流辅助模块。"""

from __future__ import annotations

import logging
import math
import random
import time
import weakref
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Locator, Page

log = logging.getLogger(__name__)

# 记录每个页面（标签页）当前鼠标所在的坐标，使用 WeakKeyDictionary 避免已关闭标签页残留引用
_MOUSE_POS: weakref.WeakKeyDictionary[Page, tuple[float, float]] = weakref.WeakKeyDictionary()

_FALLBACK_VIEWPORT = (1366.0, 860.0)


# ==============================================================================
# 第一部分：HTTP 请求节流与拟人节奏控制（用于 httpx 批量拉取详情页与 PDF）
# ==============================================================================


class RequestPacer:
    """
    模拟真人连续翻阅网页与下载附件时的节奏控制器：
    1. 单次间隔采用截断正态分布 + 随机长尾停顿，避免固定均匀分布特征。
    2. 每连续请求 burst_size 次后触发一次较长的阅读/整理停顿（Burst Cooldown）。
    3. 自动维护上一跳页面 URL 作为 Referer 请求头。
    """

    def __init__(
        self,
        *,
        base_min: float = 0.25,
        base_max: float = 0.75,
        burst_size: int = 15,
        burst_pause: tuple[float, float] = (1.8, 3.6),
    ) -> None:
        self.base_min = base_min
        self.base_max = base_max
        self.burst_size = max(1, burst_size)
        self.burst_pause = burst_pause
        self.request_count = 0
        self.last_url: str | None = None

    def wait(self, reason: str = "") -> float:
        """执行一次拟人请求间隔等待，返回实际等待秒数。"""
        self.request_count += 1
        if self.request_count % self.burst_size == 0:
            delay = random.uniform(*self.burst_pause)
            log.debug("⏳ 批次冷却等待 %.2fs（已完成 %d 次请求%s）", delay, self.request_count, f"，{reason}" if reason else "")
        else:
            mean = (self.base_min + self.base_max) / 2.0
            sigma = (self.base_max - self.base_min) / 3.0
            delay = max(self.base_min, min(self.base_max * 1.6, random.gauss(mean, sigma)))
            # 12% 概率出现短暂停顿（模拟人眼扫视标题）
            if random.random() < 0.12:
                delay += random.uniform(0.35, 0.95)
        time.sleep(delay)
        return delay

    def build_headers(self, referer: str | None = None) -> dict[str, str]:
        """生成包含上下文 Referer 与客户端提示头的请求头字典。"""
        ref = referer or self.last_url
        headers: dict[str, str] = {
            "Sec-Ch-Ua": '"Chromium";v="131", "Not_A Brand";v="24", "Google Chrome";v="131"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"macOS"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin" if ref else "none",
        }
        if ref:
            headers["Referer"] = ref
        return headers


def human_delay(min_sec: float = 0.25, max_sec: float = 0.8) -> None:
    """带高斯抖动与小概率长尾停顿的通用延迟函数。"""
    mean = (min_sec + max_sec) / 2.0
    sigma = max(0.05, (max_sec - min_sec) / 3.0)
    delay = max(min_sec, min(max_sec * 1.5, random.gauss(mean, sigma)))
    if random.random() < 0.10:
        delay += random.uniform(0.2, 0.6)
    time.sleep(delay)


def compute_backoff_wait(attempt: int, base_sec: float = 2.0, max_sec: float = 60.0) -> float:
    """计算请求失败或触发限流（429/503）时的指数退避等待秒数。"""
    wait = base_sec * (2 ** max(0, attempt - 1)) + random.uniform(0.3, 1.5)
    return min(wait, max_sec)


# ==============================================================================
# 第二部分：Playwright 页面鼠标轨迹、变速滚轮、点击与阅读手势模拟（对齐 X_Crawler）
# ==============================================================================


def viewport_size(page: Page) -> tuple[float, float]:
    """
    获取当前页面可视区域宽高 (width, height)。
    当开启 `no_viewport=True` 时 Playwright 返回 None，此时通过页面内 `window.innerWidth/innerHeight` 读取真实窗口尺寸。
    """
    vs = page.viewport_size
    if vs:
        return float(vs["width"]), float(vs["height"])
    try:
        dims = page.evaluate("() => [window.innerWidth, window.innerHeight]")
        if dims and dims[0] and dims[1]:
            return float(dims[0]), float(dims[1])
    except Exception as exc:
        log.debug("读取窗口尺寸失败：%s", exc)
    return _FALLBACK_VIEWPORT


def human_wait(page: Page, min_ms: int = 800, max_ms: int = 2000, reason: str = "") -> None:
    """在 Playwright 页面中随机暂停等待。"""
    wait_ms = random.randint(min_ms, max_ms)
    log.debug("⏳ 暂停等待 %.2fs%s", wait_ms / 1000.0, f"（{reason}）" if reason else "")
    page.wait_for_timeout(wait_ms)


def _glide(
    page: Page,
    start: tuple[float, float],
    end: tuple[float, float],
    steps: int,
    delay: tuple[int, int],
) -> None:
    """将鼠标从起点分步平滑移向终点，途中带有小幅随机高斯偏移。"""
    (sx, sy), (ex, ey) = start, end
    for i in range(1, steps + 1):
        t = i / steps
        page.mouse.move(
            sx + (ex - sx) * t + random.gauss(0, 0.9),
            sy + (ey - sy) * t + random.gauss(0, 0.9),
        )
        page.wait_for_timeout(random.randint(*delay))
    _MOUSE_POS[page] = end


def human_reset_gaze(page: Page, reason: str = "视线复位") -> None:
    """将鼠标平滑移回页面中上方阅读准备区并更新 _MOUSE_POS。"""
    vw, vh = viewport_size(page)
    reset_x = random.uniform(vw * 0.35, vw * 0.60)
    reset_y = random.uniform(vh * 0.25, vh * 0.45)
    page.mouse.move(reset_x, reset_y, steps=random.randint(12, 22))
    _MOUSE_POS[page] = (reset_x, reset_y)
    log.debug("🔄 %s：鼠标移回 (%.0f, %.0f)", reason, reset_x, reset_y)


def human_idle_reading_gesture(
    page: Page,
    card_locator: Locator,
    text_len: int = 140,
    elapsed_sec: float = 0.0,
) -> None:
    """
    模拟真人在阅读页面段落时的无意识手部动作 + 合理阅读时长补足：
    1. 78% 概率将鼠标滑向目标元素中间偏左的文字区域（模拟指读）。
    2. 按字数计算最短扫读时间，扣除已耗时后补足剩余停顿。
    """
    try:
        box = card_locator.bounding_box()
    except Exception:
        box = None

    if box and random.random() < 0.78:
        start = _MOUSE_POS.get(page, (600.0, 400.0))
        target = (
            box["x"] + box["width"] * random.uniform(0.18, 0.58),
            box["y"] + box["height"] * random.uniform(0.25, 0.72),
        )
        _glide(page, start, target, random.randint(10, 22), (6, 15))

    min_human_read_sec = min(4.0, max(1.8, text_len / random.uniform(130.0, 210.0)))
    remain_sec = min_human_read_sec - elapsed_sec
    if remain_sec > 0.2:
        page.wait_for_timeout(int(remain_sec * 1000) + random.randint(100, 450))


def _ensure_mouse_in_reading_area(
    page: Page,
    vw: float,
    vh: float,
    x_bounds: tuple[float, float] | None,
) -> tuple[float, float]:
    cur = _MOUSE_POS.get(page)
    out_of_area = cur is None or not (vh * 0.15 <= cur[1] <= vh * 0.82)
    if cur is not None and x_bounds is not None:
        out_of_area = out_of_area or not (vw * x_bounds[0] <= cur[0] <= vw * x_bounds[1])
    if out_of_area:
        cur = (random.uniform(vw * 0.35, vw * 0.62), random.uniform(vh * 0.32, vh * 0.58))
        page.mouse.move(cur[0], cur[1], steps=random.randint(10, 18))
        _MOUSE_POS[page] = cur
    return cur  # type: ignore[return-value]


def _hand_drift(
    page: Page,
    cur: tuple[float, float],
    vw: float,
    vh: float,
    margin: float,
) -> tuple[float, float]:
    """60% 概率伴随手握鼠标拨滚轮时的 1~3 像素微漂移。"""
    if random.random() >= 0.60:
        return cur
    x = max(margin, min(vw - margin, cur[0] + random.gauss(0, 1.6)))
    y = max(margin, min(vh - margin, cur[1] + random.gauss(0, 1.2)))
    page.mouse.move(x, y)
    _MOUSE_POS[page] = (x, y)
    return x, y


def human_scroll_to_element(page: Page, locator: Locator, target_desc: str = "") -> None:
    """
    用真实滚轮事件将目标元素滚入屏幕中上方（距顶部 24%~42%，误差 <= 70px）：
    远/中/近三档变速，伴随手部微漂移，25% 概率滚过头再往回拨。
    """
    if target_desc:
        log.debug("📜 滚动页面，将【%s】移入阅读视野", target_desc)
    vw, vh = viewport_size(page)
    cur = _ensure_mouse_in_reading_area(page, vw, vh, None)

    target_band_y = vh * random.uniform(0.24, 0.42)
    scroll_steps = 0
    prev_y: float | None = None
    stalled_steps = 0

    for _ in range(25):
        try:
            box = locator.bounding_box()
        except Exception:
            box = None
        if not box:
            break

        if prev_y is not None and abs(box["y"] - prev_y) < 1.0:
            stalled_steps += 1
            if stalled_steps >= 2:
                break
        else:
            stalled_steps = 0
        prev_y = box["y"]

        diff_y = box["y"] - target_band_y
        abs_diff = abs(diff_y)
        if abs_diff <= 70:
            break

        if abs_diff > 400:
            step_scroll, pause_ms = random.uniform(110, 180), random.randint(25, 55)
        elif abs_diff > 150:
            step_scroll, pause_ms = random.uniform(65, 115), random.randint(40, 85)
        else:
            step_scroll = min(abs_diff * random.uniform(0.6, 0.9), random.uniform(35, 70))
            pause_ms = random.randint(60, 120)

        cur = _hand_drift(page, cur, vw, vh, 100.0)
        page.mouse.wheel(0, step_scroll if diff_y > 0 else -step_scroll)
        scroll_steps += 1
        page.wait_for_timeout(pause_ms)

    if scroll_steps > 0 and random.random() < 0.25:
        tiny_over = random.choice([-1, 1]) * random.uniform(20, 45)
        page.mouse.wheel(0, tiny_over)
        page.wait_for_timeout(random.randint(80, 160))
        page.mouse.wheel(0, -tiny_over * random.uniform(0.7, 1.1))
        page.wait_for_timeout(random.randint(60, 130))


def human_page_scroll(
    page: Page,
    target_distance: float = 1600.0,
    fast_mode: bool = False,
) -> float:
    """
    拟人滚轮下拉浏览页面：
    1. 全程使用真实的 page.mouse.wheel() 分拨次滚动（加速-巡航-减速）。
    2. 鼠标若处于屏幕边缘则先移回正文区；滚动时伴随手部微漂移。
    3. 25% 概率滚过头往回拨。
    """
    vw, vh = viewport_size(page)
    cur = _ensure_mouse_in_reading_area(page, vw, vh, (0.22, 0.78))

    goal = target_distance * random.uniform(0.85, 1.15)
    total_scrolled = 0.0
    flick_count = 0

    while total_scrolled < goal:
        remaining = goal - total_scrolled
        if fast_mode:
            step_scroll, pause_ms = random.uniform(280, 460), random.randint(18, 40)
        elif remaining > 600:
            step_scroll, pause_ms = random.uniform(140, 240), random.randint(30, 68)
        elif remaining > 220:
            step_scroll, pause_ms = random.uniform(85, 145), random.randint(45, 95)
        else:
            step_scroll, pause_ms = max(40.0, remaining * random.uniform(0.65, 1.0)), random.randint(65, 130)

        cur = _hand_drift(page, cur, vw, vh, 120.0)
        page.mouse.wheel(0, step_scroll)
        total_scrolled += step_scroll
        flick_count += 1
        page.wait_for_timeout(pause_ms)

        if not fast_mode and flick_count % random.randint(4, 6) == 0 and random.random() < 0.35:
            page.wait_for_timeout(random.randint(180, 420))

    if not fast_mode and flick_count > 0 and random.random() < 0.25:
        tiny_over = random.uniform(25, 55)
        page.mouse.wheel(0, tiny_over)
        page.wait_for_timeout(random.randint(80, 160))
        back_delta = -tiny_over * random.uniform(0.75, 1.15)
        page.mouse.wheel(0, back_delta)
        total_scrolled += tiny_over + back_delta
        page.wait_for_timeout(random.randint(60, 130))

    return total_scrolled


def _in_viewport(box: dict | None, vh: float) -> bool:
    return bool(box) and box["y"] >= 0 and box["y"] + box["height"] <= vh  # type: ignore[index]


def human_move_and_click(page: Page, locator: Locator, action_desc: str = "目标元素") -> None:
    """
    拟人鼠标轨迹并点击：
    1. 连续起点（记住上次鼠标位置，杜绝从 (0, 0) 瞬移）。
    2. 三阶贝塞尔弧线轨迹，控制点偏移随距离缩放。
    3. Ease-Out 减速瞄准 + 随进度衰减的微颤抖；长距离 30% 概率过冲再拉回。
    4. 悬停瞄准（80~260ms）+ 按压保持（50~140ms）后松开。
    """
    _, vh = viewport_size(page)
    try:
        box = locator.bounding_box()
    except Exception:
        box = None

    if not box or box["y"] < 60 or box["y"] > vh - 80:
        human_scroll_to_element(page, locator, target_desc=action_desc)
        try:
            box = locator.bounding_box()
        except Exception:
            box = None

    if not _in_viewport(box, vh):
        try:
            locator.scroll_into_view_if_needed(timeout=3000)
            page.wait_for_timeout(300)
            box = locator.bounding_box()
        except Exception:
            box = None

    if not _in_viewport(box, vh):
        log.debug("🖱️ 点击【%s】（元素不在可视区域，直接点击）", action_desc)
        locator.click()
        return
    assert box is not None

    start_x, start_y = _MOUSE_POS.get(page, (random.uniform(300, 900), random.uniform(200, 600)))
    target_x = box["x"] + box["width"] * random.uniform(0.3, 0.7)
    target_y = box["y"] + box["height"] * random.uniform(0.3, 0.7)
    dist = math.hypot(target_x - start_x, target_y - start_y)
    steps = max(18, min(55, int(dist / 12) + random.randint(-4, 6)))
    log.debug(
        "🖱️ 点击【%s】：(%.0f, %.0f) → (%.0f, %.0f)，%.0fpx / %d 步",
        action_desc,
        start_x,
        start_y,
        target_x,
        target_y,
        dist,
        steps,
    )

    offset = max(20.0, dist * 0.25)
    c1x = start_x + (target_x - start_x) * random.uniform(0.2, 0.4) + random.uniform(-offset, offset)
    c1y = start_y + (target_y - start_y) * random.uniform(0.2, 0.4) + random.uniform(-offset, offset)
    c2x = start_x + (target_x - start_x) * random.uniform(0.6, 0.8) + random.uniform(-offset, offset)
    c2y = start_y + (target_y - start_y) * random.uniform(0.6, 0.8) + random.uniform(-offset, offset)

    for i in range(1, steps + 1):
        raw_t = i / steps
        t = 1 - math.pow(1 - raw_t, 2.2)
        u = 1 - t
        cur_x = u**3 * start_x + 3 * u**2 * t * c1x + 3 * u * t**2 * c2x + t**3 * target_x
        cur_y = u**3 * start_y + 3 * u**2 * t * c1y + 3 * u * t**2 * c2y + t**3 * target_y
        if i < steps:
            jitter = (1 - raw_t) * 1.8
            cur_x += random.gauss(0, jitter)
            cur_y += random.gauss(0, jitter)
        page.mouse.move(cur_x, cur_y)
        page.wait_for_timeout(int(random.uniform(4, 12) + raw_t * 6))

    if dist > 120 and random.random() < 0.3:
        page.mouse.move(
            target_x + random.uniform(-6, 6),
            target_y + random.uniform(-5, 5),
            steps=random.randint(2, 4),
        )
        page.wait_for_timeout(random.randint(30, 80))
        page.mouse.move(target_x, target_y, steps=random.randint(2, 4))

    page.wait_for_timeout(random.randint(80, 260))
    page.mouse.down()
    page.wait_for_timeout(random.randint(50, 140))
    page.mouse.up()
    _MOUSE_POS[page] = (target_x, target_y)


def human_type_text(page: Page, locator: Locator, text: str, desc: str = "输入框") -> None:
    """先拟人点击聚焦输入框，再以 80~250ms 随机间隔逐字输入。"""
    human_move_and_click(page, locator, desc)
    log.debug("⌨️ 在【%s】逐字输入 %d 个字符", desc, len(text))
    for char in text:
        page.keyboard.type(char)
        page.wait_for_timeout(random.randint(80, 250))

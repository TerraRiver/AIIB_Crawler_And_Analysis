"""浏览器持久化上下文启动与管理。"""

from __future__ import annotations

import logging
from pathlib import Path

from playwright.sync_api import BrowserContext, Playwright
from playwright.sync_api import Error as PlaywrightError

logger = logging.getLogger(__name__)

ANTI_AUTOMATION_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-infobars",
]

INIT_SCRIPT = "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"


def launch_browser_context(
    playwright: Playwright,
    profile_dir: Path,
    *,
    headless: bool = True,
) -> BrowserContext:
    """优先使用本机 Google Chrome 启动持久化上下文；若未安装则回退至内置 Chromium。"""
    profile_dir.mkdir(parents=True, exist_ok=True)
    common_kwargs = {
        "user_data_dir": str(profile_dir),
        "headless": headless,
        "viewport": {"width": 1366, "height": 860},
        "args": ANTI_AUTOMATION_ARGS,
    }

    try:
        context = playwright.chromium.launch_persistent_context(channel="chrome", **common_kwargs)
        logger.debug("已使用系统 Google Chrome 启动浏览器上下文")
    except PlaywrightError:
        logger.info("[*] 未检测到系统 Chrome 或启动失败，回退至 Playwright 内置 Chromium")
        context = playwright.chromium.launch_persistent_context(**common_kwargs)

    context.add_init_script(INIT_SCRIPT)
    return context

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from urllib.parse import urljoin

import httpx
import trafilatura
from bs4 import BeautifulSoup
from markdownify import markdownify as md_convert
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
DOC_PATH = ROOT / "docs/08_thinktank_and_media_analysis_india_aiib.md"
OUT_MD_DIR = ROOT / "papers/thinktank_media_57_md"
OUT_PDF_DIR = ROOT / "papers/thinktank_media_57_pdf"

# Exact verified canonical URLs resolved from Google Vertex grounding redirects
VERIFIED_URL_OVERRIDES: dict[int, str] = {
    1: "https://www.orfonline.org/expert-speak/perception-matters-how-chinese-funding-impacts-beijings-image-in-india",
    2: "https://www.orfonline.org/expert-speak/china-and-the-asian-infrastructure-investment-bank-55693",
    3: "https://www.gatewayhouse.in/the-new-multilateral-financial-architecture/",
    4: "https://idsa.in/publisher/strategic-analysis/multilateral-initiatives-and-security-dilemma-explaining-indias-choice-to-join-the-asian-infrastructure-investment-bank-aiib",
    5: "https://icsin.org/blogs/2016/02/15/analyzing-the-establishment-of-and-responses-to-the-asian-infrastructure-investment-bank/",
    6: "https://www.isas.nus.edu.sg/papers/383-aiib-oco-a-test-for-china-india-cooperation/",
    7: "https://www.cfr.org/articles/why-washington-should-care-about-indias-support-aiib",
    8: "https://www.cgdev.org/blog/aiib-growing-pains-and-opportunities-three-takeaways",
    9: "https://www.cigionline.org/publications/china-international-financial-system-study-ndb-and-aiib/",
    10: "https://www.chathamhouse.org/2025/04/how-china-india-relations-will-shape-asia-and-global-order",
    11: "https://www.chathamhouse.org/2025/10/how-can-aiib-help-deliver-new-climate-finance-goal",
    12: "https://www.brookings.edu/articles/welcome-the-new-aiib/",
    13: "https://www.brookings.edu/articles/india-and-g20-how-india-can-reshape-world-economic-and-financial-order/",
    14: "https://carnegieendowment.org/posts/2016/11/india-and-japan-come-together-again",
    15: "https://www.stimson.org/2015/china-aiib-challenges/",
    16: "https://www.lowyinstitute.org/the-interpreter/sco-summit-marks-steady-rise-india-china-s-worldview",
    17: "https://www.iseas.edu.sg/media/commentaries/covid-19-and-the-development-banks-more-of-the-same/",
    18: "https://cenfa.org/press-release-after-world-bank-aiib-pulls-out-of-amaravati-capital-city-project/",
    19: "https://cenfa.org/projects-in-focus/amaravati-capital-city-project/",
    20: "https://cenfa.org/videos/amaravati-the-price-of-a-dream-city/",
    21: "https://cenfa.org/videos/violations-inspection-panels-report-and-state-repression-in-the-amaravati-capital-city-project/",
    22: "https://cenfa.org/events/infrastructure-and-development-case-of-amravati-capital-city/",
    23: "https://re-course.org/newsupdates/aiib-warned-to-tread-carefully-before-turning-its-key-on-indias-mega-infrastructure-development-plans/",
    24: "https://re-course.org/newsupdates/aiib-urged-to-reject-new-200m-investment-in-india/",
    25: "https://www.brettonwoodsproject.org/2018/09/potential-inspection-panel-probe-of-amaravati-land-grab-allegations-deferred-again/",
    26: "https://www.staging.inclusivedevelopment.net/china-global-program/china-global-newsletter-edition-5/",
    27: "https://www.urgewald.org/en/aiib-watch/abfl-sustainable-infrastructure-financing",
    28: "https://www.urgewald.org/en/aiib-watch/north-haven-india-infrastructure-fund-previously-india-infrastructure-fund",
    29: "https://www.urgewald.org/en/aiib-watch/gujarat-rural-roads-project",
    30: "https://thediplomat.com/2018/03/if-india-wont-put-up-with-the-belt-and-road-why-is-it-the-largest-recipient-of-aiib-funds/",
    31: "https://foreignpolicy.com/2015/04/15/is-the-asian-infrastructure-investment-bank-good-for-india-coal-china/",
    32: "https://www.scmp.com/economy/global-economy/article/3136109/china-backed-aiib-maintained-loans-india-during-border",
    33: "https://www.scmp.com/economy/global-economy/article/3095106/china-india-tensions-will-not-influence-aiib-newly-re",
    34: "https://www.scmp.com/news/china/diplomacy-defence/article/2129686/how-india-became-china-led-development-banks-main",
    35: "https://www.scmp.com/comment/opinion/article/3097464/investing-indian-health-care-will-bolster-aiibs-global-ambition",
    36: "https://www.scmp.com/week-asia/politics/article/3098837/china-led-aiib-failing-human-rights-environment-india-and",
    37: "https://scroll.in/latest/973284/india-took-two-loans-of-over-rs-9000-crore-from-china-backed-bank-union-minister-tells-parliament",
    38: "https://indianexpress.com/article/business/aiib-okays-750-million-loan-to-india-for-covid-19-response-6464005/",
    39: "https://indianexpress.com/article/business/economy/urjit-patel-appointed-as-vice-president-of-aiib-replaces-ex-bureaucrat-from-gujarat-7718234/",
    40: "https://www.newindianexpress.com/states/andhra-pradesh/2019/Jul/24/asian-infrastructure-investment-bank-pulls-out-of-amaravati-funding-after-world-bank-snub-2008587.html",
    41: "https://www.thehindu.com/business/Industry/ex-rbi-governor-urjit-patel-appointed-vice-president-of-aiib/article38201191.ece",
    42: "https://www.thehindu.com/news/cities/Kochi/aiib-team-takes-stock-of-kochi-metros-kakkanad-extension-work/article71628013.ece",
    43: "https://www.livemint.com/industry/infrastructure/chinese-firm-gets-contract-for-construction-of-underground-stretch-of-delhi-meerut-rrts-project-11609678855713.html",
    44: "https://www.livemint.com/news/india/asian-infrastructure-investment-bank-withdraws-funding-to-amaravati-project-1563946400320.html",
    45: "https://www.business-standard.com/economy/news/aiib-sees-india-exposure-rising-to-20-billion-over-next-five-years-125073101001_1.html",
    46: "https://www.financialexpress.com/business/banking-finance/nabfid-in-talks-with-ndb-aiib-for-1-bn-credit/4375626/",
    47: "https://www.financialexpress.com/business/infrastructure-aiib-approves-356-67-million-loan-for-chennai-metro-phase-ii-2342046/",
    48: "https://theprint.in/economy/finance-minister-meets-aiib-president-urges-her-to-scale-up-investment/2868150/",
    49: "https://m.thewire.in/article/banking/ex-rbi-governor-urjit-patel-appointed-vp-of-asian-infrastructure-investment-bank",
    50: "https://www.hindustantimes.com/india-news/nirmala-sitharaman-to-lead-delegation-to-qatar-for-two-day-aiib-annual-meeting-101790536076838.html",
    51: "https://swarajyamag.com/analysis/bif-funding-boost-for-chennai-metro-rail-phase-2-aiib-grants-rs2651-cr-loan-for-2609-km-lighthouse-poonamallee-corridor-4",
    52: "https://www.downtoearth.org.in/governance/world-bank-pulls-out-of-amaravati-construction-project-65719",
    53: "https://www.thenewsminute.com/andhra-pradesh/world-bank-drops-300-million-funding-amaravati-andhras-capital-city-105698",
    54: "https://www.aljazeera.com/news/2019/10/12/as-modi-xi-wrap-summit-in-indian-temple-town-differences-remain",
    55: "https://www.aiib.org/en/who-we-are/about-aiib/leadership/Ajay-Bhushan-Pandey.html",
    56: "https://ai.economictimes.com/news/economy/finance/aiib-sees-india-exposure-growing-to-usd-20-bn-in-5-yrs-from-usd-12-bn/articleshow/123019696.cms",
    57: "https://www.livemint.com/economy/aiib-india-sovereign-infrastructure-project-pipeline-ajay-bhushan-pandey-renewable-energy-china-india-11753793962484.html",
}


def safe_filename(idx: int, source: str, title: str) -> str:
    src_short = re.sub(r"[^A-Za-z0-9\u4e00-\u9fa5]+", "_", source).strip("_")[:20]
    title_short = re.sub(r"[^A-Za-z0-9\u4e00-\u9fa5]+", "_", title).strip("_")[:55]
    return f"{idx:02d}_{src_short}_{title_short}.md"


def extract_from_html(html: str, url: str) -> str:
    # 1. Try trafilatura with recall favored
    text = trafilatura.extract(
        html,
        url=url,
        output_format="markdown",
        include_links=True,
        include_tables=True,
        favor_recall=True,
    ) or ""

    # 2. Check JSON-LD for articleBody / description (especially useful for SCMP, Indian Express, Business Standard, etc.)
    soup = BeautifulSoup(html, "html.parser")
    json_ld_bodies = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    if "@graph" in item and isinstance(item["@graph"], list):
                        items.extend(item["@graph"])
                    body = item.get("articleBody") or item.get("text")
                    desc = item.get("description") or item.get("headline")
                    if body and isinstance(body, str) and len(body) > 150:
                        json_ld_bodies.append(body.strip())
                    elif desc and isinstance(desc, str) and len(desc) > 150:
                        json_ld_bodies.append(desc.strip())
        except Exception:
            pass

    # 3. Check __NEXT_DATA__ or Apollo state (used by SCMP, Livemint, etc.)
    next_data_bodies = []
    next_script = soup.find("script", id="__NEXT_DATA__")
    if next_script and next_script.string:
        try:
            nd = json.RawDecoder().raw_decode(next_script.string.strip())[0]
            nd_str = json.dumps(nd, ensure_ascii=False)
            # Extract long text paragraphs from JSON if needed
            matches = re.findall(r'"(?:text|value|body|content|summary|lead)"\s*:\s*"([^"]{80,})"', nd_str)
            if matches:
                cleaned = [m.encode("utf-8").decode("unicode_escape", errors="ignore") for m in matches]
                next_data_bodies.append("\n\n".join(cleaned))
        except Exception:
            pass

    # 4. Fallback to BeautifulSoup main/article markdownify
    bs_md = ""
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "form", "iframe"]):
        tag.decompose()
    main_node = soup.find("article") or soup.find("main") or soup.find("div", class_=re.compile(r"article|content|post|entry|story", re.I)) or soup.body
    if main_node:
        bs_md = md_convert(str(main_node), heading_style="ATX").strip()
        bs_md = re.sub(r"\n{3,}", "\n\n", bs_md)

    candidates = [text]
    if json_ld_bodies:
        candidates.append("\n\n".join(json_ld_bodies))
    if next_data_bodies:
        candidates.append("\n\n".join(next_data_bodies))
    if len(bs_md) > len(text) * 1.2 and len(text) < 1000:
        candidates.append(bs_md)

    best = max(candidates, key=lambda s: len(s.strip()))
    return best.strip()


def find_pdf_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    pdfs = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if ".pdf" in href.lower():
            full = urljoin(base_url, href)
            if full not in pdfs:
                pdfs.append(full)
    return pdfs


async def main():
    OUT_MD_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PDF_DIR.mkdir(parents=True, exist_ok=True)

    # Parse 57 rows and update DOC_PATH with verified URLs
    md_text = DOC_PATH.read_text(encoding="utf-8")
    rows = []
    new_lines = []
    for line in md_text.splitlines():
        m = re.match(
            r"^(\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*)\[([^\]]+)\]\((https?://[^\)]+)\)(\s*\|.*)$",
            line.strip(),
        )
        if m:
            prefix, idx_s, source, title, note, link_text, old_url, suffix = m.groups()
            idx = int(idx_s)
            real_url = VERIFIED_URL_OVERRIDES.get(idx, old_url.strip())
            rows.append((idx, source.strip("* "), title.strip("* "), note.strip(), real_url))
            new_lines.append(f"{prefix}[{real_url}]({real_url}){suffix}")
        else:
            new_lines.append(line)

    DOC_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"Updated {len(rows)} canonical URLs in {DOC_PATH.name}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    results = {}
    pdf_downloads = []

    # Step 1: Fast pass with httpx
    sem = asyncio.Semaphore(10)
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=25.0, verify=False) as client:
        async def fetch_httpx(row):
            idx, source, title, note, url = row
            async with sem:
                try:
                    r = await client.get(url)
                    if r.status_code == 200:
                        body = extract_from_html(r.text, str(r.url))
                        pdfs = find_pdf_links(r.text, str(r.url))
                        return idx, r.status_code, body, pdfs, str(r.url)
                    return idx, r.status_code, "", [], str(r.url)
                except Exception as e:
                    return idx, 0, f"ERR:{e}", [], url

        httpx_res = await asyncio.gather(*(fetch_httpx(r) for r in rows))

    need_playwright = []
    for row, (idx, code, body, pdfs, final_url) in zip(rows, httpx_res):
        if code == 200 and len(body) >= 600 and not body.startswith("ERR:"):
            results[idx] = (row, body, pdfs, final_url, "httpx")
        else:
            need_playwright.append((row, code, len(body)))

    print(f"httpx succeeded (>=600 chars): {len(results)}/57. Fallback to Playwright for {len(need_playwright)} items.")

    # Step 2: Playwright pass for remaining items
    if need_playwright:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                viewport={"width": 1440, "height": 900},
            )
            await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            pw_sem = asyncio.Semaphore(4)

            async def fetch_pw(row):
                idx, source, title, note, url = row
                async with pw_sem:
                    page = await context.new_page()
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                        await page.wait_for_timeout(2500)
                        html = await page.content()
                        final_url = page.url
                        body = extract_from_html(html, final_url)
                        if len(body) < 400:
                            # Fallback to innerText of body
                            inner = await page.evaluate("() => document.body ? document.body.innerText : ''")
                            if len(inner) > len(body):
                                body = inner.strip()
                        pdfs = find_pdf_links(html, final_url)
                        results[idx] = (row, body, pdfs, final_url, "playwright")
                        print(f"  [PW #{idx:02d}] {len(body)} chars | {title[:45]}")
                    except Exception as e:
                        print(f"  [PW ERR #{idx:02d}] {e} | {url}")
                        results[idx] = (row, "", [], url, f"err:{e}")
                    finally:
                        await page.close()

            await asyncio.gather(*(fetch_pw(r) for r, _, _ in need_playwright))
            await browser.close()

    # Save all 57 Markdown files and check which ones have < 400 chars or downloadable PDFs
    short_items = []
    for idx in sorted(results.keys()):
        row, body, pdfs, final_url, method = results[idx]
        _, source, title, note, orig_url = row
        fname = safe_filename(idx, source, title)
        out_path = OUT_MD_DIR / fname
        if len(body) < 400:
            short_items.append((idx, source, title, orig_url, len(body), method, pdfs))
        md_content = (
            f"# {title}\n\n"
            f"- **序号**: #{idx:02d}\n"
            f"- **来源机构 / 媒体**: {source}\n"
            f"- **作者 / 备注**: {note}\n"
            f"- **原始链接**: [{orig_url}]({orig_url})\n"
            f"- **抓取方式**: `{method}`\n"
            + (f"- **页面内附 PDF 报告链接**: {', '.join(pdfs)}\n" if pdfs else "")
            + "\n---\n\n"
            + (body if body else "*(页面正文待进一步提取)*")
            + "\n"
        )
        out_path.write_text(md_content, encoding="utf-8")

    print(f"\nSaved {len(results)} Markdown files to {OUT_MD_DIR}")
    print(f"Items with < 400 chars: {len(short_items)}")
    for item in short_items:
        print("  SHORT:", item)


if __name__ == "__main__":
    asyncio.run(main())

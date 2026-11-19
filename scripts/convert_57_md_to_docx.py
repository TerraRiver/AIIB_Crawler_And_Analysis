from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
MD_DIR = ROOT / "papers/thinktank_media_57_md"
MINERU_DIR = ROOT / "papers/thinktank_media_57_pdf_mineru_md"
OUT_DOCX_DIR = ROOT / "papers/thinktank_media_57_docx"


def set_cell_bg(cell, hex_color: str) -> None:
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shading)


def set_run_font(run, font_en: str = "Times New Roman", font_zh: str = "微软雅黑", size_pt: float = 11.0, bold: bool = False, italic: bool = False, color: RGBColor | None = None) -> None:
    run.font.name = font_en
    run.font.size = Pt(size_pt)
    run.bold = bold
    run.italic = italic
    if color is not None:
        run.font.color.rgb = color
    rPr = run._r.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:eastAsia"), font_zh)


def configure_doc_styles(doc: Document) -> None:
    for section in doc.sections:
        section.top_margin = Inches(0.9)
        section.bottom_margin = Inches(0.9)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(11)
    rPr = normal._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:eastAsia"), "微软雅黑")


def clean_inline_links(text: str) -> str:
    # Remove markdown image tags pointing to remote URLs or blobs
    text = re.sub(r"!\[[^\]]*\]\((?:https?:|blob:)[^\)]+\)", "", text)
    # Convert [label](url) -> label (or keep url if label == url)
    def repl_link(m: re.Match) -> str:
        label, url = m.group(1).strip(), m.group(2).strip()
        if not label:
            return ""
        if label == url or label.startswith("http"):
            return url
        return label

    text = re.sub(r"\[([^\]]*)\]\(([^\)]+)\)", repl_link, text)
    return text


def add_formatted_runs(p, text: str, base_size: float = 11.0, base_color: RGBColor | None = None, base_italic: bool = False) -> None:
    text = clean_inline_links(text)
    # Tokenize **bold**, *italic*, `code`
    tokens = re.split(r"(\*\*[^*]+\*\*|\*[^*\n]+\*|`[^`\n]+`)", text)
    for tok in tokens:
        if not tok:
            continue
        if tok.startswith("**") and tok.endswith("**") and len(tok) > 4:
            r = p.add_run(tok[2:-2])
            set_run_font(r, size_pt=base_size, bold=True, italic=base_italic, color=base_color)
        elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
            r = p.add_run(tok[1:-1])
            set_run_font(r, size_pt=base_size, bold=False, italic=True, color=base_color)
        elif tok.startswith("`") and tok.endswith("`") and len(tok) > 2:
            r = p.add_run(tok[1:-1])
            set_run_font(r, font_en="Consolas", size_pt=base_size - 0.5, bold=False, italic=base_italic, color=RGBColor(0x1F, 0x4E, 0x79))
        else:
            r = p.add_run(tok)
            set_run_font(r, size_pt=base_size, bold=False, italic=base_italic, color=base_color)


def render_table(doc: Document, table_lines: list[str]) -> None:
    rows_data = []
    for line in table_lines:
        stripped = line.strip().strip("|")
        cells = [c.strip() for c in stripped.split("|")]
        # Skip separator row like :---: | :---
        if all(re.match(r"^[:\-]+$", c.replace(" ", "")) for c in cells if c):
            continue
        rows_data.append(cells)

    if not rows_data:
        return
    num_cols = max(len(r) for r in rows_data)
    table = doc.add_table(rows=len(rows_data), cols=num_cols)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    for r_idx, row in enumerate(rows_data):
        for c_idx in range(num_cols):
            val = row[c_idx] if c_idx < len(row) else ""
            cell = table.cell(r_idx, c_idx)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            if r_idx == 0:
                set_cell_bg(cell, "1F4E79")
                r = p.add_run(clean_inline_links(val).replace("**", ""))
                set_run_font(r, size_pt=9.5, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
            else:
                if r_idx % 2 == 0:
                    set_cell_bg(cell, "F5F8FC")
                add_formatted_runs(p, val, base_size=9.5)


def append_markdown_to_doc(doc: Document, md_text: str, file_prefix: str = "") -> None:
    lines = md_text.splitlines()
    i = 0
    n = len(lines)

    # Find matching MinerU image folder if any
    mineru_img_dirs = list(MINERU_DIR.glob(f"{file_prefix}_*/images")) if file_prefix else []

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^-{3,}$|^\*{3,}$", stripped):
            i += 1
            continue

        # Markdown Table
        if stripped.startswith("|") and stripped.endswith("|") and i + 1 < n and "|" in lines[i + 1]:
            t_lines = []
            while i < n and lines[i].strip().startswith("|"):
                t_lines.append(lines[i])
                i += 1
            render_table(doc, t_lines)
            p_spacer = doc.add_paragraph()
            p_spacer.paragraph_format.space_after = Pt(4)
            continue

        # Headings
        m_h = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if m_h:
            level = len(m_h.group(1))
            h_text = clean_inline_links(m_h.group(2).strip())
            p = doc.add_paragraph()
            sizes = {1: 16.0, 2: 13.5, 3: 12.0, 4: 11.0}
            colors = {
                1: RGBColor(0x1F, 0x4E, 0x79),
                2: RGBColor(0x1F, 0x4E, 0x79),
                3: RGBColor(0x2E, 0x5B, 0x88),
                4: RGBColor(0x33, 0x33, 0x33),
            }
            p.paragraph_format.space_before = Pt(10 if level <= 2 else 6)
            p.paragraph_format.space_after = Pt(4)
            r = p.add_run(h_text.replace("**", ""))
            set_run_font(r, size_pt=sizes.get(level, 11.0), bold=True, color=colors.get(level))
            i += 1
            continue

        # Local MinerU image e.g. ![](images/xxx.jpg)
        m_img = re.match(r"^!\[([^\]]*)\]\((images/[^\)]+)\)$", stripped)
        if m_img and mineru_img_dirs:
            rel_img = m_img.group(2)
            for img_dir in mineru_img_dirs:
                img_path = img_dir.parent / rel_img
                if img_path.exists():
                    try:
                        p_img = doc.add_paragraph()
                        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        p_img.add_run().add_picture(str(img_path), width=Inches(5.2))
                    except Exception:
                        pass
                    break
            i += 1
            continue

        # Blockquote
        if stripped.startswith(">"):
            q_text = stripped.lstrip("> ").strip()
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.3)
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(3)
            add_formatted_runs(p, q_text, base_size=10.5, base_color=RGBColor(0x44, 0x54, 0x6A), base_italic=True)
            i += 1
            continue

        # Bullet list
        m_ul = re.match(r"^[-*•]\s+(.+)$", stripped)
        if m_ul:
            item_text = m_ul.group(1).strip()
            if not item_text:
                i += 1
                continue
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.25)
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            r_bul = p.add_run("• ")
            set_run_font(r_bul, size_pt=10.5, bold=True, color=RGBColor(0x1F, 0x4E, 0x79))
            add_formatted_runs(p, item_text, base_size=10.5)
            i += 1
            continue

        # Numbered list
        m_ol = re.match(r"^(\d+\.)\s+(.+)$", stripped)
        if m_ol:
            num_str, item_text = m_ol.group(1), m_ol.group(2).strip()
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.25)
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            r_num = p.add_run(f"{num_str} ")
            set_run_font(r_num, size_pt=10.5, bold=True, color=RGBColor(0x1F, 0x4E, 0x79))
            add_formatted_runs(p, item_text, base_size=10.5)
            i += 1
            continue

        # Normal paragraph
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(5)
        p.paragraph_format.line_spacing = 1.25
        add_formatted_runs(p, stripped, base_size=11.0)
        i += 1


def main() -> None:
    OUT_DOCX_DIR.mkdir(parents=True, exist_ok=True)
    md_files = sorted(MD_DIR.glob("[0-9][0-9]_*.md"))

    # 1. Convert INDEX.md -> 00_INDEX_57篇核心文献总索引.docx
    idx_md = MD_DIR / "INDEX.md"
    if idx_md.exists():
        doc_idx = Document()
        configure_doc_styles(doc_idx)
        append_markdown_to_doc(doc_idx, idx_md.read_text(encoding="utf-8"))
        doc_idx.save(OUT_DOCX_DIR / "00_INDEX_57篇核心文献总索引.docx")
        print("Saved: 00_INDEX_57篇核心文献总索引.docx")

    # 2. Convert each of the 57 Markdown files to its own .docx AND build a master combined .docx
    master_doc = Document()
    configure_doc_styles(master_doc)
    p_title = master_doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_t = p_title.add_run("“印度参与亚投行（AIIB）”57 篇核心智库与权威媒体文献全集")
    set_run_font(r_t, size_pt=18.0, bold=True, color=RGBColor(0x1F, 0x4E, 0x79))
    master_doc.add_page_break()

    for idx_num, f in enumerate(md_files, 1):
        md_text = f.read_text(encoding="utf-8")
        prefix = f.name[:2]
        out_name = f.with_suffix(".docx").name
        out_path = OUT_DOCX_DIR / out_name

        doc = Document()
        configure_doc_styles(doc)
        append_markdown_to_doc(doc, md_text, file_prefix=prefix)
        doc.save(out_path)

        append_markdown_to_doc(master_doc, md_text, file_prefix=prefix)
        if idx_num < len(md_files):
            master_doc.add_page_break()

        print(f"[{idx_num:02d}/57] Saved: {out_name}")

    master_path = OUT_DOCX_DIR / "00_合集_57篇印度参与亚投行核心智库与权威媒体文献全集.docx"
    master_doc.save(master_path)
    print(f"Saved master compilation: {master_path.name} ({master_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()

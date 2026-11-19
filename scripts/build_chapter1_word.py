"""Build Chapter 1 Word report (reports/01_亚投行制度规定.docx) with native GB/T 7714-2015 footnotes."""

from __future__ import annotations

from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.opc.constants import CONTENT_TYPE as CT, RELATIONSHIP_TYPE as RT
from docx.opc.packuri import PackURI
from docx.opc.part import XmlPart
from docx.shared import Cm, Pt, RGBColor

ROOT_DIR = Path(__file__).resolve().parent.parent
FIG_DIR = ROOT_DIR / "reports" / "figures"
OUT_DOCX = ROOT_DIR / "reports" / "01_亚投行制度规定.docx"
OUT_MD = ROOT_DIR / "docs" / "05_aiib_institutional_framework.md"


class FootnoteManager:
    """Manage native Word bottom-of-page footnotes (word/footnotes.xml) in GB/T 7714-2015 format."""

    def __init__(self, doc: Document) -> None:
        self.doc = doc
        self.footnotes: list[tuple[int, str]] = []
        self._next_id = 1
        self._ensure_footnote_styles()

    def _ensure_footnote_styles(self) -> None:
        styles_elm = self.doc.styles.element
        # Ensure FootnoteReference character style exists
        if styles_elm.find(f".//w:style[@w:styleId='FootnoteReference']", styles_elm.nsmap) is None:
            fn_ref_style = parse_xml(
                f'<w:style {nsdecls("w")} w:type="character" w:styleId="FootnoteReference">'
                '<w:name w:val="footnote reference"/>'
                '<w:basedOn w:val="DefaultParagraphFont"/>'
                '<w:uiPriority w:val="99"/>'
                '<w:semiHidden/>'
                '<w:unhideWhenUsed/>'
                '<w:rPr><w:vertAlign w:val="superscript"/></w:rPr>'
                '</w:style>'
            )
            styles_elm.append(fn_ref_style)

        # Ensure FootnoteText paragraph style exists
        if styles_elm.find(f".//w:style[@w:styleId='FootnoteText']", styles_elm.nsmap) is None:
            fn_txt_style = parse_xml(
                f'<w:style {nsdecls("w")} w:type="paragraph" w:styleId="FootnoteText">'
                '<w:name w:val="footnote text"/>'
                '<w:basedOn w:val="Normal"/>'
                '<w:uiPriority w:val="99"/>'
                '<w:semiHidden/>'
                '<w:unhideWhenUsed/>'
                '<w:pPr>'
                '<w:spacing w:after="40" w:line="240" w:lineRule="auto"/>'
                '</w:pPr>'
                '<w:rPr>'
                '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/>'
                '<w:sz w:val="18"/>'
                '<w:szCs w:val="18"/>'
                '</w:rPr>'
                '</w:style>'
            )
            styles_elm.append(fn_txt_style)

    def add_footnote(self, paragraph, citation_text: str) -> int:
        """Append a native superscript footnote reference to `paragraph` and record its GB/T 7714 text."""
        fn_id = self._next_id
        self._next_id += 1
        self.footnotes.append((fn_id, citation_text))

        run = paragraph.add_run()
        rPr = run._r.get_or_add_rPr()
        rStyle = OxmlElement("w:rStyle")
        rStyle.set(qn("w:val"), "FootnoteReference")
        rPr.append(rStyle)
        vert = OxmlElement("w:vertAlign")
        vert.set(qn("w:val"), "superscript")
        rPr.append(vert)

        fn_ref = OxmlElement("w:footnoteReference")
        fn_ref.set(qn("w:id"), str(fn_id))
        run._r.append(fn_ref)
        return fn_id

    def finalize_part(self) -> None:
        """Build and attach `word/footnotes.xml` to the document package."""
        footnotes_xml_parts = [
            f'<w:footnotes {nsdecls("w", "r")}>',
            '<w:footnote w:type="separator" w:id="-1">'
            '<w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
            '<w:r><w:separator/></w:r></w:p></w:footnote>',
            '<w:footnote w:type="continuationSeparator" w:id="0">'
            '<w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
            '<w:r><w:continuationSeparator/></w:r></w:p></w:footnote>',
        ]

        for fn_id, text in self.footnotes:
            escaped = (
                text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
            )
            fn_item = (
                f'<w:footnote w:id="{fn_id}">'
                '<w:p>'
                '<w:pPr><w:pStyle w:val="FootnoteText"/>'
                '<w:spacing w:after="40" w:line="240" w:lineRule="auto"/></w:pPr>'
                '<w:r>'
                '<w:rPr>'
                '<w:rStyle w:val="FootnoteReference"/>'
                '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/>'
                '<w:sz w:val="18"/><w:szCs w:val="18"/>'
                '<w:vertAlign w:val="superscript"/>'
                '</w:rPr>'
                '<w:footnoteRef/>'
                '</w:r>'
                '<w:r>'
                '<w:rPr>'
                '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/>'
                '<w:sz w:val="18"/><w:szCs w:val="18"/>'
                '</w:rPr>'
                f'<w:t xml:space="preserve"> {escaped}</w:t>'
                '</w:r>'
                '</w:p>'
                '</w:footnote>'
            )
            footnotes_xml_parts.append(fn_item)

        footnotes_xml_parts.append("</w:footnotes>")
        xml_bytes = "".join(footnotes_xml_parts).encode("utf-8")

        partname = PackURI("/word/footnotes.xml")
        content_type = CT.WML_FOOTNOTES
        element = parse_xml(xml_bytes)
        fn_part = XmlPart(partname, content_type, element, self.doc.part.package)
        self.doc.part.relate_to(fn_part, RT.FOOTNOTES)


def configure_document_styles(doc: Document) -> None:
    """Configure A4 page margins and standard Chinese academic typography."""
    for section in doc.sections:
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(2.6)
        section.right_margin = Cm(2.6)

    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(11.0)
    normal.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    normal.paragraph_format.line_spacing = 1.35
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.space_before = Pt(0)


def add_chapter_title(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(14)
    p.paragraph_format.line_spacing = 1.25
    run = p.add_run(text)
    run.bold = True
    run.font.name = "Times New Roman"
    run.font.size = Pt(16.0)
    run.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "黑体")


def add_section_heading(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.line_spacing = 1.25
    run = p.add_run(text)
    run.bold = True
    run.font.name = "Times New Roman"
    run.font.size = Pt(13.5)
    run.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "黑体")


def add_subsection_heading(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.25
    run = p.add_run(text)
    run.bold = True
    run.font.name = "Times New Roman"
    run.font.size = Pt(11.5)
    run.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "黑体")


def add_body_paragraph(
    doc: Document,
    segments: list[tuple[str, str | None]],
    fn: FootnoteManager,
    *,
    indent: bool = True,
):
    """Add a body paragraph composed of `(text_segment, optional_footnote_citation)` tuples."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if indent:
        p.paragraph_format.first_line_indent = Pt(22)
    p.paragraph_format.line_spacing = 1.38
    p.paragraph_format.space_after = Pt(5)

    for text, citation in segments:
        run = p.add_run(text)
        run.font.name = "Times New Roman"
        run.font.size = Pt(11.0)
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
        if citation:
            fn.add_footnote(p, citation)
    return p


def set_cell_background(cell, hex_color: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)


def set_table_borders(table) -> None:
    """Apply clean academic three-line table borders (top/bottom 1.5pt, header bottom 1pt, inner horizontal 0.5pt)."""
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        '<w:top w:val="single" w:sz="12" w:space="0" w:color="1E293B"/>'
        '<w:bottom w:val="single" w:sz="12" w:space="0" w:color="1E293B"/>'
        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        '<w:left w:val="none"/>'
        '<w:right w:val="none"/>'
        '<w:insideV w:val="none"/>'
        '</w:tblBorders>'
    )
    tblPr.append(borders)


def add_styled_table(
    doc: Document,
    caption: str,
    headers: list[str],
    rows: list[list[str]],
    col_widths_cm: list[float] | None = None,
    source_note: str | None = None,
) -> None:
    """Add a three-line academic table with caption and optional source note."""
    cap_p = doc.add_paragraph()
    cap_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap_p.paragraph_format.space_before = Pt(8)
    cap_p.paragraph_format.space_after = Pt(4)
    cap_run = cap_p.add_run(caption)
    cap_run.bold = True
    cap_run.font.name = "Times New Roman"
    cap_run.font.size = Pt(10.0)
    cap_run._element.rPr.rFonts.set(qn("w:eastAsia"), "黑体")

    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table)

    # Header row
    hdr_cells = table.rows[0].cells
    for i, h_text in enumerate(headers):
        cell = hdr_cells[i]
        if col_widths_cm and i < len(col_widths_cm):
            cell.width = Cm(col_widths_cm[i])
        set_cell_background(cell, "1E3A8A")
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.15
        run = p.add_run(h_text)
        run.bold = True
        run.font.name = "Times New Roman"
        run.font.size = Pt(9.5)
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "黑体")

    # Data rows
    for r_idx, r_data in enumerate(rows):
        row_cells = table.rows[r_idx + 1].cells
        bg_color = "F8FAFC" if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, val in enumerate(r_data):
            cell = row_cells[c_idx]
            if col_widths_cm and c_idx < len(col_widths_cm):
                cell.width = Cm(col_widths_cm[c_idx])
            set_cell_background(cell, bg_color)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if len(val) > 14 else WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(2.5)
            p.paragraph_format.space_after = Pt(2.5)
            p.paragraph_format.line_spacing = 1.2
            run = p.add_run(val)
            run.font.name = "Times New Roman"
            run.font.size = Pt(9.0)
            run.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)
            run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")

    if source_note:
        note_p = doc.add_paragraph()
        note_p.paragraph_format.space_before = Pt(2)
        note_p.paragraph_format.space_after = Pt(8)
        note_run = note_p.add_run(f"资料来源：{source_note}")
        note_run.font.name = "Times New Roman"
        note_run.font.size = Pt(8.5)
        note_run.font.color.rgb = RGBColor(0x47, 0x55, 0x69)
        note_run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")


def add_figure(doc: Document, img_path: Path, caption: str, source_note: str) -> None:
    """Embed a high-resolution PNG figure centered on the page with caption and source note."""
    img_p = doc.add_paragraph()
    img_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    img_p.paragraph_format.space_before = Pt(8)
    img_p.paragraph_format.space_after = Pt(2)
    run = img_p.add_run()
    run.add_picture(str(img_path), width=Cm(15.8))

    cap_p = doc.add_paragraph()
    cap_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap_p.paragraph_format.space_before = Pt(2)
    cap_p.paragraph_format.space_after = Pt(2)
    cap_run = cap_p.add_run(caption)
    cap_run.bold = True
    cap_run.font.name = "Times New Roman"
    cap_run.font.size = Pt(9.5)
    cap_run._element.rPr.rFonts.set(qn("w:eastAsia"), "黑体")

    src_p = doc.add_paragraph()
    src_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    src_p.paragraph_format.space_before = Pt(0)
    src_p.paragraph_format.space_after = Pt(8)
    src_run = src_p.add_run(f"资料来源：{source_note}")
    src_run.font.name = "Times New Roman"
    src_run.font.size = Pt(8.5)
    src_run.font.color.rgb = RGBColor(0x47, 0x55, 0x69)
    src_run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")


# Standard GB/T 7714-2015 Footnote Citations
FN = {
    "aoa_purpose": (
        "亚洲基础设施投资银行. 亚洲基础设施投资银行协定: 第1–2条[EB/OL]. "
        "(2015-06-29)[2026-11-08]. https://www.aiib.org/en/about-aiib/basic-documents/_download/articles-of-agreement/basic_document_chinese_bank_articles_of_agreement.pdf."
    ),
    "aoa_membership": (
        "亚洲基础设施投资银行. 亚洲基础设施投资银行协定: 第1条第2款、第3条、第5条第2–3款[EB/OL]. "
        "(2015-06-29)[2026-11-08]. https://www.aiib.org/en/about-aiib/basic-documents/_download/articles-of-agreement/basic_document_chinese_bank_articles_of_agreement.pdf."
    ),
    "cn_report": (
        "Asian Infrastructure Investment Bank. Chief Negotiators' Report on the Articles of Agreement of the Asian Infrastructure Investment Bank: Paragraphs 4–7[EB/OL]. "
        "(2015-06-29)[2026-11-08]. https://www.aiib.org/en/about-aiib/basic-documents/_download/articles-of-agreement/basic_document_report_on_the_articles_of_agreement.pdf."
    ),
    "ilf_directive": (
        "Asian Infrastructure Investment Bank. Directive on the Internal Legal Framework: ILF-2024-001, Sections 4.1–4.5[EB/OL]. "
        "(2024-10-16)[2026-11-08]. https://www.aiib.org/en/about-aiib/who-we-are/role-of-law/.content/index/_download/AIIB-Directive-on-the-Internal-Legal-Framework-20241016.pdf."
    ),
    "aoa_ops": (
        "亚洲基础设施投资银行. 亚洲基础设施投资银行协定: 第11–15条[EB/OL]. "
        "(2015-06-29)[2026-11-08]. https://www.aiib.org/en/about-aiib/basic-documents/_download/articles-of-agreement/basic_document_chinese_bank_articles_of_agreement.pdf."
    ),
    "opf_policy": (
        "Asian Infrastructure Investment Bank. Operational Policy on Financing (as revised through November 26, 2024): Section III & Annexes 1–2[EB/OL]. "
        "(2024-11-26)[2026-11-08]. https://www.aiib.org/en/policies-strategies/_download/operation-policy/AIIB-Operational-Policy-on-Financing_OPF.pdf."
    ),
    "cpbf_paper": (
        "Asian Infrastructure Investment Bank. Paper on AIIB Climate-Focused Policy-Based Financing: Sections II–IV[EB/OL]. "
        "(2024-07-10)[2026-11-08]. https://www.aiib.org/en/what-we-do/Climate-Focused-Policy-Based-Financing/pdf/Paper-on-AIIB-Climate-PBF_For-disclosure_July-10-2024-final.pdf."
    ),
    "equity_strategy": (
        "Asian Infrastructure Investment Bank. Strategy on Investing in Equity: Sections 2–4[EB/OL]. "
        "(2017-06-15)[2026-11-08]. https://www.aiib.org/en/policies-strategies/_download/strategy-investing-equity/Strategy-on-Investing-in-Equity.pdf."
    ),
    "corp_strategy": (
        "Asian Infrastructure Investment Bank. AIIB Corporate Strategy: Financing Infrastructure for Tomorrow (Updated June 2025): Sections 2–5[EB/OL]. "
        "(2025-06-26)[2026-11-08]. https://www.aiib.org/en/policies-strategies/strategies/.content/index/_download/AIIB-Corporate-Strategy.pdf."
    ),
    "bpb_2026": (
        "Asian Infrastructure Investment Bank. Summary of AIIB 2026 Business Plan and Budget: Tables 1–2[EB/OL]. "
        "(2025-12-12)[2026-11-08]. https://www.aiib.org/en/policies-strategies/_download/business-plan-2026/Summary-of-AIIB-2026-Business-Plan-and-Budget.pdf."
    ),
    "nrm_strategy": (
        "Asian Infrastructure Investment Bank. Strategy on Financing Operations in Nonregional Members: Paragraphs 12–21[EB/OL]. "
        "(2026-09-26)[2026-11-08]. https://www.aiib.org/en/policies-strategies/_download/financing-operations/NRM-Strategy_Sep-BOD-Approved_For-Public-Website.pdf."
    ),
    "procurement_policy": (
        "Asian Infrastructure Investment Bank. Procurement Policy: Sections 4–5[EB/OL]. "
        "(2016-01-16)[2026-11-08]. https://www.aiib.org/en/opportunities/business/.content/index/_download/AIIB-PROCUREMENT-POLICY.pdf."
    ),
    "opf_directive": (
        "Asian Infrastructure Investment Bank. Directive on the Operational Policy on Financing: ILF-2025-013, Sections 2–7[EB/OL]. "
        "(2025-05-22)[2026-11-08]. https://www.aiib.org/en/about-aiib/who-we-are/role-of-law/.content/index/_download/Revised-Directive-on-the-Operational-Policy-on-Financing.pdf."
    ),
    "esf_directive": (
        "Asian Infrastructure Investment Bank. Directive on the Environmental and Social Framework: Sections 3–5[EB/OL]. "
        "(2021-05-21)[2026-11-08]. https://www.aiib.org/en/policies-strategies/_download/project-affected/Directive-on-the-Environmental-and-Social-Framework.pdf."
    ),
    "general_conditions": (
        "Asian Infrastructure Investment Bank. General Conditions for Sovereign-backed Loans: Articles II–VIII[EB/OL]. "
        "(2021-10-22)[2026-11-08]. https://www.aiib.org/en/policies-strategies/_download/sovereign-backed/General-Conditions-for-Sovereign-backed-Loans-October-22-2021.pdf."
    ),
    "procurement_directive": (
        "Asian Infrastructure Investment Bank. Directive on Procurement Instructions for Recipients: Sections II–IV[EB/OL]. "
        "(2024-07-26)[2026-11-08]. https://www.aiib.org/en/policies-strategies/_download/operational-directive/AIIB-Directive-on-Procurement-Instructions-for-Recipients-July-26-2024.pdf."
    ),
    "ppm_policy": (
        "亚洲基础设施投资银行. 受影响民众机制政策（2026年官方中文版）: 第2–5节[EB/OL]. "
        "(2026-01-01)[2026-11-08]. https://www.aiib.org/en/policies-strategies/_download/project-affected/Translation-of-Policy/2026-AIIB-Policy-on-the-PPM_Translation-in-Chinese.pdf."
    ),
    "oversight_paper": (
        "Asian Infrastructure Investment Bank. Paper on the Oversight Mechanism: Sections II–IV[EB/OL]. "
        "(2016-01-16)[2026-11-08]. https://www.aiib.org/en/about-aiib/governance/_common/_download/paper-on-the-oversight-mechanism-public.pdf."
    ),
    "aoa_governance": (
        "亚洲基础设施投资银行. 亚洲基础设施投资银行协定: 第21–31条[EB/OL]. "
        "(2015-06-29)[2026-11-08]. https://www.aiib.org/en/about-aiib/basic-documents/_download/articles-of-agreement/basic_document_chinese_bank_articles_of_agreement.pdf."
    ),
    "bylaws_rules": (
        "Asian Infrastructure Investment Bank. By-Laws of the Asian Infrastructure Investment Bank & Rules of Procedure of the Board of Governors[EB/OL]. "
        "(2016-01-16)[2026-11-08]. https://www.aiib.org/en/about-aiib/basic-documents/_download/by-laws-of-the-asian/basic_document_by_laws_of_aiib.pdf."
    ),
    "bod_rules": (
        "Asian Infrastructure Investment Bank. Rules of Procedure of the Board of Directors (as amended through July 10, 2019): Sections 3–7[EB/OL]. "
        "(2019-07-10)[2026-11-08]. https://www.aiib.org/en/about-aiib/basic-documents/_download/rules-of-procedure/rules-of-procedure-of-the-board-of-directors.pdf."
    ),
    "bod_committees": (
        "Asian Infrastructure Investment Bank. Terms of Reference for the Audit and Risk Committee & Terms of Reference for the Policy and Strategy Committee[EB/OL]. "
        "(2020-11-12)[2026-11-08]. https://www.aiib.org/en/about-aiib/basic-documents/_download/rules-of-directors/Asian-Infrastructure-Investment-Bank-Terms-of-Reference-for-the-Audit-and-Risk-Committee.pdf."
    ),
    "president_election": (
        "Asian Infrastructure Investment Bank. Rules for the Election of the President: Sections 2–6[EB/OL]. "
        "(2019-12-09)[2026-11-08]. https://www.aiib.org/en/news-events/news/2020/_download/Rules-for-the-Election-of-the-President-adopted-Dec-2019.pdf."
    ),
    "af_regulation": (
        "Asian Infrastructure Investment Bank. Updated Regulation on the Accountability Framework: Document No. Sec2022-100, Sections 1–4[EB/OL]. "
        "(2023-04-01)[2026-11-08]. https://www.aiib.org/en/about-aiib/governance/_common/_download/Updated-Regulation-on-the-Accountability-Framework_Sec2022-100.pdf."
    ),
    "af_paper": (
        "Asian Infrastructure Investment Bank. Paper on the Accountability Framework: Sections I–III[EB/OL]. "
        "(2018-06-25)[2026-11-08]. https://www.aiib.org/en/about-aiib/governance/_common/_download/paper-on-the-accountabilty-framework.pdf."
    ),
    "aoa_capital": (
        "亚洲基础设施投资银行. 亚洲基础设施投资银行协定: 第4–10条、第16–20条[EB/OL]. "
        "(2015-06-29)[2026-11-08]. https://www.aiib.org/en/about-aiib/basic-documents/_download/articles-of-agreement/basic_document_chinese_bank_articles_of_agreement.pdf."
    ),
    "investor_pres": (
        "Asian Infrastructure Investment Bank. AIIB Investor Presentation (Q3 2026): Pages 8–14, 39–56[EB/OL]. "
        "(2026-08-15)[2026-11-08]. https://www.aiib.org/en/treasury/_common/_download/AIIB-Investor-Presentation.pdf."
    ),
    "fin_stmt_2025": (
        "Asian Infrastructure Investment Bank. AIIB Audited Financial Statements for the Year Ended December 31, 2025: Pages 5–16, Note C & Note D[EB/OL]. "
        "(2026-03-31)[2026-11-08]. https://www.aiib.org/en/about-aiib/financial-statements/.content/index/pdf/AIIB-Financial-Statements-2025-Final.pdf."
    ),
    "alm_policy": (
        "Asian Infrastructure Investment Bank. Asset Liability Management Policy: Section 3[EB/OL]. "
        "(2024-12-09)[2026-11-08]. https://www.aiib.org/en/policies-strategies/_download/alm-policy/asset-liability-management-policy.pdf."
    ),
    "cap_adequacy": (
        "Asian Infrastructure Investment Bank. Directive on Capital Adequacy and Stress Testing: Sections 2–4[EB/OL]. "
        "(2021-07-15)[2026-11-08]. https://www.aiib.org/en/about-aiib/who-we-are/role-of-law/.content/index/_download/AIIB-Directive-on-Capital-Adequacy-and-Stress-Testing.pdf."
    ),
    "sbf_pricing": (
        "Asian Infrastructure Investment Bank. Pricing Policy for Sovereign-Backed Products (revised November 26, 2024) & Sovereign-backed Financing Fact Sheet (July 2026)[EB/OL]. "
        "(2026-07-01)[2026-11-08]. https://www.aiib.org/en/treasury/_common/_download/AIIB_Sovereign-backed-Financing-SBF-FactSheet.pdf."
    ),
    "sf_directive": (
        "Asian Infrastructure Investment Bank. Directive on the Administration of AIIB Special Funds: Sections 3–5 & Annexes 1–2[EB/OL]. "
        "(2024-01-16)[2026-11-08]. https://www.aiib.org/en/about-aiib/who-we-are/role-of-law/.content/index/_download/AIIB-Directive-on-the-Administration-of-AIIB-Special-Funds.pdf."
    ),
    "aoa_voting": (
        "亚洲基础设施投资银行. 亚洲基础设施投资银行协定: 第28条及附件二《董事选举规定》[EB/OL]. "
        "(2015-06-29)[2026-11-08]. https://www.aiib.org/en/about-aiib/basic-documents/_download/articles-of-agreement/basic_document_chinese_bank_articles_of_agreement.pdf."
    ),
}


def build_chapter1_docx() -> tuple[Path, int]:
    doc = Document()
    configure_document_styles(doc)
    fn = FootnoteManager(doc)

    # Chapter Title
    add_chapter_title(doc, "第一章  亚洲基础设施投资银行的制度规定")

    # Introductory paragraph
    add_body_paragraph(
        doc,
        [
            (
                "亚洲基础设施投资银行（Asian Infrastructure Investment Bank，简称“亚投行”或“AIIB”）是由主权国家依据多边国际条约设立的多边开发银行。"
                "2015年6月29日，57个意向创始成员国在北京签署《亚洲基础设施投资银行协定》（以下简称《亚投行协定》）；2015年12月25日，《亚投行协定》满足法定生效条件正式生效，亚投行于2016年1月16日正式开业运营",
                FN["aoa_purpose"],
            ),
            (
                "。根据《内部法律框架指令》（ILF-2024-001），亚投行的制度体系按法律效力由高至低分为四个层级：第一层级为基础国际条约《亚投行协定》；"
                "第二层级为理事会与董事会制定的附例、议事规则、条例与业务财务政策（Policies and Regulations）；"
                "第三层级为行长签发的执行指令与员工规则（Directives and Staff Rules）；"
                "第四层级为副行长或直属部门负责人签发的作业细则（Instructions）与业务指南（Guidelines）",
                FN["ilf_directive"],
            ),
            (
                "。下位制度文件不得与上位制度文件相抵触。本章依据亚投行公开发布的38份制度、政策、指令及经审计财务报表，分别对亚投行的主要功能与业务范围、项目从提出到落地的流程、理事会与董事会的权力及管理层授权边界、资金池与资金来源、投票权的构成与作用五个方面进行客观说明。",
                None,
            ),
        ],
        fn,
    )

    # Embed Figure 1-1
    add_figure(
        doc,
        FIG_DIR / "fig1_1_legal_governance_framework.png",
        "图 1-1  亚洲基础设施投资银行法律层级与治理架构关系图",
        "依据《亚洲基础设施投资银行协定》第21–31条及《内部法律框架指令》（ILF-2024-001）整理绘制。",
    )

    # =========================================================================
    # Section 1.1
    # =========================================================================
    add_section_heading(doc, "1.1  亚投行的主要功能与业务范围")

    add_subsection_heading(doc, "1.1.1  法定宗旨与四大核心功能")
    add_body_paragraph(
        doc,
        [
            (
                "根据《亚投行协定》第1条与第2条，亚投行的法定宗旨是通过在基础设施及其他生产性领域的投资，促进亚洲经济可持续发展、创造财富并改善基础设施互联互通，同时与其他多边和双边开发机构开展合作推进区域合作与伙伴关系",
                FN["aoa_purpose"],
            ),
            (
                "。为实现上述宗旨，《亚投行协定》第2条规定亚投行履行以下四项法定功能：（1）利用自有资金或筹集资金，推动区域内公共和私营资本投向发展领域，优先支持基础设施及其他生产性行业；（2）运用所掌握的资源为亚洲地区发展提供融资，优先支持有助区域和谐经济增长的项目，并兼顾区域内欠发达成员的需求；（3）鼓励私营资本参与投资有助于经济发展特别是基础设施建设的活动、企业和项目，并在私营资本无法以合理条件获得融资时补充私人投资；（4）承担有助于实现银行宗旨的其他活动并提供相关服务。",
                None,
            ),
        ],
        fn,
    )

    add_subsection_heading(doc, "1.1.2  融资对象与六类法定金融工具")
    add_body_paragraph(
        doc,
        [
            (
                "根据《亚投行协定》第11条第1款及《融资业务政策》（Operational Policy on Financing，简称“OPF”），亚投行的合格融资对象包括三类：一是任何成员国政府或其政治分部、政府代理机构；二是在成员国领土内开展业务的实体或企业（包括国有企业与私营企业）；三是致力于区域经济发展的国际或区域性机构与实体",
                FN["aoa_ops"],
            ),
            (
                "。按照融资是否附带成员国主权信用担保，《融资业务政策》将亚投行的业务划分为两大类别：第一类为主权担保融资（Sovereign-backed Financing，简称“SBF”），即由成员国直接作为借款人，或由成员国对借款人的本息偿还义务提供无条件主权担保的融资；第二类为非主权担保融资（Non-sovereign-backed Financing，简称“NSBF”），即在不要求成员国提供主权担保的条件下，直接向主权下级地方政府、国有企业、私营企业、特殊目的公司（SPV）或私募股权基金提供的商业化融资",
                FN["opf_policy"],
            ),
            ("。", None),
        ],
        fn,
    )

    add_body_paragraph(
        doc,
        [
            (
                "在具体金融工具方面，《亚投行协定》第11条第2款、第15条及《融资业务政策》规定了六类融资工具：（1）直接贷款、联合融资或参与贷款，涵盖主权投资项目融资（IPF）、基于结果的融资（Results-based Financing，简称“RBF”，以实现事先约定的“与拨款挂钩的成果指标DLR”作为拨款条件）以及2024年7月设立的“气候导向政策性融资”（Climate-Focused Policy-Based Financing，简称“CPBF”，必须与世界银行或亚洲开发银行联合融资，且在2026—2028年期间占全行年度批准总额的比例不超过20%）",
                FN["cpbf_paper"],
            ),
            (
                "；（2）股权投资（Equity Investment），依据《股权投资战略》直接认购基础设施企业的股权或作为有限合伙人（LP）出资基础设施私募股权基金，原则上不寻求控股股东地位",
                FN["equity_strategy"],
            ),
            (
                "；（3）主权或非主权信用担保（Guarantees），作为第一性债务人或第二性债务人，全部或部分担保用于经济发展之贷款的偿还；（4）根据特别基金协定部署和使用特别基金资源（Special Funds Resources）；（5）向成员及受款人提供有偿或无偿的技术援助（Technical Assistance）；（6）经理事会按特别多数（理事人数过半且代表不少于1/2总投票权）批准的其他融资品种。",
                None,
            ),
        ],
        fn,
    )

    add_subsection_heading(doc, "1.1.3  投资方向与业务范围")
    add_body_paragraph(
        doc,
        [
            (
                "在行业与战略方向上，2025年6月更新的《亚投行企业战略：为明日基础设施融资（2021—2030）》确立了四大专题优先领域：绿色基础设施（Green Infrastructure）、促进互联互通与区域合作（Connectivity and Regional Cooperation）、技术赋能基础设施（Technology-enabled Infrastructure）以及动员私人资本（Private Capital Mobilization）",
                FN["corp_strategy"],
            ),
            (
                "。量化业务指标方面，亚投行规定气候融资（包含气候减缓与气候适应）占年度实际批准融资额的比例须持续高于50%，跨境互联互通项目占比目标为25%—30%，私营部门融资（含非主权融资与直接动员的私人资本）占比目标在2030年达到50%",
                FN["bpb_2026"],
            ),
            ("。", None),
        ],
        fn,
    )

    add_body_paragraph(
        doc,
        [
            (
                "在地理与业务边界上，亚投行受四项制度规则约束：第一，域内成员持股底线规则。《亚投行协定》第1条第2款将成员划分为域内成员（Regional Members，即联合国划定的亚洲和大洋洲地理区域内的成员）与非域内成员（Non-regional Members）；第5条第2款与第3款规定，域内成员持有的认缴股本总额占全行认缴股本总额的比例不得低于75%（除非理事会以至少2/3理事、代表不少于75%总投票权的超级多数另行决定，且《首席谈判代表报告》明确域内持股比例在任何情况下不得低于70%）",
                FN["aoa_membership"],
            ),
            (
                "。第二，非域内成员融资比例上限。根据董事会于2026年9月26日批准的《非域内成员融资业务战略》第19段，亚投行在非域内成员境内开展融资业务的年度批准金额不得超过全行年度融资批准总额的25%，且项目必须符合“促进与亚洲的跨境互联互通、支持亚洲海外投资贸易、或提供应对气候变化与全球卫生安全等全球公共产品”的标准",
                FN["nrm_strategy"],
            ),
            (
                "。第三，化石能源行业排除清单。根据《环境与社会框架》与《能源行业战略》，亚投行不向动力煤开采、燃煤发电与供热以及油气田上游勘探开发项目提供融资。第四，全球无国别限制采购规则。《亚投行协定》第13条第8款与《采购政策》规定，亚投行对使用银行融资采购货物、工程和服务不设任何成员国国别限制，允许来自任何国家（不论该国是否为亚投行成员）的合格企业在公平条件下参与投标",
                FN["procurement_policy"],
            ),
            ("。", None),
        ],
        fn,
    )

    add_styled_table(
        doc,
        "表 1-1  亚洲基础设施投资银行六类法定融资工具与业务边界对照表",
        ["融资工具类别", "制度依据", "适用对象与担保要求", "核心运行规则与比例限制"],
        [
            [
                "1. 主权担保贷款（SBF：IPF / RBF / CPBF）",
                "《协定》第11条；《融资业务政策》附件1",
                "成员国政府，或由成员国提供无条件主权担保的公共/私营机构",
                "统一适用主权贷款定价政策；最长宽限期与期限可达35年（平均到期期限≤20年）；气候政策性融资（CPBF）须与WB/ADB联合融资且2026—2028年占比≤20%",
            ],
            [
                "2. 非主权贷款与债务融资（NSBF Debt）",
                "《协定》第11条；《融资业务政策》附件2",
                "无主权担保的国有企业、私营企业、基础设施SPV、金融机构",
                "按市场化风险定价；在东道国政府未对项目提出异议（No-objection）的前提下，可提供高级贷款、次级贷款、银团B类贷款或认购企业债券",
            ],
            [
                "3. 股权投资（Equity Investment）",
                "《协定》第11条第2款第2项；《股权投资战略》",
                "基础设施企业直接股权、基础设施私募股权基金（LP份额）",
                "由股东权益（Equity）资金匹配支持；不寻求控股地位，单笔股权投资超过3,500万美元须提请董事会审批；投资总额受法定资本充足率约束",
            ],
            [
                "4. 信用担保（Guarantees）",
                "《协定》第11条第2款第3项；《融资业务政策》",
                "主权担保或非主权商业担保（第一性或第二性债务人）",
                "对基础设施贷款或债券的本息偿付提供部分信用担保或主权政治风险担保，计入银行风险敞口与资本占用",
            ],
            [
                "5. 特别基金资源部署（Special Funds）",
                "《协定》第17条；《特别基金管理指令》",
                "欠发达成员政府、主权下级机构或经成员国无异议确认的实体",
                "使用PPSF、MCDF、GIF等提供无偿技术援助赠款（TA），或使用SFW窗口为欠发达成员主权贷款提供最高100个基点的利差减免",
            ],
            [
                "6. 技术援助与咨询服务（Technical Assistance）",
                "《协定》第15条；《特别基金管理指令》附件2",
                "成员国政府、项目筹备机构、区域性发展组织",
                "支持项目可行性研究、环境社会影响评估、采购招标文件编制与机构能力建设；费用可由受款人承担或由特别基金赠款全额资助",
            ],
        ],
        col_widths_cm=[3.2, 3.0, 3.6, 6.0],
        source_note="《亚洲基础设施投资银行协定》第11–17条、《融资业务政策》（2024年11月修订版）及《气候导向政策性融资文件》（2024年7月）。",
    )

    # =========================================================================
    # Section 1.2
    # =========================================================================
    add_section_heading(doc, "1.2  项目从提出到落地的流程")

    add_body_paragraph(
        doc,
        [
            (
                "根据《融资业务政策》及2025年5月22日生效的《融资业务政策执行指令》（ILF-2025-013），亚投行融资项目从立项提出到完工后评估分为六个连续阶段，由投资业务部门、跨部门审查机构、政策合规部门、决策机关与独立监督机构分段履职",
                FN["opf_directive"],
            ),
            ("。图1-2展示了六个阶段的审查流程、负责机构及强制信息披露时限。", None),
        ],
        fn,
    )

    # Embed Figure 1-2
    add_figure(
        doc,
        FIG_DIR / "fig1_2_project_cycle.png",
        "图 1-2  亚洲基础设施投资银行项目周期六阶段流程与信息披露节点图",
        "依据《融资业务政策执行指令》（ILF-2025-013，2025年5月22日生效）第2–7节绘制。",
    )

    add_subsection_heading(doc, "1.2.1  第一阶段：项目选择、排序与立项初筛（Selection, Prioritization and Screening）")
    add_body_paragraph(
        doc,
        [
            (
                "在项目发起阶段，投资业务部门（Investment Client Groups，简称“IC Groups”）指派项目组长（Project Team Leader，简称“PTL”）组建项目团队，与潜在借款人或项目发起方接洽，核实项目的开发目标、建设内容、拟议融资金额及与亚投行《企业战略》的契合度",
                FN["opf_directive"],
            ),
            (
                "。同时，可持续发展与受托解决方案局（Sustainability and Fiduciary Solutions Department，简称“SFD”）协助对项目进行环境与社会风险初筛，依据《环境与社会框架执行指令》将项目划分为四个等级：A类（可能产生重大、不可逆或前所未有的不利环境社会影响）、B类（不利影响有限、局限于特定地点且可通过常规缓解措施消除）、C类（环境社会不利影响极小或无不利影响）以及FI类（通过金融中介机构转贷或投资的项目）",
                FN["esf_directive"],
            ),
            (
                "。随后，项目提交管理层下设的初筛委员会（Screening Committee，简称“SC”）进行初筛审查（Screening Review）。通过初筛审查的项目正式纳入亚投行“滚动投资储备库”（Rolling Investment Pipeline），并由初筛委员会确定后续适用标准的两阶段审查通道（概念审查+最终审查）或快速单次合并审查通道（Single Review）。管理层按季度向董事会通报滚动投资储备库清单。",
                None,
            ),
        ],
        fn,
    )

    add_subsection_heading(doc, "1.2.2  第二阶段：尽职调查与跨部门评估审查（Assessment and Interdepartmental Review）")
    add_body_paragraph(
        doc,
        [
            (
                "项目进入储备库后，项目团队联合各职能部门开展全面尽职调查：经济部门（ECON）评估项目的经济内部收益率与外部性；财务与司库部门（CFO/TRE）核查财务可持续性与融资方案；风险管理部（RMD）评估主权或商业信用风险、市场风险及经济资本占用；可持续发展与受托解决方案局（SFD）审查借款人编制的环境与社会影响评估报告（ESIA）、环境与社会管理计划（ESMP）、征地拆迁安置计划（RP）及采购计划；法律部（LEG）核查东道国法律合规性与《国际关系业务政策》适用情况",
                FN["opf_directive"],
            ),
            (
                "。跨部门审查（Interdepartmental Review，简称“IDR”）由投资委员会（Investment Committee，简称“IC”）或跨部门审查小组（Interdepartmental Review Panel，简称“IDRP”）主持。在两阶段审查通道下，项目先接受概念审查（Concept Review），完成实地评估与尽职调查后再接受评估/最终审查（Appraisal / Final Review）。信息披露节点在此阶段体现出主权与非主权项目的明确区分：根据《融资业务政策执行指令》第5.1条，主权担保融资项目（SBF）必须在通过概念审查（或单次审查）后的10个工作日内在亚投行官网公开《项目摘要信息》（Project Summary Information，简称“PSI”）；非主权融资项目（NSBF）则因商业谈判保密需要，在通过最终审查（或单次审查）后的10个工作日内首次公开《项目摘要信息（PSI）》",
                FN["opf_directive"],
            ),
            ("。", None),
        ],
        fn,
    )

    add_subsection_heading(doc, "1.2.3  第三阶段：政策合规确认（Policy Assurance）")
    add_body_paragraph(
        doc,
        [
            (
                "项目通过跨部门审查并完成与借款人的法律与财务条款谈判后，提交政策与战略群组（Policy and Strategy Group，简称“PSG”）开展独立的政策合规确认（Policy Assurance）。PSG逐项核验项目文件是否完整遵守《融资业务政策》《环境与社会框架》《采购政策》及《公共信息政策》等董事会政策。如果项目因特殊客观情况需要豁免或偏离董事会现行政策中的任何强制性条款（Derogation），PSG必须在文件中明确标注，且该项目不得由行长审批，必须强制提请董事会审议批准",
                FN["opf_directive"],
            ),
            ("。", None),
        ],
        fn,
    )

    add_subsection_heading(doc, "1.2.4  第四阶段：项目批准与法律协议签署（Approval and Legal Agreements）")
    add_body_paragraph(
        doc,
        [
            (
                "完成政策合规确认后，最终项目摘要文件发送全体董事。根据《问责框架更新条例》（Sec2022-100），属于董事会保留审批权限或被任一董事在14个日历日窗口期内行使“提请审议权”（Call-In）的项目，提交董事会审议表决；其余项目由行长行使授权签批。项目获批后的10个工作日内，主权担保融资项目（SBF）在官网同时公开更新版《项目摘要信息（PSI）》与完整的《项目文件》（Project Document，简称“PD”）；非主权融资项目（NSBF）仅公开更新版《项目摘要信息（PSI）》，不对外公开包含商业机密与财务模型的《项目文件（PD）》",
                FN["opf_directive"],
            ),
            (
                "。项目获批后，法律部（LEG）与借款人签署《贷款协议》（Loan Agreement）及《项目协议》。主权担保贷款统一适用《主权贷款通则》（General Conditions for Sovereign-backed Loans），借款人出具国内法律意见书并满足协议约定的生效先决条件后，贷款协议正式生效",
                FN["general_conditions"],
            ),
            ("。", None),
        ],
        fn,
    )

    add_subsection_heading(doc, "1.2.5  第五阶段：项目实施监测、招标采购与资金拨付（Implementation, Procurement and Disbursement）")
    add_body_paragraph(
        doc,
        [
            (
                "项目进入实施期后，受款人负责按照《采购政策》与《受款人采购指令》（2024年7月26日生效）开展工程、货物与咨询服务的招标采购。亚投行根据项目采购风险等级，对大额或复杂合同实施事前审查（Prior Review，即招标文件发布、评标报告确认及合同授予前均须获得亚投行“无异议函”），对中小额合同实施事后抽查（Post Review）",
                FN["procurement_directive"],
            ),
            (
                "。在资金拨付方面，主账房（Office of the Controller，简称“CTL”）与司库（Office of the Treasurer，简称“TRE”）根据工程进度或成果指标核实拨款。根据《融资业务政策执行指令》第6.1条与第6.2条，主权投资项目可申请不超过贷款总额20%的追溯融资（Retroactive Financing），用于报销贷款协议签署前12个月内借款人已支付的合格项目支出；结果导向型项目（RBF）可申请最高25%的预付款（Advances），预付款与签约前已实现成果指标的合并拨付比例最高可达贷款额的30%",
                FN["opf_directive"],
            ),
            (
                "。实施期间，项目组长与投资组合管理局（PMD）定期编制《项目执行监测报告》（Project Implementation Monitoring Report，简称“PIMR”），其中SBF项目的《PIMR》在分发董事会后10个工作日内对外公开。若项目建设对当地社区造成环境或社会损害，受影响民众可向项目级申诉处理机制（GRM）或直接向亚投行独立的“受影响民众机制”（Project-affected People's Mechanism，简称“PPM”）提交问题解决或合规审查申请（在世界银行或亚洲开发银行牵头联合融资且适用其环境社会政策的项目中，则由牵头机构的独立问责机制受理）",
                FN["ppm_policy"],
            ),
            ("。", None),
        ],
        fn,
    )

    add_subsection_heading(doc, "1.2.6  第六阶段：项目完工总结与独立后评估（Completion and Independent Evaluation）")
    add_body_paragraph(
        doc,
        [
            (
                "贷款账户关闭后，投资业务部门的项目团队负责对项目进行全面盘点，编制《项目完工说明》（Project Completion Note，简称“PCN”），核算项目实际完工成本、工期履约情况、发展目标达成度及受托合规情况；主权担保融资项目（SBF）的《PCN》在分发董事会后10个工作日内在官网公开",
                FN["opf_directive"],
            ),
            (
                "。在管理层自我总结之外，独立于管理层并直接向董事会报告的“投诉解决、评估与廉政局”（Complaints-resolution, Evaluation and Integrity Unit，简称“CEIU”）抽样开展《项目学习评估》（Project Learning Review，简称“PLR”）及国别/行业专题评估，独立验证项目成果并向董事会提交评估报告",
                FN["oversight_paper"],
            ),
            ("。", None),
        ],
        fn,
    )

    add_styled_table(
        doc,
        "表 1-2  主权担保融资（SBF）与非主权融资（NSBF）全周期审查及信息披露对比表",
        ["对比维度", "主权担保融资（SBF）", "非主权担保融资（NSBF）"],
        [
            ["借款人与担保条件", "成员国政府直接借款，或由成员国政府提供无条件主权担保", "国有企业、私营企业、SPV或基金借款，不要求成员国提供主权担保"],
            ["东道国政府同意程序", "成员国财政部作为主权代表直接发起并谈判签约", "须按《协定》第13条第3款确认项目所在成员国政府无异议（No-objection）"],
            ["首次信息披露节点", "通过概念审查（Concept Review）后10个工作日内公开《PSI》", "通过最终审查（Final Review）后10个工作日内首次公开《PSI》"],
            ["批准后披露文件范围", "批准后10个工作日内公开更新版《PSI》及完整《项目文件（PD）》", "批准后10个工作日内仅公开更新版《PSI》，不公开《项目文件（PD）》"],
            ["执行期监测报告披露", "《项目执行监测报告（PIMR）》在分发董事会后10个工作日内公开", "《项目执行监测报告（PIMR）》仅供内部管理与董事会监督，不对外公开"],
            ["完工总结报告披露", "《项目完工说明（PCN）》在分发董事会后10个工作日内公开", "完工总结文件因涉及商业保密条款，不对外公开全文"],
            ["追溯融资与预付款上限", "投资项目追溯融资≤贷款额20%；结果导向项目预付款≤25%（合并≤30%）", "按商业贷款协议或银团融资合同约定的提款先决条件拨付"],
        ],
        col_widths_cm=[3.2, 6.3, 6.3],
        source_note="《融资业务政策执行指令》（ILF-2025-013）第5.1条、第6.1–6.2条。",
    )

    # =========================================================================
    # Section 1.3
    # =========================================================================
    add_section_heading(doc, "1.3  理事会与董事会的权力及管理层授权边界")

    add_body_paragraph(
        doc,
        [
            (
                "根据《亚投行协定》第五章（第21条至第31条），亚投行实行“理事会（Board of Governors）—董事会（Board of Directors）—行长（President）及高级管理层”三层治理架构",
                FN["aoa_governance"],
            ),
            ("。", None),
        ],
        fn,
    )

    add_subsection_heading(doc, "1.3.1  理事会的组成、法定人数与11项专属保留权力")
    add_body_paragraph(
        doc,
        [
            (
                "理事会是亚投行的最高权力机关。根据《亚投行协定》第22条至第24条，每个成员国任命正理事（Governor）和副理事（Alternate Governor）各一名（通常由各成员国财政部长或同级别内阁官员担任），任期由任命国自定；副理事仅在正理事缺席时方有表决权。理事会每年举行一次年会，也可应董事会要求或5个以上、代表不少于1/4总投票权的成员请求召开特别会议。理事会会议的法定人数（Quorum）为过半数理事出席，且出席理事代表不少于全行总投票权的2/3。理事与副理事任职期间不在亚投行领取薪酬",
                FN["bylaws_rules"],
            ),
            ("。", None),
        ],
        fn,
    )

    add_body_paragraph(
        doc,
        [
            (
                "《亚投行协定》第23条第1款规定，银行的一切权力归属于理事会；第23条第2款规定，理事会可将其部分或全部权力授权给董事会行使，但以下11项核心宪制权力必须由理事会专属保留，在任何情况下均不得授权给董事会：（1）接纳新成员并确定其加入条件；（2）增加或减少银行的法定股本总额；（3）暂停成员资格；（4）对董事会关于《亚投行协定》解释或适用的决定所引发的申诉作出最终裁决；（5）选举银行董事，以及确定董事、副董事的报酬和费用报销政策；（6）选举银行行长、决定暂停或免去行长职务，以及确定行长的薪酬与任职条件；（7）在审阅审计报告后批准银行的资产负债表和损益表；（8）决定银行储备金以及净收入的留存与分配；（9）修改《亚投行协定》；（10）决定终止银行业务并分配银行资产；（11）《亚投行协定》明确规定归属于理事会的其他特定权力",
                FN["aoa_governance"],
            ),
            ("。", None),
        ],
        fn,
    )

    add_subsection_heading(doc, "1.3.2  非常驻董事会的运作机制与四个常设委员会")
    add_body_paragraph(
        doc,
        [
            (
                "董事会负责指导银行的总体业务运营。根据《亚投行协定》第25条至第27条，董事会由12名非理事担任的董事组成，其中9名由域内成员理事选举产生，3名由非域内成员理事选举产生，董事任期为2年，可连选连任。每名董事任命1名副董事（构成人数达5个及以上成员的选区可任命2名副董事）。董事会会议的法定人数为过半数董事出席，且代表不少于全行总投票权的2/3",
                FN["bod_rules"],
            ),
            (
                "。与世界银行或亚洲开发银行设立常驻总部并领取全额年薪的执行董事会不同，《亚投行协定》第27条第1款规定亚投行董事会实行“非常驻制”（Non-resident basis）：董事和副董事平时不在北京总部常驻办公，亦不在银行领取固定年薪，而是按照《董事会议事规则》第3条每季度至少召开一次定期会议，日常大量议案通过双向实时电子视频会议（Electronic Meeting）、无会表决（Voting without meeting，不少于10天）或无异议程序（Approval in absence of objection，不少于10天）处理",
                FN["bod_rules"],
            ),
            (
                "。根据《亚投行协定》第26条，董事会行使六项主要职权：筹备理事会工作；按照不少于3/4总投票权的多数制定银行重大业务政策与财务政策；决定融资业务或按不少于3/4总投票权的多数将该权力授权给行长；通过监督机制对管理层进行经常性监督；批准企业战略、年度业务计划和预算；设立下属委员会。",
                None,
            ),
        ],
        fn,
    )

    add_body_paragraph(
        doc,
        [
            (
                "为协助非常驻董事会履行专业审查职能，董事会下设四个常设委员会：（1）审计与风险委员会（Audit and Risk Committee），负责审查年度财务报表、内部与外部审计报告、风险偏好声明（RAS）及廉政合规事项；（2）政策与战略委员会（Policy and Strategy Committee），负责在提交董事会全会前审议银行企业战略、行业战略及各项业务政策；（3）预算与人力资源委员会（Budget and Human Resources Committee），负责审查年度行政与资本预算、员工薪酬福利体系及人力资源政策；（4）道德委员会（Ethics Committee），负责处理适用《董事会官员行为准则》的利益冲突与道德规范事项",
                FN["bod_committees"],
            ),
            (
                "。此外，根据《董事会议事规则》第7条，董事会设立“董事会主任”（Dean of the Board of Directors），由与行长不同国籍、任职时间最长的董事担任（任期2年，最多连任两届）；当董事会审议涉及行长利益冲突或针对行长不当行为的议案时，由董事会主任代替行长主持董事会非公开会议（Executive Session）",
                FN["bod_rules"],
            ),
            ("。", None),
        ],
        fn,
    )

    add_subsection_heading(doc, "1.3.3  行长职权与《问责框架》下的项目审批分权及“提请审议（Call-In）”机制")
    add_body_paragraph(
        doc,
        [
            (
                "根据《亚投行协定》第29条与《行长选举规则》，亚投行行长必须为域内成员国国民，由理事会按超级多数（至少2/3理事、代表不少于75%总投票权）选举产生，任期5年，可连任一次",
                FN["president_election"],
            ),
            (
                "。行长是银行的法定代表、全体员工的最高行政主管，并兼任董事会主席（在董事会主持会议期间无投票权，仅在赞成票与反对票完全相等时投决定票）。副行长由行长根据公开、透明、择优的程序提名，由董事会任命。",
                None,
            ),
        ],
        fn,
    )

    add_body_paragraph(
        doc,
        [
            (
                "为明确非常驻董事会与行长在项目融资审批上的权限边界，董事会依据《亚投行协定》第26条第3项制定了《问责框架》（Accountability Framework），最新修订版《问责框架更新条例》（文件号Sec2022-100）于2023年4月1日正式生效",
                FN["af_regulation"],
            ),
            (
                "。该条例第1.1条与第2.1条确立了“原则授权行长、三类例外保留董事会、牵头多边银行联合融资豁免、董事14日提请审议（Call-In）兜底”的四步审批权限规则：",
                None,
            ),
        ],
        fn,
    )

    add_body_paragraph(
        doc,
        [
            (
                "第一，保留归属董事会直接审批的三类例外项目（条例第2.1条）：（1）第I类“开创先例事项”（Precedent Setting），包括亚投行在某一成员国开展的第1个项目、在某一新获批行业战略下开展的前3个项目、首次使用某项新金融工具的项目、以及首次与某一联合融资伙伴合作且直接适用其政策的项目；（2）第II类“涉及重大战略或政策事项”（Strategic or Policy Issues），包括在非域内成员境内开展的任何项目、在尚未制定行业战略的行业开展的项目、需要偏离或豁免董事会现行政策（Derogation）的项目、以及触发《国际关系业务政策》敏感条款的项目；（3）第III类“超过风险或单笔金额上限事项”（Risk Thresholds），包括单项目经济资本占用（Economic Capital Utilization）超过3,750万美元的项目，或主权担保融资（SBF）超过3亿美元、非主权债务或担保融资超过1.5亿美元、股权投资超过3,500万美元的项目",
                FN["af_regulation"],
            ),
            ("。", None),
        ],
        fn,
    )

    add_body_paragraph(
        doc,
        [
            (
                "第二，牵头多边开发银行联合融资豁免条款（条例第2.1条首段但书）：即便拟议项目触发上述第I类、第II类或第III类保留标准，只要该项目是与世界银行（WB）、亚洲开发银行（ADB）、欧洲复兴开发银行（EBRD）或欧洲投资银行（EIB）作为牵头机构开展联合融资，且亚投行自身提供的融资金额不超过5亿美元（≤ USD 500 million），其审批权限仍豁免转入行长授权审批通道",
                FN["af_regulation"],
            ),
            ("。", None),
        ],
        fn,
    )

    add_body_paragraph(
        doc,
        [
            (
                "第三，董事“提请审议权”（Call-In Right，条例第4.1.1条）：对于所有进入行长授权审批通道的项目，自该项目纳入滚动投资储备库通知董事会之日起，直至管理层将最终项目摘要文件（Project Summary Document）发送全体董事满14个日历日（14 calendar days）为止，任何一名董事（Any Director）均有权随时提出书面要求，将该授权项目撤回并提交董事会进行正式审议表决，无需其他董事附议。只有在14个日历日窗口期内没有任何董事行使“提请审议权”的情况下，行长方可正式签批该项目。行长批准的项目须在每次董事会例会上集中报备，并通过半年度与年度《业务问责报告》接受董事会的事后监督与年度绩效考评",
                FN["af_paper"],
            ),
            ("。", None),
        ],
        fn,
    )

    # Embed Figure 1-3
    add_figure(
        doc,
        FIG_DIR / "fig1_3_accountability_call_in.png",
        "图 1-3  《问责框架更新条例》项目审批分权与董事“提请审议（Call-In）”流程图",
        "依据《问责框架更新条例》（Sec2022-100，2023年4月1日生效）第1–4节绘制。",
    )

    add_styled_table(
        doc,
        "表 1-3  理事会、董事会与行长的职权划分及《问责框架》项目审批权限表",
        ["治理与执行主体", "人员构成与产生方式", "会议制度与法定人数", "核心专属职权与项目审批权限边界"],
        [
            [
                "理事会\n（Board of Governors）",
                "每个成员国任命正理事、副理事各1名（共106名理事），任期由任命国自定，不在银行领薪",
                "每年召开1次年会；法定人数为过半数理事出席且代表≥2/3总投票权",
                "行使《协定》第23条第2款规定的11项不可授权专属权力（接纳新成员、增减法定股本、选举董事、选举及罢免行长、批准经审计财务报表、分配储备金与净收入、修改《协定》、终止业务等）；不直接审批具体融资项目",
            ],
            [
                "非常驻董事会\n（Board of Directors）",
                "12名董事（域内9名、非域内3名），任期2年可连任；下设4个常设委员会及独立监督局（CEIU）",
                "非常驻制，每季度至少1次例会，日常采用视频会或无异议程序；法定人数为过半数董事且代表≥2/3总投票权",
                "制定重大业务与财务政策（须≥75%总投票权通过）；审批年度业务计划与预算；直接审批三类保留项目（首例项目、非域内/政策豁免等战略敏感项目、超风险限额项目，且非牵头MDB联合融资≤5亿美元）以及被任一董事行使14日Call-In提请审议的项目",
            ],
            [
                "行长与高级管理层\n（President & Senior Management）",
                "行长须为域内成员国民，由理事会超级多数选出，任期5年可连任1次；副行长由行长提名、董事会任命",
                "常驻北京总部全职履职；主持执行委员会（ExCom）、投资委员会（IC）及初筛委员会（SC）",
                "负责银行日常经营管理与员工任免；依据《问责框架更新条例》审批除董事会保留事项以外的全部项目，以及与WB/ADB/EBRD/EIB联合融资且亚投行出资≤5亿美元的项目（须经14日无董事Call-In窗口期），并于每次董事会例会集中报备",
            ],
        ],
        col_widths_cm=[2.8, 3.6, 3.6, 5.8],
        source_note="《亚洲基础设施投资银行协定》第22–30条、《董事会议事规则》及《问责框架更新条例》（Sec2022-100）。",
    )

    # =========================================================================
    # Section 1.4
    # =========================================================================
    add_section_heading(doc, "1.4  资金池与资金来源")

    add_subsection_heading(doc, "1.4.1  双资金池严格隔离架构：普通资本资源（OCR）与特别基金资源（SFR）")
    add_body_paragraph(
        doc,
        [
            (
                "根据《亚投行协定》第8条、第9条、第10条及第17条，亚投行的全部资金按性质划分为两个相互独立的资金池：第一资金池为“普通资本资源”（Ordinary Capital Resources，简称“OCR”），由成员国认缴股本（含实缴股本与待缴股本）、银行在国际资本市场通过发行债券等筹集的借款、普通贷款本息回收款及留存收益组成；第二资金池为“特别基金资源”（Special Funds Resources，简称“SFR”），由捐资国或外部伙伴机构自愿提供的无偿捐资、特别基金专项拨款及其投资收益组成",
                FN["aoa_capital"],
            ),
            (
                "。《亚投行协定》第10条第1款至第3款对两个资金池规定了法定隔离规则：普通资本资源与特别基金资源必须在账户、使用、支配、投资及财务报表核算上完全分离，银行在任何情况下均不得动用或拆借普通资本资源去清偿、弥补因特别基金业务或其他活动所产生的亏损或债务；同时，《亚投行协定》第17条规定，管理任何特别基金所产生的全部直接与间接行政开支均由该特别基金自行承担",
                FN["sf_directive"],
            ),
            ("。图1-4展示了双资金池隔离架构与普通资本资源的资金循环机制。", None),
        ],
        fn,
    )

    # Embed Figure 1-4
    add_figure(
        doc,
        FIG_DIR / "fig1_4_capital_pool_funding.png",
        "图 1-4  亚洲基础设施投资银行双资金池隔离架构与资金循环图（2026年6月末）",
        "依据《亚洲基础设施投资银行协定》第4–20条、《2025年度经审计财务报表》及《投资者演示报告》（2026年第三季度）整理绘制。",
    )

    add_subsection_heading(doc, "1.4.2  法定股本结构：20%实缴股本与80%待缴股本")
    add_body_paragraph(
        doc,
        [
            (
                "根据《亚投行协定》第4条与第6条，亚投行的法定股本（Authorized Capital Stock）为1,000亿美元，划分为100万股，每股面值10万美元。法定股本由两部分构成：一是20%的实缴股本（Paid-in Capital，法定总额200亿美元），由各成员国自加入起分5期（发展中成员国最多可分10期）以美元或其他可自由兑换货币实缴入账，直接形成银行无付息成本的核心股东权益；二是80%的待缴股本（Callable Capital，法定总额800亿美元）",
                FN["aoa_capital"],
            ),
            (
                "。截至2026年6月30日，亚投行106个正式成员合计已认缴股本976.32亿美元（976,322股），其中待缴股本781.11亿美元，实缴股本195.25亿美元，实际已收缴到账的实缴股本达195.21亿美元。亚投行20%的法定实缴股本比例高于世界银行国际复兴开发银行（IBRD，约7%）、亚洲开发银行（ADB，约5%）、非洲开发银行（AfDB，约6%）、泛美开发银行（IADB，约7%）及欧洲投资银行（EIB，约9%）的实缴股本比例",
                FN["investor_pres"],
            ),
            ("。", None),
        ],
        fn,
    )

    add_body_paragraph(
        doc,
        [
            (
                "关于80%待缴股本的法律性质与触发条件，《亚投行协定》第6条第3款与第20条作出严格界定：待缴股本在银行日常运营中无需成员国缴纳现金，且银行不得为开展常规项目放贷而催缴待缴股本；只有在银行发生极端流动性枯竭、无法向国际债券持有人或担保债权人按期履约偿债时，董事会方可按全体成员国的持股比例发出统一催缴指令。在债务风险吸收顺位上，亚投行设有五级缓冲序列：第一顺位为贷款预期信用损失拨备（截至2025年末为2.69亿美元）；第二顺位为当期净收入（2025年全年净收入为12.23亿美元）；第三顺位为一般储备金与留存收益（截至2026年6月末为45.27亿美元）；第四顺位为未动用的实缴股本（195.21亿美元）；第五顺位方为向106个主权成员国催缴待缴股本（781.11亿美元）。自亚投行开业至今，待缴股本催缴次数为0",
                FN["fin_stmt_2025"],
            ),
            ("。", None),
        ],
        fn,
    )

    add_subsection_heading(doc, "1.4.3  国际债券市场发债筹资与资产负债表配置")
    add_body_paragraph(
        doc,
        [
            (
                "在195.21亿美元实收股本、781.11亿美元主权待缴股本担保、主权贷款“优先债权人地位”（Preferred Creditor Status）以及《亚投行协定》第12条第1款“法定放贷与股权投资未偿总额不得超过未减损认缴股本、储备金与留存收益之和的100%（经超级多数批准最高不超过250%）”的杠杆约束下，亚投行自2017年起持续获得标准普尔（S&P）、穆迪（Moody's）和惠誉（Fitch）三大评级机构的AAA/Aaa/AAA最高主权信用评级，并享有巴塞尔银行监管委员会0%风险权重及1级优质流动性资产（HQLA Level 1）监管待遇",
                FN["investor_pres"],
            ),
            ("。", None),
        ],
        fn,
    )

    add_body_paragraph(
        doc,
        [
            (
                "依托AAA评级，亚投行依据《亚投行协定》第16条在国际资本市场大规模发行债券筹集低成本资金，发债品种涵盖美国证券交易委员会（SEC）注册的美元全球基准债券（Global Benchmark Bonds）、全球中期票据计划（GMTN，含欧元债、英镑债）、澳元袋鼠债（Kangaroo Bonds）、纽元毛利债（Kauri Bonds）、中国银行间市场人民币熊猫债（Panda Bonds）、港元云吞债（Wonton Bonds）以及80亿美元额度的欧元商业票据（ECP）。2023年至2025年，亚投行年度发债筹资规模分别为99亿美元、102亿美元和98亿美元，2026年董事会授权的年度最高发债额度为110亿美元",
                FN["investor_pres"],
            ),
            (
                "。根据《资产负债管理政策》（2024年12月9日修订版），亚投行将发债募集的非美元资金通过交叉货币与利率掉期（Swaps）统一套期保值转换为美元浮动利率基准（SOFR），将单年债务到期赎回比例上限（Debt Redemption Limit）控制在存续长期债务本金的30%以内，并要求司库高流动性资产池始终覆盖未来36个月预计净现金流需求的40%以上",
                FN["alm_policy"],
            ),
            (
                "。截至2026年6月30日，亚投行普通资本资源（OCR）总资产达692.25亿美元；其中负债端存续国际债券筹资余额为434.14亿美元（占总资产的62.7%），股东权益总额为240.48亿美元（占总资产的34.7%），国际债券市场募集资金已成为亚投行最主要的资金来源",
                FN["investor_pres"],
            ),
            ("。表1-4列出了亚投行2025年末（经审计）与2026年6月末（未经审计）的普通资本资源资产负债结构。", None),
        ],
        fn,
    )

    add_styled_table(
        doc,
        "表 1-4  亚洲基础设施投资银行普通资本资源（OCR）资产负债与资金池结构表",
        ["资产负债表科目", "2025年12月31日（经审计，百万美元）", "2026年6月30日（未经审计，百万美元）", "占2026年6月末总资产比例（%）"],
        [
            ["一、资产总额（Total Assets）", "64,660.1", "69,225.0", "100.00%"],
            ["  1. 司库流动性资金池（现金、银行存款与交易性证券）", "29,886.9", "33,324.0", "48.14%"],
            ["  2. 项目贷款投资净额（Loan Investments, net）", "29,631.9", "31,089.6", "44.91%"],
            ["  3. 债券投资组合（Bond Portfolio / Amortized Cost）", "3,098.4", "2,508.6", "3.62%"],
            ["  4. 股权投资、衍生金融资产及其他资产", "2,042.9", "2,302.8", "3.33%"],
            ["二、负债总额（Total Liabilities）", "41,083.2", "45,176.5", "65.26%"],
            ["  1. 国际市场发债筹资余额（Borrowings）", "39,072.8", "43,414.0", "62.71%"],
            ["  2. 衍生金融负债及其他负债", "2,010.4", "1,762.5", "2.55%"],
            ["三、成员国股东权益总额（Total Members' Equity）", "23,576.9", "24,048.5", "34.74%"],
            ["  1. 已认缴股本总额（Subscribed Capital）", "97,627.2", "97,632.2", "—"],
            ["  2. 减：待缴股本（Callable Capital，80%）", "(78,101.8)", "(78,105.8)", "—"],
            ["  3. 实缴股本（Paid-in Capital，20%）", "19,525.4", "19,526.4", "28.21%"],
            ["  4. 减：尚未到期应收实缴股本分期款", "(8.0)", "(5.5)", "-0.01%"],
            ["  5. 实收股本净额（Paid-in Capital Received）", "19,517.4", "19,520.9", "28.20%"],
            ["  6. 留存收益与储备金（Retained Earnings & Reserves）", "4,059.5", "4,527.6", "6.54%"],
        ],
        col_widths_cm=[6.2, 3.2, 3.2, 3.2],
        source_note="《2025年度经审计财务报表》第6页及《投资者演示报告》（2026年第三季度）第56页。",
    )

    add_subsection_heading(doc, "1.4.4  主权担保贷款的统一定价机制与五大特别基金窗口")
    add_body_paragraph(
        doc,
        [
            (
                "根据《主权担保产品定价政策》（2024年11月26日修订版）与《主权融资情况说明书》（2026年7月版），亚投行对所有成员国的主权担保贷款（SBF）实行不区分借款国主权信用评级的统一定价原则（Uniform Pricing）。主权贷款主要采用可变利差贷款（Variable Spread Loans，简称“VSL”），提供美元（基准利率为SOFR）、欧元（基准利率为6个月EURIBOR）和人民币（基准利率为3年期SHIBOR）等币种，最长最终到期期限可达35年，加权平均还款期限（Average Maturity）最长可达20年",
                FN["sbf_pricing"],
            ),
            (
                "。以美元主权可变利差贷款为例，借款人需支付两项费用与四部分合成利率：一是前端费（Front-end Fee），按贷款总额的0.25%一次性收取；二是承诺费（Commitment Fee），自贷款协议签署满60日起，对尚未提款的贷款余额按年化0.25%计收；三是贷款执行利率，等于“6个月复利SOFR基准利率 + 亚投行实际发债筹资成本利差（2026年上半年为0.42%） + 固定合同利差（0.50%） + 按平均还款期限分6档递增的期限溢价（0.00%至0.50%）”，合成后的美元主权贷款年利率区间为SOFR + 0.92%至SOFR + 1.42%",
                FN["sbf_pricing"],
            ),
            ("。对于符合条件的欠发达成员，亚投行可通过“欠发达成员特别基金窗口”（SFW）提供最高100个基点（1.00%）的利率减免贴息。", None),
        ],
        fn,
    )

    add_styled_table(
        doc,
        "表 1-5  亚洲基础设施投资银行美元主权可变利差贷款（VSL）定价与期限费率表",
        ["平均还款期限档次（Average Maturity）", "基准利率", "筹资成本利差（a）", "固定合同利差（b）", "期限溢价（c）", "总利差（a+b+c）", "前端费 / 年度承诺费"],
        [
            ["第1档：≤ 8年", "SOFR", "0.42%", "0.50%", "0.00%", "0.92%", "前端费0.25% / 承诺费0.25%"],
            ["第2档：> 8年 且 ≤ 10年", "SOFR", "0.42%", "0.50%", "0.05%", "0.97%", "前端费0.25% / 承诺费0.25%"],
            ["第3档：> 10年 且 ≤ 12年", "SOFR", "0.42%", "0.50%", "0.15%", "1.07%", "前端费0.25% / 承诺费0.25%"],
            ["第4档：> 12年 且 ≤ 15年", "SOFR", "0.42%", "0.50%", "0.25%", "1.17%", "前端费0.25% / 承诺费0.25%"],
            ["第5档：> 15年 且 ≤ 18年", "SOFR", "0.42%", "0.50%", "0.35%", "1.27%", "前端费0.25% / 承诺费0.25%"],
            ["第6档：> 18年 且 ≤ 20年", "SOFR", "0.42%", "0.50%", "0.50%", "1.42%", "前端费0.25% / 承诺费0.25%"],
        ],
        col_widths_cm=[3.6, 1.6, 2.0, 2.0, 1.8, 2.0, 2.8],
        source_note="《主权担保产品定价政策》（2024年11月26日修订）及《主权融资情况说明书》（2026年7月），其中0.42%为2026年上半年亚投行美元发债实际筹资成本利差。",
    )

    # =========================================================================
    # Section 1.5
    # =========================================================================
    add_section_heading(doc, "1.5  投票权的构成与作用")

    add_subsection_heading(doc, "1.5.1  投票权的三元计算公式及其对大股东权重的稀释效应")
    add_body_paragraph(
        doc,
        [
            (
                "根据《亚投行协定》第28条第1款，每个成员国在亚投行理事会与董事会中的总投票权（Total Voting Power）并非单纯按出资股本比例折算，而是由“基本投票权（Basic Votes）+ 股份投票权（Share Votes）+ 创始成员投票权（Founding Member Votes）”三部分相加构成",
                FN["aoa_voting"],
            ),
            ("：", None),
        ],
        fn,
    )

    add_body_paragraph(
        doc,
        [
            (
                "第一，基本投票权（Basic Votes）：恒定占全行所有成员总投票权的12.00%，由全体正式成员（不论出资规模大小）平均分配。截至2026年3月，全行总投票权为1,136,676票，106个正式成员每个国家均分获得1,286票基本投票权（合计约136,354票）。由于基本投票权固定占总投票权的12%，每当有新成员加入亚投行，基本投票权基数即自动重算，从而在数学上固定将股份投票权的权重上限锁定在88%以内",
                FN["investor_pres"],
            ),
            ("。", None),
        ],
        fn,
    )

    add_body_paragraph(
        doc,
        [
            (
                "第二，股份投票权（Share Votes）：等于该成员国认缴的亚投行股本份数，即每认缴1股（面值10万美元）获得1票股份投票权。截至2026年3月，全行已认缴股本976,322股，对应976,322票股份投票权，占全行总投票权的85.89%。",
                None,
            ),
        ],
        fn,
    )

    add_body_paragraph(
        doc,
        [
            (
                "第三，创始成员投票权（Founding Member Votes）：向《亚投行协定》附件一所列并完成批约加入的每个创始成员国固定分配600票；根据《亚投行协定》第3条第2款后续新加入的普通成员国不享有创始成员投票权（为0票）。全行创始成员投票权合计占总投票权的2.11%。",
                None,
            ),
        ],
        fn,
    )

    add_body_paragraph(
        doc,
        [
            (
                "上述三元公式的直接定量结果是：认缴股本排名靠前的大股东，其最终投票权占比低于其认缴股本占比；而认缴股本较少的中小发展中国家成员，其最终投票权占比高于其认缴股本占比。例如，截至2026年3月，中国认缴股本297.804亿美元，占全行已认缴股本的30.50%，经12%基本投票权与600票创始成员票加权折算后，中国持有299,690票，占全行总投票权的26.37%（较股本占比下降4.13个百分点）；第二大股东印度认缴股本83.673亿美元，占全行已认缴股本的8.57%，折算后持有85,559票，占全行总投票权的7.53%（较股本占比下降1.04个百分点）；第三大股东俄罗斯认缴股本65.362亿美元（占6.69%），实际投票权占比为5.91%；第四大股东德国认缴股本44.842亿美元（占4.60%），实际投票权占比为4.15%",
                FN["investor_pres"],
            ),
            ("。图1-5展示了投票权三元构成、选区董事选举门槛与四级多数决表决机制的对应关系。", None),
        ],
        fn,
    )

    # Embed Figure 1-5
    add_figure(
        doc,
        FIG_DIR / "fig1_5_voting_power_thresholds.png",
        "图 1-5  亚洲基础设施投资银行投票权三元构成、董事选举门槛与四级表决机制图",
        "依据《亚洲基础设施投资银行协定》第28条、附件二及《投资者演示报告》（2026年第三季度）第13页整理绘制。",
    )

    add_subsection_heading(doc, "1.5.2  投票权在董事会席位产生中的控制作用：选区组建门槛")
    add_body_paragraph(
        doc,
        [
            (
                "根据《亚投行协定》第25条、第28条第3款及附件二《董事选举规定》，亚投行董事会的12名董事通过选区（Constituencies）机制产生并实行集合投票制：域内成员理事选举产生9名域内董事（Regional Directors），非域内成员理事选举产生3名非域内董事（Non-regional Directors）。在董事会表决时，每名董事有权投出其当选时所代表选区内全部成员国的合计票数，且一名董事所投的票数无需作为一个整体投出，可以根据选区内不同成员国的意愿拆分别投",
                FN["aoa_voting"],
            ),
            ("。", None),
        ],
        fn,
    )

    add_body_paragraph(
        doc,
        [
            (
                "《亚投行协定》附件二第2条规定了当选董事的最低投票权门槛：当选一名域内董事的初始最低得票门槛为全体域内成员总投票权的6%；当选一名非域内董事的初始最低得票门槛为全体非域内成员总投票权的15%。这一制度安排直接决定了各成员国在董事会的席位控制形态：凡是单一国家持有的域内投票权占全体域内成员总投票权的比例达到或超过6%的域内主权成员，无需与其他成员国拼凑选票或协商轮值，即可凭借本国一国票数独立跨过6%当选门槛，单独组建“单一国家选区”（Single-country Constituency），长期固定指派一名本国国籍的董事和副董事。截至2026年3月，全体域内成员总投票权为825,951票，其中中国持有299,690票（占域内总投票权的36.32%）、印度持有85,559票（占域内总投票权的10.36%）、俄罗斯持有67,248票（占域内总投票权的8.13%）。因此，中国、印度（第10选区）和俄罗斯均各自超过6%域内门槛，独立拥有专属董事席位；其余域内成员与全部非域内成员则必须通过跨国联合组建多国选区，按选区内部协议轮流派任董事与副董事",
                FN["aoa_voting"],
            ),
            ("。", None),
        ],
        fn,
    )

    add_subsection_heading(doc, "1.5.3  四级多数决表决门槛及其控制的决策事项")
    add_body_paragraph(
        doc,
        [
            (
                "根据《亚投行协定》第28条第2款与第3款、《理事会议事规则》第6条以及《董事会议事规则》第5条，亚投行在理事会和董事会的日常运作中，优先由主席根据讨论情况确定并宣布“会议共识”（Sense of the Meeting）或通过不少于10天的“无异议程序”作出决定，无需每次进行正式投票；但如果任何一名理事或董事要求进行正式表决，则严格按照所涉事项的重要性等级，分别适用以下四级多数决门槛",
                FN["bod_rules"],
            ),
            ("：", None),
        ],
        fn,
    )

    add_body_paragraph(
        doc,
        [
            (
                "第一级：简单多数（Simple Majority，即所投票数的过半数 > 50%）。除《亚投行协定》另有明确规定外，理事会和董事会审议的一切常规事项均按所投票数的过半数决定。受简单多数控制的事项包括：常规项目融资审批（含三类保留项目及被董事Call-In提请董事会表决的项目）、年度业务计划与行政预算批准、一般性行政规章等。由于没有任何单一成员国持有超过50%的投票权（第一大股东中国占26.37%），在常规项目贷款审批与年度预算表决上，没有任何单一国家拥有单边否决权",
                FN["aoa_voting"],
            ),
            ("。", None),
        ],
        fn,
    )

    add_body_paragraph(
        doc,
        [
            (
                "第二级：理事会特别多数（Special Majority of Governors，即理事总人数过半数、且代表不少于全行总投票权的50%）。受理事会特别多数控制的事项共4项：（1）批准接纳新成员加入亚投行并确定其认缴股本条件（第3条第2款）；（2）在特定情况下按高于面值的价格增发新股（第7条第1款）；（3）批准开展《亚投行协定》第11条列明的前五类金融工具以外的新型融资业务（第11条第2款第6项）；（4）批准设立服务于银行宗旨的附属机构（第16条第8款）",
                FN["aoa_voting"],
            ),
            ("。", None),
        ],
        fn,
    )

    add_body_paragraph(
        doc,
        [
            (
                "第三级：董事会四分之三多数（Three-Quarters Majority of Directors，即代表不少于全行总投票权的75%）。受董事会四分之三多数控制的事项共2项：（1）制定与修改银行重大业务政策和财务政策（第26条第2项，如《融资业务政策》《环境与社会框架》《采购政策》《主权担保产品定价政策》《资产负债管理政策》等）；（2）根据《问责框架》将项目融资审批权或业务决策权授权给行长（第26条第3项）。在75%投票权门槛下，任何持有超过25%总投票权的单一成员或成员组合即拥有合规否决能力",
                FN["aoa_governance"],
            ),
            ("。", None),
        ],
        fn,
    )

    add_body_paragraph(
        doc,
        [
            (
                "第四级：理事会超级多数（Super Majority of Governors，即理事总人数不少于2/3、且代表不少于全行总投票权的75%）。受理事会超级多数控制的事项为11项涉及银行宪制基础与资本安全的重大决定：（1）增加银行法定股本（第4条第3款）；（2）允许域内成员认缴股本占比低于75%（第5条第2、3款）；（3）向非标准受款对象提供融资（第11条第1款第2项）；（4）将银行放贷与股权投资杠杆上限从股东权益的100%提高至最高250%（第12条第1款）；（5）将银行净收入分配作其他用途（第18条第1款）；（6）调整董事会的规模或构成（第25条第2款）；（7）改变非常驻董事会制度、设立常驻董事会（第27条第1款）；（8）选举、暂停或罢免银行行长（第29条第1、2款）；（9）暂停或恢复成员国资格（第38条）；（10）决定终止银行业务（第41条第1款）；（11）修改《亚投行协定》（第53条第1款；但若修改涉及成员自由退出银行的权利、成员对银行债务的有限责任边界、或成员在增资时的优先认购权，则按第53条第2款必须经全体理事100%全票同意）",
                FN["aoa_voting"],
            ),
            ("。", None),
        ],
        fn,
    )

    add_styled_table(
        doc,
        "表 1-6  亚洲基础设施投资银行前十大股东股本、投票权及四级表决门槛对照表（截至2026年3月）",
        ["排名与成员国（或表决层级）", "认缴股本（百万美元）", "认缴股本占比（%）", "总投票权（票）", "占全行总投票权比例（%）", "制度地位或受控决策事项"],
        [
            ["1. 中国（域内创始成员）", "29,780.4", "30.50%", "299,690", "26.37%", "单一国家选区；对≥75%门槛的重大政策、授权、增资、选任行长、修约拥有单国否决权（>25%）"],
            ["2. 印度（域内创始成员）", "8,367.3", "8.57%", "85,559", "7.53%", "占域内投票权10.36%（>6%门槛），单独组建第10选区并直派执行董事；前两大借款国之一"],
            ["3. 俄罗斯（域内创始成员）", "6,536.2", "6.69%", "67,248", "5.91%", "占域内投票权8.13%（>6%门槛），单独组建域内选区并直派执行董事"],
            ["4. 德国（非域内创始成员）", "4,484.2", "4.60%", "46,728", "4.15%", "非域内第一大股东；牵头欧元区选区"],
            ["5. 韩国（域内创始成员）", "3,738.7", "3.83%", "39,273", "3.46%", "域内第四大股东；多国选区核心成员"],
            ["6. 澳大利亚（域内创始成员）", "3,691.2", "3.78%", "38,798", "3.41%", "域内第五大股东；多国选区核心成员"],
            ["7. 法国（非域内创始成员）", "3,375.6", "3.46%", "35,642", "3.14%", "非域内第二大股东；欧元区选区核心成员"],
            ["8. 印度尼西亚（域内创始成员）", "3,360.7", "3.44%", "35,493", "3.12%", "东南亚第一大股东；主力主权借款国之一"],
            ["9. 英国（非域内创始成员）", "3,054.7", "3.13%", "32,433", "2.85%", "非域内第三大股东；非欧元区欧洲选区核心成员"],
            ["10. 土耳其（域内创始成员）", "2,609.9", "2.67%", "27,985", "2.46%", "横跨欧亚域内成员；前三大主权借款国之一"],
            ["其余96个正式成员合计", "28,633.3", "29.33%", "427,827", "37.60%", "凭借12%均分基本投票权，总投票权占比高于认缴股本占比8.27个百分点"],
            ["全行106个正式成员总计", "97,632.2", "100.00%", "1,136,676", "100.00%", "股份票976,322票（85.89%）+ 基本票136,354票（12.00%）+ 创始票24,000票（2.11%）"],
            ["表决第1级：简单多数", "—", "—", "> 50% 所投票", "> 50.00%", "常规项目融资审批（含Call-In上会项目）、年度业务计划与预算；无任何单一国家拥有否决权"],
            ["表决第2级：理事会特别多数", "—", "—", ">1/2理事 + ≥50%票", "≥ 50.00%", "接纳新成员、新增金融工具、溢价增发新股、设立附属机构"],
            ["表决第3级：董事会3/4多数", "—", "—", "代表 ≥ 75% 总票数", "≥ 75.00%", "制定与修改重大业务及财务政策、按《问责框架》向行长授予项目审批权"],
            ["表决第4级：理事会超级多数", "—", "—", "≥2/3理事 + ≥75%票", "≥ 75.00%", "增加法定股本、下调域内75%持股下限、放宽杠杆上限至250%、选任/罢免行长、修改《协定》等11项"],
        ],
        col_widths_cm=[3.6, 2.2, 1.8, 2.2, 2.0, 4.0],
        source_note="《亚洲基础设施投资银行协定》第28条、附件二及《投资者演示报告》（2026年第三季度）第13页、第54–55页。",
    )

    # Finalize and inject word/footnotes.xml
    fn.finalize_part()

    OUT_DOCX.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUT_DOCX))
    return OUT_DOCX, len(fn.footnotes)


def build_companion_markdown(docx_path: Path) -> Path:
    """Export a clean Markdown preview of Chapter 1 for quick inspection in the workspace."""
    doc = Document(str(docx_path))
    lines = ["# 第一章 亚洲基础设施投资银行的制度规定（Word报告同步预览版）\n"]
    for p in doc.paragraphs:
        txt = p.text.strip()
        if not txt:
            continue
        if txt.startswith("第一章"):
            lines.append(f"\n## {txt}\n")
        elif txt[:3] in ("1.1", "1.2", "1.3", "1.4", "1.5") and len(txt) < 40:
            lines.append(f"\n### {txt}\n")
        elif txt[:5] in (
            "1.1.1", "1.1.2", "1.1.3",
            "1.2.1", "1.2.2", "1.2.3", "1.2.4", "1.2.5", "1.2.6",
            "1.3.1", "1.3.2", "1.3.3",
            "1.4.1", "1.4.2", "1.4.3", "1.4.4",
            "1.5.1", "1.5.2", "1.5.3",
        ):
            lines.append(f"\n#### {txt}\n")
        else:
            lines.append(f"{txt}\n")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    return OUT_MD


def verify_docx_footnotes(docx_path: Path) -> dict[str, int]:
    """Verify that word/footnotes.xml is packaged inside the .docx and referenced in document.xml."""
    with zipfile.ZipFile(docx_path, "r") as zf:
        names = zf.namelist()
        assert "word/footnotes.xml" in names, "Missing word/footnotes.xml in .docx archive!"
        doc_xml = zf.read("word/document.xml").decode("utf-8")
        fn_xml = zf.read("word/footnotes.xml").decode("utf-8")
        rels_xml = zf.read("word/_rels/document.xml.rels").decode("utf-8")
        assert "footnotes.xml" in rels_xml, "Missing footnotes relationship in document.xml.rels!"

        ref_count = doc_xml.count("<w:footnoteReference ")
        fn_root = ET.fromstring(fn_xml)
        fn_items = [
            el for el in fn_root.findall("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}footnote")
            if int(el.attrib.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id", "0")) > 0
        ]
        return {"body_refs": ref_count, "footnotes_xml_items": len(fn_items)}


def main() -> None:
    docx_path, fn_count = build_chapter1_docx()
    md_path = build_companion_markdown(docx_path)
    stats = verify_docx_footnotes(docx_path)
    print(f"Successfully generated Word report: {docx_path} ({docx_path.stat().st_size / 1024:.1f} KB)")
    print(f"Companion Markdown preview: {md_path}")
    print(f"Footnotes verified: {stats} (total GB/T 7714-2015 footnotes: {fn_count})")


if __name__ == "__main__":
    main()

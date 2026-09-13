"""Render an analysis as a PDF report.

Takes the same dict the API returns from /api/analyze and produces PDF bytes.
Knows nothing about HTTP, files or requests - it is handed data and returns
bytes, which makes it testable with a literal dict.

DESIGN NOTE: the web UI is dark, this document is light. A report is printed,
emailed and pasted into applications; a dark PDF wastes a cartridge of toner
and is unreadable on paper. The accent colour and the score bands carry over so
the two still read as one product.

PRIVACY: the report contains skills, scores and advice. It never contains name,
gender, age, photo, religion, nationality, marital status or disability,
because none of those are ever extracted. The disclaimer is printed on every
page footer rather than buried on the last one.
"""

from datetime import datetime
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Design tokens, mirroring tailwind.config.js where it makes sense on paper.
# ---------------------------------------------------------------------------
INK = colors.HexColor("#111113")
MUTED = colors.HexColor("#55555F")
SUBTLE = colors.HexColor("#8A8A94")
LINE = colors.HexColor("#E3E3E8")
PANEL = colors.HexColor("#F7F7F9")
ACCENT = colors.HexColor("#6366F1")

BAND_COLORS = {
    "early": colors.HexColor("#DC2626"),
    "developing": colors.HexColor("#D97706"),
    "strong": colors.HexColor("#059669"),
}
BAND_LABELS = {
    "early": "Early match",
    "developing": "Developing match",
    "strong": "Strong match",
}
SEVERITY_COLORS = {
    "critical": colors.HexColor("#DC2626"),
    "important": colors.HexColor("#D97706"),
    "optional": SUBTLE,
}
TIER_LABELS = {
    "must_have": "Must have",
    "good_to_have": "Good to have",
    "nice_to_have": "Nice to have",
}

# Helvetica, not Inter: Inter would have to be shipped as a .ttf and registered,
# adding ~300KB to the repo for a document nobody reads for its typography.
# Helvetica is one of the 14 fonts every PDF reader already has.
FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

# The list bullet, and a trap worth documenting.
#
# The obvious choice, U+2022 BULLET, is silently wrong: in Helvetica reportlab
# encodes it as byte 0x7F, which is undefined in WinAnsiEncoding, so the bullet
# renders as nothing at all. Drawing it from ZapfDingbats (one of the 14 base
# fonts, so never missing) is the reliable route - and reportlab maps U+25CF
# BLACK CIRCLE onto ZapfDingbats glyph "l", the filled circle we want. Passing
# U+2022 here instead lands on "n", a filled square.
BULLET_FONT = "ZapfDingbats"
BULLET = "●"

PAGE_MARGIN = 16 * mm
FOOTER_HEIGHT = 14 * mm

DISCLAIMER = (
    "This score estimates how well the listed skills overlap with a role's requirements. "
    "It is not a hiring decision, and it does not consider name, gender, age, photo, "
    "religion, nationality, marital status or disability."
)


def build_report(analysis: dict[str, Any]) -> bytes:
    """Take an analysis payload, return the bytes of a PDF report.

    `analysis` is the AnalysisResponse shape: target_role, skills_found,
    skills_by_category, role_ranking, gaps, roadmap, meta.
    """
    buffer = BytesIO()
    styles = _build_styles()
    target = analysis["target_role"]

    document = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=PAGE_MARGIN,
        rightMargin=PAGE_MARGIN,
        topMargin=PAGE_MARGIN,
        bottomMargin=PAGE_MARGIN + FOOTER_HEIGHT,
        title=f"Resume analysis - {target['role_name']}",
        author="Resume Signal",
        # Explicitly no subject/keywords: metadata is another place personal
        # data leaks into a document by accident.
        subject="Skill match analysis",
    )

    frame = Frame(
        document.leftMargin,
        document.bottomMargin,
        document.width,
        document.height,
        id="body",
        showBoundary=0,
    )
    document.addPageTemplates(
        [PageTemplate(id="report", frames=[frame], onPage=_draw_page_furniture)]
    )

    story: list[Flowable] = []
    story += _hero(analysis, styles)
    story += _tier_breakdown(target, styles)
    story += _skills(analysis, styles)
    story += _role_ranking(analysis, styles)
    story += _gaps(analysis, styles)
    story += _roadmap(analysis, styles)

    document.build(story)
    return buffer.getvalue()


def suggested_filename(analysis: dict[str, Any]) -> str:
    """Take an analysis payload, return a safe download filename.

    Built from the role id and the date only - never from the uploaded file
    name, which is user-controlled and could carry a path or a script.
    """
    role_id = str(analysis["target_role"]["role_id"])
    safe_role = "".join(char for char in role_id if char.isalnum() or char in "-_")
    return f"resume-analysis-{safe_role or 'report'}-{datetime.now():%Y-%m-%d}.pdf"


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def _hero(analysis: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Flowable]:
    """Take the analysis, return the title block, score dial and summary line."""
    target = analysis["target_role"]
    meta = analysis["meta"]
    generated = _parse_timestamp(meta.get("analyzed_at"))

    header = Table(
        [
            [
                Paragraph("Resume analysis", styles["kicker"]),
                Paragraph(f"{generated:%d %B %Y}", styles["kicker_right"]),
            ]
        ],
        colWidths=["*", 45 * mm],
    )
    header.setStyle(
        TableStyle(
            [
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("LINEBELOW", (0, 0), (-1, -1), 0.75, LINE),
            ]
        )
    )

    summary_cell = [
        Paragraph(target["role_name"], styles["h1"]),
        Paragraph(BAND_LABELS.get(target["band"], "Match"), styles["band"]),
        Spacer(1, 4),
        Paragraph(analysis["gaps"]["summary"], styles["body"]),
    ]

    hero = Table(
        [[ScoreDial(target["score"], target["band"]), summary_cell]],
        colWidths=[38 * mm, "*"],
    )
    hero.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("LEFTPADDING", (1, 0), (1, 0), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )

    return [header, hero, Spacer(1, 6)]


def _tier_breakdown(
    target: dict[str, Any], styles: dict[str, ParagraphStyle]
) -> list[Flowable]:
    """Take the target role score, return the three-tier explanation panel."""
    semantic = target.get("semantic_score")
    rows = [
        ("Skill coverage", target["skill_coverage"], "45%"),
        ("Meaning similarity", semantic, "35%"),
        ("Keyword similarity", target["tfidf_score"], "20%"),
    ]

    cells = []
    for label, value, weight in rows:
        shown = "n/a" if value is None else f"{round(value * 100)}%"
        cells.append(
            [
                Paragraph(f"{label} &nbsp;<font color='#8A8A94'>{weight}</font>", styles["tiny"]),
                Paragraph(shown, styles["stat"]),
            ]
        )

    table = Table([[cell[0] for cell in cells], [cell[1] for cell in cells]], colWidths=["*"] * 3)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PANEL),
                ("BOX", (0, 0), (-1, -1), 0.75, LINE),
                # Hairlines between the three columns, none between the rows -
                # each column is one statistic read top to bottom.
                ("LINEAFTER", (0, 0), (-2, -1), 0.75, LINE),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, 0), 9),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 9),
                ("TOPPADDING", (0, 1), (-1, 1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
            ]
        )
    )
    return [table, Spacer(1, 16)]


def _skills(analysis: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Flowable]:
    """Take the analysis, return the detected-skills section grouped by category."""
    by_category: dict[str, list[dict]] = analysis.get("skills_by_category") or {}
    total = len(analysis.get("skills_found") or [])

    story: list[Flowable] = [
        _section_heading(f"Skills detected ({total})", styles),
    ]

    if not by_category:
        story.append(
            Paragraph(
                "No known skills were detected. If the resume is a scanned image, "
                "export it as a text-based PDF and try again.",
                styles["body"],
            )
        )
        story.append(Spacer(1, 16))
        return story

    rows = []
    for category, skills in sorted(by_category.items(), key=lambda item: -len(item[1])):
        names = ", ".join(skill["name"] for skill in skills)
        rows.append(
            [
                Paragraph(category, styles["label"]),
                Paragraph(names, styles["body"]),
            ]
        )

    table = Table(rows, colWidths=[46 * mm, "*"])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -2), 0.5, LINE),
            ]
        )
    )
    story += [table, Spacer(1, 16)]
    return story


def _role_ranking(
    analysis: dict[str, Any], styles: dict[str, ParagraphStyle]
) -> list[Flowable]:
    """Take the analysis, return the eight-role comparison with bars."""
    ranking = analysis["role_ranking"]
    target_id = analysis["target_role"]["role_id"]

    rows = []
    for role in ranking:
        is_target = role["role_id"] == target_id
        rows.append(
            [
                Paragraph(role["role_name"], styles["row_bold"] if is_target else styles["row"]),
                ScoreBar(role["score"], highlight=is_target),
                Paragraph(
                    f"{round(role['score'])}%",
                    styles["row_right_bold"] if is_target else styles["row_right"],
                ),
            ]
        )

    table = Table(rows, colWidths=[52 * mm, "*", 14 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, -1), 0),
                ("RIGHTPADDING", (1, 0), (1, -1), 8),
                ("RIGHTPADDING", (2, 0), (2, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    return [
        _section_heading("How this resume ranks across all eight roles", styles),
        table,
        Spacer(1, 16),
    ]


def _gaps(analysis: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Flowable]:
    """Take the analysis, return the missing-skills table and the tier tally."""
    gaps = analysis["gaps"]
    role_name = analysis["target_role"]["role_name"]

    tally = " &nbsp;&middot;&nbsp; ".join(
        f"{TIER_LABELS.get(tier, tier)} {counts['have']}/{counts['total']}"
        for tier, counts in gaps["tier_summary"].items()
    )

    story: list[Flowable] = [
        _section_heading(f"Requirements for {role_name}", styles),
        Paragraph(
            f"{tally} &nbsp;&middot;&nbsp; {gaps['earned_weight']} of "
            f"{gaps['total_weight']} weighted points",
            styles["tiny"],
        ),
        Spacer(1, 8),
    ]

    if not gaps["missing"]:
        story += [
            Paragraph("Every skill listed for this role was detected.", styles["body"]),
            Spacer(1, 16),
        ]
        return story

    header = [
        Paragraph("Missing skill", styles["th"]),
        Paragraph("Category", styles["th"]),
        Paragraph("Importance", styles["th"]),
    ]
    rows = [header]
    for gap in gaps["missing"]:
        rows.append(
            [
                Paragraph(gap["name"], styles["row"]),
                Paragraph(gap["category"], styles["row_muted"]),
                Paragraph(
                    # hexval() returns "0xdc2626"; reportlab's inline markup
                    # wants CSS-style "#dc2626".
                    f"<font color='#{SEVERITY_COLORS[gap['severity']].hexval()[2:]}'>"
                    f"{gap['severity'].upper()}</font>",
                    styles["row_small"],
                ),
            ]
        )

    table = Table(rows, colWidths=["*", 52 * mm, 26 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LINEBELOW", (0, 0), (-1, 0), 0.75, LINE),
                ("LINEBELOW", (0, 1), (-1, -2), 0.5, LINE),
            ]
        )
    )
    story += [table, Spacer(1, 16)]
    return story


def _roadmap(analysis: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Flowable]:
    """Take the analysis, return the four-week plan."""
    story: list[Flowable] = [_section_heading("Four-week plan", styles)]

    for week in analysis["roadmap"]:
        block: list[Flowable] = [
            Paragraph(
                f"WEEK {week['week']} &nbsp;&middot;&nbsp; {week['estimated_hours']} HOURS",
                styles["label"],
            ),
            Paragraph(week["title"], styles["h3"]),
            Paragraph(week["objective"], styles["body_muted"]),
        ]

        if week.get("focus_skills"):
            block.append(
                Paragraph(
                    "Focus: " + ", ".join(week["focus_skills"]),
                    styles["tiny_accent"],
                )
            )

        block.append(Spacer(1, 3))
        for activity in week["activities"]:
            # The bullet is drawn by bulletText so a long activity wraps with a
            # hanging indent instead of tucking under the dot.
            block.append(Paragraph(activity, styles["bullet"], bulletText=BULLET))

        block.append(Spacer(1, 12))
        # KeepTogether stops a week's heading being orphaned at a page break.
        story.append(KeepTogether(block))

    return story


# ---------------------------------------------------------------------------
# Custom flowables
# ---------------------------------------------------------------------------

class ScoreDial(Flowable):
    """A donut gauge showing the score, drawn directly on the canvas."""

    def __init__(self, score: float, band: str, size: float = 32 * mm) -> None:
        super().__init__()
        self.score = max(0.0, min(100.0, float(score)))
        self.color = BAND_COLORS.get(band, ACCENT)
        self.size = size
        self.stroke = size * 0.11

    def wrap(self, available_width: float, available_height: float) -> tuple[float, float]:
        """Take the available space, return the space this flowable claims."""
        return self.size, self.size

    def draw(self) -> None:
        """Draw the track, the progress arc and the number."""
        canvas = self.canv
        inset = self.stroke / 2
        radius = self.size / 2

        canvas.setLineWidth(self.stroke)
        canvas.setLineCap(1)  # rounded ends, matching the web ring

        canvas.setStrokeColor(LINE)
        canvas.circle(radius, radius, radius - inset, stroke=1, fill=0)

        if self.score > 0:
            path = canvas.beginPath()
            # startAng=90 puts the start at 12 o'clock; a negative extent
            # sweeps clockwise, the direction people read a dial.
            path.arc(
                inset,
                inset,
                self.size - inset,
                self.size - inset,
                90,
                -(self.score / 100) * 360,
            )
            canvas.setStrokeColor(self.color)
            canvas.drawPath(path, stroke=1, fill=0)

        canvas.setFillColor(INK)
        canvas.setFont(FONT_BOLD, self.size * 0.26)
        canvas.drawCentredString(radius, radius - self.size * 0.06, f"{round(self.score)}%")

        canvas.setFillColor(SUBTLE)
        canvas.setFont(FONT, self.size * 0.1)
        canvas.drawCentredString(radius, radius - self.size * 0.21, "MATCH")


class ScoreBar(Flowable):
    """A horizontal bar for one role in the ranking."""

    def __init__(self, score: float, highlight: bool = False, height: float = 3.2 * mm) -> None:
        super().__init__()
        self.score = max(0.0, min(100.0, float(score)))
        self.highlight = highlight
        self.height = height
        self.width = 0.0  # set in wrap(), since the column width is dynamic

    def wrap(self, available_width: float, available_height: float) -> tuple[float, float]:
        """Take the available space, claim the full column width."""
        self.width = available_width
        return self.width, self.height

    def draw(self) -> None:
        """Draw the track and the filled portion."""
        canvas = self.canv
        radius = self.height / 2

        canvas.setFillColor(PANEL)
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.5)
        canvas.roundRect(0, 0, self.width, self.height, radius, stroke=1, fill=1)

        filled = self.width * (self.score / 100)
        if filled > self.height:  # below one bar-height a rounded rect degenerates
            canvas.setFillColor(ACCENT if self.highlight else colors.HexColor("#C7C7D1"))
            canvas.setStrokeColor(ACCENT if self.highlight else colors.HexColor("#C7C7D1"))
            canvas.roundRect(0, 0, filled, self.height, radius, stroke=1, fill=1)


# ---------------------------------------------------------------------------
# Page furniture and styles
# ---------------------------------------------------------------------------

def _draw_page_furniture(canvas: Canvas, document: BaseDocTemplate) -> None:
    """Draw the footer on every page: disclaimer, product mark and page number.

    The disclaimer goes on every page because a reader who only sees page 3
    still needs to know what the number does and does not mean.
    """
    canvas.saveState()
    width, _ = A4
    baseline = PAGE_MARGIN + 4 * mm

    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(PAGE_MARGIN, baseline + 7 * mm, width - PAGE_MARGIN, baseline + 7 * mm)

    canvas.setFont(FONT, 6.5)
    canvas.setFillColor(SUBTLE)
    # Wrapped by hand: a Paragraph cannot be drawn from an onPage callback
    # without building a whole frame for it.
    text = canvas.beginText(PAGE_MARGIN, baseline + 3.4 * mm)
    text.textLine(
        "This score estimates how well the listed skills overlap with a role's requirements. "
        "It is not a hiring decision, and it does not"
    )
    text.textLine(
        "consider name, gender, age, photo, religion, nationality, marital status or disability."
    )
    canvas.drawText(text)

    canvas.setFont(FONT, 7)
    canvas.drawString(PAGE_MARGIN, baseline - 3 * mm, "Resume Signal")
    canvas.drawRightString(width - PAGE_MARGIN, baseline - 3 * mm, f"Page {document.page}")

    canvas.restoreState()


def _section_heading(text: str, styles: dict[str, ParagraphStyle]) -> Flowable:
    """Take a heading string, return it styled with its rule above."""
    return Paragraph(text, styles["h2"])


def _build_styles() -> dict[str, ParagraphStyle]:
    """Return every paragraph style the report uses, defined once."""
    base = ParagraphStyle(
        "base",
        fontName=FONT,
        fontSize=9,
        leading=13.5,
        textColor=INK,
        alignment=TA_LEFT,
    )

    def derive(name: str, **overrides: Any) -> ParagraphStyle:
        return ParagraphStyle(name, parent=base, **overrides)

    return {
        "kicker": derive("kicker", fontName=FONT_BOLD, fontSize=8, textColor=ACCENT, leading=11),
        "kicker_right": derive("kicker_right", fontSize=8, textColor=SUBTLE, leading=11, alignment=2),
        "h1": derive("h1", fontName=FONT_BOLD, fontSize=19, leading=23),
        "band": derive("band", fontSize=10, textColor=MUTED, leading=14),
        "h2": derive("h2", fontName=FONT_BOLD, fontSize=11.5, leading=15, spaceBefore=4, spaceAfter=7),
        "h3": derive("h3", fontName=FONT_BOLD, fontSize=10, leading=14, spaceAfter=1),
        "body": derive("body", fontSize=9, leading=13.5),
        "body_muted": derive("body_muted", fontSize=8.5, leading=12.5, textColor=MUTED),
        "label": derive("label", fontName=FONT_BOLD, fontSize=7, leading=11, textColor=SUBTLE),
        "tiny": derive("tiny", fontSize=7.5, leading=11, textColor=MUTED),
        "tiny_accent": derive("tiny_accent", fontSize=7.5, leading=11, textColor=ACCENT, spaceBefore=3),
        "stat": derive("stat", fontName=FONT_BOLD, fontSize=15, leading=18),
        "th": derive("th", fontName=FONT_BOLD, fontSize=7, leading=10, textColor=SUBTLE),
        "row": derive("row", fontSize=8.5, leading=12),
        "row_bold": derive("row_bold", fontName=FONT_BOLD, fontSize=8.5, leading=12),
        "row_muted": derive("row_muted", fontSize=8, leading=12, textColor=MUTED),
        "row_small": derive("row_small", fontName=FONT_BOLD, fontSize=6.5, leading=11),
        "row_right": derive("row_right", fontSize=8.5, leading=12, alignment=2, textColor=MUTED),
        "row_right_bold": derive("row_right_bold", fontName=FONT_BOLD, fontSize=8.5, leading=12, alignment=2),
        "bullet": derive(
            "bullet",
            fontSize=8.5,
            leading=12.5,
            leftIndent=10,
            bulletIndent=1,
            textColor=MUTED,
            bulletFontName=BULLET_FONT,
            # 3.4pt against 8.5pt body: a dingbat circle at text size would be
            # a golf ball next to the words.
            bulletFontSize=3.4,
            bulletColor=SUBTLE,
        ),
    }


def _parse_timestamp(value: Any) -> datetime:
    """Take an ISO timestamp or datetime, return a datetime. Falls back to now."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            # fromisoformat rejects a trailing Z before Python 3.11's relaxation.
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now()

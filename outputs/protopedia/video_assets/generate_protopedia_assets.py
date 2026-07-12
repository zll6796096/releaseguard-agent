from __future__ import annotations

import html
import json
import math
import os
import subprocess
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs" / "protopedia"
ASSETS = OUT / "video_assets"
SHOTS = OUT / "raw_screenshots"

W, H = 1920, 1080

COLORS = {
    "bg": "#F6F7F9",
    "panel": "#FFFFFF",
    "ink": "#101828",
    "muted": "#667085",
    "line": "#D0D5DD",
    "navy": "#17233D",
    "blue": "#2563EB",
    "teal": "#0F766E",
    "green": "#15803D",
    "red": "#DC2626",
    "amber": "#B45309",
    "purple": "#7C3AED",
    "soft_blue": "#DBEAFE",
    "soft_teal": "#CCFBF1",
    "soft_red": "#FEE2E2",
    "soft_amber": "#FEF3C7",
    "soft_green": "#DCFCE7",
}


def existing_font(paths: list[str]) -> str:
    for path in paths:
        if Path(path).exists():
            return path
    return "/System/Library/Fonts/SFNS.ttf"


FONT_REG = existing_font(
    [
        "/System/Library/AssetsV2/PreinstalledAssetsV2/InstallWithOs/com_apple_MobileAsset_Font7/11ead4dd9f3a3503b4ced2546782dd8bc31871c9.asset/AssetData/YuGothic-Medium.otf",
        "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/ee89e7987a76cc8cfdff36c96bd7bc77655b343e.asset/AssetData/YuGothic-Medium.otf",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
    ]
)
FONT_BOLD = existing_font(
    [
        "/System/Library/AssetsV2/PreinstalledAssetsV2/InstallWithOs/com_apple_MobileAsset_Font7/0703ece025f7511095fc290b30bc2d3d59.asset/AssetData/YuGothic-Bold.otf",
        "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/b7a6a6575a699e801915b73b9e1e75c74a3404ce.asset/AssetData/YuGothic-Bold.otf",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
    ]
)
FONT_MONO = "/System/Library/Fonts/SFNSMono.ttf"


def font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_MONO if mono else (FONT_BOLD if bold else FONT_REG), size)


def img(bg: str = COLORS["bg"]) -> Image.Image:
    return Image.new("RGB", (W, H), bg)


def bbox(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont) -> tuple[int, int]:
    b = draw.textbbox((0, 0), text, font=fnt)
    return b[2] - b[0], b[3] - b[1]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        line = ""
        for ch in para:
            candidate = line + ch
            if bbox(draw, candidate, fnt)[0] <= max_width or not line:
                line = candidate
            else:
                lines.append(line)
                line = ch
        lines.append(line)
    return lines


def draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    fnt: ImageFont.ImageFont,
    fill: str = COLORS["ink"],
    max_width: int | None = None,
    line_gap: int = 12,
    anchor: str | None = None,
    align: str = "left",
) -> int:
    x, y = xy
    if max_width is None:
        draw.text((x, y), text, font=fnt, fill=fill, anchor=anchor, align=align)
        return bbox(draw, text, fnt)[1]
    h_total = 0
    for line in wrap_text(draw, text, fnt, max_width):
        draw.text((x, y + h_total), line, font=fnt, fill=fill)
        h_total += bbox(draw, line, fnt)[1] + line_gap
    return h_total


def rounded(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], fill: str, outline: str | None = None, width: int = 2, radius: int = 8) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def card(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], fill: str = COLORS["panel"], outline: str = COLORS["line"]) -> None:
    rounded(draw, xy, fill, outline=outline, radius=8)


def paste_fit(base: Image.Image, src_path: Path, box: tuple[int, int, int, int], crop: tuple[int, int, int, int] | None = None, radius: int = 8) -> None:
    src = Image.open(src_path).convert("RGB")
    if crop:
        src = src.crop(crop)
    x1, y1, x2, y2 = box
    bw, bh = x2 - x1, y2 - y1
    src.thumbnail((bw, bh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (bw, bh), "#0B1220")
    ox = (bw - src.width) // 2
    oy = (bh - src.height) // 2
    canvas.paste(src, (ox, oy))
    mask = Image.new("L", (bw, bh), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, bw, bh), radius=radius, fill=255)
    base.paste(canvas, (x1, y1), mask)


def pill(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fill: str, fg: str = "#FFFFFF") -> int:
    f = font(28, bold=True)
    tw, th = bbox(draw, text, f)
    x, y = xy
    rounded(draw, (x, y, x + tw + 40, y + 50), fill, radius=8)
    draw.text((x + 20, y + 10), text, font=f, fill=fg)
    return tw + 50


def arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: str = COLORS["navy"], width: int = 5) -> None:
    draw.line((start, end), fill=color, width=width)
    sx, sy = start
    ex, ey = end
    ang = math.atan2(ey - sy, ex - sx)
    size = 18
    pts = [
        (ex, ey),
        (ex - size * math.cos(ang - math.pi / 6), ey - size * math.sin(ang - math.pi / 6)),
        (ex - size * math.cos(ang + math.pi / 6), ey - size * math.sin(ang + math.pi / 6)),
    ]
    draw.polygon(pts, fill=color)


def title_block(draw: ImageDraw.ImageDraw, kicker: str, title: str, subtitle: str, x: int = 90, y: int = 70, width: int = 1180) -> int:
    draw_text(draw, (x, y), kicker, font(28, bold=True), fill=COLORS["teal"])
    h1 = draw_text(draw, (x, y + 46), title, font(72, bold=True), fill=COLORS["ink"], max_width=width, line_gap=8)
    h2 = draw_text(draw, (x, y + 60 + h1), subtitle, font(34), fill=COLORS["muted"], max_width=width, line_gap=10)
    return y + 70 + h1 + h2


def draw_code_panel(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], lines: list[tuple[str, str]]) -> None:
    card(draw, xy, fill="#0B1220", outline="#24324A")
    x1, y1, x2, _ = xy
    y = y1 + 34
    for text, color in lines:
        draw.text((x1 + 34, y), text, font=font(26, mono=True), fill=color)
        y += 40


def architecture_diagram(base: Image.Image, compact: bool = False) -> None:
    draw = ImageDraw.Draw(base)
    title_block(
        draw,
        "SYSTEM ARCHITECTURE",
        "実装に基づく構成",
        "PRの変更差分とプレビュー環境を集め、証拠からリリース可否を返します。",
        90,
        60,
        1200,
    )

    nodes = {
        "user": (90, 270, 390, 410, "User / Client", "Developer\nPR reviewer", COLORS["soft_teal"], COLORS["teal"]),
        "gha": (470, 270, 780, 410, "GitHub Actions", "call_releaseguard.py", COLORS["soft_blue"], COLORS["blue"]),
        "api": (870, 250, 1250, 430, "Backend / API", "ReleaseGuard FastAPI\nPOST /evaluate", COLORS["panel"], COLORS["navy"]),
        "frontend": (90, 570, 390, 730, "Frontend", "Demo Store\ncheckout UI", COLORS["panel"], COLORS["purple"]),
        "probes": (870, 540, 1250, 760, "Evidence Skills", "API Probe\nPlaywright Probe\nSecret Scan", COLORS["soft_amber"], COLORS["amber"]),
        "llm": (1350, 260, 1770, 420, "AI / LLM", "Gemini 2.5 Flash\nstructured output", COLORS["soft_green"], COLORS["green"]),
        "storage": (1350, 540, 1770, 700, "Database / Storage", "永続DBなし\n/tmp artifacts", "#E0F2FE", COLORS["blue"]),
        "auth": (470, 570, 780, 730, "Authentication", "Bearer token\nGitHub secrets", COLORS["soft_red"], COLORS["red"]),
        "deploy": (650, 840, 1270, 960, "Deployment / Hosting", "Docker containers on Google Cloud Run", "#F3E8FF", COLORS["purple"]),
    }

    for key, (x1, y1, x2, y2, head, body, fill, accent) in nodes.items():
        card(draw, (x1, y1, x2, y2), fill=fill, outline=accent)
        draw_text(draw, (x1 + 24, y1 + 22), head, font(27, bold=True), fill=accent, max_width=x2 - x1 - 48, line_gap=8)
        draw_text(draw, (x1 + 24, y1 + 74), body, font(24), fill=COLORS["ink"], max_width=x2 - x1 - 48, line_gap=8)

    arrow(draw, (390, 340), (470, 340), COLORS["teal"])
    arrow(draw, (780, 340), (870, 340), COLORS["blue"])
    arrow(draw, (1060, 430), (1060, 540), COLORS["navy"])
    arrow(draw, (1250, 340), (1350, 340), COLORS["green"])
    arrow(draw, (1250, 650), (1350, 620), COLORS["blue"])
    draw_text(draw, (110, 750), "Playwrightが画面を検査", font(21), fill=COLORS["muted"], max_width=330)
    draw_text(draw, (490, 750), "Bearer tokenで/evaluateを保護", font(21), fill=COLORS["muted"], max_width=300)
    arrow(draw, (1050, 760), (980, 840), COLORS["amber"])

    draw_text(
        draw,
        (90, 990),
        "注: 現行MVPに永続DBはなく、判定はステートレス。スクリーンショットは /tmp/releaseguard-artifacts に一時保存します。",
        font(25),
        fill=COLORS["muted"],
        max_width=1700,
    )


def make_image_01() -> None:
    base = img()
    draw = ImageDraw.Draw(base)
    title_block(
        draw,
        "Findy Hackathon / Proto Pedia 提出作品",
        "ReleaseGuard Agent",
        "CIの先で、リリース可否を証拠で判断するAIゲート",
        90,
        80,
        1000,
    )
    y = 360
    for label, color in [
        ("API Probe", COLORS["blue"]),
        ("Playwright", COLORS["teal"]),
        ("Secret Scan", COLORS["red"]),
        ("Gemini", COLORS["green"]),
        ("Policy", COLORS["purple"]),
    ]:
        y_offset = pill(draw, (90, y), label, color)
        y += 70
    draw_text(
        draw,
        (90, 760),
        "壊れたユーザー導線や漏洩リスクを、PRレビュー前に見える証拠として返します。",
        font(38, bold=True),
        fill=COLORS["ink"],
        max_width=760,
    )
    card(draw, (1010, 140, 1810, 900), fill="#0B1220", outline="#24324A")
    paste_fit(base, SHOTS / "02_checkout_clean.png", (1060, 190, 1760, 585), crop=(600, 110, 1320, 900), radius=8)
    draw_code_panel(
        draw,
        (1060, 640, 1760, 850),
        [
            ("verdict: APPROVE / BLOCK", "#E5E7EB"),
            ("overall_risk: 90/100", "#FCA5A5"),
            ("evidence: playwright_probe fail", "#93C5FD"),
            ("policy: deterministic BLOCK", "#FDE68A"),
        ],
    )
    base.save(OUT / "image_01_main.png")


def make_image_02() -> None:
    base = img()
    draw = ImageDraw.Draw(base)
    title_block(
        draw,
        "PROBLEM",
        "CIは緑。でも購入できない。",
        "DOMにボタンが残っていても、CSSで透明ならユーザーには見えません。",
        90,
        70,
        760,
    )
    items = [
        ("単体テスト", "selector は見つかる", COLORS["blue"], COLORS["soft_blue"]),
        ("目視確認", "毎回は続かない", COLORS["amber"], COLORS["soft_amber"]),
        ("本番リスク", "checkout 導線が停止", COLORS["red"], COLORS["soft_red"]),
    ]
    y = 360
    for head, body, accent, fill in items:
        card(draw, (90, y, 760, y + 130), fill=fill, outline=accent)
        draw_text(draw, (120, y + 24), head, font(34, bold=True), fill=accent)
        draw_text(draw, (120, y + 74), body, font(31), fill=COLORS["ink"])
        y += 160
    card(draw, (900, 160, 1780, 910), fill="#0B1220", outline=COLORS["red"])
    paste_fit(base, SHOTS / "05_checkout_hidden_button.png", (945, 215, 1735, 770), crop=(610, 130, 1310, 920), radius=8)
    # Expected button region in cropped checkout screenshot.
    draw.rounded_rectangle((1080, 702, 1600, 775), radius=8, outline=COLORS["red"], width=7)
    draw_text(draw, (1090, 790), "ここにあるはずの Pay ボタン\nopacity: 0 で不可視", font(29, bold=True), fill="#FCA5A5", max_width=620)
    base.save(OUT / "image_02_problem.png")


def make_image_03() -> None:
    data = json.loads((ASSETS / "evaluation_hidden_checkout.json").read_text(encoding="utf-8"))
    base = img()
    draw = ImageDraw.Draw(base)
    title_block(
        draw,
        "DEMO",
        "入力 → 検査 → BLOCK",
        "ローカル起動した実画面と API 結果を使用しています。",
        90,
        60,
        1180,
    )
    card(draw, (90, 260, 700, 820), fill="#0B1220", outline=COLORS["teal"])
    paste_fit(base, SHOTS / "03_checkout_filled.png", (120, 300, 670, 780), crop=(650, 140, 1270, 900), radius=8)
    draw_text(draw, (150, 835), "1. checkout を実操作", font(30, bold=True), fill=COLORS["teal"])
    arrow(draw, (730, 530), (860, 530), COLORS["navy"], width=7)
    card(draw, (890, 250, 1230, 810), fill=COLORS["soft_red"], outline=COLORS["red"])
    draw_text(draw, (930, 300), "ReleaseGuard\nVerdict", font(31, bold=True), fill=COLORS["red"], max_width=280)
    draw_text(draw, (930, 380), data["verdict"], font(82, bold=True), fill=COLORS["red"])
    draw_text(draw, (930, 500), f"Risk {data['overall_risk']}/100", font(45, bold=True), fill=COLORS["ink"])
    ev_y = 590
    for ev in data["evidence"]:
        status = "PASS" if ev["status"] in ("success", "pass") else "FAIL"
        color = COLORS["green"] if status == "PASS" else COLORS["red"]
        draw_text(draw, (930, ev_y), f"{status}  {ev['category']}", font(25, mono=True), fill=color)
        ev_y += 42
    arrow(draw, (1260, 530), (1390, 530), COLORS["navy"], width=7)
    card(draw, (1420, 260, 1810, 820), fill="#0B1220", outline=COLORS["red"])
    paste_fit(base, SHOTS / "05_checkout_hidden_button.png", (1450, 300, 1780, 740), crop=(650, 140, 1270, 900), radius=8)
    draw_text(draw, (1450, 835), "2. 透明ボタンを検知", font(30, bold=True), fill=COLORS["red"])
    base.save(OUT / "image_03_demo.png")


def make_image_04() -> None:
    base = img()
    draw = ImageDraw.Draw(base)
    title_block(
        draw,
        "TECHNOLOGY",
        "AI要約 + 決定論ポリシー",
        "重大リスクの BLOCK はローカルポリシーが優先します。",
        90,
        60,
        1180,
    )
    x_positions = [120, 470, 820, 1170, 1520]
    labels = [
        ("GitHub PR", "diff / SHA / URL", COLORS["blue"], COLORS["soft_blue"]),
        ("FastAPI", "POST /evaluate", COLORS["navy"], "#E5E7EB"),
        ("Probes", "API / UI / Secret", COLORS["teal"], COLORS["soft_teal"]),
        ("Gemini", "structured JSON", COLORS["green"], COLORS["soft_green"]),
        ("Policy", "final BLOCK", COLORS["red"], COLORS["soft_red"]),
    ]
    for i, (head, body, accent, fill) in enumerate(labels):
        x = x_positions[i]
        card(draw, (x, 360, x + 280, 560), fill=fill, outline=accent)
        draw_text(draw, (x + 24, 400), head, font(32, bold=True), fill=accent)
        draw_text(draw, (x + 24, 460), body, font(26), fill=COLORS["ink"], max_width=230)
        if i < len(labels) - 1:
            arrow(draw, (x + 285, 460), (x_positions[i + 1] - 20, 460), COLORS["navy"])
    callouts = [
        ("並列収集", "API health、DOM、Playwright、Secret Scan を同時に集める", COLORS["teal"]),
        ("LLM要約", "Gemini 2.5 Flash が証拠を構造化して人間向けに説明", COLORS["green"]),
        ("安全優先", "見えない checkout や漏洩は AI の判断に関係なく BLOCK", COLORS["red"]),
    ]
    y = 670
    for head, body, accent in callouts:
        card(draw, (150, y, 1770, y + 100), fill=COLORS["panel"], outline=accent)
        draw_text(draw, (185, y + 25), head, font(30, bold=True), fill=accent)
        draw_text(draw, (390, y + 26), body, font(29), fill=COLORS["ink"], max_width=1280)
        y += 120
    base.save(OUT / "image_04_technology.png")


def make_image_05() -> None:
    base = img()
    draw = ImageDraw.Draw(base)
    title_block(
        draw,
        "IMPACT",
        "本番前に止める",
        "自動マージではなく、証拠つきの判断材料をPRに返します。",
        90,
        70,
        1180,
    )
    left = [
        ("Before", "CIは成功\n目視確認は属人化\n危険なPRを見逃す", COLORS["amber"], COLORS["soft_amber"]),
        ("After", "BLOCK判定\n証拠つきPRコメント\n安全な次アクション", COLORS["green"], COLORS["soft_green"]),
    ]
    for i, (head, body, accent, fill) in enumerate(left):
        x = 110 + i * 510
        card(draw, (x, 330, x + 440, 720), fill=fill, outline=accent)
        draw_text(draw, (x + 35, 370), head, font(44, bold=True), fill=accent)
        draw_text(draw, (x + 35, 460), body, font(38, bold=True), fill=COLORS["ink"], max_width=360, line_gap=20)
    card(draw, (1160, 300, 1810, 800), fill="#0B1220", outline=COLORS["blue"])
    draw_code_panel(
        draw,
        (1210, 360, 1760, 710),
        [
            ("Rule: visual failure -> BLOCK", "#FCA5A5"),
            ("Rule: secret leak -> BLOCK", "#FCA5A5"),
            ("AI: explain risk and next action", "#86EFAC"),
            ("Human: final merge decision", "#93C5FD"),
            ("No auto-merge / no traffic shift", "#FDE68A"),
        ],
    )
    draw_text(
        draw,
        (1200, 830),
        "今後: 認証つきE2E、Cloud Logging異常検知、DB migrationリスク分析へ拡張",
        font(30, bold=True),
        fill=COLORS["navy"],
        max_width=650,
    )
    base.save(OUT / "image_05_impact.png")


def make_system_architecture() -> None:
    base = img()
    architecture_diagram(base)
    base.save(OUT / "system_architecture.png")

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<rect width="1920" height="1080" fill="{COLORS["bg"]}"/>
<style>
text {{ font-family: "Yu Gothic", "Hiragino Sans", sans-serif; fill: {COLORS["ink"]}; }}
.h {{ font-size: 54px; font-weight: 700; }}
.k {{ font-size: 24px; font-weight: 700; fill: {COLORS["teal"]}; }}
.s {{ font-size: 28px; fill: {COLORS["muted"]}; }}
.box {{ fill: white; stroke: {COLORS["line"]}; stroke-width: 3; rx: 8; }}
.label {{ font-size: 27px; font-weight: 700; }}
.body {{ font-size: 23px; }}
.note {{ font-size: 23px; fill: {COLORS["muted"]}; }}
.arrow {{ stroke: {COLORS["navy"]}; stroke-width: 5; marker-end: url(#arrow); fill: none; }}
</style>
<defs><marker id="arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 Z" fill="{COLORS["navy"]}"/></marker></defs>
<text x="90" y="95" class="k">SYSTEM ARCHITECTURE</text>
<text x="90" y="165" class="h">ReleaseGuard Agent 実装構成</text>
<text x="90" y="215" class="s">GitHub PR と Cloud Run プレビューを証拠化し、ReleaseDecision JSON と PR コメントを返します。</text>
'''
    svg_nodes = [
        (90, 300, 270, 125, "User / Client", "Developer / Reviewer"),
        (430, 300, 310, 125, "Frontend", "Demo Store Jinja2 UI"),
        (820, 275, 350, 175, "Backend / API", "ReleaseGuard FastAPI\\nPOST /evaluate"),
        (1250, 285, 350, 145, "AI / External API", "Gemini 2.5 Flash"),
        (820, 555, 350, 190, "Evidence Skills", "API Probe\\nPlaywright Probe\\nSecret Scan"),
        (1250, 555, 350, 160, "Database / Storage", "No persistent DB\\n/tmp artifacts"),
        (430, 555, 310, 160, "Authentication", "HTTP Bearer token\\nGitHub Secrets"),
        (650, 845, 620, 105, "Deployment / Hosting", "Docker containers on Google Cloud Run"),
    ]
    for x, y, w, h, label, body in svg_nodes:
        svg += f'<rect x="{x}" y="{y}" width="{w}" height="{h}" class="box"/>\n'
        svg += f'<text x="{x+24}" y="{y+42}" class="label">{html.escape(label)}</text>\n'
        for idx, line in enumerate(body.split("\\n")):
            svg += f'<text x="{x+24}" y="{y+82+idx*34}" class="body">{html.escape(line)}</text>\n'
    for x1, y1, x2, y2 in [
        (360, 360, 430, 360),
        (740, 360, 820, 360),
        (995, 450, 995, 555),
        (1170, 360, 1250, 360),
        (1170, 650, 1250, 630),
        (740, 635, 820, 635),
        (995, 745, 960, 845),
    ]:
        svg += f'<path d="M{x1},{y1} L{x2},{y2}" class="arrow"/>\n'
    svg += f'<text x="90" y="1010" class="note">MVP はステートレスです。永続DBは実装されておらず、スクリーンショットはコンテナ内 /tmp に一時保存します。</text></svg>\n'
    (OUT / "system_architecture.svg").write_text(svg, encoding="utf-8")


def make_video_slides() -> list[tuple[Path, int]]:
    slides: list[tuple[Image.Image, int, str]] = []

    def blank(title: str, subtitle: str, kicker: str = "ReleaseGuard Agent") -> tuple[Image.Image, ImageDraw.ImageDraw]:
        base = img()
        d = ImageDraw.Draw(base)
        title_block(d, kicker, title, subtitle, 90, 70, 1260)
        return base, d

    base, d = blank("CIの先で、リリース可否を証拠で判断するAIゲート", "Findy Hackathon / Proto Pedia 提出作品")
    paste_fit(base, OUT / "image_01_main.png", (1140, 240, 1810, 860), crop=(900, 80, 1830, 940), radius=8)
    slides.append((base, 5, "slide_00_title.png"))

    base, d = blank("課題: テストは通る。でもユーザー導線が壊れる。", "checkout ボタンがDOMに存在しても、opacity: 0なら購入できません。", "Problem")
    paste_fit(base, SHOTS / "05_checkout_hidden_button.png", (1040, 250, 1780, 830), crop=(600, 120, 1320, 930), radius=8)
    draw_text(d, (120, 380), "誰が困るか", font(36, bold=True), fill=COLORS["red"])
    draw_text(d, (120, 450), "・小規模チームのPRレビュアー\n・Cloud Runで高速に出す個人開発者\n・本番障害を避けたいスタートアップ", font(34), fill=COLORS["ink"], max_width=760, line_gap=18)
    slides.append((base, 10, "slide_01_problem.png"))

    base, d = blank("解決策: PRごとに証拠を集めて、危険ならBLOCK", "API、画面、差分、秘密情報、AI要約を1つの判定にまとめます。", "Solution")
    for i, (head, color) in enumerate([("API", COLORS["blue"]), ("UI", COLORS["teal"]), ("Secret", COLORS["red"]), ("Gemini", COLORS["green"]), ("Policy", COLORS["purple"])]):
        x = 140 + i * 330
        card(d, (x, 420, x + 240, 590), fill=COLORS["panel"], outline=color)
        draw_text(d, (x + 35, 465), head, font(42, bold=True), fill=color)
        if i < 4:
            arrow(d, (x + 250, 505), (x + 315, 505), COLORS["navy"])
    draw_text(d, (150, 720), "重大リスクは決定論ルールが優先。Geminiは説明と次アクションを補強します。", font(40, bold=True), fill=COLORS["ink"], max_width=1500)
    slides.append((base, 10, "slide_02_solution.png"))

    base, d = blank("デモ 1: 正常な checkout", "入力して購入ボタンが見える状態を確認します。", "Demo")
    paste_fit(base, SHOTS / "03_checkout_filled.png", (170, 260, 1050, 900), crop=(610, 120, 1320, 930), radius=8)
    draw_code_panel(d, (1150, 330, 1760, 760), [("GET /healthz -> 200", "#86EFAC"), ("GET /checkout -> 200", "#86EFAC"), ("button visible -> true", "#86EFAC"), ("secret_scan -> clean", "#86EFAC")])
    slides.append((base, 8, "slide_03_demo_clean.png"))

    base, d = blank("デモ 2: ボタンが透明化", "selector は存在しますが、ユーザーには見えない regression です。", "Demo")
    paste_fit(base, SHOTS / "05_checkout_hidden_button.png", (170, 260, 1050, 900), crop=(610, 120, 1320, 930), radius=8)
    draw_code_panel(d, (1150, 330, 1760, 760), [("class=\"hidden-button\"", "#FCA5A5"), ("computed opacity: 0", "#FCA5A5"), ("playwright_probe: fail", "#FCA5A5"), ("user journey: broken", "#FDE68A")])
    slides.append((base, 8, "slide_04_demo_bug.png"))

    data = json.loads((ASSETS / "evaluation_hidden_checkout.json").read_text(encoding="utf-8"))
    base, d = blank("デモ 3: BLOCK 判定", "hidden checkout は Risk 90/100 でリリース不可。", "Demo")
    draw_text(d, (140, 330), data["verdict"], font(100, bold=True), fill=COLORS["red"])
    draw_text(d, (145, 460), f"Overall Risk {data['overall_risk']}/100", font(50, bold=True), fill=COLORS["ink"])
    y = 570
    for ev in data["evidence"]:
        status = "PASS" if ev["status"] in ("success", "pass") else "FAIL"
        color = COLORS["green"] if status == "PASS" else COLORS["red"]
        draw_text(d, (150, y), f"{status:4} {ev['category']}", font(32, mono=True), fill=color)
        y += 52
    draw_code_panel(d, (980, 300, 1780, 790), [("Rule: checkout button invisible", "#FCA5A5"), ("Rule: Playwright journey failed", "#FCA5A5"), ("Gemini fallback: manual review", "#FDE68A"), ("Final: do not ship", "#93C5FD")])
    slides.append((base, 10, "slide_05_demo_block.png"))

    base = img()
    architecture_diagram(base, compact=True)
    slides.append((base, 10, "slide_06_architecture.png"))

    base, d = blank("価値: AI任せではなく、安全な意思決定レイヤー", "自動マージや本番トラフィック切替は行わず、人間に証拠を返します。", "Value")
    values = [("壊れたUIを本番前に検知", COLORS["red"]), ("漏洩候補をPR差分で検出", COLORS["amber"]), ("PRコメントで修正行動を提示", COLORS["blue"]), ("Cloud Runへそのまま載せやすい", COLORS["green"])]
    for i, (text, color) in enumerate(values):
        x = 130 + (i % 2) * 820
        y = 340 + (i // 2) * 220
        card(d, (x, y, x + 710, y + 150), fill=COLORS["panel"], outline=color)
        draw_text(d, (x + 35, y + 48), text, font(40, bold=True), fill=color, max_width=640)
    slides.append((base, 10, "slide_07_value.png"))

    base, d = blank("今後: より深いリリースリスクへ", "ログイン導線、Cloud Logging、DB migration、複数画面E2Eへ拡張できます。", "Future")
    draw_text(d, (120, 390), "想定ユーザー: GitHub Actions + Cloud Runで開発する個人開発者、小規模チーム、スタートアップ", font(38, bold=True), fill=COLORS["ink"], max_width=1600)
    draw_text(d, (120, 560), "ReleaseGuard Agent", font(80, bold=True), fill=COLORS["navy"])
    draw_text(d, (120, 660), "証拠が足りないリリースを、出す前に止める。", font(46, bold=True), fill=COLORS["teal"])
    slides.append((base, 13, "slide_08_end.png"))

    written: list[tuple[Path, int]] = []
    for image, duration, name in slides:
        path = ASSETS / name
        image.save(path)
        written.append((path, duration))
    return written


def make_bgm(duration: int, path: Path) -> None:
    sr = 44100
    total = duration * sr
    freqs = [220.0, 277.18, 329.63, 440.0]
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        frames = bytearray()
        for i in range(total):
            t = i / sr
            amp = min(1.0, t / 3.0, (duration - t) / 3.0) * 0.18
            val = sum(math.sin(2 * math.pi * f * t) for f in freqs) / len(freqs)
            val += 0.25 * math.sin(2 * math.pi * 110.0 * t)
            sample = int(max(-1.0, min(1.0, val * amp)) * 32767)
            frames += sample.to_bytes(2, byteorder="little", signed=True)
        wf.writeframes(frames)


def make_video(slides: list[tuple[Path, int]]) -> None:
    concat = ASSETS / "concat_slides.txt"
    lines = []
    total = 0
    for path, duration in slides:
        lines.append(f"file '{path}'")
        lines.append(f"duration {duration}")
        total += duration
    lines.append(f"file '{slides[-1][0]}'")
    concat.write_text("\n".join(lines) + "\n", encoding="utf-8")
    bgm = ASSETS / "soft_bgm.wav"
    make_bgm(total, bgm)
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat),
        "-i",
        str(bgm),
        "-vf",
        "fps=24,format=yuv420p",
        "-c:v",
        "libx264",
        "-profile:v",
        "high",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-shortest",
        str(OUT / "demo_video.mp4"),
    ]
    subprocess.run(cmd, check=True)


def write_markdown_files() -> None:
    story = """## ① 本作品で解決したい課題とその背景
CI は「書かれたテストが通ったか」を確認できますが、「その変更をユーザーに届けるだけの証拠が揃っているか」までは判断しません。今回のデモでは、checkout ボタンが DOM には存在するのに CSS の `opacity: 0` でユーザーから見えなくなる regression を扱います。selector ベースのテストや health check は通っても、実際の購入導線は止まります。小規模チームほどリリース前の目視確認が属人化しやすく、見逃しがそのまま本番障害につながります。

## ② 想定する利用ユーザー
GitHub Actions と Google Cloud Run を使って Web サービスを継続的に開発・デプロイする個人開発者、小規模チーム、スタートアップを想定しています。特に、PR のたびにプレビュー環境は作っているものの、UI の視覚的な壊れ方や PR 差分のリスクを毎回十分にレビューしきれないチームに向いています。

## ③ プロダクトの特徴
ReleaseGuard Agent は、PR の changed files / diff / commit SHA / preview URL を受け取り、API health、checkout DOM、Playwright による実レンダリング、Secret Scan を並列に実行します。収集した証拠は Gemini 2.5 Flash の構造化出力で人間に読みやすく要約し、最終判定は決定論的な Risk Policy が安全側に統合します。たとえば checkout ボタン不可視化や秘密情報漏洩は、AI の判断に関係なく `BLOCK` します。自動マージや本番トラフィック切替は行わず、PR コメントとして証拠と安全な次アクションを返す点が特徴です。"""

    video_script = """# ReleaseGuard Agent demo video script

想定尺: 84秒。動画内テロップは日本語。音声合成は使わず、BGMと画面テロップで完結する構成。

| 時間 | 画面 | ナレーション台本 |
|---|---|---|
| 0-5秒 | タイトル | ReleaseGuard Agent は、CI の先でリリース可否を証拠から判断する AI Release Gate です。Findy Hackathon / Proto Pedia 提出作品です。 |
| 5-15秒 | 課題 | CI はテストが通ったことを示します。しかし、checkout ボタンが CSS で透明になっていても、DOM に残っていれば selector test は通ることがあります。ユーザーには購入ボタンが見えません。 |
| 15-25秒 | 解決策 | ReleaseGuard は PR の preview URL、変更差分、commit 情報を受け取り、API、UI、秘密情報、AI 要約を組み合わせて判断します。 |
| 25-33秒 | 正常画面デモ | まず正常な checkout 画面です。入力欄と Pay ボタンが表示され、ユーザー導線は成立しています。 |
| 33-41秒 | regression デモ | 次に、PR で `hidden-button` が入った状態です。ボタンは HTML に存在しますが、画面上は見えずクリックできません。 |
| 41-51秒 | BLOCK 結果 | ReleaseGuard は Playwright で computed opacity を確認し、checkout button invisible として Risk 90 の BLOCK を返しました。 |
| 51-61秒 | 技術構成 | Backend は FastAPI、ブラウザ検証は Playwright、AI 要約は Gemini 2.5 Flash、デプロイ先は Google Cloud Run です。GitHub Actions から `/evaluate` を呼びます。 |
| 61-71秒 | 安全設計 | Gemini は説明を補強しますが、重大リスクの BLOCK は決定論ルールが優先します。自動マージや本番トラフィック切替は行いません。 |
| 71-84秒 | 価値と今後 | 小規模チームでも、目視に頼りきらず、証拠つきで危険な PR を止められます。今後は認証つき E2E、Cloud Logging、DB migration リスク分析へ拡張します。 |
"""
    (OUT / "video_script_ja.md").write_text(video_script, encoding="utf-8")

    storyboard = """# Storyboard

1. タイトル: ReleaseGuard Agent / 証拠で判断するAIリリースゲート
2. 課題: CIは緑だが、checkoutボタンが透明で購入できない
3. 解決策: PR previewをAPI・UI・Secret・AIで検査
4. デモ1: 正常なcheckout入力画面
5. デモ2: hidden-button regression
6. デモ3: BLOCK 90/100 の実行結果
7. 技術: GitHub Actions、FastAPI、Playwright、Gemini、Cloud Run
8. 価値: 本番前に止める、人間が最終判断する
9. 今後: 認証つきE2E、ログ異常、DB migrationチェック
"""
    (OUT / "storyboard.md").write_text(storyboard, encoding="utf-8")

    youtube = """# YouTube / Vimeo upload metadata

## Upload status
YouTube へ限定公開でアップロード済み。

- Video URL: https://youtu.be/ZTKjSorZjx8
- ProtoPedia URL: https://protopedia.net/prototype/8771
- Note: YouTube のカスタムサムネイルはアカウントの電話番号確認が必要だったため、動画先頭スライド由来の自動サムネイルを使用。

## Title
ReleaseGuard Agent - 証拠でリリース可否を判断するAI Release Gate

## Description
ReleaseGuard Agent は、GitHub PR と Google Cloud Run のプレビュー環境を対象に、API health、Playwright による実画面検証、Secret Scan、Gemini 2.5 Flash の構造化要約を組み合わせて、危険なリリースを本番前に BLOCK する AI Release Gate です。

この動画では、checkout ボタンが DOM に存在するにもかかわらず CSS の opacity: 0 によりユーザーから見えなくなる regression をデモします。通常の CI が見逃し得るユーザー導線の破損を、ReleaseGuard が証拠つきで検出し、PR 上に BLOCK 判定を返します。

Findy Hackathon / Proto Pedia 提出作品

## Tags
findy_hackathon, ReleaseGuard, AI, 生成AI, DevOps, GitHub Actions, Google Cloud Run, FastAPI, Playwright, Gemini, リリース管理, セキュリティ

## Thumbnail
`image_01_main.png`
"""
    (OUT / "youtube_vimeo_metadata.md").write_text(youtube, encoding="utf-8")

    arch_md = """# System Architecture

## 構成概要
ReleaseGuard Agent は、GitHub Actions から `POST /evaluate` を受け取り、PR の preview URL と diff を証拠として検査するステートレスな FastAPI サービスです。対象アプリケーションは Demo Store の Jinja2 checkout UI で、Cloud Run 上のプレビュー環境を想定しています。

## 実装に基づくコンポーネント
- **User / Client**: GitHub PR を作成・確認する developer / reviewer。
- **Frontend**: `apps/demo_store` の FastAPI + Jinja2 + HTML/CSS checkout UI。GitHub PR コメントも結果表示面になる。
- **Backend / API**: `apps/releaseguard` の FastAPI。`GET /healthz` と `POST /evaluate` を提供。
- **AI / LLM / External API**: `google-genai` SDK で Gemini 2.5 Flash を呼び、`GeminiJudgement` schema の structured output を生成。
- **Database / Storage**: 現行 MVP に永続DBはない。Playwright screenshot は `/tmp/releaseguard-artifacts/checkout.png` に一時保存。
- **Authentication**: `RELEASEGUARD_SHARED_TOKEN` が設定されている場合、HTTP Bearer token を要求。GitHub Actions 側は repository secrets / variables を使用。
- **Deployment / Hosting**: Docker コンテナを Google Cloud Run に配置。ローカル検証は Docker network 上の Demo Store と ReleaseGuard Agent で実施。

## 判定フロー
1. GitHub Actions が PR context、changed files、diff、preview URL を `scripts/call_releaseguard.py` で収集する。
2. ReleaseGuard Agent が `ApiProbe`、`SecretScan`、`PlaywrightProbe` を並列実行する。
3. `RiskPolicy` が checkout failure、secret leak、Playwright failure を決定論的に BLOCK する。
4. Gemini が証拠を構造化要約する。Gemini が失敗または未設定の場合は WARN fallback を返す。
5. 最終 risk は policy risk と Gemini risk の最大値。最終 report は Markdown と JSON で返る。
6. GitHub Actions が `actions/github-script` で PR コメントを作成・更新し、BLOCK / ESCALATE なら workflow を fail させる。
"""
    (OUT / "system_architecture.md").write_text(arch_md, encoding="utf-8")

    submission = f"""# Proto Pedia submission draft

## 作品ステータス案
開発中（MVP はローカル・Cloud Run 想定構成で動作確認済み。今後の拡張余地があるため）

## 作品タイトル案
ReleaseGuard Agent：証拠で止めるAIリリースゲート

## 概要
PRのプレビュー環境をAPI・UI・秘密情報・AIで検証し、本番前に危険な変更をBLOCKするリリースゲート。

## 動画URL欄
https://youtu.be/ZTKjSorZjx8

## ProtoPedia 登録済みURL
https://protopedia.net/prototype/8771

## システム構成説明
ReleaseGuard Agent は GitHub Actions から `POST /evaluate` を受ける FastAPI サービスです。PR の changed files、diff、commit SHA、preview URL を入力に、API health check、checkout DOM 検査、Playwright の実レンダリング検査、Secret Scan を並列実行します。Gemini 2.5 Flash は収集証拠を `GeminiJudgement` schema で要約し、最終判定は決定論的な `RiskPolicy` が統合します。checkout ボタン不可視化や秘密情報漏洩は、AI の判断に関係なく `BLOCK` します。現行 MVP は永続DBを持たず、Playwright screenshot はコンテナ内 `/tmp/releaseguard-artifacts` に一時保存します。Cloud Run / Docker / GitHub Actions での運用を想定しています。

## 開発素材一覧
- Python 3.12
- FastAPI
- Pydantic / pydantic-settings
- HTTPX
- structlog
- Playwright / headless Chromium
- Google GenAI SDK
- Gemini 2.5 Flash
- Jinja2 / HTML / CSS
- Docker
- Google Cloud Run
- GitHub Actions
- actions/github-script / GitHub REST API
- pytest / pytest-asyncio

## タグ一覧
findy_hackathon, AI, 生成AI, DevOps, GitHubActions, CloudRun, FastAPI, Playwright, リリース管理, セキュリティ

## ストーリー
{story}

## 関連URL候補
- GitHub Repository: https://github.com/zll6796096/releaseguard-agent
- Demo Store URL: https://demo-store-788259830737.asia-northeast1.run.app
- ReleaseGuard Agent URL: https://releaseguard-agent-788259830737.asia-northeast1.run.app
- Demo PR: https://github.com/zll6796096/releaseguard-agent/pull/2
- YouTube Demo: https://youtu.be/ZTKjSorZjx8
- ProtoPedia: https://protopedia.net/prototype/8771

## YouTube / Vimeo 用タイトル
ReleaseGuard Agent - 証拠でリリース可否を判断するAI Release Gate

## YouTube / Vimeo 用説明文
ReleaseGuard Agent は、GitHub PR と Google Cloud Run のプレビュー環境を対象に、API health、Playwright による実画面検証、Secret Scan、Gemini 2.5 Flash の構造化要約を組み合わせて、危険なリリースを本番前に BLOCK する AI Release Gate です。

この動画では、checkout ボタンが DOM に存在するにもかかわらず CSS の opacity: 0 によりユーザーから見えなくなる regression をデモします。通常の CI が見逃し得るユーザー導線の破損を、ReleaseGuard が証拠つきで検出し、PR 上に BLOCK 判定を返します。

## YouTube / Vimeo 用タグ
findy_hackathon, ReleaseGuard, AI, 生成AI, DevOps, GitHub Actions, Google Cloud Run, FastAPI, Playwright, Gemini, リリース管理, セキュリティ

## サムネイルに使う画像ファイル名
`image_01_main.png`
"""
    (OUT / "protopedia_submission.md").write_text(submission, encoding="utf-8")

    readme = """# Proto Pedia deliverables

## 必須成果物
- `demo_video.mp4`: YouTube / Vimeo アップロード用 MP4。日本語テロップ、BGM、実画面スクリーンショット入り。
- `video_script_ja.md`: 動画の日本語ナレーション台本。
- `youtube_vimeo_metadata.md`: アップロード用タイトル、説明文、タグ、サムネイル指定。
- `image_01_main.png`: メインビジュアル。作品名と価値提案。
- `image_02_problem.png`: 課題画像。CI が見逃す透明 checkout ボタン。
- `image_03_demo.png`: デモ画像。実行結果の BLOCK 90/100。
- `image_04_technology.png`: 技術画像。AI と決定論ルールの分離。
- `image_05_impact.png`: 成果画像。導入後の価値。
- `system_architecture.png`: 登録用システムアーキテクチャ図。
- `system_architecture.svg`: 同内容の SVG 版。
- `system_architecture.md`: 技術説明文。
- `protopedia_submission.md`: Proto Pedia 登録欄に貼る本文ドラフト。

## 追加成果物
- `storyboard.md`: 動画構成の簡易 storyboard。
- `raw_screenshots/`: Docker 起動した実アプリから撮影した 1920x1080 PNG。
- `video_assets/`: 評価 JSON、動画スライド、BGM、生成スクリプト。
- `protopedia_upload/`: ProtoPedia アップロード用に 880x495 へ正規化した画像。

## 登録済みURL
- YouTube: https://youtu.be/ZTKjSorZjx8
- ProtoPedia: https://protopedia.net/prototype/8771

## ローカル検証で使った起動方法
既存の `8081` が使用中だったため、提出素材用には次のポートで Docker 起動しました。

```bash
docker network create rg-proto-net
docker run -d --name rg-proto-demo --network rg-proto-net -p 8091:8080 -e BUG_HIDE_CHECKOUT_BUTTON=false releaseguard-demo-store-protopedia:local
docker run -d --name rg-proto-agent --network rg-proto-net -p 8095:8080 -e GEMINI_MODEL=gemini-2.5-flash releaseguard-agent-protopedia:local
```

## 登録時の注意
YouTube へ限定公開でアップロードし、ProtoPedia へ作品登録済みです。YouTube のカスタムサムネイルはアカウントの電話番号確認が必要だったため設定できませんでした。ProtoPedia 作品画像には `image_01_main.png` を含む 5 枚を登録済みです。
"""
    (OUT / "README_DELIVERABLES.md").write_text(readme, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    make_image_01()
    make_image_02()
    make_image_03()
    make_image_04()
    make_image_05()
    make_system_architecture()
    slides = make_video_slides()
    make_video(slides)
    write_markdown_files()


if __name__ == "__main__":
    main()

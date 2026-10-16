"""
카드뉴스 고정 디자인 템플릿 (@hyewon_high1)

carousel_draft.md 를 읽어 1080x1350 카드 이미지를 만든다.

    python generate_cards.py
    python generate_cards.py --draft carousel_draft.md --out output_cards --category "SPORT NUTRITION"

원고(md) 규칙
- "## Slide N" 아래의 코드 블록을 읽는다.
- "**메인 헤드라인" 다음 코드 블록 = 타이틀, "**서브 카피" ~ "**이미지/시각" 사이 코드 블록 = 본문.
- "[🚨 문구]" = 라운드 뱃지. 첫 이모지로 색이 정해진다 (🚨 레드 / ⚠️ 옐로우 / ✅ 그린).
  타이틀 블록에 쓰면 큰 뱃지, 본문 블록에 쓰면 구간 뱃지가 된다.
- 뱃지가 있는 블록의 "- " 항목 = [✓] 체크 항목. 그 외 "- " = 불릿.
- "1️⃣" = 번호 항목, 🔴🟡🟢 = 신호 점(글머리에 오면 소제목).
- "(하단 작게)" = 작은 각주, "(하단 상자)" = 테두리 안내 상자.
- 시각 가이드의 "강조 키워드" 항목에 백틱으로 적은 문구는 포인트 컬러로 강조된다.
"""

import argparse
import re
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ─────────────────────────────────────────────
# 디자인 토큰 (여기만 바꾸면 전체 톤이 바뀐다)
# ─────────────────────────────────────────────
W, H = 1080, 1350          # 4:5 세로형
SS = 2                     # 2배로 그린 뒤 축소 (도형·글자 가장자리를 매끄럽게)
SAFE_Y = 150               # 상하단 여백
SIDE = 100                 # 좌우 여백

BG = "#F4F1EA"             # 웜 베이지
INK = "#222222"            # 메인 텍스트
POINT = "#6B523B"          # 포인트 (웜 브라운)
MUTED = "#8C857B"          # 보조 텍스트
HAIRLINE = "#DCD5C8"       # 구분선
SAND = "#D8C8AC"           # 안내 상자 테두리
SAND_TEXT = "#6E6253"      # 안내 상자 글자
SIGNAL = {                 # 신호 점: 채도를 낮춘 흙빛 톤
    "🔴": "#B4533C",
    "🟡": "#C79A3B",
    "🟢": "#4A6B53",
}
BADGE_COLORS = {           # 뱃지: (배경, 글자)
    "🚨": ("#FADBD8", "#78281F"),
    "⚠": ("#FCF3CF", "#7D6608"),
    "✅": ("#D4EFDF", "#145A32"),
}
BADGE_DEFAULT = ("#EAE2D3", POINT)

CATEGORY = "SPORT NUTRITION"
HANDLE = "@hyewon_high1"

FONT_DIR = Path(r"C:\Windows\Fonts")
FONTS = {
    "sans": FONT_DIR / "NotoSansKR-VF.ttf",
    "serif": FONT_DIR / "NotoSerifKR-VF.ttf",
    "emoji": FONT_DIR / "seguiemj.ttf",
}
FALLBACK_FONT = FONT_DIR / "malgun.ttf"


@dataclass(frozen=True)
class Style:
    family: str = "sans"
    weight: int = 400
    size: float = 32
    color: str = INK
    tracking: float = 0.0  # em 단위 자간

    def font(self, u):
        return load_font(self.family, self.weight, max(1, round(self.size * u)))


# 타이포그래피 스케일
COVER_TITLE = Style("serif", 600, 84, INK, -0.03)
TITLE = Style("serif", 600, 60, INK, -0.025)
BODY = Style("sans", 400, 32, INK, -0.015)
HEADER = Style("sans", 600, 34, INK, -0.015)
BULLET = Style("sans", 400, 30, INK, -0.015)
CHECK = Style("sans", 400, 28, INK, -0.015)
NOTE = Style("sans", 400, 28, MUTED, -0.01)
NUMBER = Style("serif", 600, 32, POINT, 0.0)
FOOTNOTE = Style("sans", 400, 20, MUTED, 0.0)
BOX_NOTE = Style("sans", 400, 26, SAND_TEXT, -0.01)
TAG = Style("sans", 500, 20, POINT, 0.22)
PAGE = Style("sans", 400, 20, MUTED, 0.12)
LOGO = Style("sans", 500, 22, INK, 0.04)
LOGO_SUB = Style("sans", 400, 22, MUTED, 0.0)


@dataclass(frozen=True)
class BadgeSpec:
    style: Style
    pad_x: float
    pad_y: float
    radius: float


BADGE_SECTION = BadgeSpec(Style("sans", 700, 32, INK, -0.01), 24, 12, 8)   # 2장 구간 뱃지
BADGE_HERO = BadgeSpec(Style("sans", 800, 38, INK, -0.01), 32, 16, 10)     # 타이틀 뱃지

CHECK_ROW = 48             # 체크 항목 행간 (px)
CHECK_BOX = 28             # 체크박스 크기 (px)
BOX_PAD = (24, 14)         # 안내 상자 패딩 (좌우, 상하)

# 한글 글자가 차지하는 세로 중심 (기준선 위로 em 비율)
GLYPH_MID = 0.36
EMOJI_SCALE = 0.92


@lru_cache(maxsize=None)
def load_font(family, weight, px):
    path = FONTS.get(family)
    if not path or not path.exists():
        path = FALLBACK_FONT
    f = ImageFont.truetype(str(path), px)
    if family != "emoji":
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass  # 가변 폰트가 아니면 기본 굵기 사용
    return f


def is_emoji(ch):
    o = ord(ch)
    return ch not in SIGNAL and (o >= 0x1F000 or 0x2600 <= o <= 0x27BF)


# ─────────────────────────────────────────────
# 원고 파싱
# ─────────────────────────────────────────────
CODE = re.compile(r"```[^\n]*\n(.*?)```", re.S)
KEYCAP = re.compile(r"^\s*([0-9])\uFE0F?\u20E3\s*(.*)$")
BADGE_LINE = re.compile(r"^\s*\[(.+)\]\s*$")
FOOTNOTE_PREFIX = "(하단 작게)"
BOX_PREFIX = "(하단 상자)"


@dataclass
class Slide:
    num: int
    role: str
    headline: list
    blocks: list
    footnotes: list
    box_notes: list
    keywords: list


def _between(text, start, end):
    s = text.find(start)
    if s < 0:
        return ""
    e = text.find(end, s) if end else -1
    return text[s:e if e >= 0 else len(text)]


def _block_lines(block):
    lines = [l.rstrip() for l in block.split("\n")]
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def parse_draft(path):
    text = Path(path).read_text(encoding="utf-8")
    parts = re.split(r"^## Slide (\d+)\s*$", text, flags=re.M)
    slides = []
    for i in range(1, len(parts), 2):
        body = re.split(r"^## ", parts[i + 1], maxsplit=1, flags=re.M)[0]
        role = re.search(r"\*\*카드 번호 및 역할:\*\*\s*(.+)", body)
        headline = CODE.findall(_between(body, "**메인 헤드라인", "**서브 카피"))
        blocks, footnotes, box_notes = [], [], []
        for block in CODE.findall(_between(body, "**서브 카피", "**이미지/시각")):
            lines = _block_lines(block)
            first = lines[0].strip() if lines else ""
            for prefix, bucket in ((FOOTNOTE_PREFIX, footnotes), (BOX_PREFIX, box_notes)):
                if first.startswith(prefix):
                    lines[0] = first[len(prefix):]
                    bucket += [l.strip() for l in lines if l.strip()]
                    break
            else:
                if lines:
                    blocks.append(lines)
        guide = _between(body, "**이미지/시각", None)
        kw_line = next((l for l in guide.splitlines() if "강조 키워드" in l), "")
        slides.append(Slide(
            num=int(parts[i]),
            role=role.group(1).strip() if role else "",
            headline=_block_lines(headline[0]) if headline else [],
            blocks=blocks,
            footnotes=footnotes,
            box_notes=box_notes,
            keywords=re.findall(r"`([^`]+)`", kw_line),
        ))
    return slides


def clean(text):
    """이모지 변형 문자를 정리하고, 곧은 따옴표는 둥근 따옴표로 바꾼다."""
    text = text.replace("👉", "→").replace("\uFE0F", "").replace("\u20E3", "")
    text = re.sub(r"'([^']*)'", "\u2018\\1\u2019", text)
    text = re.sub(r'"([^"]*)"', "\u201C\\1\u201D", text)
    return text


def badge_colors(text):
    return BADGE_COLORS.get(text[:1], BADGE_DEFAULT)


def classify(lines):
    """본문 블록의 각 줄을 (종류, 텍스트, 부가정보)로 나눈다."""
    has_bullets = any(l.strip().startswith("- ") for l in lines)
    badge = next((BADGE_LINE.match(l) for l in lines if BADGE_LINE.match(l)), None)
    check_color = badge_colors(clean(badge.group(1)).strip())[1] if badge else None
    out = []
    for raw in lines:
        if not raw.strip():
            continue
        m = KEYCAP.match(raw)
        b = BADGE_LINE.match(raw)
        s = raw.strip()
        if b:
            out.append(("badge", clean(b.group(1)).strip(), None))
        elif m:
            out.append(("num", clean(m.group(2)).strip(), m.group(1).zfill(2)))
        elif s.startswith("- "):
            kind = "check" if check_color else "bullet"
            out.append((kind, clean(s[2:]).strip(), check_color))
        elif has_bullets and s[0] in SIGNAL:
            out.append(("header", clean(s[1:]).strip(), s[0]))
        elif raw[:1].isspace() and out:
            out.append(("cont", clean(s), None))
        else:
            out.append(("text", clean(s), None))
    return out


def keyword_mask(texts, keywords, first_only=False):
    """줄바꿈을 넘어가는 강조 키워드도 찾도록 줄을 공백으로 이어 붙여 검색한다."""
    flat = " ".join(texts)
    mask = [False] * len(flat)
    for kw in keywords:
        kw = clean(kw).strip()
        hit = False
        for m in re.finditer(re.escape(kw), flat) if kw else ():
            mask[m.start():m.end()] = [True] * (m.end() - m.start())
            hit = True
        if hit and first_only:
            break
    return mask


def to_runs(texts, mask, styles):
    """줄마다 [(문자열, Style)] 목록을 만든다. styles = [(기본, 강조)]"""
    result, pos = [], 0
    for text, (base, hi) in zip(texts, styles):
        runs = []
        for i, ch in enumerate(text):
            st = hi if mask[pos + i] else base
            if runs and runs[-1][1] == st:
                runs[-1][0] += ch
            else:
                runs.append([ch, st])
        result.append([(t, s) for t, s in runs])
        pos += len(text) + 1
    return result


# ─────────────────────────────────────────────
# 조판 엔진
# ─────────────────────────────────────────────
@dataclass
class Para:
    runs: list
    lh: float                 # 행간 (글자 크기 배수)
    indent: float = 0         # 왼쪽 들여쓰기 (px)
    marker: tuple = None      # ("bullet",) / ("num", "01") / ("dot", 색) / ("check", 색)
    gap: float = 0            # 앞 문단과의 간격 (px)
    rule: bool = False        # 간격 가운데에 가는 구분선


@dataclass
class Badge:
    text: str
    spec: BadgeSpec
    gap: float = 0


@dataclass
class Accent:
    length: float = 56
    thickness: float = 2
    before: float = 44
    after: float = 52


def char_w(ch, st, u):
    if ch in SIGNAL:
        return st.size * u * 0.72
    if is_emoji(ch):
        return emoji_font(st, u).getlength(ch) + st.tracking * st.size * u
    return st.font(u).getlength(ch) + st.tracking * st.size * u


def emoji_font(st, u):
    return load_font("emoji", 400, max(1, round(st.size * EMOJI_SCALE * u)))


def line_w(chars, u):
    return sum(char_w(c, s, u) for c, s in chars)


def wrap(runs, max_w, u):
    """어절(띄어쓰기) 단위 줄바꿈. 한 어절이 너무 길면 글자 단위로 자른다."""
    words, cur = [], []
    for text, st in runs:
        for c in text:
            if c == " ":
                if cur:
                    words.append(cur)
                    cur = []
                words.append([(c, st)])
            else:
                cur.append((c, st))
    if cur:
        words.append(cur)

    lines, line, lw = [], [], 0.0

    def flush():
        nonlocal line, lw
        while line and line[-1][0] == " ":
            line.pop()
        if line:
            lines.append(line)
        line, lw = [], 0.0

    for word in words:
        if word[0][0] == " " and not line:
            continue
        ww = line_w(word, u)
        if line and lw + ww > max_w and word[0][0] != " ":
            flush()
        if ww > max_w:
            for c in word:
                cw = char_w(*c, u)
                if line and lw + cw > max_w:
                    flush()
                line.append(c)
                lw += cw
        else:
            line.extend(word)
            lw += ww
    flush()
    return lines


def layout(items, width, u):
    """문단 목록을 줄 단위로 배치한다. 반환: (rows, 전체 높이)"""
    rows, y = [], 0.0
    for it in items:
        if isinstance(it, Accent):
            y += it.before * u if rows else 0
            rows.append(("accent", y, it.length * u, it.thickness * u))
            y += it.thickness * u + it.after * u
            continue
        if rows:
            if getattr(it, "rule", False):
                rows.append(("rule", y + it.gap * u / 2))
            y += it.gap * u
        if isinstance(it, Badge):
            h = (it.spec.style.size + 2 * it.spec.pad_y) * u
            rows.append(("badge", y, h, it))
            y += h
            continue
        size = max(st.size for _, st in it.runs)
        row_h = size * it.lh * u
        for i, line in enumerate(wrap(it.runs, width - it.indent * u, u)):
            rows.append(("text", y, row_h, size * u, it.indent * u, line,
                         it.marker if i == 0 else None))
            y += row_h
    return rows, y


def baseline_of(top, row_h, size_px):
    return top + row_h / 2 + GLYPH_MID * size_px


def draw_chars(d, x, baseline, chars, u):
    for ch, st in chars:
        w = char_w(ch, st, u)
        if ch in SIGNAL:
            r = st.size * u * 0.21
            cx, cy = x + w / 2, baseline - GLYPH_MID * st.size * u
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=SIGNAL[ch])
        elif is_emoji(ch):
            d.text((x, baseline), ch, font=emoji_font(st, u), embedded_color=True, anchor="ls")
        else:
            d.text((x, baseline), ch, font=st.font(u), fill=st.color, anchor="ls")
        x += w
    return x


def draw_checkbox(d, x, mid, color, u):
    s = CHECK_BOX * u
    top = mid - s / 2
    d.rounded_rectangle([x, top, x + s, top + s], radius=6 * u, outline=color, width=round(2 * u))
    pts = [(0.25, 0.52), (0.43, 0.70), (0.76, 0.33)]
    d.line([(x + px * s, top + py * s) for px, py in pts], fill=color, width=round(3 * u), joint="curve")


def draw_badge(d, x, top, h, badge, u):
    spec = badge.spec
    bg, fg = badge_colors(badge.text)
    st = replace(spec.style, color=fg)
    chars = [(c, st) for c in badge.text]
    w = line_w(chars, u) + 2 * spec.pad_x * u
    d.rounded_rectangle([x, top, x + w, top + h], radius=spec.radius * u, fill=bg)
    draw_chars(d, x + spec.pad_x * u, baseline_of(top, h, st.size * u), chars, u)


def draw_rows(d, rows, x0, y0, width, u):
    for row in rows:
        kind = row[0]
        if kind == "rule":
            y = y0 + row[1]
            d.line([(x0, y), (x0 + width, y)], fill=HAIRLINE, width=SS)
        elif kind == "accent":
            _, y, length, thick = row
            d.rectangle([x0, y0 + y, x0 + length, y0 + y + thick], fill=POINT)
        elif kind == "badge":
            _, y, h, badge = row
            draw_badge(d, x0, y0 + y, h, badge, u)
        else:
            _, top, row_h, size_px, indent, chars, marker = row
            base = baseline_of(y0 + top, row_h, size_px)
            mid = base - GLYPH_MID * size_px
            if marker and marker[0] == "bullet":
                r = 3.2 * u
                cx = x0 + 6 * u
                d.ellipse([cx - r, mid - r, cx + r, mid + r], fill=MUTED)
            elif marker and marker[0] == "check":
                draw_checkbox(d, x0, mid, marker[1], u)
            elif marker and marker[0] == "num":
                st = replace(NUMBER, size=size_px / u)
                d.text((x0, base), marker[1], font=st.font(u), fill=st.color, anchor="ls")
            elif marker and marker[0] == "dot":
                r = size_px * 0.21
                cx = x0 + r
                d.ellipse([cx - r, mid - r, cx + r, mid + r], fill=SIGNAL[marker[1]])
            draw_chars(d, x0 + indent, base, chars, u)


# ─────────────────────────────────────────────
# 슬라이드 구성
# ─────────────────────────────────────────────
def emphasize(st, bold=True):
    return replace(st, color=POINT, weight=max(st.weight, 600) if bold else st.weight)


def build_items(slide, is_cover):
    items = []

    # 타이틀 블록: [뱃지] 줄은 큰 뱃지, 나머지는 타이틀
    title_st = COVER_TITLE if is_cover else TITLE
    hl = [clean(l).strip() for l in slide.headline if l.strip()]
    titles = [l for l in hl if not BADGE_LINE.match(l)]
    title_runs = iter(to_runs(titles, keyword_mask(titles, slide.keywords, first_only=True),
                              [(title_st, emphasize(title_st, bold=False))] * len(titles)))
    for line in hl:
        b = BADGE_LINE.match(line)
        gap = 28 if items else 0
        if b:
            items.append(Badge(b.group(1).strip(), BADGE_HERO, gap=gap))
        else:
            items.append(Para(next(title_runs), lh=1.34, gap=gap))

    if slide.blocks and titles:
        items.append(Accent())

    for bi, block in enumerate(slide.blocks):
        lines = classify(block)
        is_section = any(k == "header" for k, _, _ in lines)
        starts_badge = lines and lines[0][0] == "badge"
        texts = [t for _, t, _ in lines]
        styles = []
        for kind, _, _ in lines:
            base = {"header": HEADER, "bullet": BULLET, "check": CHECK, "cont": NOTE}.get(kind, BODY)
            # 소제목은 이미 굵으므로 부분 강조하지 않는다
            styles.append((base, base if kind == "header" else emphasize(base)))
        runs_list = to_runs(texts, keyword_mask(texts, slide.keywords), styles)

        for li, ((kind, text, meta), runs) in enumerate(zip(lines, runs_list)):
            if li == 0:
                if not items:
                    gap = 0
                elif starts_badge:
                    gap = 24 if bi else 0
                else:
                    gap = 0 if bi == 0 else (56 if is_section else 34)
            else:
                gap = {"header": 12, "badge": 6}.get(lines[li - 1][0], 0)
            if kind == "badge":
                items.append(Badge(text, BADGE_SECTION, gap=gap))
                continue
            para = Para(runs, lh=1.65, gap=gap, rule=(li == 0 and bi > 0 and is_section))
            if kind == "header":
                para.lh, para.indent, para.marker = 1.5, HEADER.size * 0.42 + 16, ("dot", meta)
            elif kind == "bullet":
                para.lh, para.indent, para.marker = 1.6, 30, ("bullet",)
            elif kind == "check":
                para.lh, para.indent, para.marker = CHECK_ROW / CHECK.size, CHECK_BOX + 14, ("check", meta)
            elif kind == "num":
                para.indent, para.marker = 64, ("num", meta)
            elif kind == "cont":
                para.indent = 64 if any(k == "num" for k, _, _ in lines[:li]) else 0
            items.append(para)
    return items


def has_fixed_specs(items):
    """규격이 고정된 요소(뱃지·체크 항목)가 있으면 자동 축소하지 않는다."""
    return any(isinstance(it, Badge) or (isinstance(it, Para) and it.marker and it.marker[0] == "check")
               for it in items)


def draw_line_text(d, x, baseline, runs, u, align="left"):
    chars = [(c, st) for t, st in runs for c in t]
    if align == "right":
        x -= line_w(chars, u)
    draw_chars(d, x, baseline, chars, u)


def draw_box_note(d, x, bottom, text, u):
    """테두리 안내 상자를 그리고 상자 윗변 y를 돌려준다."""
    chars = [(c, BOX_NOTE) for c in clean(text)]
    pad_x, pad_y = BOX_PAD[0] * u, BOX_PAD[1] * u
    h = BOX_NOTE.size * u + 2 * pad_y
    w = line_w(chars, u) + 2 * pad_x
    top = bottom - h
    d.rounded_rectangle([x, top, x + w, bottom], radius=8 * u, outline=SAND, width=round(1.5 * u))
    draw_chars(d, x + pad_x, baseline_of(top, h, BOX_NOTE.size * u), chars, u)
    return top


def render_slide(slide, total, out_path, category):
    u = SS
    img = Image.new("RGB", (W * SS, H * SS), BG)
    d = ImageDraw.Draw(img)
    left, right = SIDE * u, (W - SIDE) * u
    width = right - left

    # 상단: 카테고리 태그 + 페이지 번호 (대문자 윗선을 Safe Zone 경계에 맞춤)
    top_base = (SAFE_Y + TAG.size * 0.74) * u
    draw_line_text(d, left, top_base, [(category.upper(), TAG)], u)
    draw_line_text(d, right, top_base, [(f"{slide.num:02d} / {total:02d}", PAGE)], u, "right")

    # 하단: 텍스트 로고 (1장의 '스포츠 영양코치 @...' 각주는 로고 자리로 올린다)
    footnotes = list(slide.footnotes)
    logo_runs = [(HANDLE, LOGO)]
    for note in footnotes:
        if HANDLE in note:
            before = clean(note.split(HANDLE)[0]).strip()
            logo_runs = ([(before + "  ", LOGO_SUB)] if before else []) + [(HANDLE, LOGO)]
            footnotes.remove(note)
            break
    logo_base = (H - SAFE_Y - LOGO.size * 0.22) * u
    draw_line_text(d, left, logo_base, logo_runs, u)
    if slide.num < total:
        draw_line_text(d, right, logo_base, [("→", replace(LOGO, color=MUTED, weight=300))], u, "right")
    logo_top = logo_base - LOGO.size * 0.8 * u

    # 로고 위로: 안내 상자 → 작은 각주 순서로 쌓는다
    bottom = logo_top - 36 * u
    region_bottom = logo_top - 70 * u
    for text in reversed(slide.box_notes):
        bottom = draw_box_note(d, left, bottom, text, u) - 16 * u
        region_bottom = bottom - 24 * u
    if footnotes:
        notes = [Para([(clean(n), FOOTNOTE)], lh=1.6) for n in footnotes]
        rows, h = layout(notes, width, u)
        note_top = bottom - h
        draw_rows(d, rows, left, note_top, width, u)
        region_bottom = note_top - 56 * u

    # 본문: 고정 규격 슬라이드는 그대로, 나머지는 영역에 맞을 때까지 비율을 줄인다
    region_top = (SAFE_Y + 70) * u
    region_h = region_bottom - region_top
    items = build_items(slide, is_cover=slide.num == 1)
    fixed = has_fixed_specs(items)
    scale = 1.0
    while True:
        rows, h = layout(items, width, u * scale)
        if h <= region_h or fixed or scale <= 0.62:
            break
        scale -= 0.025
    if h > region_h:
        print(f"  ! Slide {slide.num}: 본문이 영역을 {(h - region_h) / u:.0f}px 넘칩니다. 원고 분량을 줄여 주세요.")
    elif scale < 0.85:
        print(f"  · Slide {slide.num}: 분량이 많아 글자 크기를 {scale:.0%}로 줄였습니다.")
    y0 = region_top + max(0, region_h - h) * 0.45  # 시각적 중심 (살짝 위)
    draw_rows(d, rows, left, y0, width, u * scale)

    img.resize((W, H), Image.LANCZOS).save(out_path, optimize=True)


def main():
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(description="carousel_draft.md → 카드뉴스 PNG")
    ap.add_argument("--draft", default=here / "carousel_draft.md", type=Path)
    ap.add_argument("--out", default=here / "output_cards", type=Path)
    ap.add_argument("--category", default=CATEGORY)
    args = ap.parse_args()

    slides = parse_draft(args.draft)
    if not slides:
        raise SystemExit(f"'## Slide N' 형식의 슬라이드를 찾지 못했습니다: {args.draft}")
    args.out.mkdir(parents=True, exist_ok=True)
    for slide in slides:
        path = args.out / f"slide_{slide.num:02d}.png"
        render_slide(slide, len(slides), path, args.category)
        print(f"✓ {path.name}  {slide.role}")


if __name__ == "__main__":
    main()

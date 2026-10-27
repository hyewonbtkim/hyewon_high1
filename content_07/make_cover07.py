"""
content_07 릴스 표지 영상 — 춘천 서브4 썸네일(make_cover.py)과 같은 포맷·같은 글자 위치.

    python content_07/make_cover07.py                 # 노랑 (최근 게시물과 같은 색)
    python content_07/make_cover07.py --color lime    # 라임 (브랜드 규칙: 라임 뱃지 + 포레스트 글자)

화질: 글자는 원본 해상도(2114x3758)에서 바로 그려 확대 없이 얹고,
영상은 H.264 CRF 12 / slow 로 한 번만 인코딩 (원본 해상도·fps·색 범위 유지, 오디오는 그대로 복사).
"""

import argparse
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from make_reel import FF, H as BASE_H, TEXT_MAX_W, YELLOW, runs  # noqa: E402

DIR = Path(__file__).resolve().parent
SRC = DIR / "IMG_1483.mov"
OUT = DIR / "output" / "제마D-5_표지.mp4"
LIME, FOREST = (212, 242, 90), (31, 74, 58)        # 브랜드 색 (brand/시안)
COLORS = {                                          # 뱃지 배경, 뱃지 글자, 헤드라인 강조
    "yellow": (YELLOW, "black", YELLOW),
    "lime": (LIME, FOREST, LIME),
}
BADGE, BADGE_TEXT, ACCENT = COLORS["yellow"]
W, H = 2114, 3758                 # 원본 해상도 그대로
S = H / BASE_H                    # 1080x1920 기준 크기 → 원본 배율 (약 1.96)

FONT = DIR.parent / "brand" / "fonts" / "Jua-Regular.ttf"   # 주아체: 둥글고 친근 + 굵어서 잘 보임 (OFL, 상업 사용 가능)

LABEL = ("제마 D-5", 80, 0.552)                     # 노란 뱃지 (춘천 썸네일 56보다 크게, 헤드라인과 안 겹치게 살짝 위로)
HEADLINE = ("{미련} 함께\n버리실 분 모집", 140, 0.70)   # 춘천마라톤에서 서브4 하기 와 같은 높이·크기


def font(size):
    return ImageFont.truetype(str(FONT), size)


def bottom_shade(start=0.5, alpha=200):
    shade = Image.new("L", (1, H))
    for y in range(H):
        t = max(0.0, (y / H - start) / (1 - start))
        shade.putpixel((0, y), int(alpha * min(t, 1) ** 1.2))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    layer.putalpha(shade.resize((W, H)))
    return layer


def label(text, size, y):
    size = round(size * S)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = font(size)
    tw = f.getlength(text)
    pad_x, pad_y = size * 0.6, size * 0.38
    cx, cy = W / 2, H * y
    d.rounded_rectangle([cx - tw / 2 - pad_x, cy - size / 2 - pad_y, cx + tw / 2 + pad_x, cy + size / 2 + pad_y],
                        radius=size * 0.5, fill=BADGE)
    d.text((cx, cy), text, font=f, fill=BADGE_TEXT, anchor="mm")
    return layer


def subtitle(text, size, text_y):
    """make_reel.subtitle 과 같은 모양을 원본 해상도로."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lines = [runs(l) for l in text.split("\n")]
    while True:
        f = font(round(size * S))
        widths = [sum(f.getlength(t) for t, _ in l) for l in lines]
        if max(widths) <= TEXT_MAX_W * S or size <= 40:
            break
        size -= 2
    px = round(size * S)
    stroke = max(4, round(px * 0.11))
    line_h = round(px * 1.28)
    y = H * text_y - line_h * len(lines) / 2
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds, d = ImageDraw.Draw(shadow), ImageDraw.Draw(layer)
    for l, lw in zip(lines, widths):
        x = (W - lw) / 2
        for t, color in l:
            ds.text((x + 6 * S, y + 8 * S), t, font=f, fill=(0, 0, 0, 160), stroke_width=stroke,
                    stroke_fill=(0, 0, 0, 160))
            d.text((x, y), t, font=f, fill=ACCENT if color == YELLOW else color, stroke_width=stroke, stroke_fill="black")
            x += f.getlength(t)
        y += line_h
    return Image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(6 * S)), layer)


def main():
    global BADGE, BADGE_TEXT, ACCENT
    ap = argparse.ArgumentParser()
    ap.add_argument("--color", choices=COLORS, default="yellow")
    a = ap.parse_args()
    BADGE, BADGE_TEXT, ACCENT = COLORS[a.color]
    out = OUT if a.color == "yellow" else OUT.with_name(f"{OUT.stem}_{a.color}{OUT.suffix}")
    out.parent.mkdir(parents=True, exist_ok=True)
    overlay = bottom_shade()
    overlay = Image.alpha_composite(overlay, label(*LABEL))
    overlay = Image.alpha_composite(overlay, subtitle(*HEADLINE))
    png = out.parent / f"overlay_{a.color}.png"
    overlay.save(png)

    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", str(SRC), "-i", str(png),
                    "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto,format=yuvj420p[v]",
                    "-map", "[v]", "-map", "0:a:0",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "12", "-profile:v", "high",
                    "-color_range", "pc", "-colorspace", "bt709", "-color_trc", "bt709", "-color_primaries", "bt709",
                    "-c:a", "copy", "-movflags", "+faststart", str(out)], check=True)
    print(f"완료: {out}")


if __name__ == "__main__":
    main()

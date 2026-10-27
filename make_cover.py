"""
릴스 썸네일(커버) 만들기 (@hyewon_high1) — 1080x1920 (9:16)

영상의 한 장면 + 헤드라인. 자막 스타일·피부 보정은 make_reel.py 와 같음.

    python make_cover.py
    python make_cover.py --out content_03/output/A_썸네일.jpg

인스타 프로필 그리드에서는 커버 가운데 3:4 부분(위아래 240px씩 잘림)만 보이므로
헤드라인은 위에서 240px ~ 1680px 사이에 둔다.
"""

import argparse
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from make_reel import BEAUTY, FF, H, W, YELLOW, font, subtitle

SRC = "content_03/V20241027_133825000_3EC758ED-7746-4059-AEA5-3B6D47DCEE00.MOV"
AT = 10.4                  # 웃는 얼굴 + 메달이 보이는 장면 (초)
LABEL = ("5초 차이로 서브4 했던 사람의", 56, 0.565)   # 노란 띠: 말하는 사람의 근거
HEADLINE = [               # (자막, 글자 크기, 세로 위치)
    ("춘천마라톤에서\n{서브4} 하기", 140, 0.70),
    ("= 첫 풀마라톤 팁 =", 62, 0.835),
]


def grab_frame(path, at, out):
    vf = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1{BEAUTY}[v]")
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{at}", "-i", str(path),
                    "-filter_complex", vf, "-map", "[v]", "-frames:v", "1", str(out)], check=True)


# 팔자 주름 위치 (이 장면 AT=10.4초 기준 좌표. 장면을 바꾸면 다시 잡아야 함)
FOLDS = [
    [(458, 700), (446, 728), (434, 756), (428, 782)],   # 화면 왼쪽
    [(552, 704), (566, 732), (580, 758), (590, 782)],   # 화면 오른쪽
]
FOLD_STRENGTH = 0.75       # 0 = 그대로, 1 = 거의 지움. 자연스러운 범위 0.5~0.8


def soften_folds(img):
    """팔자 주름 자리만 부드럽게 + 그림자를 살짝 밝게. 가장자리를 흐리게 섞어 티 나지 않게."""
    smooth = ImageEnhance.Brightness(img.filter(ImageFilter.GaussianBlur(6))).enhance(1.07)
    mask = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(mask)
    for line in FOLDS:
        d.line(line, fill=int(255 * FOLD_STRENGTH), width=34, joint="curve")
    return Image.composite(smooth, img, mask.filter(ImageFilter.GaussianBlur(12)))


def bottom_shade(img, start=0.5, alpha=200):
    """아래쪽을 서서히 어둡게 해서 글자가 잘 보이게."""
    shade = Image.new("L", (1, H))
    for y in range(H):
        t = max(0.0, (y / H - start) / (1 - start))
        shade.putpixel((0, y), int(alpha * min(t, 1) ** 1.2))
    black = Image.new("RGB", (W, H), "black")
    return Image.composite(black, img, shade.resize((W, H)))


def label(text, size, y):
    """노란 둥근 띠 + 검은 굵은 글자 (대상 지목용)."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = font(size)
    tw = f.getlength(text)
    pad_x, pad_y = size * 0.6, size * 0.38
    cx, cy = W / 2, H * y
    d.rounded_rectangle([cx - tw / 2 - pad_x, cy - size / 2 - pad_y, cx + tw / 2 + pad_x, cy + size / 2 + pad_y],
                        radius=size * 0.5, fill=YELLOW)
    d.text((cx, cy), text, font=f, fill="black", anchor="mm")
    return layer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="content_03/output/A_썸네일.jpg")
    a = ap.parse_args()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "frame.png"
        grab_frame(SRC, AT, raw)
        img = bottom_shade(soften_folds(Image.open(raw).convert("RGB"))).convert("RGBA")
    img = Image.alpha_composite(img, label(*LABEL))
    for text, size, y in HEADLINE:
        img = Image.alpha_composite(img, subtitle(text, size, y))
    img.convert("RGB").save(out, quality=95)
    print(f"완료: {out}")


if __name__ == "__main__":
    main()

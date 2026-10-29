"""
content_08 릴스 표지 — content_07(make_cover07.py)과 같은 포맷·같은 글자 위치 (대회 뱃지 없음: 제마 안 나가는 러너까지 대상).

    python content_08/make_cover08.py                 # 노랑 (최근 게시물과 같은 색)
    python content_08/make_cover08.py --color lime    # 라임 (브랜드 규칙: 라임 뱃지 + 포레스트 글자)

화질: IMG_1687(두 병 들고 있는 장면) 한 프레임을 원본 해상도(2160x3840) 그대로 PNG로 꺼내
글자를 얹고 PNG(무손실)로 저장. 인스타 표지 업로드용 JPG(품질 100, 4:4:4)도 같이 만듦.
"""

import argparse
import subprocess
import sys
from pathlib import Path

from PIL import Image

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR.parent / "content_07"))
sys.path.insert(0, str(DIR.parent))
import make_cover07 as c7  # noqa: E402
import make_reel as mr  # noqa: E402

c7.font = mr.font   # 춘천 서브4 썸네일(make_cover.py)과 같은 Noto Sans KR Black

SRC, AT = DIR / "IMG_1687.MOV", 4.6             # 두 병이 라벨까지 잘 보이는 순간
OUT = DIR / "output" / "D_표지.png"
c7.W, c7.H = 2160, 3840
c7.S = c7.H / c7.BASE_H

HEADLINE = ("러닝 후\n{뭐가 더 좋을까?}", 140, 0.70)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--color", choices=c7.COLORS, default="yellow")
    a = ap.parse_args()
    c7.BADGE, c7.BADGE_TEXT, c7.ACCENT = c7.COLORS[a.color]
    out = OUT if a.color == "yellow" else OUT.with_name(f"{OUT.stem}_{a.color}{OUT.suffix}")
    out.parent.mkdir(parents=True, exist_ok=True)

    frame = out.parent / "_frame.png"
    subprocess.run([c7.FF, "-hide_banner", "-loglevel", "error", "-y", "-ss", str(AT), "-i", str(SRC),
                    "-frames:v", "1", "-vf", "scale=in_color_matrix=bt709:in_range=tv:out_range=pc:flags=lanczos,format=rgb24",
                    str(frame)], check=True)
    img = Image.open(frame).convert("RGBA")
    assert img.size == (c7.W, c7.H), img.size
    img = Image.alpha_composite(img, c7.bottom_shade())
    img = Image.alpha_composite(img, c7.subtitle(*HEADLINE))
    img = img.convert("RGB")
    img.save(out)
    img.save(out.with_suffix(".jpg"), quality=100, subsampling=0)
    frame.unlink()
    print(f"완료: {out} (+ .jpg)")


if __name__ == "__main__":
    main()

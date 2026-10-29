"""
content_08 영상형 썸네일 (2~3초) — 본 릴스 'D_러닝후_제로만_마시는사람.mp4' 앞에 쓰는 용도.

    python content_08/make_thumb08.py

- IMG_1687에서 두 병을 들어 올리는 순간부터 3초
- 헤드라인 "뛰고 나서 {뭐 마셔야 해??}"는 처음부터 끝까지 유지 (춘천 서브4 썸네일과 같은 Noto Sans KR Black, content_07 표지 위치)
- 머리 높이 양옆에 병 이름 뱃지: (좌) 일반 / (우) 제로 — 검정 바탕 · 노랑 글씨
화질: 원본 해상도 · 60fps 그대로, H.264 CRF 12 slow 한 번만 인코딩, 오디오는 원본 그대로 복사
"""

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR.parent / "content_07"))
sys.path.insert(0, str(DIR.parent))
import make_cover07 as c7  # noqa: E402
import make_reel as mr  # noqa: E402

c7.font = mr.font   # 춘천 서브4 썸네일(make_cover.py)과 같은 Noto Sans KR Black

SRC, START, DUR = DIR / "IMG_1687.MOV", 2.0, 3.0
OUT = DIR / "output" / "D_영상썸네일.mp4"
c7.W, c7.H = 2160, 3840
c7.S = c7.H / c7.BASE_H

HEADLINE = ("뛰고 나서\n{뭐 마셔야 해??}", 140, 0.70)
NAMES = [("일반", 0.17), ("제로", 0.83)]     # (글자, 가로 위치) — 각 병 위, 머리 높이
NAME_Y, NAME_SIZE = 0.37, 72


def badge(text, x, y, size):
    """make_cover07.label 과 같은 모양을 원하는 가로 위치에 (검정 바탕 · 노랑 글씨)."""
    size = round(size * c7.S)
    layer = Image.new("RGBA", (c7.W, c7.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = c7.font(size)
    tw = f.getlength(text)
    pad_x, pad_y = size * 0.6, size * 0.38
    cx, cy = c7.W * x, c7.H * y
    d.rounded_rectangle([cx - tw / 2 - pad_x, cy - size / 2 - pad_y, cx + tw / 2 + pad_x, cy + size / 2 + pad_y],
                        radius=size * 0.5, fill="black")
    d.text((cx, cy), text, font=f, fill=mr.YELLOW, anchor="mm")   # 편의점 밝은 배경에서 잘 보이게 검정 바탕 + 노랑 글씨
    return layer


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    overlay = c7.bottom_shade()
    for text, x in NAMES:
        overlay = Image.alpha_composite(overlay, badge(text, x, NAME_Y, NAME_SIZE))
    overlay = Image.alpha_composite(overlay, c7.subtitle(*HEADLINE))
    png = OUT.parent / "_thumb_overlay.png"
    tmp = OUT.parent / "_thumb_tmp.mp4"
    overlay.save(png)

    subprocess.run([c7.FF, "-hide_banner", "-loglevel", "error", "-y", "-ss", str(START), "-t", str(DUR), "-i", str(SRC),
                    "-i", str(png), "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto,fps=60,format=yuv420p[v]",
                    "-map", "[v]", "-map", "0:a:0", "-frames:v", str(round(DUR * 60)),
                    "-c:v", "libx264", "-preset", "slow", "-crf", "12", "-profile:v", "high",
                    "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
                    "-c:a", "copy", "-shortest", str(tmp)], check=True)
    # filter_complex를 쓰면 원본의 '세로 회전' 표시가 결과에 남아 한 번 더 돌아감 → 표시만 0으로 (스트림 복사, 재인코딩 없음)
    subprocess.run([c7.FF, "-hide_banner", "-loglevel", "error", "-y", "-display_rotation", "0", "-i", str(tmp),
                    "-c", "copy", "-movflags", "+faststart", str(OUT)], check=True)
    tmp.unlink()
    png.unlink()
    print(f"완료: {OUT}")


if __name__ == "__main__":
    main()

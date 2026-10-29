"""
content_08 릴스: 러닝 후 제로 파워에이드만 마시는 사람? (언제 뭘 마실지)

    python content_08/make_reel08.py          (insta-automation 폴더에서 실행)

- 대본: drafts/D_제로파워에이드_vs_오리지널_릴스.txt
- 자막 · 합성은 make_reel.py 함수를 그대로 쓰고, 화질만 바꿈
  원본 그대로 2160x3840 · 60fps, 중간 파일은 무손실(x264 qp 0), 최종 1번만 H.264 CRF 12 slow
- 원본 소리는 쓰지 않음 (음악은 인스타 앱에서 추가)
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import make_reel as mr  # noqa: E402

# ── 4K 60fps로 바꿔 쓰기 (make_reel.py 함수들이 이 값을 읽음)
S = 2                                          # make_reel.py(1080 기준) 대비 배율
mr.W, mr.H, mr.FPS = 2160, 3840, 60
mr.TEXT_MAX_W = 820 * S
COLOR = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]
mr.ENC = ["-c:v", "libx264", "-preset", "ultrafast", "-qp", "0", "-pix_fmt", "yuv420p", "-r", "60", "-an", *COLOR]
W, H = mr.W, mr.H
SRC = ROOT / "content_08"
OUT = SRC / "output" / "D_러닝후_제로만_마시는사람.mp4"

CREAM, FOREST, YELLOW = (245, 241, 232), (31, 74, 58), (255, 226, 0)

TALK = "IMG_1687.MOV"      # 편의점에서 말하기 → 두 병 들어 보이기 (왼쪽 마운틴블라스트, 오른쪽 제로)
WATCH = "IMG_1683.mov"     # 러닝 직후 시계: 최대 심박수 187
CU = "IMG_1683 (1).mov"    # 밤 CU 외관
SHELF = "IMG_1684.MOV"     # 편의점 안 → 파워에이드 진열대 (22.4~ 제로, 23.9~ 마운틴블라스트 클로즈업)
FRIDGE = "IMG_1686.MOV"    # 삼각대: 냉장고에서 두 병 꺼내 라벨 보기
LABEL = "IMG_1688.MOV"     # 마운틴블라스트 라벨 클로즈업 (위아래 뒤집혀 찍힘 → rot180)

# 컷: clips=[(파일, 시작, 원본 길이, 옵션)]. 옵션: rot180 / x3(3배속) / card(흐린 배경)
# 자막은 make_reel.py 규칙 그대로 ({강조}=노랑, 리스트=차례로)
TIMELINE = [
    # ── 상황: 시계 → CU 간판 → 문 열고 음료 매대 → 두 병 꺼내기
    dict(clips=[(WATCH, 0.5, 2.3)], text="{인터벌} 완료!!",
         pop=False, text_y=0.72),
    dict(clips=[(CU, 1.1, 0.9)], text="끝나자마자 {편의점}으로"),
    dict(clips=[(SHELF, 0.0, 9.6, "x3")], text="음료 코너 직행"),
    dict(clips=[(FRIDGE, 0.0, 10.4, "x3")], text="{파워에이드} 두 병 꺼내고"),
    # ── 질문
    dict(clips=[(TALK, 1.0, 3.2)], text="둘 중에\n{뭘 마셔야 해??}", size=130),
    # ── 마운틴블라스트: 진열대 → 병 앞면 → 당류 15g 라벨
    dict(clips=[(SHELF, 23.3, 1.2), (LABEL, 0.2, 1.6, "rot180"), (LABEL, 14.2, 1.6, "rot180")],
         text=["{마운틴블라스트}는", "{인터벌} · {고강도} 운동 후", "당 {15g}이 회복을 도와요"], times=[1.2, 1.6, 1.6]),
    # ── 제로: 진열대 → 라벨 보는 모습
    dict(clips=[(SHELF, 20.8, 2.2), (FRIDGE, 10.6, 2.6)],
         text=["{제로}는", "{저강도} 러닝 후", "바로 {식사}하러 갈 때"], times=[1.2, 1.6, 2.0]),
    # ── 정리
    dict(clips=[(FRIDGE, 9.0, 6.5, "card")], card=True, text="자세한 근거는 {본문에}", text_y=0.885, size=64),
]


def card_png(path):
    """마지막 정리 화면: 크림 바탕 · 포레스트 글씨 · 음료 이름만 노란 형광펜."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pw, ph = 1980, 2550
    x0, y0 = (W - pw) // 2, int(H * 0.12)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((x0 + 12, y0 + 20, x0 + pw + 12, y0 + ph + 20), 60, fill=(0, 0, 0, 120))
    layer = Image.alpha_composite(layer, shadow.filter(ImageFilter.GaussianBlur(24)))
    ImageDraw.Draw(layer).rounded_rectangle((x0, y0, x0 + pw, y0 + ph), 60, fill=CREAM)
    soft = (31, 74, 58, 170)

    def mark(x, y, w, size):   # 살짝 기운 형광펜
        hl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(hl).polygon([(x - 30, y + size * 0.25), (x + w + 36, y + size * 0.15),
                                    (x + w + 26, y + size * 1.12), (x - 36, y + size * 1.2)], fill=YELLOW + (255,))
        layer.alpha_composite(hl)

    def text(txt, x, y, size, color=FOREST):
        ImageDraw.Draw(layer).text((x, y), txt, font=mr.font(size), fill=color)
        return mr.font(size).getlength(txt)

    lx = x0 + 130
    title = "러닝 후, 이렇게 골라요"
    text(title, (W - mr.font(124).getlength(title)) / 2, y0 + 110, 124)
    y = y0 + 380
    sections = [
        ("마운틴블라스트", "당 15g · 60kcal · 나트륨 318mg", ["인터벌 · 고강도 운동 후", "90분 넘게 오래 뛴 날", "식사까지 시간이 걸릴 때"],
         "→ 당이 회복을 도와요", "근육 분해를 줄이고, 다 쓴 에너지(글리코겐)를 빨리 채움"),
        ("제로", "당 0g · 4kcal · 나트륨 357mg", ["1시간 안쪽 저강도 러닝 후", "바로 단백질 식사하러 갈 때"],
         "→ 식사로 충분해요", "단백질을 먹으면 당을 더해도 근육 효과는 비슷"),
    ]
    for k, (name, spec, bullets, point, why) in enumerate(sections):
        if k:
            ImageDraw.Draw(layer).line((x0 + 90, y - 70, x0 + pw - 90, y - 70), fill=(31, 74, 58, 90), width=5)
        w = mr.font(116).getlength(name)
        mark(lx, y, w, 116)
        text(name, lx, y, 116)
        text(spec, lx + 8, y + 180, 72, soft)
        y += 310
        for line in bullets:
            text("· " + line, lx, y, 88)
            y += 132
        y += 20
        text(point, lx, y, 88)
        y += 124
        text(why, lx + 92, y, 60, soft)
        y += 230
    text("※ 레이스 땐 한 병으론 부족해요. 젤은 따로", lx, y0 + ph - 170, 60, soft)
    layer.save(path)


def piece(src, start, dur, opts, out):
    """원본 한 구간 → 2160x3840 60fps 무손실 (자막 없음)."""
    vf = [f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos", f"crop={W}:{H}", "fps=60", "setsar=1"]
    if "rot180" in opts:
        vf.insert(0, "hflip,vflip")
    if "card" in opts:   # 정리 화면 뒤 배경: 영상을 흐리고 어둡게
        vf += ["gblur=sigma=40", "eq=brightness=-0.12:saturation=0.8"]
    speed = float(opts.split("x")[-1]) if "x" in opts else 1.0
    if speed != 1.0:     # 빨리 감기: 원본 프레임을 건너뛸 뿐 화질 손실 없음
        vf.insert(0, f"setpts=PTS/{speed}")
    mr.run(["-ss", f"{start}", "-t", f"{dur}", "-i", str(src), "-vf", ",".join(vf),
            "-frames:v", str(round(dur / speed * 60)), *mr.ENC, str(out)])


def length(c):
    """화면에 나오는 길이 (빨리 감기면 짧아짐)."""
    opts = c[3] if len(c) > 3 else ""
    return c[2] / (float(opts.split("x")[-1]) if "x" in opts else 1.0)


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    total = sum(sum(length(c) for c in t["clips"]) for t in TIMELINE)
    print(f"타임라인 합계 {total:.1f}초, 컷 {len(TIMELINE)}개")
    tmp = Path(tempfile.mkdtemp(prefix="reel08_"))
    parts = []
    for i, t in enumerate(TIMELINE):
        t = {**t, "dur": sum(length(c) for c in t["clips"])}
        t["size"] = t.get("size", 76) * S
        pieces = []
        for j, c in enumerate(t["clips"]):
            f, s, d, *o = c
            p = tmp / f"c{i:02d}_{j}.mp4"
            piece(SRC / f, s, d, o[0] if o else "", p)
            pieces.append(p)
        base = tmp / f"c{i:02d}.mp4"
        mr.join(pieces, base) if len(pieces) > 1 else shutil.copy(pieces[0], base)
        track, ty = mr.subtitle_track(t, tmp, i)
        if t.get("card"):
            png = tmp / f"card{i:02d}.png"
            card_png(png)
            track = [(png, 0.0, t["dur"], "fade")] + track
        out = tmp / f"p{i:02d}.mp4"
        mr.with_subs(["-i", str(base)], "[0:v]null[bg]", track, ty, t["dur"], out)
        parts.append(out)
        txt = t["text"][0] if isinstance(t["text"], list) else t["text"]
        print(f"  {i + 1:2d}. {t['dur']:.1f}초  {txt.splitlines()[0]}")

    joined = tmp / "joined.mp4"
    mr.join(parts, joined)
    # 최종 1번만 인코딩: H.264 High, CRF 12, slow, 원본 해상도 · 60fps 유지 + 무음 오디오 (음악은 앱에서)
    mr.run(["-i", str(joined), "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{total}",
            "-c:v", "libx264", "-preset", "slow", "-crf", "12", "-profile:v", "high", "-pix_fmt", "yuv420p", *COLOR,
            "-c:a", "aac", "-b:a", "320k", "-shortest", "-movflags", "+faststart", str(OUT)])
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"완료: {OUT}")


if __name__ == "__main__":
    main()

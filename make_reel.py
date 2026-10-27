"""
릴스 영상 자동 편집 (@hyewon_high1)

사진·영상 소스와 타임라인(대본)을 읽어 1080x1920(9:16), 30초 mp4를 만든다.
현재 타임라인 = drafts/A_춘천2024_5초서브4_릴스.txt 의 컷 구성.

    python make_reel.py
    python make_reel.py --src content_03 --out content_03/output/A_5초서브4.mp4

필요 패키지: pip install pillow pillow-heif imageio-ffmpeg
(ffmpeg는 imageio-ffmpeg에 들어 있는 실행 파일을 사용)

타임라인 규칙
- 컷마다 kind = photo / video / montage / black
- photo: fit="cover"(꽉 채워 자르기) / "blur"(전체가 보이게 + 흐린 배경) / "dim"(흐리고 어둡게)
  zoom=True면 천천히 줌인, zoom="punch"면 빠르게 확 줌인 (첫 3초용)
  fg_y: blur일 때 사진을 놓을 세로 위치 (0=맨 위, 0.5=가운데). 자막과 겹치지 않게 위로 올릴 때 사용
- video: start(초)부터 dur만큼 잘라 씀. 원본 소리는 쓰지 않음 (음악은 인스타 앱에서 추가)
  clips=[(파일, start, 길이), ...]로 여러 영상을 이어 붙이면 자막은 그 위에 한 번만 나옴
  beauty=True: 자연스러운 피부 보정 (질감 살짝 부드럽게 + 약간 밝고 따뜻하게)
- montage: 사진 여러 장을 빠르게 넘김. 자막은 한 번만 나옴
- crop: 사진 일부만 쓰기 (왼, 위, 오른, 아래 비율). 예) 기록증에서 기록 카드 부분만

자막 규칙 (유튜브식: 굵은 흰 글자 + 두꺼운 검은 테두리, 강조는 노란색)
- 한 자막은 최대 2줄. 더 길면 text를 리스트로 나눠 쓰면 차례로 바뀌며 나옴
  예) text=["2년 전 춘천\n서브4는 꿈도 안 꿨고", "그냥 {완주}가 목표였어요"]
  times=[1.2, 1.2]로 각 자막의 길이를 정할 수 있음 (없으면 똑같이 나눔)
- reveal=True: 줄마다 차례로 하나씩 나타나서 마지막엔 모든 줄이 보임 (검은 화면용)
- {중괄호} 안의 글자는 노란색으로 강조
- size: 글자 크기 (기본 76). 화면 폭을 넘으면 자동으로 줄어듦
- text_y: 자막 세로 위치. 기본은 모든 컷 같은 높이 (TEXT_Y)
- pop=False: 자막 팝업 효과 끄기 (첫 컷은 첫 프레임부터 바로 보여야 해서 끔)
"""

import argparse
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
import pillow_heif
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

pillow_heif.register_heif_opener()

W, H, FPS = 1080, 1920, 30
FONT = "C:/Windows/Fonts/NotoSansKR-VF.ttf"   # 가변 폰트 → Black(900) 굵기로 사용
TEXT_Y = 0.63            # 자막 가운데 높이 (화면 위에서 63% = 아래에서 약 1/3 지점)
TEXT_MAX_W = 820         # 자막 최대 폭 (오른쪽 좋아요·댓글 버튼과 겹치지 않게)
WHITE, YELLOW = (255, 255, 255), (255, 226, 0)
FF = imageio_ffmpeg.get_ffmpeg_exe()

# ─────────────────────────────────────────────
# 타임라인 (합계 30초)
# ─────────────────────────────────────────────
CERT = "P20241027_152233609_2A42C886-CF20-4451-B509-E3712A365E23.JPG"
CERT_CARD = dict(file=CERT, fit="blur", crop=(0.0, 0.27, 1.0, 0.84), fg_y=0.06)   # 기록 카드만, 화면 위쪽에
V1 = "V20241027_100938000_88F81F27-F13F-4C48-8074-6DBD608202FD.MOV"   # 레이스 초반 (무리 속 · 발밑 · 산길)
V2 = "V20241027_101227000_6832E08B-1468-4B54-846A-3C7CF65F39CF.MOV"   # 달리면서 셀카
V3 = "V20241027_133731000_E9A13C38-43EA-4B16-AEFF-C8248BA725BA.mov"   # 완주 후 메달 들어 보이기
V4 = "V20241027_133825000_3EC758ED-7746-4059-AEA5-3B6D47DCEE00.MOV"   # 완주 후 바나나 · 메달 깨물기
MEDAL = "P20241027_145125322_C5888399-CB4D-4B20-AADA-8D176F9C9B4C.heic"
TIMELINE = [
    # ── 첫 3초 (훅): 움직이는 얼굴 + 큰 글자 → 기록증 빠른 줌인
    dict(kind="video", file=V4, start=10.0, dur=1.5, text="{5초 차이}로\n서브4", size=150, pop=False, beauty=True),
    dict(kind="photo", **CERT_CARD, dur=2.0, zoom="punch", text="제 인생 첫 풀마라톤 서브4는\n{셔터 닫고} 달성했어요"),
    # ── 준비
    dict(kind="photo", file="P20241025_221530515_31FA7FD9-A6D2-4765-849F-7CF05C9A5E81.HEIC", dur=2.4,
         fit="blur", fg_y=0.12, zoom=True, text=["2년 전 춘천\n서브4는 꿈도 안 꿨고", "그냥 {완주}가 목표였어요"]),
    dict(kind="montage", dur=2.6, text="정말 탄수 열심히 먹었어요\n{충분히 먹었다}고 생각했거든요?", files=[
        ("P20241026_064646080_C2F87100-70DE-4080-84D0-AD69E4675A8D.JPG", (0.0, 0.0, 1.0, 0.64)),  # 아래 시계 글씨 잘라냄
        "P20241026_075910469_D0891201-41DB-4916-B921-825716D1D2A8.HEIC",
        "P20241026_111356778_CF2E5176-EB2D-4F5C-981A-F75951292649.HEIC",
        "P20241026_175018541_90AAC479-36B0-4FD8-B47D-EE0CF12DB91C.HEIC",
        "P20241026_210140790_0299C70A-7A40-4375-806F-6C5DD053F939.HEIC",
        "P20241027_061638784_4344F5AD-1DE5-4459-BA5A-A1392E583293.HEIC",
    ]),
    # ── 전략
    dict(kind="video", file=V1, start=0.0, dur=2.2, text="초반엔 신났죠"),
    dict(kind="video", file=V2, start=0.0, dur=2.6, times=[1.0, 1.6],
         text=["스마트워치는 안 보고", "{무리 없는 페이스}로\n천천히 빌드업"]),
    dict(kind="video", file=V2, start=4.5, dur=2.2, text="그 다음엔\n{할 만한 페이스}만 지키기"),
    # ── 벽: 검은 화면 한가운데, 한 줄씩 나타나 마지막엔 세 줄
    dict(kind="black", dur=2.8, reveal=True, times=[0.0, 0.8, 1.6], text_y=0.5,
         text="춘천댐 오르막 지나 30km\n\"{젤 더 챙길걸…}\"\n이 생각만 수십 번"),
    # ── 반전
    dict(kind="video", file=V1, start=5.0, dur=2.6, times=[1.2, 1.4],
         text=["41km, 처음 본 스마트워치", "{잘하면… 서브4?}"]),
    dict(kind="video", file=V1, start=2.0, dur=1.6, text="그때부터\n{다시 힘을 짜냈어요}"),
    # ── 결말
    dict(kind="photo", **CERT_CARD, dur=0.6, text="{3:59:55}", size=170),
    dict(kind="video", clips=[(V4, 1.8, 1.4), (V3, 1.5, 1.2)], dur=2.6, text="{5초} 남기고\n들어왔습니다"),
    # ── 끝 화면
    dict(kind="photo", file=MEDAL, dur=2.4, fit="cover", zoom=True, text="첫 풀마라톤 뛰는 분께\n드리는 조언 3가지"),
    dict(kind="photo", file=MEDAL, dur=1.9, fit="dim", text="{본문에 있어요}", size=96),
]


def run(args):
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def load(path, crop=None):
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    if crop:
        l, t, r, b = crop
        img = img.crop((int(img.width * l), int(img.height * t), int(img.width * r), int(img.height * b)))
    return img


def cover(img, w=W, h=H):
    return ImageOps.fit(img, (w, h), Image.LANCZOS)


def frame(img, fit, fg_y=None):
    """사진 한 장을 1080x1920 화면으로 만든다."""
    if fit == "cover":
        return cover(img)
    bg = cover(img).filter(ImageFilter.GaussianBlur(40))
    if fit == "dim":
        return Image.blend(bg, Image.new("RGB", (W, H), "black"), 0.45)
    bg = Image.blend(bg, Image.new("RGB", (W, H), "black"), 0.25)
    scale = min(W / img.width, H / img.height)       # 작은 사진도 화면 폭에 맞게 키움
    fg = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    top = (H - fg.height) // 2 if fg_y is None else int(H * fg_y)
    bg.paste(fg, ((W - fg.width) // 2, top))
    return bg


def font(size):
    f = ImageFont.truetype(FONT, size)
    f.set_variation_by_axes([900])
    return f


def runs(line):
    """'{강조}' 표시를 [(글자, 색), ...]로 나눈다."""
    return [(p[1:-1], YELLOW) if p.startswith("{") else (p, WHITE) for p in re.split(r"(\{[^}]*\})", line) if p]


def subtitle(text, size=76, text_y=TEXT_Y, only=None):
    """유튜브식 자막: 굵은 흰 글자 + 두꺼운 검은 테두리 + 그림자, {강조}는 노란색.
    only=k면 전체 줄 배치는 그대로 두고 k번째 줄만 그린다 (한 줄씩 나타나기용)."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if not text:
        return layer
    lines = [runs(l) for l in text.split("\n")]
    while True:                                       # 화면 폭을 넘으면 글자 크기를 줄임
        f = font(size)
        widths = [sum(f.getlength(t) for t, _ in l) for l in lines]
        if max(widths) <= TEXT_MAX_W or size <= 40:
            break
        size -= 2
    stroke = max(4, round(size * 0.11))
    line_h = round(size * 1.28)
    y = H * text_y - line_h * len(lines) / 2

    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds, d = ImageDraw.Draw(shadow), ImageDraw.Draw(layer)
    for k, (l, lw) in enumerate(zip(lines, widths)):
        x = (W - lw) / 2
        for t, color in l:
            if only is None or only == k:
                ds.text((x + 6, y + 8), t, font=f, fill=(0, 0, 0, 160), stroke_width=stroke,
                        stroke_fill=(0, 0, 0, 160))
                d.text((x, y), t, font=f, fill=color, stroke_width=stroke, stroke_fill="black")
            x += f.getlength(t)
        y += line_h
    return Image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(6)), layer)


def subtitle_track(c, tmp, i):
    """컷 하나의 자막들 → [(png, 시작, 끝, 효과)]. 효과: pop(살짝 커지며) / fade(서서히) / still(바로)."""
    dur, size, ty = c["dur"], c.get("size", 76), c.get("text_y", TEXT_Y)
    text = c.get("text", "")
    first = "pop" if c.get("pop", True) else "still"
    track = []
    if c.get("reveal"):                               # 줄마다 차례로 나타나서 끝까지 유지
        starts = c.get("times") or [dur * k / len(text.split("\n")) for k in range(len(text.split("\n")))]
        for k, a in enumerate(starts):
            png = tmp / f"sub{i:02d}_{k}.png"
            subtitle(text, size, ty, only=k).save(png)
            track.append((png, a, dur, "fade"))
    elif isinstance(text, list):                     # 자막이 차례로 바뀜 (2줄 넘는 내용 나누기)
        lens = c.get("times") or [dur / len(text)] * len(text)
        a = 0.0
        for k, (t, ln) in enumerate(zip(text, lens)):
            png = tmp / f"sub{i:02d}_{k}.png"
            subtitle(t, size, ty).save(png)
            track.append((png, a, a + ln if k < len(text) - 1 else dur, first if k == 0 else "pop"))
            a += ln
    elif text:
        png = tmp / f"sub{i:02d}.png"
        subtitle(text, size, ty).save(png)
        track.append((png, 0.0, dur, first))
    return track, ty


ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS), "-an"]


def with_subs(bg_inputs, bg_filter, track, ty, dur, out):
    """배경 + 자막들을 합쳐 dur초 클립으로. 자막은 각자 [시작, 끝] 동안만 보임."""
    n = round(dur * FPS)
    inputs, graph, last = list(bg_inputs), [bg_filter], "bg"
    for k, (png, a, b, fx) in enumerate(track):
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", f"{dur}", "-i", str(png)]
        src = f"[{k + 1}:v]format=rgba"
        if fx == "pop":      # 0.12초 동안 살짝 커졌다 제자리로
            src += (f",fade=in:st={a}:d=0.12:alpha=1,"
                    f"scale=w='{W}*(1.08-0.08*min(max(t-{a},0)/0.12,1))':h=-1:eval=frame")
        elif fx == "fade":
            src += f",fade=in:st={a}:d=0.2:alpha=1"
        graph.append(f"{src}[s{k}]")
        graph.append(f"[{last}][s{k}]overlay=x='(W-w)/2':y='(H-h)*{ty}':enable='between(t,{a},{b})'[v{k}]")
        last = f"v{k}"
    run([*inputs, "-filter_complex", ";".join(graph), "-map", f"[{last}]", "-frames:v", str(n), *ENC, str(out)])


def render_still(base, track, ty, dur, zoom, out):
    """사진 화면 + 자막. zoom=True 천천히(1.0→1.06), "punch" 빠르게(1.0→1.18) 확대."""
    n = round(dur * FPS)
    amt = 0.18 if zoom == "punch" else 0.06
    curve = f"(1-pow(1-on/{n},3))" if zoom == "punch" else f"on/{n}"   # punch는 처음에 확 → 끝에 느리게
    vf = (f"[0:v]scale={W*2}:{H*2},zoompan=z='1+{amt}*{curve}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
          f":d=1:s={W}x{H}:fps={FPS}[bg]" if zoom else f"[0:v]fps={FPS}[bg]")
    with_subs(["-loop", "1", "-framerate", str(FPS), "-t", f"{dur}", "-i", str(base)], vf, track, ty, dur, out)


# 자연스러운 피부 보정: 경계는 살리고 질감만 부드럽게 한 결과를 원본과 45:55로 섞음 (피부결 유지)
# + 아주 약간 밝고 따뜻하게. 세게 하려면 all_opacity를 올리고, 약하게 하려면 내림
BEAUTY = (",split[o][b];[b]bilateral=sigmaS=6:sigmaR=0.06[bb];[o][bb]blend=all_opacity=0.45,"
          "eq=brightness=0.015:gamma=1.03:saturation=1.03,colorbalance=rm=0.02:bm=-0.015")


def render_video(src, start, dur, track, ty, out, beauty=False):
    vf = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1"
          f"{BEAUTY if beauty else ''}[bg]")
    with_subs(["-ss", f"{start}", "-t", f"{dur}", "-i", str(src)], vf, track, ty, dur, out)


def join(pieces, out):
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{q.as_posix()}'\n" for q in pieces), encoding="utf-8")
    run(["-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="content_03")
    ap.add_argument("--out", default="content_03/output/A_5초서브4.mp4")
    a = ap.parse_args()
    src, out = Path(a.src), Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    total = sum(c["dur"] for c in TIMELINE)
    print(f"타임라인 합계 {total:.1f}초, 컷 {len(TIMELINE)}개")

    tmp = Path(tempfile.mkdtemp(prefix="reel_"))
    parts = []
    for i, c in enumerate(TIMELINE):
        track, ty = subtitle_track(c, tmp, i)
        p = tmp / f"p{i:02d}.mp4"
        if c["kind"] == "video" and "clips" in c:
            # 영상 여러 개를 자막 없이 먼저 잇고, 자막은 그 위에 한 번만
            pieces = []
            for j, (f, s, d) in enumerate(c["clips"]):
                piece = tmp / f"c{i:02d}_{j}.mp4"
                render_video(src / f, s, d, [], ty, piece)
                pieces.append(piece)
            joined = tmp / f"c{i:02d}.mp4"
            join(pieces, joined)
            render_video(joined, 0, c["dur"], track, ty, p)
        elif c["kind"] == "video":
            render_video(src / c["file"], c["start"], c["dur"], track, ty, p, c.get("beauty", False))
        elif c["kind"] == "montage":
            # 사진들을 자막 없이 먼저 이어 붙이고, 자막은 그 위에 한 번만 (사진마다 반복되지 않게)
            each = c["dur"] / len(c["files"])
            pieces = []
            for j, f in enumerate(c["files"]):
                f, crop = f if isinstance(f, tuple) else (f, None)   # (파일, crop)으로 일부만 쓸 수 있음
                base = tmp / f"b{i:02d}_{j}.png"
                frame(load(src / f, crop), "cover").save(base)
                piece = tmp / f"m{i:02d}_{j}.mp4"
                render_still(base, [], ty, each, False, piece)
                pieces.append(piece)
            montage = tmp / f"m{i:02d}.mp4"
            join(pieces, montage)
            render_video(montage, 0, c["dur"], track, ty, p)
        else:
            base = tmp / f"b{i:02d}.png"
            img = (Image.new("RGB", (W, H), "black") if c["kind"] == "black"
                   else frame(load(src / c["file"], c.get("crop")), c["fit"], c.get("fg_y")))
            img.save(base)
            render_still(base, track, ty, c["dur"], c.get("zoom", False), p)
        parts.append(p)
        t = c.get("text", "")
        first = (t[0] if isinstance(t, list) else t).splitlines()[0] if t else ""
        print(f"  {i+1:2d}. {c['kind']:7s} {c['dur']:.1f}초  {first}")

    joined = tmp / "joined.mp4"
    join(parts, joined)
    # 무음 오디오 트랙을 붙여 마무리 (음악은 인스타 앱에서 추가)
    run(["-i", str(joined), "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{total}",
         "-c:v", "copy", "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(out)])
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"완료: {out}")


if __name__ == "__main__":
    main()

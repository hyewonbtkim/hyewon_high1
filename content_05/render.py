"""carbo.html → output/slide_01~08.png (2배 렌더링 후 1080x1350 PNG로 축소, 무손실)"""
import subprocess, sys, time
from pathlib import Path
from PIL import Image

HERE = Path(__file__).parent
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
N, W, H, S = 8, 1080, 1350, 2
out = HERE / "output"; out.mkdir(exist_ok=True)
big = out / "_full@2x.png"
subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                f"--force-device-scale-factor={S}", f"--window-size={W},{H*N}", "--virtual-time-budget=8000",
                f"--screenshot={big}", (HERE / "carbo.html").as_uri()], check=True, capture_output=True)
im = Image.open(big)
for i in range(N):
    slide = im.crop((0, i*H*S, W*S, (i+1)*H*S)).resize((W, H), Image.LANCZOS)
    for attempt in range(10):  # 미리보기·동기화가 파일을 잠깐 잡고 있을 때 재시도
        try:
            slide.save(out / f"slide_{i+1:02d}.png"); break
        except OSError:
            time.sleep(0.5)
    else:
        sys.exit(f"slide_{i+1:02d}.png 저장 실패 (파일이 열려 있는지 확인)")
print("done", im.size)
im.close(); big.unlink()  # 중간 파일 정리

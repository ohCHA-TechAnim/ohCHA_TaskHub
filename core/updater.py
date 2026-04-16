import urllib.request
import json
import zipfile
import io
import os
import shutil
import time
from pathlib import Path
from PySide6.QtCore import QThread, Signal

# 다운로드용 깃허브 경로
GITHUB_REPO = "ohCHA-TechAnim/ohCHA_TaskHub" 

# 깃허브에 올릴 때는 이 숫자를 반드시 1.0.1 로 올려서 커밋해야 무한 루프에 빠지지 않습니다.
CURRENT_VERSION = "1.0.2"

# 현재 updater.py의 위치를 기반으로 앱의 최상위 폴더(main.py가 있는 곳)를 절대 경로로 찾습니다.
BASE_DIR = Path(__file__).resolve().parent.parent

class UpdateChecker(QThread):
    update_available = Signal(str, str, str)

    def run(self):
        try:
            # 🔥 [핵심] 주소 맨 뒤에 '?t=시간' 을 붙여서 깃허브 캐시를 완벽히 무력화합니다!
            url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/version.json?t={int(time.time())}"
            req = urllib.request.Request(url, headers={'Cache-Control': 'no-cache'})
            
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                remote_version = data.get("version", "1.0.0")
                notes = data.get("release_notes", "업데이트가 있습니다.")
                
                # 테스트 확인용 출력 (터미널에 뜹니다)
                print(f"📡 깃허브 버전: {remote_version} / 내 버전: {CURRENT_VERSION}")
                
                if self.is_newer(remote_version, CURRENT_VERSION):
                    download_url = f"https://github.com/{GITHUB_REPO}/archive/refs/heads/main.zip"
                    self.update_available.emit(remote_version, notes, download_url)
        except Exception as e:
            # 🔥 에러가 나면 터미널에 빨간 글씨로 이유를 알려줍니다.
            print(f"❌ 업데이트 확인 실패: {e}")

    def is_newer(self, remote, local):
        try:
            r = tuple(map(int, remote.split('.')))
            l = tuple(map(int, local.split('.')))
            return r > l
        except:
            return False


class UpdateDownloader(QThread):
    finished = Signal(bool, str)

    def __init__(self, download_url):
        super().__init__()
        self.download_url = download_url

    def run(self):
        try:
            req = urllib.request.Request(self.download_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                with zipfile.ZipFile(io.BytesIO(response.read())) as z:
                    
                    temp_dir = BASE_DIR / "update_temp"
                    z.extractall(temp_dir)
                    
                    # 깃허브 압축 해제 시 생성되는 최상위 폴더 찾기
                    extracted_folders = [f for f in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, f))]
                    if not extracted_folders:
                        raise Exception("압축 해제된 폴더를 찾을 수 없습니다.")
                        
                    src_dir = os.path.join(temp_dir, extracted_folders[0])
                    
                    # 🔥 앱의 진짜 최상단 경로(BASE_DIR)로 파일 강제 덮어쓰기
                    for item in os.listdir(src_dir):
                        s = os.path.join(src_dir, item)
                        d = os.path.join(BASE_DIR, item)
                        if os.path.isdir(s):
                            shutil.copytree(s, d, dirs_exist_ok=True)
                        else:
                            shutil.copy2(s, d)
                            
                    # 임시 폴더 삭제
                    shutil.rmtree(temp_dir)
                    
            self.finished.emit(True, "업데이트 완료! 앱이 종료됩니다. 다시 실행해 주세요.")
        except Exception as e:
            self.finished.emit(False, f"업데이트 중 오류가 발생했습니다: {e}")
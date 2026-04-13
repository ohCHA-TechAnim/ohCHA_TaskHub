import urllib.request
import json
import zipfile
import io
import os
import shutil
from PySide6.QtCore import QThread, Signal

# 🔥 여기에 본인의 GitHub 정보를 입력하세요! (예: "ohCHA/TaskHub_App")
GITHUB_REPO = "ohCHA-TechAnim/ohCHA_TaskHub" 

# 앱의 현재 로컬 버전 (업데이트할 때마다 main.py와 함께 이 숫자도 올려줘야 합니다)
CURRENT_VERSION = "1.0.0"

class UpdateChecker(QThread):
    """백그라운드에서 GitHub 버전을 체크하는 스레드"""
    update_available = Signal(str, str, str) # 버전, 릴리즈노트, 다운로드URL

    def run(self):
        try:
            # GitHub에서 raw 버전 파일 읽어오기 (캐시 방지 헤더 추가)
            url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/version.json"
            req = urllib.request.Request(url, headers={'Cache-Control': 'no-cache'})
            
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                remote_version = data.get("version", "1.0.0")
                notes = data.get("release_notes", "업데이트가 있습니다.")
                
                # 원격 버전이 로컬 버전보다 높으면 시그널 발생!
                if self.is_newer(remote_version, CURRENT_VERSION):
                    download_url = f"https://github.com/{GITHUB_REPO}/archive/refs/heads/main.zip"
                    self.update_available.emit(remote_version, notes, download_url)
        except Exception as e:
            print(f"업데이트 확인 실패 (인터넷 미연결 등): {e}")

    def is_newer(self, remote, local):
        """버전 문자열 비교 (예: 1.0.1 > 1.0.0)"""
        try:
            r = tuple(map(int, remote.split('.')))
            l = tuple(map(int, local.split('.')))
            return r > l
        except:
            return False


class UpdateDownloader(QThread):
    """새 버전을 다운로드하고 코드를 덮어쓰는 스레드"""
    finished = Signal(bool, str) # 성공여부, 메시지

    def __init__(self, download_url):
        super().__init__()
        self.download_url = download_url

    def run(self):
        try:
            # 1. 깃허브에서 main.zip 다운로드
            req = urllib.request.Request(self.download_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                with zipfile.ZipFile(io.BytesIO(response.read())) as z:
                    
                    # 2. 임시 폴더에 압축 해제
                    temp_dir = "update_temp"
                    z.extractall(temp_dir)
                    
                    # 깃허브 압축파일은 최상단에 '저장소이름-main' 폴더가 생김
                    root_folder = os.listdir(temp_dir)[0]
                    src_dir = os.path.join(temp_dir, root_folder)
                    
                    # 3. 현재 작업 디렉토리(앱 폴더)로 파일들 덮어쓰기 복사
                    for item in os.listdir(src_dir):
                        s = os.path.join(src_dir, item)
                        d = os.path.join(os.getcwd(), item)
                        if os.path.isdir(s):
                            shutil.copytree(s, d, dirs_exist_ok=True) # Python 3.8+ 지원
                        else:
                            shutil.copy2(s, d)
                            
                    # 4. 임시 폴더 삭제
                    shutil.rmtree(temp_dir)
                    
            self.finished.emit(True, "업데이트가 성공적으로 완료되었습니다!\n적용을 위해 앱이 종료됩니다. 다시 실행해 주세요.")
        except Exception as e:
            self.finished.emit(False, f"업데이트 중 오류가 발생했습니다: {e}")
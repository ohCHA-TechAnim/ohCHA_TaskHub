import urllib.request
import json
import os
import sys
import subprocess
import time
from pathlib import Path
from PySide6.QtCore import QThread, Signal

# 🔥 본인의 깃허브 정보
GITHUB_REPO = "YourUsername/YourRepoName" 

# 내 앱의 버전
CURRENT_VERSION = "1.0.4"

class UpdateChecker(QThread):
    update_available = Signal(str, str, str)

    def run(self):
        try:
            url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/version.json?t={int(time.time())}"
            req = urllib.request.Request(url, headers={'Cache-Control': 'no-cache'})
            
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                remote_version = data.get("version", "1.0.0")
                notes = data.get("release_notes", "업데이트가 있습니다.")
                
                if self.is_newer(remote_version, CURRENT_VERSION):
                    # 🔥 [변경점] 소스코드(.zip)가 아니라, Releases에 올려둔 최신 EXE 파일의 다운로드 링크를 만듭니다!
                    # 예: https://github.com/ohCHA/TaskHub/releases/download/v1.0.4/TaskHub.exe
                    exe_name = "TaskHub.exe" # 깃허브 릴리즈에 올릴 고정된 파일 이름
                    download_url = f"https://github.com/{GITHUB_REPO}/releases/download/v{remote_version}/{exe_name}"
                    
                    self.update_available.emit(remote_version, notes, download_url)
        except Exception as e:
            print(f"업데이트 확인 실패: {e}")

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
            # 1. 내가 현재 실행 중인 파일의 절대 경로 찾기 (예: C:/바탕화면/TaskHub_v1.0.3.exe)
            current_exe = sys.executable
            
            # 파이썬 스크립트 모드(python main.py)로 실행 중이면 업데이트 중단 (EXE 환경에서만 작동)
            if not current_exe.endswith(".exe") or "python" in current_exe.lower():
                self.finished.emit(False, "[개발 모드] EXE 빌드 버전에서만 자동 업데이트가 지원됩니다.\n깃허브에서 코드를 Pull 받아주세요.")
                return

            current_dir = os.path.dirname(current_exe)
            current_name = os.path.basename(current_exe)
            
            # 2. 다운받을 새 파일의 임시 이름 (예: TaskHub_new.exe)
            new_exe = os.path.join(current_dir, "TaskHub_new.exe")
            
            # 3. 깃허브 Releases에서 새 EXE 파일 다운로드
            req = urllib.request.Request(self.download_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as response, open(new_exe, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)

            # 4. 🔥 [궁극의 마법] 자기 자신(.exe)은 실행 중일 때 지울 수 없으므로,
            # 앱이 꺼진 직후에 구버전을 지우고 새 버전의 이름을 원래대로 바꾼 뒤 실행하는 .bat 파일을 만듭니다!
            bat_path = os.path.join(current_dir, "update_script.bat")
            
            bat_content = f"""@echo off
echo 업데이트 적용 중입니다. 잠시만 기다려주세요...
timeout /t 2 /nobreak > NUL
del "{current_name}"
ren "TaskHub_new.exe" "{current_name}"
start "" "{current_name}"
del "%~f0"
"""
            with open(bat_path, "w", encoding="euc-kr") as f:
                f.write(bat_content)

            # 5. .bat 파일을 백그라운드로 실행하고 스레드 종료
            subprocess.Popen([bat_path], shell=True)
            
            self.finished.emit(True, "업데이트 다운로드 완료!\n앱을 재시작하여 새 버전을 적용합니다.")
            
        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.finished.emit(False, "업데이트 실패: 깃허브 Releases에 해당 버전의 EXE 파일이 아직 업로드되지 않았습니다.")
            else:
                self.finished.emit(False, f"다운로드 오류: {e}")
        except Exception as e:
            self.finished.emit(False, f"업데이트 중 오류가 발생했습니다: {e}")
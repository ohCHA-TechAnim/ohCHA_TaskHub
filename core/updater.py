import urllib.request
import json
import os
import sys
import subprocess
import time
import shutil
from pathlib import Path
from PySide6.QtCore import QThread, Signal

# 🔥 [매우 중요] 본인의 GitHub 주소가 대소문자까지 정확한지 꼭 확인하세요!
# 예: "ohCHA-TechAnim/ohCHA_TaskHub"
GITHUB_REPO = "ohCHA-TechAnim/ohCHA_TaskHub" 

CURRENT_VERSION = "1.0.4"

class UpdateChecker(QThread):
    update_available = Signal(str, str, str)
    
    # 🔥 에러가 나면 팝업을 띄우기 위해 메인 윈도우로 시그널을 보냅니다.
    check_error = Signal(str) 

    def run(self):
        try:
            # 1. version.json 읽어오기 (캐시 방지 타임스탬프 추가)
            url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/version.json?t={int(time.time())}"
            print(f"[디버그] 업데이트 체크 URL: {url}") # 터미널용 디버그
            
            req = urllib.request.Request(url, headers={'Cache-Control': 'no-cache'})
            
            with urllib.request.urlopen(req, timeout=5) as response:
                raw_data = response.read().decode('utf-8')
                print(f"[디버그] 깃허브에서 받은 데이터: {raw_data}") # 터미널용 디버그
                
                data = json.loads(raw_data)
                remote_version = data.get("version", "1.0.0")
                notes = data.get("release_notes", "업데이트가 있습니다.")
                
                # 2. 버전 비교
                if self.is_newer(remote_version, CURRENT_VERSION):
                    # 3. 새 버전의 EXE 다운로드 URL 생성
                    exe_name = "TaskHub.exe"
                    download_url = f"https://github.com/{GITHUB_REPO}/releases/download/v{remote_version}/{exe_name}"
                    
                    print(f"[디버그] 새 버전 발견! 다운로드 URL: {download_url}")
                    self.update_available.emit(remote_version, notes, download_url)
                else:
                    print(f"[디버그] 최신 버전입니다. (로컬: {CURRENT_VERSION} / 깃허브: {remote_version})")
                    
        except Exception as e:
            # 🔥 여기서 에러가 나면 조용히 죽지 않고 시그널을 쏴서 화면에 띄웁니다!
            error_msg = f"업데이트 확인 중 치명적 오류 발생:\n{str(e)}"
            print(f"[디버그] ❌ {error_msg}")
            self.check_error.emit(error_msg)

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
            current_exe = sys.executable
            
            if not current_exe.endswith(".exe") or "python" in current_exe.lower():
                self.finished.emit(False, "[개발 모드] EXE 빌드 버전에서만 자동 업데이트가 지원됩니다.\n깃허브에서 코드를 Pull 받아주세요.")
                return

            current_dir = os.path.dirname(current_exe)
            current_name = os.path.basename(current_exe)
            new_exe = os.path.join(current_dir, "TaskHub_new.exe")
            
            req = urllib.request.Request(self.download_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as response, open(new_exe, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)

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

            subprocess.Popen([bat_path], shell=True)
            self.finished.emit(True, "업데이트 다운로드 완료!\n앱을 재시작하여 새 버전을 적용합니다.")
            
        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.finished.emit(False, "업데이트 실패: 깃허브 Releases에 해당 버전의 EXE 파일이 아직 업로드되지 않았습니다.")
            else:
                self.finished.emit(False, f"다운로드 오류: {e}")
        except Exception as e:
            self.finished.emit(False, f"업데이트 중 오류가 발생했습니다: {e}")
# -*- coding: utf-8 -*-
import sys
import os
import ctypes
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtGui import QIcon

# Core 로직 임포트
from core.config_manager import ConfigManager
from core.rule_engine import RuleEngine

# UI 로직 임포트
from ui.onboarding import OnboardingWizard
from ui.main_window import MainWindow

def resource_path(relative_path):
    """
    PyInstaller로 패키징된 실행 파일(.exe)이 실행될 때
    임시 폴더(_MEIPASS)에 압축이 풀린 리소스(아이콘 등)의 절대 경로를 찾아줍니다.
    일반 파이썬 스크립트로 실행할 때는 현재 폴더를 반환합니다.
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def main():
    # 1. 윈도우 작업 표시줄 아이콘 분리 마법 (Windows API)
    # (파이썬 기본 뱀 모양 아이콘 대신, 우리가 설정한 로고가 작업 표시줄에 단독으로 뜨게 만듭니다.)
    try:
        myappid = 'ohCHA.TaskHub.WorkspaceManager.1_0_3' # 고유 ID (버전 올릴 때 같이 올려주면 좋음)
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    # 2. PySide6 앱 객체 생성 및 기본 스타일 적용
    app = QApplication(sys.argv)
    app.setStyle("Fusion") 
    
    # 3. 앱 전체(창 모서리, 알림창, 작업표시줄 등)에 로고 아이콘 강제 세팅!
    # (resource_path 함수를 통해 .exe 내부의 logo.ico를 완벽하게 찾아냄)
    icon_path = resource_path("logo.ico")
    app.setWindowIcon(QIcon(icon_path))
    
    # 4. 의존성 주입 (Core 모듈 초기화)
    config_mgr = ConfigManager()
    rule_engine = RuleEngine(config_mgr)
    
    # 5. 초기 설정 확인 (루트 경로가 비어있으면 온보딩 마법사 실행)
    if config_mgr.is_setup_required():
        wizard = OnboardingWizard(config_mgr)
        # 마법사 창을 모달(Modal)로 띄우고, 창을 그냥 꺼버리면 앱 종료
        if wizard.exec() == QDialog.Rejected:
            sys.exit(0)
            
    # 6. 메인 대시보드 화면 띄우기
    window = MainWindow(config_mgr, rule_engine)
    window.show()
    
    # 7. 앱 이벤트 루프 실행 (사용자가 끌 때까지 대기)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
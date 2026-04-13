import sys
from PySide6.QtWidgets import QApplication, QDialog

# Core 로직 임포트
from core.config_manager import ConfigManager
from core.rule_engine import RuleEngine

# UI 로직 임포트
from ui.onboarding import OnboardingWizard
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion") # OS 상관없이 깔끔한 UI 테마 적용
    
    # 1. 의존성 주입
    config_mgr = ConfigManager()
    rule_engine = RuleEngine(config_mgr)
    
    # 2. 초기 설정 확인 (루트 경로가 비어있으면 마법사 실행)
    if config_mgr.is_setup_required():
        wizard = OnboardingWizard(config_mgr)
        # 마법사 창을 모달(Modal)로 띄우고, 창을 그냥 꺼버리면(Rejected) 앱 종료
        if wizard.exec() == QDialog.Rejected:
            sys.exit(0)
            
    # 3. 메인 화면 띄우기
    window = MainWindow(config_mgr, rule_engine)
    window.show()
    
    # 앱 이벤트 루프 실행
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
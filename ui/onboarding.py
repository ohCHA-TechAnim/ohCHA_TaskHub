from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QLineEdit, 
                               QFileDialog, QMessageBox)

class OnboardingWizard(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        
        self.setWindowTitle("TaskHub - 초기 설정 마법사")
        self.setFixedSize(500, 300)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>환영합니다! 작업 환경을 설정해 주세요.</h2>"))

        # 1. 루트 경로 설정 영역
        root_layout = QHBoxLayout()
        self.root_input = QLineEdit()
        self.root_input.setPlaceholderText("기본 작업 드라이브/폴더 (예: D:/Work)")
        
        root_btn = QPushButton("폴더 찾기")
        root_btn.clicked.connect(self.browse_root)
        
        root_layout.addWidget(self.root_input)
        root_layout.addWidget(root_btn)
        layout.addWidget(QLabel("1. 메인 루트 폴더 설정"))
        layout.addLayout(root_layout)

        # 2. 규칙 설정 영역
        self.rule_input = QLineEdit()
        # 설정된 기본값을 가져와서 텍스트창에 채워줌
        self.rule_input.setText(self.config.get("rules", "character_folder"))
        layout.addWidget(QLabel("2. 폴더 생성 규칙 정의 (변수: {root}, {type}, {name}, {number})"))
        layout.addWidget(self.rule_input)

        # 3. Preset TXT 설정 영역
        preset_layout = QHBoxLayout()
        self.preset_input = QLineEdit()
        self.preset_input.setPlaceholderText("Preset TXT 파일 경로 (선택사항)")
        
        preset_btn = QPushButton("파일 찾기")
        preset_btn.clicked.connect(self.browse_preset)
        
        preset_layout.addWidget(self.preset_input)
        preset_layout.addWidget(preset_btn)
        layout.addWidget(QLabel("3. 작업 구조 프리셋 파일 (TXT)"))
        layout.addLayout(preset_layout)

        # 하단 여백 및 저장 버튼
        layout.addStretch()
        
        save_btn = QPushButton("설정 완료 및 시작")
        save_btn.setStyleSheet("background-color: #2b5797; color: white; padding: 10px; font-weight: bold;")
        save_btn.clicked.connect(self.save_and_close)
        layout.addWidget(save_btn)

    def browse_root(self):
        folder = QFileDialog.getExistingDirectory(self, "루트 폴더 선택")
        if folder: 
            self.root_input.setText(folder)

    def browse_preset(self):
        file, _ = QFileDialog.getOpenFileName(self, "프리셋 파일 선택", "", "Text Files (*.txt)")
        if file: 
            self.preset_input.setText(file)

    def save_and_close(self):
        if not self.root_input.text():
            QMessageBox.warning(self, "경고", "루트 폴더는 필수입니다.")
            return
            
        # UI에서 입력받은 값을 ConfigManager를 통해 업데이트 후 저장
        self.config.update("paths", "root_path", self.root_input.text())
        self.config.update("paths", "preset_txt_path", self.preset_input.text())
        self.config.update("rules", "character_folder", self.rule_input.text())
        self.config.save()
        
        self.accept() # 창을 닫고 성공(True) 상태 반환
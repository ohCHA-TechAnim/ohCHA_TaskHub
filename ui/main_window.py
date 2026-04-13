import re
from pathlib import Path
from core.updater import UpdateChecker, UpdateDownloader, CURRENT_VERSION
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, QSplitter, 
                               QListWidget, QStackedWidget, QMessageBox, QCheckBox)
from PySide6.QtCore import Qt, Slot

from ui.settings_dialog import SettingsDialog
from core.preset_parser import PresetParser

class MainWindow(QMainWindow):
    def __init__(self, config_manager, rule_engine):
        super().__init__()
        self.config = config_manager
        self.rule_engine = rule_engine
        self.dynamic_inputs = {}
        
        self.config.config_changed.connect(self.on_config_changed)
        
        # 타이틀 바에 현재 로컬 버전 표시
        self.setWindowTitle(f"TaskHub - Workspace Manager (v{CURRENT_VERSION})")
        self.resize(1100, 700)
        self.setup_ui()
        
        # 🔥 앱 켜질 때 자동 업데이트 체크 시작
        self.check_for_updates()

    def setup_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        self.setCentralWidget(main_widget)

        top_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 파일, 태그, 작업 로그 통합 검색...")
        self.search_bar.setMinimumHeight(35)
        
        settings_btn = QPushButton("⚙️ 환경 설정")
        settings_btn.setMinimumHeight(35)
        settings_btn.clicked.connect(self.open_settings)
        
        top_layout.addWidget(self.search_bar)
        top_layout.addWidget(settings_btn)
        main_layout.addLayout(top_layout)

        splitter = QSplitter(Qt.Horizontal)
        self.sidebar = QListWidget()
        self.sidebar.addItems(["📂 폴더 생성기 (Rule Engine)", "🧠 프리셋 관리", "🧾 작업 로그", "📊 대시보드"])
        self.sidebar.setMaximumWidth(220)
        self.sidebar.currentRowChanged.connect(self.change_page)
        
        self.content_stack = QStackedWidget()
        
        self.folder_creator_widget = QWidget()
        self.folder_creator_layout = QVBoxLayout(self.folder_creator_widget)
        self.build_folder_creator_ui()
        self.content_stack.addWidget(self.folder_creator_widget)
        
        self.content_stack.addWidget(QLabel("<h2 align='center'>프리셋 관리 (준비 중)</h2>"))
        self.content_stack.addWidget(QLabel("<h2 align='center'>작업 로그 (준비 중)</h2>"))
        self.content_stack.addWidget(QLabel("<h2 align='center'>대시보드 (준비 중)</h2>"))

        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.content_stack)
        splitter.setSizes([200, 900]) 
        
        main_layout.addWidget(splitter)
        self.sidebar.setCurrentRow(0)

    def build_folder_creator_ui(self):
        while self.folder_creator_layout.count():
            item = self.folder_creator_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())

        self.dynamic_inputs.clear()

        self.folder_creator_layout.addWidget(QLabel("<h2>🎯 룰 엔진 기반 폴더 생성기</h2>"))
        
        template = self.config.get("rules", "character_folder")
        root = self.config.get("paths", "root_path")
        info_label = QLabel(f"적용된 루트: <b>{root}</b><br>현재 규칙: <b>{template}</b>")
        info_label.setStyleSheet("color: #555; margin-bottom: 10px;")
        self.folder_creator_layout.addWidget(info_label)

        input_layout = QHBoxLayout()
        variables = self.rule_engine.extract_variables("character_folder")
        
        for var in variables:
            if var == "root": 
                continue
            input_layout.addWidget(QLabel(f"<b>{var}:</b>"))
            line_edit = QLineEdit()
            line_edit.setPlaceholderText(f"{var} 입력...")
            line_edit.textChanged.connect(self.preview_path)
            input_layout.addWidget(line_edit)
            self.dynamic_inputs[var] = line_edit

        self.folder_creator_layout.addLayout(input_layout)

        # 🔥 일괄 생성(Batch) 옵션 체크박스 추가
        self.batch_checkbox = QCheckBox("🚀 루트 하위의 모든 기존 폴더에 일괄 생성 적용 (배치 모드)")
        self.batch_checkbox.setStyleSheet("font-weight: bold; color: #d35400; padding: 10px 0;")
        self.folder_creator_layout.addWidget(self.batch_checkbox)

        btn_layout = QHBoxLayout()
        preview_btn = QPushButton("경로 새로고침")
        preview_btn.clicked.connect(self.preview_path)
        
        create_btn = QPushButton("실제 폴더 생성하기")
        create_btn.setStyleSheet("background-color: #2b5797; color: white; font-weight: bold;")
        create_btn.clicked.connect(self.create_folder)
        
        btn_layout.addWidget(preview_btn)
        btn_layout.addWidget(create_btn)
        self.folder_creator_layout.addLayout(btn_layout)

        self.result_label = QLabel("값을 입력하면 경로가 미리 표시됩니다.")
        self.folder_creator_layout.addWidget(self.result_label)
        self.folder_creator_layout.addStretch()

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())
        layout.deleteLater()

    def change_page(self, index):
        self.content_stack.setCurrentIndex(index)

    def open_settings(self):
        dialog = SettingsDialog(self.config, self)
        dialog.exec()

    def get_generated_path(self):
        kwargs = {}
        forbidden_chars = r'[<>:"/\\|?*]' 
        
        for var_name, widget in self.dynamic_inputs.items():
            val = widget.text().strip()
            if not val:
                raise ValueError("입력칸을 모두 채워주세요.")
            if re.search(forbidden_chars, val):
                raise ValueError(f"'{val}'에는 사용할 수 없는 특수기호가 포함되어 있습니다.")
            kwargs[var_name] = val

        return self.rule_engine.generate_path("character_folder", **kwargs)

    def preview_path(self):
        try:
            path = self.get_generated_path()
            path = path.replace("\\", "/") 
            self.result_label.setText(f"<b>[미리보기]</b><br><br><span style='color:blue;'>{path}</span>")
            self.result_label.setStyleSheet("padding: 15px; border: 1px dashed blue; background-color: #f0f8ff; font-size: 14px;")
            return path
        except ValueError as e:
            self.result_label.setText(f"❌ <b>경고:</b> {str(e)}")
            self.result_label.setStyleSheet("padding: 15px; border: 1px solid red; background-color: #ffe6e6; color: red;")
            return None
        except Exception as e:
            self.result_label.setText(f"❌ 시스템 오류: {str(e)}")
            return None

    def create_folder(self):
        path = self.preview_path()
        if not path: return 
        
        root_dir = Path(self.config.get("paths", "root_path"))
        target_dir = Path(path)
        
        # 프리셋 파서에서 최신 서브 폴더 목록 가져오기
        parser = PresetParser(self.config)
        preset_data = parser.get_preset_data()
        sub_folders = preset_data.get("sub_folders", [])

        try:
            # 🔥 일괄 생성 (배치 모드) 작동
            if self.batch_checkbox.isChecked():
                # 기준이 될 상대 경로 추출 (예: D:/Root/A/B -> A/B)
                if not target_dir.is_relative_to(root_dir):
                    raise ValueError("배치 모드를 사용하려면 생성 경로가 루트 폴더 하위에 있어야 합니다.")
                
                rel_path = target_dir.relative_to(root_dir)
                
                # 루트 디렉토리 안에 있는 모든 하위 폴더 검색 (숨김 폴더 제외)
                root_subdirs = [d for d in root_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
                
                if not root_subdirs:
                    QMessageBox.warning(self, "알림", "루트 폴더 하위에 기준이 될 기존 폴더가 하나도 없습니다.")
                    return

                created_count = 0
                for base_dir in root_subdirs:
                    # 각 하위 폴더에 상대 경로를 결합하여 최종 목적지 생성
                    batch_target = base_dir / rel_path
                    batch_target.mkdir(parents=True, exist_ok=True)
                    
                    # 서브 폴더 생성
                    for sub in sub_folders:
                        (batch_target / sub).mkdir(exist_ok=True)
                    created_count += 1
                
                QMessageBox.information(self, "일괄 생성 완료", f"총 {created_count}개의 폴더에 성공적으로 일괄 생성(및 서브 폴더 적용) 되었습니다!")
            
            # 🟢 단일 생성 (일반 모드) 작동
            else:
                if target_dir.exists():
                    QMessageBox.warning(self, "알림", "이미 존재하는 폴더입니다.\n\n경로: " + path)
                    return
                    
                target_dir.mkdir(parents=True, exist_ok=True)
                for sub in sub_folders:
                    (target_dir / sub).mkdir(exist_ok=True)
                
                msg = f"폴더가 성공적으로 생성되었습니다!\n\n경로: {path}"
                if sub_folders:
                    msg += f"\n\n적용된 프리셋 하위 폴더 ({len(sub_folders)}개):\n" + ", ".join(sub_folders)
                QMessageBox.information(self, "성공", msg)
            
            # 생성 후 UI 비우기
            for widget in self.dynamic_inputs.values():
                widget.clear()
                
        except PermissionError:
            QMessageBox.critical(self, "권한 오류", "해당 경로에 폴더를 생성할 권한이 없습니다.")
        except Exception as e:
            QMessageBox.critical(self, "실패", f"폴더 생성 중 오류가 발생했습니다.\n{str(e)}")
    def check_for_updates(self):
        self.updater_thread = UpdateChecker()
        self.updater_thread.update_available.connect(self.prompt_update)
        self.updater_thread.start()

    @Slot(str, str, str)
    def prompt_update(self, version, notes, download_url):
        # 업데이트 팝업 띄우기
        reply = QMessageBox.question(
            self, 
            "새 업데이트 가능!", 
            f"새로운 버전(v{version})이 출시되었습니다.\n지금 업데이트 하시겠습니까?\n\n[업데이트 내용]\n{notes}",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.start_download(download_url)

    def start_download(self, download_url):
        # 다운로드 중 화면 조작 방지 및 안내 띄우기
        self.setEnabled(False)
        self.setWindowTitle("다운로드 및 업데이트 중... 앱을 끄지 마세요.")
        
        self.download_thread = UpdateDownloader(download_url)
        self.download_thread.finished.connect(self.on_update_finished)
        self.download_thread.start()

    @Slot(bool, str)
    def on_update_finished(self, success, message):
        if success:
            QMessageBox.information(self, "업데이트 완료", message)
            import sys
            sys.exit(0) # 앱 강제 종료 (유저가 다시 켜면 신버전 적용됨)
        else:
            QMessageBox.critical(self, "업데이트 실패", message)
            self.setEnabled(True)
            self.setWindowTitle(f"TaskHub - Workspace Manager (v{CURRENT_VERSION})")

    @Slot()
    def on_config_changed(self):
        self.build_folder_creator_ui()
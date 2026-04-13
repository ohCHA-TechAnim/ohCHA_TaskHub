import json
import shutil
from pathlib import Path
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QLineEdit, 
                               QFileDialog, QMessageBox, QTabWidget,
                               QWidget, QListWidget, QTableWidget,
                               QTableWidgetItem, QHeaderView, QInputDialog)

class SettingsDialog(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.setWindowTitle("환경 설정 및 프리셋 관리")
        self.setFixedSize(600, 400)
        self.setup_ui()
        # 창이 켜질 때 현재 설정된 JSON을 읽어서 UI에 채워넣음
        self.load_preset_to_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # 탭 위젯 생성
        self.tabs = QTabWidget()
        self.tab_general = QWidget()
        self.tab_subfolders = QWidget()
        self.tab_shortcuts = QWidget()
        
        self.tabs.addTab(self.tab_general, "기본 설정")
        self.tabs.addTab(self.tab_subfolders, "서브 폴더 관리")
        self.tabs.addTab(self.tab_shortcuts, "숏컷(단축어) 매핑")
        
        self.setup_general_tab()
        self.setup_subfolders_tab()
        self.setup_shortcuts_tab()
        
        main_layout.addWidget(self.tabs)

        # 하단 버튼 영역
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("저장 후 닫기")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 5px 15px;")
        save_btn.clicked.connect(self.save_settings)
        
        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        main_layout.addLayout(btn_layout)

    def setup_general_tab(self):
        layout = QVBoxLayout(self.tab_general)
        
        # 루트, 룰, 프리셋 UI (기존과 동일하되 레이아웃만 맞춤)
        root_layout = QHBoxLayout()
        self.root_input = QLineEdit(self.config.get("paths", "root_path"))
        root_btn = QPushButton("폴더 찾기")
        root_btn.clicked.connect(self.browse_root)
        root_layout.addWidget(self.root_input)
        root_layout.addWidget(root_btn)
        
        self.rule_input = QLineEdit(self.config.get("rules", "character_folder"))
        
        preset_layout = QHBoxLayout()
        self.preset_input = QLineEdit(self.config.get("paths", "preset_txt_path"))
        preset_browse_btn = QPushButton("불러오기")
        preset_browse_btn.clicked.connect(self.browse_preset)
        preset_saveas_btn = QPushButton("새 프리셋으로 저장")
        preset_saveas_btn.setStyleSheet("background-color: #2b5797; color: white;")
        preset_saveas_btn.clicked.connect(self.save_as_preset)
        
        preset_layout.addWidget(self.preset_input)
        preset_layout.addWidget(preset_browse_btn)
        preset_layout.addWidget(preset_saveas_btn)

        layout.addWidget(QLabel("<b>1. 메인 작업 루트 폴더</b>"))
        layout.addLayout(root_layout)
        layout.addWidget(QLabel("<b>2. 폴더 생성 규칙 (변수를 { } 로 감싸세요)</b>"))
        layout.addWidget(self.rule_input)
        layout.addWidget(QLabel("<b>3. 연결된 프리셋 파일 (JSON)</b>"))
        layout.addLayout(preset_layout)
        layout.addStretch()

    def setup_subfolders_tab(self):
        layout = QVBoxLayout(self.tab_subfolders)
        layout.addWidget(QLabel("규칙에 의해 생성된 메인 폴더 안에 들어갈 <b>하위 폴더 목록</b>입니다.\n비워두면 하위 폴더를 생성하지 않습니다."))
        
        self.subfolder_list = QListWidget()
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("폴더 추가")
        add_btn.clicked.connect(self.add_subfolder)
        del_btn = QPushButton("선택 삭제")
        del_btn.clicked.connect(self.del_subfolder)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addStretch()
        
        layout.addWidget(self.subfolder_list)
        layout.addLayout(btn_layout)

    def setup_shortcuts_tab(self):
        layout = QVBoxLayout(self.tab_shortcuts)
        layout.addWidget(QLabel("입력칸에 <b>'입력값'</b>을 적으면 자동으로 <b>'변환값'</b>으로 교체되어 폴더가 생성됩니다.\n(예: 바나나 -> 001, 사과 -> 002)"))
        
        self.shortcut_table = QTableWidget(0, 2)
        self.shortcut_table.setHorizontalHeaderLabels(["입력값 (예: 바나나)", "변환값 (예: 001)"])
        self.shortcut_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("단축어 추가")
        add_btn.clicked.connect(self.add_shortcut)
        del_btn = QPushButton("선택 삭제")
        del_btn.clicked.connect(self.del_shortcut)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addStretch()
        
        layout.addWidget(self.shortcut_table)
        layout.addLayout(btn_layout)

    # --- UI Action Methods ---
    def browse_root(self):
        folder = QFileDialog.getExistingDirectory(self, "루트 폴더 선택")
        if folder: self.root_input.setText(folder)

    def browse_preset(self):
        start_dir = self.preset_input.text().strip() or str(Path.home())
        file, _ = QFileDialog.getOpenFileName(self, "프리셋 파일 불러오기", start_dir, "JSON Files (*.json)")
        if file: 
            self.preset_input.setText(file)
            self.load_preset_to_ui()

    def add_subfolder(self):
        text, ok = QInputDialog.getText(self, "서브 폴더 추가", "생성할 하위 폴더 이름을 입력하세요:")
        if ok and text.strip():
            self.subfolder_list.addItem(text.strip())

    def del_subfolder(self):
        for item in self.subfolder_list.selectedItems():
            self.subfolder_list.takeItem(self.subfolder_list.row(item))

    def add_shortcut(self):
        row = self.shortcut_table.rowCount()
        self.shortcut_table.insertRow(row)
        self.shortcut_table.setItem(row, 0, QTableWidgetItem("입력값"))
        self.shortcut_table.setItem(row, 1, QTableWidgetItem("변환값"))

    def del_shortcut(self):
        current_row = self.shortcut_table.currentRow()
        if current_row >= 0:
            self.shortcut_table.removeRow(current_row)

    # --- Data Processing Methods ---
    def load_preset_to_ui(self):
        """JSON 파일을 읽어서 3개의 탭 UI에 데이터를 채워넣습니다."""
        preset_path = self.preset_input.text().strip()
        if not preset_path or not preset_path.endswith(".json") or not Path(preset_path).exists():
            return

        try:
            with open(preset_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # 1. 룰 세팅
                if "rule" in data:
                    self.rule_input.setText(data["rule"])
                
                # 2. 서브 폴더 세팅
                self.subfolder_list.clear()
                self.subfolder_list.addItems(data.get("sub_folders", []))
                
                # 3. 숏컷 세팅
                self.shortcut_table.setRowCount(0)
                for key, val in data.get("shortcuts", {}).items():
                    row = self.shortcut_table.rowCount()
                    self.shortcut_table.insertRow(row)
                    self.shortcut_table.setItem(row, 0, QTableWidgetItem(key))
                    self.shortcut_table.setItem(row, 1, QTableWidgetItem(val))
        except Exception as e:
            QMessageBox.warning(self, "경고", f"JSON을 읽는 중 오류가 발생했습니다.\n{e}")

    def gather_data_from_ui(self):
        """UI에 입력된 데이터들을 모아서 JSON 구조(Dict)로 만듭니다."""
        # 서브 폴더 목록 수집
        sub_folders = [self.subfolder_list.item(i).text() for i in range(self.subfolder_list.count())]
        
        # 숏컷 목록 수집
        shortcuts = {}
        for row in range(self.shortcut_table.rowCount()):
            key_item = self.shortcut_table.item(row, 0)
            val_item = self.shortcut_table.item(row, 1)
            if key_item and val_item and key_item.text().strip():
                shortcuts[key_item.text().strip()] = val_item.text().strip()

        return {
            "rule": self.rule_input.text().strip(),
            "sub_folders": sub_folders,
            "shortcuts": shortcuts
        }

    def save_as_preset(self):
        file, _ = QFileDialog.getSaveFileName(self, "새 프리셋 저장", "new_preset.json", "JSON Files (*.json)")
        if not file: return

        data = self.gather_data_from_ui()
        try:
            with open(file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            self.preset_input.setText(file)
            QMessageBox.information(self, "성공", "새 프리셋 파일이 생성되었습니다.")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"저장 중 오류가 발생했습니다.\n{e}")

    def save_settings(self):
        if not self.root_input.text():
            QMessageBox.warning(self, "경고", "루트 경로는 비워둘 수 없습니다.")
            return

        # 🔥 1. UI의 변경사항을 현재 연결된 JSON 파일에 바로 덮어쓰기 저장!
        preset_path = self.preset_input.text().strip()
        if preset_path and preset_path.endswith(".json"):
            data = self.gather_data_from_ui()
            try:
                with open(preset_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
            except Exception as e:
                QMessageBox.warning(self, "경고", f"JSON 파일 덮어쓰기 실패.\n{e}")

        # 🔥 2. 메인 앱 설정(Config) 업데이트
        self.config.update("paths", "root_path", self.root_input.text())
        self.config.update("paths", "preset_txt_path", preset_path)
        self.config.update("rules", "character_folder", self.rule_input.text())
        self.config.save()
        self.accept()
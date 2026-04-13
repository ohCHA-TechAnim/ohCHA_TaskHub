import json
import string
from pathlib import Path
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QLineEdit, 
                               QFileDialog, QMessageBox, QTabWidget,
                               QWidget, QListWidget, QTableWidget,
                               QTableWidgetItem, QHeaderView, QInputDialog, QComboBox)

class SettingsDialog(QDialog):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.setWindowTitle("환경 설정 및 프리셋 관리")
        self.setFixedSize(650, 450)
        self.setup_ui()
        self.load_preset_to_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        
        self.tab_general = QWidget()
        self.tab_subfolders = QWidget()
        self.tab_shortcuts = QWidget()
        self.tab_variables = QWidget()
        
        self.tabs.addTab(self.tab_general, "기본 설정")
        self.tabs.addTab(self.tab_subfolders, "서브 폴더")
        self.tabs.addTab(self.tab_shortcuts, "단축어 맵핑")
        self.tabs.addTab(self.tab_variables, "변수 규격화(Dropdown)")
        
        self.setup_general_tab()
        self.setup_subfolders_tab()
        self.setup_shortcuts_tab()
        self.setup_variables_tab()
        
        main_layout.addWidget(self.tabs)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("저장 후 닫기")
        save_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        main_layout.addLayout(btn_layout)

    # (general, subfolders, variables는 이전 답변과 100% 동일)
    def setup_general_tab(self):
        layout = QVBoxLayout(self.tab_general)
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
        preset_saveas_btn = QPushButton("새 프리셋 저장")
        preset_saveas_btn.clicked.connect(self.save_as_preset)
        preset_layout.addWidget(self.preset_input)
        preset_layout.addWidget(preset_browse_btn)
        preset_layout.addWidget(preset_saveas_btn)
        layout.addWidget(QLabel("<b>1. 메인 작업 루트 폴더</b>"))
        layout.addLayout(root_layout)
        layout.addWidget(QLabel("<b>2. 폴더 생성 규칙 (예: /{캐릭터}/{타입})</b>"))
        layout.addWidget(self.rule_input)
        layout.addWidget(QLabel("<b>3. 연결된 프리셋 파일 (JSON)</b>"))
        layout.addLayout(preset_layout)
        layout.addStretch()

    def setup_subfolders_tab(self):
        layout = QVBoxLayout(self.tab_subfolders)
        self.subfolder_list = QListWidget()
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("추가")
        add_btn.clicked.connect(self.add_subfolder)
        del_btn = QPushButton("삭제")
        del_btn.clicked.connect(self.del_subfolder)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        layout.addWidget(self.subfolder_list)
        layout.addLayout(btn_layout)

    def setup_variables_tab(self):
        layout = QVBoxLayout(self.tab_variables)
        layout.addWidget(QLabel("숫자 범위는 물결(~)을 사용하세요! (예: 000~999)\n자동으로 000부터 999까지 목록을 생성해 줍니다."))
        self.variable_table = QTableWidget(0, 2)
        self.variable_table.setHorizontalHeaderLabels(["변수명", "옵션 (쉼표 구분)"])
        self.variable_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("규칙 추가")
        add_btn.clicked.connect(self.add_variable_rule)
        del_btn = QPushButton("선택 삭제")
        del_btn.clicked.connect(self.del_variable_rule)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        layout.addWidget(self.variable_table)
        layout.addLayout(btn_layout)

    # 🔥 숏컷 탭: 3칸(적용 변수, 텍스트, 기계값)으로 변경!
    def setup_shortcuts_tab(self):
        layout = QVBoxLayout(self.tab_shortcuts)
        layout.addWidget(QLabel("<b>적용될 변수</b>를 선택하고 단축어를 지정하세요.\n이제 스킨넘버 001과 캐릭터 001이 헷갈리지 않습니다!"))
        
        self.shortcut_table = QTableWidget(0, 3)
        self.shortcut_table.setHorizontalHeaderLabels(["적용 변수", "입력값 (예: 레픽)", "기계값 (예: 001)"])
        self.shortcut_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("추가")
        add_btn.clicked.connect(self.add_shortcut)
        del_btn = QPushButton("삭제")
        del_btn.clicked.connect(self.del_shortcut)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        layout.addWidget(self.shortcut_table)
        layout.addLayout(btn_layout)

    # --- Actions ---
    def browse_root(self):
        folder = QFileDialog.getExistingDirectory(self, "루트 선택")
        if folder: self.root_input.setText(folder)
    def browse_preset(self):
        start_dir = self.preset_input.text().strip() or str(Path.home())
        file, _ = QFileDialog.getOpenFileName(self, "불러오기", start_dir, "JSON Files (*.json)")
        if file: 
            self.preset_input.setText(file)
            self.load_preset_to_ui()

    def add_subfolder(self):
        text, ok = QInputDialog.getText(self, "추가", "이름:")
        if ok and text.strip(): self.subfolder_list.addItem(text.strip())
    def del_subfolder(self):
        for item in self.subfolder_list.selectedItems(): self.subfolder_list.takeItem(self.subfolder_list.row(item))

    # 🔥 숏컷 추가 시 콤보박스(변수 선택) 렌더링
    def add_shortcut(self, var_name=None, human="", machine=""):
        r = self.shortcut_table.rowCount()
        self.shortcut_table.insertRow(r)
        
        # 현재 작성된 룰에서 변수들 뽑아오기
        rule_text = self.rule_input.text()
        vars = [v for _, v, _, _ in string.Formatter().parse(rule_text) if v and v != "root"]
        
        combo = QComboBox()
        combo.addItems(vars)
        if var_name in vars: combo.setCurrentText(var_name)
        
        self.shortcut_table.setCellWidget(r, 0, combo)
        self.shortcut_table.setItem(r, 1, QTableWidgetItem(human))
        self.shortcut_table.setItem(r, 2, QTableWidgetItem(machine))
        
    def del_shortcut(self):
        r = self.shortcut_table.currentRow()
        if r >= 0: self.shortcut_table.removeRow(r)

    def add_variable_rule(self):
        r = self.variable_table.rowCount()
        self.variable_table.insertRow(r)
        self.variable_table.setItem(r, 0, QTableWidgetItem("변수명"))
        self.variable_table.setItem(r, 1, QTableWidgetItem("000~999"))
    def del_variable_rule(self):
        r = self.variable_table.currentRow()
        if r >= 0: self.variable_table.removeRow(r)

    # --- Data Processing ---
    def load_preset_to_ui(self):
        preset_path = self.preset_input.text().strip()
        if not preset_path or not Path(preset_path).exists(): return
        try:
            with open(preset_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "rule" in data: self.rule_input.setText(data["rule"])
                
                self.subfolder_list.clear()
                self.subfolder_list.addItems(data.get("sub_folders", []))
                
                # 🔥 변수종속형 숏컷 불러오기
                self.shortcut_table.setRowCount(0)
                shortcuts_data = data.get("shortcuts", {})
                for var_name, mapping in shortcuts_data.items():
                    for human, machine in mapping.items():
                        self.add_shortcut(var_name, human, machine)
                    
                self.variable_table.setRowCount(0)
                for k, v_list in data.get("variable_rules", {}).items():
                    r = self.variable_table.rowCount()
                    self.variable_table.insertRow(r)
                    self.variable_table.setItem(r, 0, QTableWidgetItem(k))
                    self.variable_table.setItem(r, 1, QTableWidgetItem(", ".join(v_list)))
        except Exception: pass

    def gather_data_from_ui(self):
        sub_folders = [self.subfolder_list.item(i).text() for i in range(self.subfolder_list.count())]
        
        # 🔥 UI 3칸 테이블 -> {"캐릭터": {"에시모": "012"}} 형태로 변환
        shortcuts = {}
        for r in range(self.shortcut_table.rowCount()):
            combo = self.shortcut_table.cellWidget(r, 0)
            human_item = self.shortcut_table.item(r, 1)
            machine_item = self.shortcut_table.item(r, 2)
            if combo and human_item and machine_item:
                var_name = combo.currentText()
                human = human_item.text().strip()
                machine = machine_item.text().strip()
                if var_name and human:
                    if var_name not in shortcuts: shortcuts[var_name] = {}
                    shortcuts[var_name][human] = machine
            
        variable_rules = {}
        for r in range(self.variable_table.rowCount()):
            k, v = self.variable_table.item(r, 0), self.variable_table.item(r, 1)
            if k and v and k.text().strip(): 
                variable_rules[k.text().strip()] = [opt.strip() for opt in v.text().split(",") if opt.strip()]

        return {
            "rule": self.rule_input.text().strip(),
            "sub_folders": sub_folders,
            "shortcuts": shortcuts,
            "variable_rules": variable_rules
        }

    def save_as_preset(self):
        file, _ = QFileDialog.getSaveFileName(self, "저장", "new_preset.json", "JSON Files (*.json)")
        if not file: return
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(self.gather_data_from_ui(), f, indent=4, ensure_ascii=False)
        self.preset_input.setText(file)

    def save_settings(self):
        preset_path = self.preset_input.text().strip()
        if preset_path and preset_path.endswith(".json"):
            with open(preset_path, 'w', encoding='utf-8') as f:
                json.dump(self.gather_data_from_ui(), f, indent=4, ensure_ascii=False)

        self.config.update("paths", "root_path", self.root_input.text())
        self.config.update("paths", "preset_txt_path", preset_path)
        self.config.update("rules", "character_folder", self.rule_input.text())
        self.config.save()
        self.accept()
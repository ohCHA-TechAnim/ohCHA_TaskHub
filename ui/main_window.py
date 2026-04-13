import re
import os
from pathlib import Path
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, QSplitter, 
                               QListWidget, QStackedWidget, QMessageBox, QCheckBox,
                               QListWidgetItem, QComboBox, QMenu, QDialog, QTreeWidget, QTreeWidgetItem)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QDesktopServices, QAction
from PySide6.QtCore import QUrl

from ui.settings_dialog import SettingsDialog
from core.preset_parser import PresetParser
from core.database import Database
from core.search_engine import SearchWorker 

class FolderDetailsDialog(QDialog):
    """🔥 자세히 보기 팝업 창 (OS 폴더 내용 스캔)"""
    def __init__(self, folder_path, parent=None):
        super().__init__(parent)
        self.folder_path = Path(folder_path)
        self.setWindowTitle(f"폴더 상세 정보 - {self.folder_path.name}")
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<b>경로:</b> {self.folder_path}"))
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["이름", "종류"])
        self.tree.setColumnWidth(0, 400)
        layout.addWidget(self.tree)
        
        self.load_contents()

    def load_contents(self):
        if not self.folder_path.exists(): return
        
        folders = QTreeWidgetItem(self.tree, ["📁 하위 폴더", "Folder"])
        images = QTreeWidgetItem(self.tree, ["🖼️ 이미지", "Image"])
        videos = QTreeWidgetItem(self.tree, ["🎬 영상", "Video"])
        files = QTreeWidgetItem(self.tree, ["📄 기타 파일", "File"])
        
        img_ext = {'.png', '.jpg', '.jpeg', '.tga', '.exr'}
        vid_ext = {'.mp4', '.mov', '.avi'}
        
        try:
            for item in self.folder_path.iterdir():
                if item.is_dir():
                    QTreeWidgetItem(folders, [item.name, "Folder"])
                else:
                    ext = item.suffix.lower()
                    if ext in img_ext: QTreeWidgetItem(images, [item.name, "Image"])
                    elif ext in vid_ext: QTreeWidgetItem(videos, [item.name, "Video"])
                    else: QTreeWidgetItem(files, [item.name, "File"])
        except Exception:
            pass
            
        self.tree.expandAll()

class MainWindow(QMainWindow):
    def __init__(self, config_manager, rule_engine):
        super().__init__()
        self.config = config_manager
        self.rule_engine = rule_engine
        self.db = Database()
        self.dynamic_inputs = {}
        self.search_worker = None
        self.config.config_changed.connect(self.on_config_changed)
        self.setWindowTitle("TaskHub - Workspace Manager")
        self.resize(1100, 750)
        self.setup_ui()

    def setup_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        self.setCentralWidget(main_widget)

        top_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 파일, 태그, 작업 로그 통합 검색...")
        settings_btn = QPushButton("⚙️ 환경 설정")
        settings_btn.clicked.connect(self.open_settings)
        top_layout.addWidget(self.search_bar)
        top_layout.addWidget(settings_btn)
        main_layout.addLayout(top_layout)

        splitter = QSplitter(Qt.Horizontal)
        self.sidebar = QListWidget()
        self.sidebar.addItems(["📂 폴더 생성기", "⭐ 폴더 즐겨찾기", "🧾 작업 로그", "📊 대시보드"])
        self.sidebar.setMaximumWidth(220)
        self.sidebar.currentRowChanged.connect(self.change_page)
        
        self.content_stack = QStackedWidget()
        self.folder_creator_widget = QWidget()
        self.folder_creator_layout = QVBoxLayout(self.folder_creator_widget)
        self.build_folder_creator_ui()
        self.content_stack.addWidget(self.folder_creator_widget)
        
        self.favorites_widget = self.build_favorites_ui()
        self.content_stack.addWidget(self.favorites_widget)
        
        self.content_stack.addWidget(QLabel("<h2 align='center'>작업 로그 (준비 중)</h2>"))
        self.content_stack.addWidget(QLabel("<h2 align='center'>대시보드 (준비 중)</h2>"))

        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.content_stack)
        splitter.setSizes([200, 900]) 
        main_layout.addWidget(splitter)
        self.sidebar.setCurrentRow(0)

    # --- 즐겨찾기 UI ---
    def build_favorites_ui(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("<h2>⭐ 내 작업 폴더 즐겨찾기</h2>"))

        scan_layout = QHBoxLayout()
        self.scan_filter_input = QLineEdit()
        self.scan_filter_input.setPlaceholderText("검색어 입력 (예: 031, 에시모) 후 엔터")
        self.scan_filter_input.returnPressed.connect(self.toggle_scan)
        self.scan_btn = QPushButton("🔍 딥 스캔 시작")
        self.scan_btn.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold;")
        self.scan_btn.clicked.connect(self.toggle_scan)
        scan_layout.addWidget(self.scan_filter_input)
        scan_layout.addWidget(self.scan_btn)
        
        layout.addLayout(scan_layout)
        self.scan_result_list = QListWidget()
        self.scan_result_list.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(self.scan_result_list)

        add_fav_btn = QPushButton("👇 선택한 항목을 내 즐겨찾기에 추가 👇")
        add_fav_btn.setStyleSheet("background-color: #2b5797; color: white; padding: 5px;")
        add_fav_btn.clicked.connect(self.add_selected_to_favorites)
        layout.addWidget(add_fav_btn)

        layout.addSpacing(10)
        layout.addWidget(QLabel("<b>[2단계] 내 즐겨찾기 (우클릭하여 메뉴 보기 / 더블클릭 열기)</b>"))
        
        self.favorites_list = QListWidget()
        self.favorites_list.setStyleSheet("font-size: 14px; padding: 5px;")
        self.favorites_list.itemDoubleClicked.connect(self.open_favorite_folder)
        
        # 🔥 우클릭 컨텍스트 메뉴 허용
        self.favorites_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.favorites_list.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.favorites_list)

        del_fav_btn = QPushButton("선택한 즐겨찾기 삭제")
        del_fav_btn.clicked.connect(self.delete_favorite)
        layout.addWidget(del_fav_btn)

        self.refresh_favorites_list()
        return widget

    # 🔥 우클릭 메뉴 구현
    def show_context_menu(self, pos):
        item = self.favorites_list.itemAt(pos)
        if not item: return

        menu = QMenu()
        open_act = QAction("📂 폴더 열기 (Explorer)", self)
        open_act.triggered.connect(lambda: self.open_favorite_folder(item))
        
        detail_act = QAction("🔍 자세히 보기 (팝업)", self)
        detail_act.triggered.connect(lambda: self.show_folder_details(item))

        menu.addAction(open_act)
        menu.addAction(detail_act)
        menu.exec(self.favorites_list.mapToGlobal(pos))

    def show_folder_details(self, item):
        folder_path = item.data(Qt.UserRole)
        dialog = FolderDetailsDialog(folder_path, self)
        dialog.exec()

    # --- 스캔 엔진 ---
    def toggle_scan(self):
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.cancel()
            self.scan_btn.setText("🔍 딥 스캔 시작")
            self.scan_btn.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold;")
        else:
            self.start_deep_scan()

    def start_deep_scan(self):
        root_path = self.config.get("paths", "root_path")
        filter_text = self.scan_filter_input.text().strip()
        if not filter_text: return QMessageBox.warning(self, "안내", "검색할 키워드를 입력해 주세요.")

        self.scan_result_list.clear()
        self.scan_btn.setText("🛑 검색 중지")
        self.scan_btn.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold;")

        preset_data = PresetParser(self.config).get_preset_data()
        shortcuts = preset_data.get("shortcuts", {}) # {"캐릭터": {"에시모": "012"}}
        
        # 🔥 규칙 템플릿에서 실제 순서대로 변수명 목록 추출 (root 제외)
        variables = [v for v in self.rule_engine.extract_variables("character_folder") if v != "root"]

        # 엔진에 variables까지 같이 넘겨줌
        self.search_worker = SearchWorker(root_path, filter_text, shortcuts, variables)
        self.search_worker.result_found.connect(self.on_scan_result_found)
        self.search_worker.finished.connect(self.on_scan_finished)
        self.search_worker.error.connect(self.on_scan_error)
        self.search_worker.start()

    @Slot(str, str)
    def on_scan_result_found(self, real_path, display_name):
        item = QListWidgetItem(f"📁 {display_name}")
        item.setData(Qt.UserRole, real_path)
        self.scan_result_list.addItem(item)

    @Slot(int)
    def on_scan_finished(self, count):
        self.scan_btn.setText("🔍 딥 스캔 시작")
        self.scan_btn.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold;")

    @Slot(str)
    def on_scan_error(self, error_msg):
        self.scan_btn.setText("🔍 딥 스캔 시작")
        self.scan_btn.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold;")

    def add_selected_to_favorites(self):
        for item in self.scan_result_list.selectedItems():
            self.db.add_favorite(item.text(), item.data(Qt.UserRole))
        self.refresh_favorites_list()

    def refresh_favorites_list(self):
        self.favorites_list.clear()
        for display_name, folder_path in self.db.get_all_favorites():
            item = QListWidgetItem(display_name)
            item.setData(Qt.UserRole, folder_path)
            self.favorites_list.addItem(item)

    def open_favorite_folder(self, item):
        folder_path = item.data(Qt.UserRole)
        if Path(folder_path).exists(): QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))

    def delete_favorite(self):
        for item in self.favorites_list.selectedItems():
            self.db.delete_favorite(item.data(Qt.UserRole))
        self.refresh_favorites_list()

    # --- 폴더 생성기 UI (🔥🔥 변수 규격화 적용) ---
    def build_folder_creator_ui(self):
        while self.folder_creator_layout.count():
            item = self.folder_creator_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            elif item.layout(): self.clear_layout(item.layout())

        self.dynamic_inputs.clear()
        self.folder_creator_layout.addWidget(QLabel("<h2>🎯 룰 엔진 기반 폴더 생성기</h2>"))
        
        template = self.config.get("rules", "character_folder")
        root = self.config.get("paths", "root_path")
        self.folder_creator_layout.addWidget(QLabel(f"적용된 루트: <b>{root}</b><br>현재 규칙: <b>{template}</b>"))

        input_layout = QHBoxLayout()
        variables = self.rule_engine.extract_variables("character_folder")
        
        preset_data = PresetParser(self.config).get_preset_data()
        variable_rules = preset_data.get("variable_rules", {})
        
        for var in variables:
            if var == "root": continue
            input_layout.addWidget(QLabel(f"<b>{var}:</b>"))
            
            if var in variable_rules and variable_rules[var]:
                combo = QComboBox()
                
                # 🔥 [마법의 로직] 물결(~) 기호를 감지하여 숫자 범위를 자동 팽창시킴!
                expanded_options = []
                for opt in variable_rules[var]:
                    if "~" in opt:
                        try:
                            start_str, end_str = opt.split("~")
                            width = len(start_str.strip()) # 001이면 3자리 유지
                            start, end = int(start_str), int(end_str)
                            for n in range(start, end + 1):
                                expanded_options.append(str(n).zfill(width))
                        except Exception:
                            expanded_options.append(opt) # 변환 실패 시 그냥 원본 추가
                    else:
                        expanded_options.append(opt)

                combo.addItems(expanded_options)
                combo.currentTextChanged.connect(self.preview_path)
                input_layout.addWidget(combo)
                self.dynamic_inputs[var] = combo 
            else:
                line_edit = QLineEdit()
                line_edit.setPlaceholderText(f"{var} 입력...")
                line_edit.textChanged.connect(self.preview_path)
                input_layout.addWidget(line_edit)
                self.dynamic_inputs[var] = line_edit

        self.folder_creator_layout.addLayout(input_layout)
        self.batch_checkbox = QCheckBox("🚀 루트 하위의 모든 기존 폴더에 일괄 생성 적용 (배치 모드)")
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
            if item.widget(): item.widget().deleteLater()
            elif item.layout(): self.clear_layout(item.layout())
        layout.deleteLater()

    def change_page(self, index): self.content_stack.setCurrentIndex(index)
    def open_settings(self): SettingsDialog(self.config, self).exec()

    def get_generated_path(self):
        kwargs = {}
        for var_name, widget in self.dynamic_inputs.items():
            # 🔥 QComboBox인지 QLineEdit인지에 따라 값 추출 방식 분기
            if isinstance(widget, QComboBox): val = widget.currentText().strip()
            else: val = widget.text().strip()
            
            if not val: raise ValueError("입력칸을 모두 채워주세요.")
            if re.search(r'[<>:"/\\|?*]', val): raise ValueError(f"'{val}'에 특수기호가 포함되어 있습니다.")
            kwargs[var_name] = val
        return self.rule_engine.generate_path("character_folder", **kwargs)

    def preview_path(self):
        try:
            path = self.get_generated_path().replace("\\", "/")
            self.result_label.setText(f"<b>[미리보기]</b><br><br><span style='color:blue;'>{path}</span>")
            return path
        except Exception as e:
            self.result_label.setText(f"❌ {str(e)}")
            return None

    def create_folder(self):
        path = self.preview_path()
        if not path: return 
        root_dir = Path(self.config.get("paths", "root_path"))
        target_dir = Path(path)
        sub_folders = PresetParser(self.config).get_preset_data().get("sub_folders", [])

        try:
            if self.batch_checkbox.isChecked():
                rel_path = target_dir.relative_to(root_dir)
                root_subdirs = [d for d in root_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
                for base_dir in root_subdirs:
                    batch_target = base_dir / rel_path
                    batch_target.mkdir(parents=True, exist_ok=True)
                    for sub in sub_folders: (batch_target / sub).mkdir(exist_ok=True)
                QMessageBox.information(self, "완료", "일괄 생성 되었습니다!")
            else:
                target_dir.mkdir(parents=True, exist_ok=True)
                for sub in sub_folders: (target_dir / sub).mkdir(exist_ok=True)
                QMessageBox.information(self, "성공", "폴더가 성공적으로 생성되었습니다!")
                
        except Exception as e: QMessageBox.critical(self, "실패", f"오류 발생: {str(e)}")

    @Slot()
    def on_config_changed(self): self.build_folder_creator_ui()
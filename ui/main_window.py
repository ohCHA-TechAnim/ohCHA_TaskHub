import re
import os
import shutil
import time
from pathlib import Path
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QLineEdit, QPushButton, QSplitter, 
                               QListWidget, QStackedWidget, QMessageBox, QCheckBox,
                               QListWidgetItem, QComboBox, QMenu, QDialog, QTreeWidget, 
                               QTreeWidgetItem, QGroupBox, QFileDialog, QAbstractItemView, QScrollArea, QTextEdit, QSizePolicy, QGridLayout, QInputDialog)
from PySide6.QtCore import Qt, Slot, QUrl, QSize
from PySide6.QtGui import QDesktopServices, QAction, QTextDocument, QGuiApplication, QIcon

from ui.settings_dialog import SettingsDialog
from core.preset_parser import PresetParser
from core.database import Database
from core.search_engine import SearchWorker 
from ui.widgets.todo_widget import TodoItemWidget
from core.updater import UpdateChecker, UpdateDownloader, CURRENT_VERSION

# ==========================================
# 🔥 출력창 더블클릭 복사를 위한 특수 텍스트 에디터
# ==========================================
class ResultTextEdit(QTextEdit):
    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        clipboard = QGuiApplication.clipboard()
        mime_data = self.createMimeDataFromSelection()
        if not mime_data: 
            self.selectAll()
            mime_data = self.createMimeDataFromSelection()
            self.moveCursor(self.textCursor().End) 
        
        clipboard.setMimeData(mime_data)
        print("복사 완료!")

# ==========================================
# 🔥 TO-DO 이미지 선택 다이얼로그
# ==========================================
class TodoImageDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.selected_image_path = None
        self.setWindowTitle("TO-DO 작업 사진 불러오기")
        self.resize(600, 500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("메시지에 삽입할 TO-DO 이미지를 더블클릭 하세요."))
        
        self.img_list = QListWidget()
        self.img_list.setViewMode(QListWidget.IconMode)
        self.img_list.setIconSize(QSize(150, 150))
        self.img_list.setResizeMode(QListWidget.Adjust)
        self.img_list.setSpacing(10)
        self.img_list.itemDoubleClicked.connect(self.on_image_selected)
        
        layout.addWidget(self.img_list)
        self.load_images()

    def load_images(self):
        todos = self.db.get_all_todos()
        for todo in todos:
            todo_id, title, details, memo, is_done, order_idx, images_str = todo
            if images_str:
                for img_path in images_str.split("|"):
                    if os.path.exists(img_path):
                        item = QListWidgetItem(QIcon(img_path), f"[{title}]")
                        item.setData(Qt.UserRole, img_path)
                        self.img_list.addItem(item)

    def on_image_selected(self, item):
        self.selected_image_path = item.data(Qt.UserRole)
        self.accept()

# ==========================================
# 🔥 상세정보 팝업 다이얼로그 (3D 필터링 & 파일 실행 기능 추가)
# ==========================================
class FolderDetailsDialog(QDialog):
    def __init__(self, folder_path, parent=None):
        super().__init__(parent)
        self.folder_path = Path(folder_path)
        self.setWindowTitle(f"상세 정보 - {self.folder_path.name}")
        self.resize(700, 500)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<b>경로:</b> {self.folder_path}"))
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["이름", "종류"])
        self.tree.setColumnWidth(0, 500)
        
        # 더블 클릭하면 파일 열기 연결
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        # 우클릭 메뉴 연결
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.tree)
        self.load_contents()

    def load_contents(self):
        if not self.folder_path.exists(): return
        
        folders = QTreeWidgetItem(self.tree, ["📁 하위 폴더", "Folder"])
        assets_3d = QTreeWidgetItem(self.tree, ["🧊 3D 모델 (Max, FBX 등)", "3D Asset"]) # 3D 전용 카테고리
        images = QTreeWidgetItem(self.tree, ["🖼️ 이미지", "Image"])
        videos = QTreeWidgetItem(self.tree, ["🎬 영상", "Video"])
        files = QTreeWidgetItem(self.tree, ["📄 기타 파일", "File"])
        
        img_ext = {'.png', '.jpg', '.jpeg', '.tga', '.exr', '.psd'}
        vid_ext = {'.mp4', '.mov', '.avi'}
        asset_ext = {'.max', '.fbx', '.obj', '.blend', '.ma', '.mb'}
        
        try:
            for item in self.folder_path.iterdir():
                if item.name.startswith('.'): continue
                
                # 경로 저장
                item_path = str(item.resolve())
                
                if item.is_dir(): 
                    tree_item = QTreeWidgetItem(folders, [item.name, "Folder"])
                else:
                    ext = item.suffix.lower()
                    if ext in asset_ext: tree_item = QTreeWidgetItem(assets_3d, [item.name, "3D Asset"])
                    elif ext in img_ext: tree_item = QTreeWidgetItem(images, [item.name, "Image"])
                    elif ext in vid_ext: tree_item = QTreeWidgetItem(videos, [item.name, "Video"])
                    else: tree_item = QTreeWidgetItem(files, [item.name, "File"])
                
                tree_item.setData(0, Qt.UserRole, item_path)
                
        except Exception as e: print(f"폴더 읽기 오류: {e}")
        self.tree.expandAll()

    def on_item_double_clicked(self, item, column):
        file_path = item.data(0, Qt.UserRole)
        if file_path and os.path.exists(file_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))

    def show_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item: return
        file_path = item.data(0, Qt.UserRole)
        if not file_path: return 
        
        menu = QMenu()
        open_act = QAction("🚀 파일/폴더 열기", self)
        open_act.triggered.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(file_path)))
        copy_act = QAction("📋 절대 경로 복사", self)
        copy_act.triggered.connect(lambda: [QGuiApplication.clipboard().setText(file_path), QMessageBox.information(self, "복사 완료", "클립보드에 경로가 복사되었습니다!")])
        
        menu.addAction(open_act)
        menu.addAction(copy_act)
        menu.exec(self.tree.mapToGlobal(pos))


# ==========================================
# 🔥 메인 윈도우 클래스 시작
# ==========================================
class MainWindow(QMainWindow):
    def __init__(self, config_manager, rule_engine):
        super().__init__()
        self.config = config_manager
        self.rule_engine = rule_engine
        self.db = Database()
        self.dynamic_inputs = {}
        self.search_worker = None
        self.config.config_changed.connect(self.on_config_changed)
        
        self.setWindowTitle(f"TaskHub - Workspace Manager (v{CURRENT_VERSION})")
        self.resize(1200, 850)
        self.setup_ui()
        self.check_for_updates()

    def setup_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        self.setCentralWidget(main_widget)

        splitter = QSplitter(Qt.Horizontal)
        self.sidebar = QListWidget()
        self.sidebar.addItems(["⭐ 폴더 허브 (생성 & 검색)", "🧾 TO-DO 체크리스트", "💬 자동 메시지 포매터"])
        self.sidebar.setMaximumWidth(220)
        self.sidebar.currentRowChanged.connect(self.change_page)
        
        self.content_stack = QStackedWidget()
        
        self.content_stack.addWidget(self.build_folder_hub_ui())
        self.content_stack.addWidget(self.build_todo_ui())
        self.content_stack.addWidget(self.build_formatter_ui()) 

        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.content_stack)
        splitter.setSizes([200, 1000]) 
        main_layout.addWidget(splitter)
        self.sidebar.setCurrentRow(0)

    # ------------------------------------------
    # 🔥 1. 폴더 통합 허브 UI 로직
    # ------------------------------------------
    def build_folder_hub_ui(self):
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        container = QWidget()
        layout = QVBoxLayout(container)
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h2>⭐ 폴더 통합 허브</h2>"))
        settings_btn = QPushButton("⚙️ 환경 설정")
        settings_btn.setStyleSheet("background-color: #34495e; color: white; font-weight: bold; padding: 5px;")
        settings_btn.clicked.connect(self.open_settings)
        header_layout.addStretch()
        header_layout.addWidget(settings_btn)
        layout.addLayout(header_layout)

        self.fav_box = QGroupBox("내 작업 폴더 스캔 및 즐겨찾기")
        self.fav_box.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #aaa; border-radius: 5px; margin-top: 10px; padding: 10px; }")
        fav_layout = QVBoxLayout(self.fav_box)
        scan_layout = QHBoxLayout()
        self.scan_filter_input = QLineEdit()
        self.scan_filter_input.setPlaceholderText("검색어 입력 (예: 031, 에시모) 후 엔터")
        self.scan_filter_input.returnPressed.connect(self.toggle_scan)
        self.scan_btn = QPushButton("🔍 딥 스캔 시작")
        self.scan_btn.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold;")
        self.scan_btn.clicked.connect(self.toggle_scan)
        scan_layout.addWidget(self.scan_filter_input)
        scan_layout.addWidget(self.scan_btn)
        fav_layout.addLayout(scan_layout)
        
        self.scan_result_list = QListWidget()
        self.scan_result_list.setMaximumHeight(150)
        self.scan_result_list.setSelectionMode(QListWidget.MultiSelection)
        fav_layout.addWidget(self.scan_result_list)

        add_fav_btn = QPushButton("👇 선택한 항목을 내 즐겨찾기에 추가 👇")
        add_fav_btn.setStyleSheet("background-color: #2b5797; color: white; padding: 5px;")
        add_fav_btn.clicked.connect(self.add_selected_to_favorites)
        fav_layout.addWidget(add_fav_btn)

        fav_layout.addWidget(QLabel("<b>내 즐겨찾기 목록 (우클릭 메뉴 / 더블클릭 열기)</b>"))
        self.favorites_list = QListWidget()
        self.favorites_list.setStyleSheet("font-size: 14px; padding: 5px;")
        self.favorites_list.itemDoubleClicked.connect(self.open_favorite_folder)
        self.favorites_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.favorites_list.customContextMenuRequested.connect(self.show_favorites_context_menu)
        fav_layout.addWidget(self.favorites_list)

        del_fav_btn = QPushButton("선택한 즐겨찾기 삭제")
        del_fav_btn.clicked.connect(self.delete_favorite)
        fav_layout.addWidget(del_fav_btn)
        
        self.refresh_favorites_list()
        layout.addWidget(self.fav_box)

        layout.addSpacing(20)

        self.toggle_creator_btn = QPushButton("▶ 룰 엔진 기반 폴더 생성기 (클릭하여 펼치기)")
        self.toggle_creator_btn.setStyleSheet("background-color: #eee; border: 1px solid #ccc; padding: 8px; font-weight: bold; text-align: left;")
        self.toggle_creator_btn.clicked.connect(self.toggle_creator_visibility)
        layout.addWidget(self.toggle_creator_btn)

        self.creator_box = QWidget()
        self.creator_box.setStyleSheet("border: 1px solid #ddd; background-color: #fafafa;")
        self.folder_creator_layout = QVBoxLayout(self.creator_box)
        self.build_folder_creator_inner_ui()
        self.creator_box.setVisible(False)
        layout.addWidget(self.creator_box)
        
        layout.addStretch()
        scroll_area.setWidget(container)
        main_layout.addWidget(scroll_area)
        return widget

    def toggle_creator_visibility(self):
        is_vis = not self.creator_box.isVisible()
        self.creator_box.setVisible(is_vis)
        self.toggle_creator_btn.setText("▼ 룰 엔진 기반 폴더 생성기 닫기" if is_vis else "▶ 룰 엔진 기반 폴더 생성기 (클릭하여 펼치기)")

    def build_folder_creator_inner_ui(self):
        while self.folder_creator_layout.count():
            item = self.folder_creator_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            elif item.layout(): self.clear_layout(item.layout())

        self.dynamic_inputs.clear()
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
                expanded_options = []
                for opt in variable_rules[var]:
                    if "~" in opt:
                        try:
                            start, end = int(opt.split("~")[0]), int(opt.split("~")[1])
                            width = len(opt.split("~")[0].strip())
                            for n in range(start, end + 1): expanded_options.append(str(n).zfill(width))
                        except: expanded_options.append(opt)
                    else: expanded_options.append(opt)
                combo.addItems(expanded_options)
                combo.currentTextChanged.connect(self.preview_path)
                input_layout.addWidget(combo)
                self.dynamic_inputs[var] = combo 
            else:
                line_edit = QLineEdit()
                line_edit.textChanged.connect(self.preview_path)
                input_layout.addWidget(line_edit)
                self.dynamic_inputs[var] = line_edit

        self.folder_creator_layout.addLayout(input_layout)
        self.batch_checkbox = QCheckBox("루트 하위의 모든 기존 폴더에 일괄 생성 적용 (배치 모드)")
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

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            elif item.layout(): self.clear_layout(item.layout())
        layout.deleteLater()

    def change_page(self, index): self.content_stack.setCurrentIndex(index)
    def open_settings(self): SettingsDialog(self.config, self).exec()

    # 🔥 즐겨찾기 우클릭 (복사 기능)
    def show_favorites_context_menu(self, pos):
        item = self.favorites_list.itemAt(pos)
        if not item: return
        folder_path = item.data(Qt.UserRole)
        
        menu = QMenu()
        open_act = QAction("📂 윈도우 탐색기로 열기", self)
        open_act.triggered.connect(lambda: self.open_favorite_folder(item))
        
        detail_act = QAction("🔍 자세히 보기 (팝업)", self)
        detail_act.triggered.connect(lambda: self.show_folder_details(item))
        
        copy_act = QAction("📋 폴더 절대 경로 복사", self)
        copy_act.triggered.connect(lambda: [QGuiApplication.clipboard().setText(folder_path), QMessageBox.information(self, "복사 완료", "클립보드에 폴더 경로가 복사되었습니다!")])
        
        menu.addAction(open_act)
        menu.addAction(detail_act)
        menu.addSeparator() 
        menu.addAction(copy_act)
        menu.exec(self.favorites_list.mapToGlobal(pos))

    def show_folder_details(self, item): FolderDetailsDialog(item.data(Qt.UserRole), self).exec()

    def toggle_scan(self):
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.cancel()
            self.scan_btn.setText("🔍 딥 스캔 시작")
            self.scan_btn.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold;")
        else: self.start_deep_scan()

    def start_deep_scan(self):
        root_path = self.config.get("paths", "root_path")
        filter_text = self.scan_filter_input.text().strip()
        if not filter_text: return QMessageBox.warning(self, "안내", "검색할 키워드를 입력해 주세요.")
        self.scan_result_list.clear()
        self.scan_btn.setText("🛑 검색 중지")
        self.scan_btn.setStyleSheet("background-color: #e74c3c; color: white; font-weight: bold;")
        preset_data = PresetParser(self.config).get_preset_data()
        shortcuts = preset_data.get("shortcuts", {})
        variables = [v for v in self.rule_engine.extract_variables("character_folder") if v != "root"]
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
        for item in self.scan_result_list.selectedItems(): self.db.add_favorite(item.text(), item.data(Qt.UserRole))
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
        for item in self.favorites_list.selectedItems(): self.db.delete_favorite(item.data(Qt.UserRole))
        self.refresh_favorites_list()

    def get_generated_path(self):
        kwargs = {}
        for var_name, widget in self.dynamic_inputs.items():
            val = widget.currentText().strip() if isinstance(widget, QComboBox) else widget.text().strip()
            if not val: raise ValueError("입력칸을 모두 채워주세요.")
            if re.search(r'[<>:"/\\|?*]', val): raise ValueError(f"'{val}'에 특수기호가 포함되어 있습니다.")
            kwargs[var_name] = val
        return self.rule_engine.generate_path("character_folder", **kwargs)

    def preview_path(self):
        try:
            path = self.get_generated_path().replace("\\", "/")
            self.result_label.setText(f"<b>[미리보기]</b><br><span style='color:blue;'>{path}</span>")
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
    def on_config_changed(self): self.build_folder_creator_inner_ui()

    # ------------------------------------------
    # 🔥 2. TO-DO 체크리스트 (여백 최적화 완벽판)
    # ------------------------------------------
    def build_todo_ui(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignTop) 
        
        header_box = QGroupBox("📌 프로젝트 작업 정보")
        header_box.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #ccc; border-radius: 5px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        header_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        header_main_layout = QVBoxLayout(header_box)
        header_main_layout.setSpacing(10)

        info_layout = QHBoxLayout()
        def create_info_input(label_text, config_key):
            l = QVBoxLayout()
            l.addWidget(QLabel(label_text))
            line_edit = QLineEdit(self.config.get("project_info", config_key))
            line_edit.setStyleSheet("background: white; border: 1px solid #bbb; padding: 4px;")
            line_edit.editingFinished.connect(lambda: [self.config.update("project_info", config_key, line_edit.text()), self.config.save()])
            l.addWidget(line_edit)
            return l, line_edit

        l1, self.team_input = create_info_input("팀 이름", "team")
        l2, self.worker_input = create_info_input("작업자", "worker")
        l3, self.char_input = create_info_input("캐릭터", "char")
        l4, self.skin_input = create_info_input("스킨넘버", "skin")

        info_layout.addLayout(l1)
        info_layout.addLayout(l2)
        info_layout.addLayout(l3)
        info_layout.addLayout(l4)
        header_main_layout.addLayout(info_layout)

        link_layout = QVBoxLayout()
        link_title_layout = QHBoxLayout()
        link_title_layout.addWidget(QLabel("🔗 관련 링크 (Jira, WIKI 등 / 줄바꿈으로 여러 개 입력)"))
        
        open_all_btn = QPushButton("🚀 모두 열기")
        open_all_btn.setStyleSheet("background-color: #0052CC; color: white; font-weight: bold; padding: 4px 10px;")
        open_all_btn.clicked.connect(self.open_all_jiras)
        link_title_layout.addStretch()
        link_title_layout.addWidget(open_all_btn)
        link_layout.addLayout(link_title_layout)

        link_input_layout = QHBoxLayout()
        self.jira_input = QTextEdit(self.config.get("project_info", "jira"))
        self.jira_input.setFixedHeight(50) 
        self.jira_input.setStyleSheet("background: white; border: 1px solid #bbb; padding: 4px; font-size: 12px;")
        self.jira_input.textChanged.connect(lambda: [self.config.update("project_info", "jira", self.jira_input.toPlainText()), self.config.save()])
        
        open_each_btn = QPushButton("열기 ▶")
        open_each_btn.setToolTip("커서가 있는 줄의 링크를 엽니다.")
        open_each_btn.setStyleSheet("background-color: #34495e; color: white; font-weight: bold; height: 50px; width: 60px;")
        open_each_btn.clicked.connect(self.open_current_jira)
        
        link_input_layout.addWidget(self.jira_input)
        link_input_layout.addWidget(open_each_btn)
        link_layout.addLayout(link_input_layout)

        header_main_layout.addLayout(link_layout)
        layout.addWidget(header_box)

        input_layout = QHBoxLayout()
        self.new_todo_input = QLineEdit()
        self.new_todo_input.setPlaceholderText("새로운 작업 목표를 입력하고 엔터 (≡ 핸들을 잡아 상하로 드래그 하세요!)")
        self.new_todo_input.setMinimumHeight(35)
        self.new_todo_input.returnPressed.connect(self.add_new_todo)
        
        add_btn = QPushButton("추가")
        add_btn.setMinimumHeight(35)
        add_btn.setStyleSheet("background-color: #2b5797; color: white; font-weight: bold;")
        add_btn.clicked.connect(self.add_new_todo)
        
        export_btn = QPushButton("📦 위클리 데이터 생성 (완료 항목만 추출)")
        export_btn.setMinimumHeight(35)
        export_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 5px 15px;")
        export_btn.clicked.connect(self.export_weekly_data)
        
        input_layout.addWidget(self.new_todo_input)
        input_layout.addWidget(add_btn)
        input_layout.addWidget(export_btn)
        layout.addLayout(input_layout)

        self.todo_list_widget = QListWidget()
        self.todo_list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.todo_list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.todo_list_widget.setDragEnabled(True)
        self.todo_list_widget.setAcceptDrops(True)
        self.todo_list_widget.setDropIndicatorShown(True)
        self.todo_list_widget.setStyleSheet("QListWidget { border: none; background: transparent; outline: none; } QListWidget::item { border: none; margin-bottom: 2px; }")
        self.todo_list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.todo_list_widget.model().rowsMoved.connect(self.on_todo_order_changed)
        self._is_refreshing_todo = False
        
        layout.addWidget(self.todo_list_widget)
        self.refresh_todo_list()
        return widget

    def open_all_jiras(self):
        text = self.jira_input.toPlainText()
        urls = re.findall(r'(https?://[^\s]+)', text)
        if not urls: return QMessageBox.warning(self, "안내", "http:// 또는 https:// 로 시작하는 웹 주소를 찾을 수 없습니다.")
        for url in urls: QDesktopServices.openUrl(QUrl(url))

    def open_current_jira(self):
        cursor = self.jira_input.textCursor()
        cursor.select(cursor.LineUnderCursor)
        line_text = cursor.selectedText()
        urls = re.findall(r'(https?://[^\s]+)', line_text)
        if urls: QDesktopServices.openUrl(QUrl(urls[0]))
        else: QMessageBox.warning(self, "안내", "현재 커서가 있는 줄에 올바른 링크가 없습니다.")

    def add_new_todo(self):
        title = self.new_todo_input.text().strip()
        if not title: return
        self.db.add_todo(title)
        self.new_todo_input.clear()
        self.refresh_todo_list()

    def refresh_todo_list(self):
        self._is_refreshing_todo = True
        self.todo_list_widget.clear()
        
        for todo in self.db.get_all_todos():
            todo_id, title, details, memo, is_done, order_idx, images = todo
            item_widget = TodoItemWidget(self.db, todo_id, title, details, memo, is_done, images)
            item_widget.deleted.connect(self.delete_todo)
            
            list_item = QListWidgetItem(self.todo_list_widget)
            list_item.setData(Qt.UserRole, todo_id)
            item_widget.height_changed.connect(lambda w=item_widget, i=list_item: i.setSizeHint(w.sizeHint()))
            self.todo_list_widget.setItemWidget(list_item, item_widget)
            list_item.setSizeHint(item_widget.sizeHint())
            
        self._is_refreshing_todo = False

    @Slot()
    def on_todo_order_changed(self):
        if self._is_refreshing_todo: return
        for index in range(self.todo_list_widget.count()):
            todo_id = self.todo_list_widget.item(index).data(Qt.UserRole)
            self.db.update_todo_order(todo_id, index)

    @Slot(int)
    def delete_todo(self, todo_id):
        if QMessageBox.question(self, "삭제", "삭제하시겠습니까?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.db.delete_todo(todo_id)
            self.refresh_todo_list()

    def export_weekly_data(self):
        last_dir = self.config.get("paths", "last_export_dir")
        if not last_dir or not Path(last_dir).exists(): last_dir = str(Path.home() / "Desktop")

        dest_dir = QFileDialog.getExistingDirectory(self, "위클리 데이터를 저장할 폴더를 선택하세요", last_dir)
        if not dest_dir: return

        self.config.update("paths", "last_export_dir", dest_dir)
        self.config.save()

        t_team = self.team_input.text().strip()
        t_worker = self.worker_input.text().strip()
        t_char = self.char_input.text().strip()
        t_skin = self.skin_input.text().strip()

        exported_count = 0
        for todo in self.db.get_all_todos():
            todo_id, title, details, memo_txt, is_done, order_idx, images_str = todo
            if int(is_done) != 1: continue

            seq_num = str(order_idx + 1).zfill(3) 
            
            try:
                base_name = f"{t_team}_{t_worker}_{t_char}_{t_skin}_{seq_num}_{title}"
                base_name = re.sub(r'[\\/*?:"<>|]', "", base_name)
            except Exception as e:
                return QMessageBox.critical(self, "오류", f"이름 생성 문제: {e}")

            img_paths = images_str.split("|") if images_str else []
            for i, local_path in enumerate(img_paths):
                if os.path.exists(local_path):
                    ext = os.path.splitext(local_path)[1]
                    final_img_name = f"{base_name}_{i+1}{ext}" if len(img_paths) > 1 else f"{base_name}{ext}"
                    shutil.copy(local_path, os.path.join(dest_dir, final_img_name))

            plain_text = memo_txt.strip()
            if plain_text:
                with open(os.path.join(dest_dir, f"{base_name}_메모.txt"), 'w', encoding='utf-8') as f:
                    f.write(plain_text)
                    
            exported_count += 1

        if exported_count > 0: QMessageBox.information(self, "완료", f"총 {exported_count}개의 데이터가 성공적으로 내보내졌습니다!")
        else: QMessageBox.warning(self, "항목 없음", "완료된 항목이 없거나 추출할 데이터가 없습니다.")


    # ------------------------------------------
    # 🔥 3. 자동 메시지 포매터
    # ------------------------------------------
    def build_formatter_ui(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        preset_box = QGroupBox("💾 메시지 포맷 프리셋 관리")
        preset_box.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #aaa; border-radius: 5px; margin-top: 10px; padding: 10px; }")
        preset_layout = QHBoxLayout(preset_box)
        
        self.msg_preset_combo = QComboBox()
        self.msg_preset_combo.addItem("새 프리셋 작성 중...")
        self.msg_preset_combo.currentTextChanged.connect(self.load_msg_preset)
        
        save_preset_btn = QPushButton("현재 설정 저장")
        save_preset_btn.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold;")
        save_preset_btn.clicked.connect(self.save_msg_preset)
        
        del_preset_btn = QPushButton("삭제")
        del_preset_btn.setStyleSheet("background-color: #e74c3c; color: white;")
        del_preset_btn.clicked.connect(self.delete_msg_preset)
        
        preset_layout.addWidget(QLabel("저장된 템플릿:"))
        preset_layout.addWidget(self.msg_preset_combo, 1)
        preset_layout.addWidget(save_preset_btn)
        preset_layout.addWidget(del_preset_btn)
        layout.addWidget(preset_box)

        rule_group = QGroupBox("⚙️ 메시지 치환 규칙 설정")
        rule_group.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #ccc; border-radius: 5px; margin-top: 10px; padding: 10px; }")
        rule_layout = QGridLayout(rule_group)

        def create_rule_input(row, label, config_key, placeholder):
            rule_layout.addWidget(QLabel(label), row, 0)
            inp = QLineEdit(self.config.get("msg_formatter", config_key))
            inp.setPlaceholderText(placeholder)
            inp.textChanged.connect(lambda: [self.config.update("msg_formatter", config_key, inp.text()), self.config.save(), self.process_format()])
            rule_layout.addWidget(inp, row, 1)
            return inp

        self.trim_front_input = create_rule_input(0, "지울 앞부분 텍스트:", "trim_front", "예: D:/UnrealProjects/")
        self.trim_back_input = create_rule_input(1, "지울 뒷부분 텍스트:", "trim_back", "예: .uasset")
        self.header_text_input = create_rule_input(2, "메시지 머리말(Top):", "header", "예: [애니메이션 리타겟팅 에셋 목록]")
        self.footer_text_input = create_rule_input(3, "메시지 꼬리말(Bottom):", "footer", "예: 확인 부탁드립니다.")
        layout.addWidget(rule_group)

        input_group = QGroupBox("📥 원본 텍스트 (퍼포스 경로 등 여러 줄)")
        input_group.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #ccc; border-radius: 5px; margin-top: 10px; }")
        input_layout = QVBoxLayout(input_group)
        self.raw_text_input = QTextEdit()
        self.raw_text_input.setPlaceholderText("경로나 텍스트를 여러 줄 붙여넣으세요...\n(작성 시 실시간으로 아래 결과창에 변환됩니다)")
        self.raw_text_input.setFixedHeight(100)
        self.raw_text_input.textChanged.connect(self.process_format)
        input_layout.addWidget(self.raw_text_input)
        layout.addWidget(input_group)

        output_group = QGroupBox("📤 최종 메시지 및 이미지")
        output_group.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #2980b9; border-radius: 5px; margin-top: 10px; }")
        output_layout = QVBoxLayout(output_group)

        self.result_output = ResultTextEdit()
        self.result_output.setStyleSheet("background-color: #f4f6f7; border: 1px solid #bdc3c7; font-size: 13px; color: #2c3e50;")
        self.result_output.setPlaceholderText("변환된 메시지가 여기에 표시됩니다.")
        self.result_output.setReadOnly(True) 
        output_layout.addWidget(self.result_output)

        self.msg_image_list = QListWidget()
        self.msg_image_list.setViewMode(QListWidget.IconMode)
        self.msg_image_list.setIconSize(QSize(80, 80))
        self.msg_image_list.setFixedHeight(100)
        self.msg_image_list.setStyleSheet("border: 1px dashed #aaa; background-color: #fff;")
        output_layout.addWidget(QLabel("첨부된 TO-DO 이미지 (더블클릭 시 클립보드에 이미지 복사!)"))
        output_layout.addWidget(self.msg_image_list)

        btn_layout = QHBoxLayout()
        insert_img_btn = QPushButton("🖼️ TO-DO 리스트에서 사진 가져오기")
        insert_img_btn.setStyleSheet("background-color: #8e44ad; color: white; font-weight: bold; padding: 8px;")
        insert_img_btn.clicked.connect(self.open_todo_image_dialog)
        
        copy_txt_btn = QPushButton("📋 텍스트 결과 복사")
        copy_txt_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 8px;")
        copy_txt_btn.clicked.connect(self.copy_formatted_text)
        
        clear_img_btn = QPushButton("❌ 첨부 이미지 비우기")
        clear_img_btn.clicked.connect(self.msg_image_list.clear)

        btn_layout.addWidget(insert_img_btn)
        btn_layout.addWidget(clear_img_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(copy_txt_btn)
        output_layout.addLayout(btn_layout)

        layout.addWidget(output_group)
        self.refresh_msg_presets()
        return widget

    def process_format(self):
        raw_text = self.raw_text_input.toPlainText()
        tf = self.trim_front_input.text()
        tb = self.trim_back_input.text()
        
        processed_lines = []
        for line in raw_text.split("\n"):
            if not line.strip(): continue
            if tf and line.startswith(tf): line = line[len(tf):]
            if tb and line.endswith(tb): line = line[:-len(tb)]
            processed_lines.append(line)
            
        core_text = "\n".join(processed_lines)
        final_text = ""
        if self.header_text_input.text(): final_text += f"{self.header_text_input.text()}\n\n"
        final_text += core_text
        if self.footer_text_input.text(): final_text += f"\n\n{self.footer_text_input.text()}"
        self.result_output.setPlainText(final_text)

    def open_todo_image_dialog(self):
        dialog = TodoImageDialog(self.db, self)
        if dialog.exec() == QDialog.Accepted and dialog.selected_image_path:
            item = QListWidgetItem(QIcon(dialog.selected_image_path), "")
            item.setData(Qt.UserRole, dialog.selected_image_path)
            self.msg_image_list.addItem(item)
            item.setToolTip("더블클릭 하면 메신저(카톡, 슬랙)에 붙여넣을 수 있게 복사됩니다!")
            self.msg_image_list.itemDoubleClicked.connect(self.copy_image_to_clipboard)

    def copy_image_to_clipboard(self, item):
        img_path = item.data(Qt.UserRole)
        if os.path.exists(img_path):
            from PySide6.QtGui import QImage
            QGuiApplication.clipboard().setImage(QImage(img_path))
            QMessageBox.information(self, "이미지 복사", "사진이 클립보드에 복사되었습니다!\n메신저에 Ctrl+V 하세요.")

    def copy_formatted_text(self):
        QGuiApplication.clipboard().setText(self.result_output.toPlainText())
        QMessageBox.information(self, "텍스트 복사", "포맷된 텍스트가 복사되었습니다!")

    def refresh_msg_presets(self):
        self.msg_preset_combo.blockSignals(True)
        self.msg_preset_combo.clear()
        self.msg_preset_combo.addItem("새 프리셋 작성 중...")
        presets = self.config.get("msg_presets", "list") or {}
        for name in presets.keys(): self.msg_preset_combo.addItem(name)
        self.msg_preset_combo.blockSignals(False)

    def save_msg_preset(self):
        name, ok = QInputDialog.getText(self, "프리셋 저장", "이 메시지 템플릿의 이름을 입력하세요:")
        if ok and name.strip():
            preset_data = {
                "trim_front": self.trim_front_input.text(),
                "trim_back": self.trim_back_input.text(),
                "header": self.header_text_input.text(),
                "footer": self.footer_text_input.text()
            }
            presets = self.config.get("msg_presets", "list") or {}
            presets[name.strip()] = preset_data
            self.config.update("msg_presets", "list", presets)
            self.config.save()
            self.refresh_msg_presets()
            self.msg_preset_combo.setCurrentText(name.strip())
            QMessageBox.information(self, "저장 완료", f"'{name.strip()}' 템플릿이 저장되었습니다.")

    def load_msg_preset(self, name):
        if name == "새 프리셋 작성 중...": return
        presets = self.config.get("msg_presets", "list") or {}
        if name in presets:
            data = presets[name]
            self.trim_front_input.setText(data.get("trim_front", ""))
            self.trim_back_input.setText(data.get("trim_back", ""))
            self.header_text_input.setText(data.get("header", ""))
            self.footer_text_input.setText(data.get("footer", ""))

    def delete_msg_preset(self):
        name = self.msg_preset_combo.currentText()
        if name == "새 프리셋 작성 중...": return
        if QMessageBox.question(self, "삭제", f"'{name}' 프리셋을 삭제하시겠습니까?") == QMessageBox.Yes:
            presets = self.config.get("msg_presets", "list") or {}
            if name in presets:
                del presets[name]
                self.config.update("msg_presets", "list", presets)
                self.config.save()
                self.refresh_msg_presets()

    # ==========================================
    # 🔥 OTA 자동 업데이트 (수정됨)
    # ==========================================
    # ==========================================
    # 🔥 OTA 자동 업데이트 (수정됨)
    # ==========================================
    def check_for_updates(self):
        self.updater_thread = UpdateChecker()
        self.updater_thread.update_available.connect(self.prompt_update)
        
        # 🔥 에러가 발생하면 화면에 무조건 띄우도록 연결!
        self.updater_thread.check_error.connect(self.show_update_error)
        
        self.updater_thread.start()

    @Slot(str)
    def show_update_error(self, error_msg):
        # 팝업으로 에러 원인을 적나라하게 보여줍니다.
        QMessageBox.critical(self, "업데이트 통신 에러", error_msg)

    @Slot(str, str, str)
    def prompt_update(self, version, notes, download_url):
        reply = QMessageBox.question(self, "새 업데이트 가능!", f"새로운 버전(v{version})이 출시되었습니다.\n지금 업데이트 하시겠습니까?\n\n[업데이트 내용]\n{notes}", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes: self.start_download(download_url)

    def start_download(self, download_url):
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
            sys.exit(0)
        else:
            QMessageBox.critical(self, "업데이트 실패", message)
            self.setEnabled(True)
            self.setWindowTitle(f"TaskHub - Workspace Manager (v{CURRENT_VERSION})")
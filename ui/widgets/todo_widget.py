import os
import time
from PySide6.QtWidgets import (QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QTextEdit, QPushButton, QCheckBox, QSizePolicy, QListWidget, QListWidgetItem)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QGuiApplication, QIcon

class ImageListWidget(QListWidget):
    """🔥 이미지만 전용으로 담아두는 가로 리스트 (Ctrl+V 지원)"""
    images_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self.setViewMode(QListWidget.IconMode)
        self.setIconSize(QSize(100, 100))
        self.setResizeMode(QListWidget.Adjust)
        self.setFixedHeight(120)
        self.setStyleSheet("QListWidget { border: 1px dashed #aaa; background-color: #f5f5f5; border-radius: 4px; padding: 5px; }")
        self.setToolTip("여기를 클릭하고 Ctrl+V를 누르면 클립보드 사진이 추가됩니다.\n(지우려면 사진 선택 후 Delete 키)")
        
        self.img_folder = os.path.join(os.getcwd(), "_todo_images")
        os.makedirs(self.img_folder, exist_ok=True)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_V and event.modifiers() == Qt.ControlModifier:
            clipboard = QGuiApplication.clipboard()
            if clipboard.mimeData().hasImage():
                image = clipboard.image()
                img_path = os.path.join(self.img_folder, f"img_{int(time.time()*1000)}.png")
                image.save(img_path, "PNG")
                self.add_image(img_path)
                self.emit_paths()
        elif event.key() == Qt.Key_Delete:
            for item in self.selectedItems():
                self.takeItem(self.row(item))
            self.emit_paths()
        else:
            super().keyPressEvent(event)

    def add_image(self, path):
        item = QListWidgetItem(QIcon(path), "")
        item.setData(Qt.UserRole, path)
        self.addItem(item)

    def load_images(self, paths_str):
        self.clear()
        if not paths_str: return
        for path in paths_str.split("|"):
            if os.path.exists(path):
                self.add_image(path)

    def emit_paths(self):
        paths = [self.item(i).data(Qt.UserRole) for i in range(self.count())]
        self.images_changed.emit("|".join(paths))


class TodoItemWidget(QFrame):
    deleted = Signal(int)
    height_changed = Signal()

    # 🔥 images 매개변수 추가 (7개)
    def __init__(self, db, todo_id, title, details, memo, is_done, images):
        super().__init__()
        self.db = db
        self.todo_id = todo_id
        self.setObjectName("TodoContainer")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setup_ui(title, details, memo, is_done, images)
        self.update_style(is_done)

    def setup_ui(self, title, details, memo, is_done, images):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.header_widget = QWidget()
        self.header_widget.setMinimumHeight(40)
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(10, 5, 10, 5)
        header_layout.setSpacing(10)
        
        drag_handle = QLabel("≡")
        drag_handle.setStyleSheet("font-weight: bold; color: #888; font-size: 18px; padding-bottom: 3px;")
        drag_handle.setCursor(Qt.SizeAllCursor)
        
        self.toggle_btn = QPushButton("▶")
        self.toggle_btn.setFixedSize(25, 25)
        self.toggle_btn.setStyleSheet("border: none; font-weight: bold;")
        self.toggle_btn.clicked.connect(self.toggle_details)
        
        style_input = "QLineEdit { background: white; border: 1px solid #ccc; border-radius: 3px; padding: 4px; font-size: 13px; color: black; }"
        self.title_input = QLineEdit(title)
        self.title_input.setPlaceholderText("작업 목표...")
        self.title_input.setStyleSheet(style_input)
        self.title_input.editingFinished.connect(lambda: self.db.update_todo(self.todo_id, "title", self.title_input.text()))

        self.details_input = QLineEdit(details)
        self.details_input.setPlaceholderText("세부 작업 방법을 적어주세요...")
        self.details_input.setStyleSheet(style_input)
        self.details_input.editingFinished.connect(lambda: self.db.update_todo(self.todo_id, "details", self.details_input.text()))

        self.del_btn = QPushButton("✖")
        self.del_btn.setFixedSize(25, 25)
        self.del_btn.setStyleSheet("color: red; border: none; font-weight: bold; font-size: 14px;")
        self.del_btn.clicked.connect(lambda: self.deleted.emit(self.todo_id))

        self.checkbox = QCheckBox(" 완료")
        self.checkbox.setStyleSheet("font-weight: bold; padding: 5px; background: #e8e8e8; border-radius: 3px;")
        
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(True if int(is_done) == 1 else False)
        self.checkbox.blockSignals(False)
        self.checkbox.clicked.connect(self.on_user_clicked_checkbox)
        
        header_layout.addWidget(drag_handle) 
        header_layout.addWidget(self.toggle_btn)
        header_layout.addWidget(self.title_input, 3)
        header_layout.addWidget(self.details_input, 5)
        header_layout.addWidget(self.checkbox)
        header_layout.addWidget(self.del_btn)

        main_layout.addWidget(self.header_widget)

        # 🔥 하단 메모 영역 (텍스트 창 2배 : 사진 창 1배)
        self.memo_widget = QWidget()
        memo_layout = QHBoxLayout(self.memo_widget)
        memo_layout.setContentsMargins(65, 0, 45, 10) 

        self.memo_input = QTextEdit(memo)
        self.memo_input.setPlaceholderText("텍스트 메모를 작성하세요...")
        self.memo_input.setFixedHeight(120)
        self.memo_input.setStyleSheet("border: 1px solid #ccc; background-color: #fff; font-size: 13px; border-radius: 4px;")
        self.memo_input.textChanged.connect(self.save_memo)
        
        self.image_list = ImageListWidget()
        self.image_list.load_images(images)
        self.image_list.images_changed.connect(lambda paths: self.db.update_todo(self.todo_id, "images", paths))
        
        memo_layout.addWidget(self.memo_input, 2)
        memo_layout.addWidget(self.image_list, 1)
        main_layout.addWidget(self.memo_widget)
        self.memo_widget.setVisible(False)

    def toggle_details(self):
        is_visible = self.memo_widget.isVisible()
        self.memo_widget.setVisible(not is_visible)
        self.toggle_btn.setText("▼" if not is_visible else "▶")
        self.height_changed.emit()

    def save_memo(self):
        self.db.update_todo(self.todo_id, "memo", self.memo_input.toPlainText())

    def on_user_clicked_checkbox(self, checked):
        is_done_int = 1 if checked else 0
        self.db.update_todo(self.todo_id, "is_done", is_done_int)
        self.update_style(is_done_int)

    def update_style(self, is_done):
        is_completed = int(is_done) == 1
        font_title = self.title_input.font()
        font_details = self.details_input.font()
        
        if is_completed:
            self.setStyleSheet("#TodoContainer { background-color: #7f8c8d; border: 1px solid #555; border-radius: 4px; margin: 2px; }")
            font_title.setStrikeOut(True)
            font_details.setStrikeOut(True)
            self.title_input.setFont(font_title)
            self.details_input.setFont(font_details)
            dark_input = "background: #95a5a6; border: 1px solid #7f8c8d; color: #ecf0f1; padding: 4px;"
            self.title_input.setStyleSheet(dark_input)
            self.details_input.setStyleSheet(dark_input)
            self.checkbox.setStyleSheet("font-weight: bold; color: white; padding: 5px; background: #2c3e50; border-radius: 3px;")
        else:
            self.setStyleSheet("#TodoContainer { background-color: #f9f9f9; border: 1px solid #ccc; border-radius: 4px; margin: 2px; }")
            font_title.setStrikeOut(False)
            font_details.setStrikeOut(False)
            self.title_input.setFont(font_title)
            self.details_input.setFont(font_details)
            white_input = "background: white; border: 1px solid #bbb; padding: 4px; color: black;"
            self.title_input.setStyleSheet(white_input)
            self.details_input.setStyleSheet(white_input)
            self.checkbox.setStyleSheet("font-weight: bold; padding: 5px; background: #e8e8e8; border-radius: 3px;")
import json
from pathlib import Path
from PySide6.QtCore import QObject, Signal

class ConfigManager(QObject):
    # 설정이 변경될 때 발생하는 시그널 (UI가 이 신호를 듣고 새로고침됨)
    config_changed = Signal()

    def __init__(self, config_file="config.json"):
        super().__init__()
        self.config_file = Path(config_file)
        self.config_data = {}
        self.load()

    def is_setup_required(self):
        # 필수 설정값(root_path)이 없으면 온보딩 마법사를 띄우기 위한 체크 함수
        return not self.config_file.exists() or not self.get("paths", "root_path")

    def load(self):
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
        else:
            self._set_default_config()

    def _set_default_config(self):
        # 최초 실행 시 기본 데이터 구조
        self.config_data = {
            "profile_name": "Default Profile",
            "paths": {"root_path": "", "preset_txt_path": ""},
            "rules": {"character_folder": "{root}/{type}/{name}_{number}"}
        }

    def save(self):
        # json 파일로 저장
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config_data, f, indent=4, ensure_ascii=False)
        self.config_changed.emit() # 저장 후 시그널 발송

    def get(self, category, key):
        # 안전하게 값 가져오기
        return self.config_data.get(category, {}).get(key, "")

    def update(self, category, key, value):
        # 값 업데이트 (저장은 별도로 save() 호출 필요)
        if category not in self.config_data:
            self.config_data[category] = {}
        self.config_data[category][key] = value

    def export_profile(self, export_path):
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(self.config_data, f, indent=4, ensure_ascii=False)

    def import_profile(self, import_path):
        with open(import_path, 'r', encoding='utf-8') as f:
            self.config_data = json.load(f)
        self.save()
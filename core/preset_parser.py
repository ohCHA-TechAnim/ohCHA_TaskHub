import json
from pathlib import Path

class PresetParser:
    def __init__(self, config_manager):
        self.config = config_manager

    def get_preset_data(self):
        preset_path = self.config.get("paths", "preset_txt_path")
        # 🔥 variable_rules 추가 (변수별 고정 선택지 보관)
        data = {"rule": "", "sub_folders": [], "shortcuts": {}, "variable_rules": {}}
        
        if not preset_path or not Path(preset_path).exists(): return data
        p = Path(preset_path)
        try:
            if p.suffix.lower() == '.json':
                with open(p, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                    data["rule"] = file_data.get("rule", "")
                    data["sub_folders"] = file_data.get("sub_folders", [])
                    data["shortcuts"] = file_data.get("shortcuts", {})
                    data["variable_rules"] = file_data.get("variable_rules", {})
            else: 
                with open(p, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    data["sub_folders"] = [line.strip() for line in lines if line.strip()]
        except Exception as e:
            print(f"프리셋 읽기 오류: {e}")
        return data
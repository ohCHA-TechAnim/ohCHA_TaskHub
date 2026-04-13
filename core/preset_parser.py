import json
from pathlib import Path

class PresetParser:
    def __init__(self, config_manager):
        self.config = config_manager

    def get_preset_data(self):
        """현재 설정된 프리셋 파일에서 모든 데이터(규칙, 서브폴더, 숏컷)를 읽어옵니다."""
        preset_path = self.config.get("paths", "preset_txt_path")
        
        # 기본 반환 구조
        data = {"rule": "", "sub_folders": [], "shortcuts": {}}
        
        if not preset_path or not Path(preset_path).exists():
            return data
            
        p = Path(preset_path)
        
        try:
            if p.suffix.lower() == '.json':
                with open(p, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                    data["rule"] = file_data.get("rule", "")
                    data["sub_folders"] = file_data.get("sub_folders", [])
                    data["shortcuts"] = file_data.get("shortcuts", {})
            else: 
                # TXT 파일 호환성 유지 (서브 폴더만 읽음)
                with open(p, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    data["sub_folders"] = [line.strip() for line in lines if line.strip()]
        except Exception as e:
            print(f"프리셋 읽기 오류: {e}")
            
        return data
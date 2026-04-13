import string
from pathlib import Path
from core.preset_parser import PresetParser

class RuleEngine:
    def __init__(self, config_manager):
        self.config = config_manager
        self.parser = PresetParser(self.config)

    def extract_variables(self, rule_name):
        template = self.config.get("rules", rule_name)
        if not template: return []
        return [fn for _, fn, _, _ in string.Formatter().parse(template) if fn is not None]

    def generate_path(self, rule_name, **kwargs):
        template = self.config.get("rules", rule_name)
        root_path = self.config.get("paths", "root_path")
        if not template: raise ValueError(f"'{rule_name}' 규칙을 찾을 수 없습니다.")

        preset_data = self.parser.get_preset_data()
        shortcuts = preset_data.get("shortcuts", {}) # 구조: {"캐릭터": {"에시모": "012"}}

        processed_kwargs = {}
        for key, val in kwargs.items():
            # 🔥 해당 변수(key)에 등록된 숏컷 사전만 꺼내서 확인!
            var_shortcuts = shortcuts.get(key, {})
            # 입력한 값(val)이 숏컷에 있으면 치환, 없으면 원래 값 유지
            processed_kwargs[key] = var_shortcuts.get(val, val)
        
        try:
            if "{root}" in template:
                final_path = template.format(root=root_path, **processed_kwargs)
                return str(Path(final_path))
            else:
                formatted_sub_path = template.format(**processed_kwargs)
                formatted_sub_path = formatted_sub_path.lstrip("\\/")
                return str(Path(root_path) / formatted_sub_path)
        except KeyError as e:
            raise ValueError(f"변수 {e}가 누락되었습니다.")
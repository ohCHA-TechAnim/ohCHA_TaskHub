import string
from pathlib import Path
from core.preset_parser import PresetParser

class RuleEngine:
    def __init__(self, config_manager):
        self.config = config_manager
        # 단축어를 읽어오기 위해 Parser 연결
        self.parser = PresetParser(self.config)

    def extract_variables(self, rule_name):
        template = self.config.get("rules", rule_name)
        if not template:
            return []
        variables = [fn for _, fn, _, _ in string.Formatter().parse(template) if fn is not None]
        return variables

    def generate_path(self, rule_name, **kwargs):
        template = self.config.get("rules", rule_name)
        root_path = self.config.get("paths", "root_path")
        
        if not template:
            raise ValueError(f"'{rule_name}' 규칙을 찾을 수 없습니다.")

        # 🔥 [핵심] JSON에서 숏컷(단축어) 사전을 불러와서 입력값 치환!
        preset_data = self.parser.get_preset_data()
        shortcuts = preset_data.get("shortcuts", {})

        processed_kwargs = {}
        for key, val in kwargs.items():
            # 만약 사용자가 입력한 값(val)이 숏컷 사전에 있다면, 변환값으로 교체!
            if val in shortcuts:
                processed_kwargs[key] = shortcuts[val]
            else:
                processed_kwargs[key] = val
        
        try:
            if "{root}" in template:
                final_path = template.format(root=root_path, **processed_kwargs)
                return str(Path(final_path))
            else:
                formatted_sub_path = template.format(**processed_kwargs)
                formatted_sub_path = formatted_sub_path.lstrip("\\/")
                final_path = Path(root_path) / formatted_sub_path
                return str(final_path)
                
        except KeyError as e:
            raise ValueError(f"경로 생성 실패: 규칙 템플릿에 필요한 변수 {e}가 누락되었습니다.")
import os
from pathlib import Path
from PySide6.QtCore import QThread, Signal

class SearchWorker(QThread):
    result_found = Signal(str, str) 
    finished = Signal(int)          
    error = Signal(str)             

    def __init__(self, root_path, filter_text, shortcuts, variables):
        super().__init__()
        self.root_path = root_path
        self.filter_text = filter_text.lower()
        self.shortcuts = shortcuts # {"캐릭터": {"에시모": "012"}}
        self.variables = variables # ['캐릭터', '타입1', '타입2', '스킨넘버']
        self.is_cancelled = False

    def run(self):
        try:
            count = 0
            # 우리가 설정한 변수 규칙의 개수 (예: 4단계)
            target_depth = len(self.variables)

            for current_dir, dirs, files in os.walk(self.root_path):
                if self.is_cancelled: break
                
                # 속도 최적화: 숨김 폴더 무시
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                if current_dir == self.root_path: continue

                # 상대 경로 가져오기 및 깊이 계산
                rel_path = str(Path(current_dir).relative_to(self.root_path)).replace("\\", "/")
                parts = rel_path.split("/")
                current_depth = len(parts)

                # 🔥 1단계: 아직 목표 깊이(최하위 에셋 폴더)에 도달하지 않았다면, 계속 파고듭니다!
                if current_depth < target_depth:
                    continue # 아무것도 하지 않고 다음 하위 폴더로 내려감

                # 🔥 2단계: 목표 깊이에 정확히 도달했을 때만 검사합니다!
                if current_depth == target_depth:
                    translated_parts = []
                    
                    for i, part in enumerate(parts):
                        var_name = self.variables[i]
                        var_shortcuts = self.shortcuts.get(var_name, {})
                        reverse_shortcuts = {v: k for k, v in var_shortcuts.items()}
                        # 치환 (사전에 없으면 원래 이름)
                        translated_parts.append(reverse_shortcuts.get(part, part))
                    
                    display_name = " - ".join(translated_parts)
                    
                    # 원본 경로(012)와 번역된 이름(에시모) 양쪽 모두에서 검색어 확인
                    if self.filter_text in rel_path.lower() or self.filter_text in display_name.lower():
                        self.result_found.emit(current_dir, display_name)
                        count += 1
                        
                    # 🔥 [안전한 가지치기] 목표 깊이에 도달했으므로, 
                    # 이 밑에 있는 프리셋 폴더(01_Model 등)는 속도 향상을 위해 더 이상 뒤지지 않습니다!
                    dirs[:] = [] 

                    if count >= 1000: break

            self.finished.emit(count)
        except Exception as e:
            self.error.emit(str(e))
            
    def cancel(self):
        self.is_cancelled = True
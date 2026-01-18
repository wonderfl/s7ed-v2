"""
morphing 폴더의 파일들 들여쓰기 수정
"""
import re

def fix_file_indentation(filepath):
    """파일의 들여쓰기 수정"""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    fixed_lines = []
    in_method = False
    method_indent = 0
    
    for i, line in enumerate(lines):
        # 메서드 정의 찾기
        if re.match(r'^\s+def \w+\(', line):
            in_method = True
            # 메서드 정의의 들여쓰기 (4칸)
            method_indent = len(line) - len(line.lstrip())
            fixed_lines.append(line)
        elif in_method:
            # 메서드 본문
            stripped = line.lstrip()
            if not stripped or stripped.startswith('#'):
                # 빈 줄이나 주석은 그대로
                fixed_lines.append(line)
            elif stripped.startswith('"""') or stripped.startswith("'''"):
                # docstring은 메서드 정의 다음 줄이면 8칸 들여쓰기
                if i > 0 and re.match(r'^\s+def \w+\(', lines[i-1]):
                    fixed_lines.append(' ' * (method_indent + 4) + stripped + '\n')
                else:
                    fixed_lines.append(line)
            elif stripped.startswith('def '):
                # 다음 메서드 시작
                in_method = False
                fixed_lines.append(line)
            else:
                # 메서드 본문은 8칸 들여쓰기 (메서드 정의 4칸 + 본문 4칸)
                current_indent = len(line) - len(stripped)
                if current_indent < method_indent + 4:
                    fixed_lines.append(' ' * (method_indent + 4) + stripped)
                else:
                    fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)

# 파일들 수정
files = [
    'gui/face_edit/morphing/ui.py',
    'gui/face_edit/morphing/handlers.py',
    'gui/face_edit/morphing/logic.py',
    'gui/face_edit/morphing/utils.py',
]

for filepath in files:
    try:
        fix_file_indentation(filepath)
        print(f"수정 완료: {filepath}")
    except Exception as e:
        print(f"오류 ({filepath}): {e}")

print("모든 파일 수정 완료!")

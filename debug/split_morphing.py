"""
morphing.py의 메서드를 분리하여 파일로 저장하는 스크립트
"""
import re
import os

# 메서드 정의 위치 (라인 번호, 1-based)
methods = {
    '_create_face_alignment_ui': 19,
    '_create_face_morphing_ui': 163,
    'on_alignment_change': 217,
    'apply_alignment': 232,
    'on_individual_region_change': 274,  # 중복 있음 (328)
    'on_eye_spacing_change': 318,
    'on_eye_region_display_change': 359,
    'on_lip_region_display_change': 368,
    'on_region_selection_change': 377,
    'on_landmarks_display_change': 389,
    'update_labels_only': 406,
    'update_polygons_only': 541,
    'on_morphing_change': 705,
    '_apply_common_sliders': 863,
    '_apply_common_sliders_to_landmarks': 983,
    '_get_region_indices': 1639,
    'reset_morphing': 1725,
    'apply_editing': 1809,
}

# 파일 읽기
with open('gui/face_edit/morphing.py', 'r', encoding='utf-8') as f:
    content = f.read()
    content_lines = content.split('\n')

# 메서드 분류
ui_methods = ['_create_face_alignment_ui', '_create_face_morphing_ui']
handler_methods = ['on_alignment_change', 'on_individual_region_change', 'on_eye_spacing_change',
                   'on_eye_region_display_change', 'on_lip_region_display_change', 
                   'on_region_selection_change', 'on_landmarks_display_change', 'on_morphing_change']
logic_methods = ['apply_alignment', 'apply_editing', 'reset_morphing', 
                 '_apply_common_sliders', '_apply_common_sliders_to_landmarks']
utils_methods = ['update_labels_only', 'update_polygons_only', '_get_region_indices']

def extract_method(method_name, start_line):
    """메서드 추출"""
    # 다음 메서드 찾기
    method_list = sorted(methods.items(), key=lambda x: x[1])
    next_method = None
    for i, (name, line) in enumerate(method_list):
        if name == method_name:
            if i + 1 < len(method_list):
                next_method = method_list[i + 1][1]
            break
    
    # 메서드 끝 라인 결정
    if next_method:
        end_line = next_method - 1
    else:
        # 마지막 메서드는 파일 끝까지
        end_line = len(content_lines)
    
    # 메서드 코드 추출
    method_lines = content_lines[start_line-1:end_line]
    method_code = '\n'.join(method_lines)
    
    return method_code

# 공통 import 및 클래스 정의
common_imports = '''"""
얼굴 편집 패널 - 얼굴 특징 보정 Mixin
얼굴 특징 보정 관리 및 편집 적용 로직을 담당
"""
import os
import tkinter as tk
from tkinter import ttk
from PIL import Image

import utils.face_landmarks as face_landmarks
import utils.face_morphing as face_morphing
import utils.style_transfer as style_transfer
import utils.face_transform as face_transform

'''

# ui.py 생성
ui_code = common_imports + '\n\nclass UIMixin:\n    """UI 생성 기능 Mixin"""\n    \n'
for method_name in ui_methods:
    method_code = extract_method(method_name, methods[method_name])
    # 메서드 정의만 추출 (들여쓰기 조정)
    method_lines = method_code.split('\n')
    # 첫 번째 def 라인 찾기
    for i, line in enumerate(method_lines):
        if line.strip().startswith('def '):
            method_code = '\n'.join(method_lines[i:])
            # 들여쓰기 조정 (4칸으로)
            adjusted_lines = []
            for ml in method_code.split('\n'):
                if ml.strip():
                    # 원래 들여쓰기 제거하고 4칸으로
                    adjusted_lines.append('    ' + ml.lstrip())
                else:
                    adjusted_lines.append('')
            ui_code += '\n'.join(adjusted_lines) + '\n\n'
            break

# handlers.py 생성
handler_code = common_imports + '\n\nclass HandlersMixin:\n    """이벤트 핸들러 기능 Mixin"""\n    \n'
for method_name in handler_methods:
    if method_name == 'on_individual_region_change':
        # 중복이 있으므로 첫 번째 것만 사용
        method_code = extract_method(method_name, methods[method_name])
        # 328줄 이전까지만
        method_lines = method_code.split('\n')
        # 다음 메서드까지
        next_start = methods['on_eye_spacing_change']
        method_start = methods[method_name]
        method_lines = content_lines[method_start-1:next_start-1]
        method_code = '\n'.join(method_lines)
    else:
        method_code = extract_method(method_name, methods[method_name])
    
    method_lines = method_code.split('\n')
    for i, line in enumerate(method_lines):
        if line.strip().startswith('def '):
            method_code = '\n'.join(method_lines[i:])
            adjusted_lines = []
            for ml in method_code.split('\n'):
                if ml.strip():
                    adjusted_lines.append('    ' + ml.lstrip())
                else:
                    adjusted_lines.append('')
            handler_code += '\n'.join(adjusted_lines) + '\n\n'
            break

# logic.py 생성
logic_code = common_imports + '\n\nclass LogicMixin:\n    """편집 적용 및 보정 로직 기능 Mixin"""\n    \n'
for method_name in logic_methods:
    method_code = extract_method(method_name, methods[method_name])
    method_lines = method_code.split('\n')
    for i, line in enumerate(method_lines):
        if line.strip().startswith('def '):
            method_code = '\n'.join(method_lines[i:])
            adjusted_lines = []
            for ml in method_code.split('\n'):
                if ml.strip():
                    adjusted_lines.append('    ' + ml.lstrip())
                else:
                    adjusted_lines.append('')
            logic_code += '\n'.join(adjusted_lines) + '\n\n'
            break

# utils.py 생성
utils_code = common_imports + '\n\nclass UtilsMixin:\n    """유틸리티 기능 Mixin"""\n    \n'
for method_name in utils_methods:
    method_code = extract_method(method_name, methods[method_name])
    method_lines = method_code.split('\n')
    for i, line in enumerate(method_lines):
        if line.strip().startswith('def '):
            method_code = '\n'.join(method_lines[i:])
            adjusted_lines = []
            for ml in method_code.split('\n'):
                if ml.strip():
                    adjusted_lines.append('    ' + ml.lstrip())
                else:
                    adjusted_lines.append('')
            utils_code += '\n'.join(adjusted_lines) + '\n\n'
            break

# __init__.py 생성
init_code = '''"""
얼굴 편집 패널 - 얼굴 특징 보정 Mixin
모든 Mixin을 통합
"""
from .ui import UIMixin
from .handlers import HandlersMixin
from .logic import LogicMixin
from .utils import UtilsMixin


class MorphingManagerMixin(
    UIMixin,
    HandlersMixin,
    LogicMixin,
    UtilsMixin
):
    """얼굴 특징 보정 관리 기능 Mixin"""
    pass
'''

# 파일 저장
os.makedirs('gui/face_edit/morphing', exist_ok=True)

with open('gui/face_edit/morphing/ui.py', 'w', encoding='utf-8') as f:
    f.write(ui_code)

with open('gui/face_edit/morphing/handlers.py', 'w', encoding='utf-8') as f:
    f.write(handler_code)

with open('gui/face_edit/morphing/logic.py', 'w', encoding='utf-8') as f:
    f.write(logic_code)

with open('gui/face_edit/morphing/utils.py', 'w', encoding='utf-8') as f:
    f.write(utils_code)

with open('gui/face_edit/morphing/__init__.py', 'w', encoding='utf-8') as f:
    f.write(init_code)

print("파일 분리 완료!")
print(f"UI 관련: {len(ui_methods)}개 메서드")
print(f"핸들러 관련: {len(handler_methods)}개 메서드")
print(f"로직 관련: {len(logic_methods)}개 메서드")
print(f"유틸리티 관련: {len(utils_methods)}개 메서드")

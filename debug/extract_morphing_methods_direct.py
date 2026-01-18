"""
morphing.py의 메서드를 원본에서 직접 추출하여 파일로 저장
"""
import os

# 파일 읽기
with open('gui/face_edit/morphing.py', 'r', encoding='utf-8') as f:
    content_lines = f.readlines()

# 공통 import
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

# UI 메서드 추출
ui_code = common_imports + '\n\nclass UIMixin:\n    """UI 생성 기능 Mixin"""\n    \n'
# _create_face_alignment_ui: 19-162
ui_code += ''.join(content_lines[18:162])
# _create_face_morphing_ui: 163-216
ui_code += ''.join(content_lines[162:216])

# Handlers 메서드 추출
handler_code = common_imports + '\n\nclass HandlersMixin:\n    """이벤트 핸들러 기능 Mixin"""\n    \n'
# on_alignment_change: 217-231
handler_code += ''.join(content_lines[216:231])
# on_individual_region_change: 274-317 (첫 번째)
handler_code += ''.join(content_lines[273:317])
# on_eye_spacing_change: 318-358
handler_code += ''.join(content_lines[317:358])
# on_eye_region_display_change: 359-367
handler_code += ''.join(content_lines[358:367])
# on_lip_region_display_change: 368-376
handler_code += ''.join(content_lines[367:376])
# on_region_selection_change: 377-388
handler_code += ''.join(content_lines[376:388])
# on_landmarks_display_change: 389-405
handler_code += ''.join(content_lines[388:405])
# on_morphing_change: 705-862
handler_code += ''.join(content_lines[704:862])

# Logic 메서드 추출
logic_code = common_imports + '\n\nclass LogicMixin:\n    """편집 적용 및 보정 로직 기능 Mixin"""\n    \n'
# apply_alignment: 232-273
logic_code += ''.join(content_lines[231:273])
# _apply_common_sliders: 863-982
logic_code += ''.join(content_lines[862:982])
# _apply_common_sliders_to_landmarks: 983-1638
logic_code += ''.join(content_lines[982:1638])
# reset_morphing: 1725-1808
logic_code += ''.join(content_lines[1724:1808])
# apply_editing: 1809-2150
logic_code += ''.join(content_lines[1808:2150])

# Utils 메서드 추출
utils_code = common_imports + '\n\nclass UtilsMixin:\n    """유틸리티 기능 Mixin"""\n    \n'
# update_labels_only: 406-540
utils_code += ''.join(content_lines[405:540])
# update_polygons_only: 541-704
utils_code += ''.join(content_lines[540:704])
# _get_region_indices: 1639-1724
utils_code += ''.join(content_lines[1638:1724])

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
print(f"UI 관련: 2개 메서드")
print(f"핸들러 관련: 8개 메서드")
print(f"로직 관련: 5개 메서드")
print(f"유틸리티 관련: 3개 메서드")

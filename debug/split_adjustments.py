"""
adjustments.py의 함수를 분리하여 파일로 저장하는 스크립트
"""
import re
import os

# 함수 정의 위치 (라인 번호, 1-based)
functions = {
    'adjust_eye_size': 25,
    'adjust_eye_spacing': 189,
    'adjust_eye_position': 367,
    'adjust_nose_size': 526,
    'adjust_jaw': 621,
    'adjust_face_size': 739,
    'adjust_mouth_size': 849,
    'adjust_upper_lip_size': 949,
    'adjust_lower_lip_size': 1059,
    'adjust_upper_lip_shape': 1169,
    'adjust_lower_lip_shape': 1335,
    'adjust_upper_lip_width': 1501,
    'adjust_lower_lip_width': 1664,
    'adjust_lip_vertical_move': 1827,
    'adjust_region_size': 2049,
    'adjust_region_position': 2306,
}

# 파일 읽기
with open('utils/face_morphing/adjustments.py', 'r', encoding='utf-8') as f:
    content = f.read()
    content_lines = content.split('\n')

# 함수 분류
eye_functions = ['adjust_eye_size', 'adjust_eye_spacing', 'adjust_eye_position']
nose_functions = ['adjust_nose_size']
mouth_functions = ['adjust_mouth_size', 'adjust_upper_lip_size', 'adjust_lower_lip_size', 
                   'adjust_upper_lip_shape', 'adjust_lower_lip_shape', 
                   'adjust_upper_lip_width', 'adjust_lower_lip_width', 'adjust_lip_vertical_move']
face_functions = ['adjust_jaw', 'adjust_face_size']
region_functions = ['adjust_region_size', 'adjust_region_position']

def extract_function(func_name, start_line):
    """함수 추출"""
    # 다음 함수 찾기
    func_list = sorted(functions.items(), key=lambda x: x[1])
    next_func = None
    for i, (name, line) in enumerate(func_list):
        if name == func_name:
            if i + 1 < len(func_list):
                next_func = func_list[i + 1][1]
            break
    
    # 함수 끝 라인 결정
    if next_func:
        end_line = next_func - 1
    else:
        # 마지막 함수는 파일 끝까지
        end_line = len(content_lines)
    
    # 함수 코드 추출
    func_lines = content_lines[start_line-1:end_line]
    func_code = '\n'.join(func_lines)
    
    return func_code

# 공통 import 및 상수
common_imports = '''"""
이미지 조정 함수 모듈
얼굴 특징(눈, 코, 입, 턱 등)을 조정하는 함수들
"""
import numpy as np
from PIL import Image

from ..constants import _cv2_available, _landmarks_available
from ..utils import _create_blend_mask
from ..region_extraction import _get_eye_region, _get_mouth_region, _get_nose_region, _get_region_center

# 외부 모듈 import
try:
    import cv2
except ImportError:
    cv2 = None

try:
    from utils.face_landmarks import detect_face_landmarks, get_key_landmarks
except ImportError:
    detect_face_landmarks = None
    get_key_landmarks = None

'''

# eye_adjustments.py 생성
eye_code = common_imports + '\n'
for func_name in eye_functions:
    func_code = extract_function(func_name, functions[func_name])
    eye_code += func_code + '\n\n'

# nose_adjustments.py 생성
nose_code = common_imports + '\n'
for func_name in nose_functions:
    func_code = extract_function(func_name, functions[func_name])
    nose_code += func_code + '\n\n'

# mouth_adjustments.py 생성
mouth_code = common_imports + '\n'
for func_name in mouth_functions:
    func_code = extract_function(func_name, functions[func_name])
    mouth_code += func_code + '\n\n'

# face_adjustments.py 생성
face_code = common_imports + '\n'
for func_name in face_functions:
    func_code = extract_function(func_name, functions[func_name])
    face_code += func_code + '\n\n'

# region_adjustments.py 생성
region_code = common_imports + '\n'
for func_name in region_functions:
    func_code = extract_function(func_name, functions[func_name])
    region_code += func_code + '\n\n'

# __init__.py 생성
init_code = '''"""
이미지 조정 함수 모듈
모든 조정 함수를 export
"""
from .eye_adjustments import (
    adjust_eye_size,
    adjust_eye_spacing,
    adjust_eye_position
)
from .nose_adjustments import (
    adjust_nose_size
)
from .mouth_adjustments import (
    adjust_mouth_size,
    adjust_upper_lip_size,
    adjust_lower_lip_size,
    adjust_upper_lip_shape,
    adjust_lower_lip_shape,
    adjust_upper_lip_width,
    adjust_lower_lip_width,
    adjust_lip_vertical_move
)
from .face_adjustments import (
    adjust_jaw,
    adjust_face_size
)
from .region_adjustments import (
    adjust_region_size,
    adjust_region_position
)

__all__ = [
    'adjust_eye_size',
    'adjust_eye_spacing',
    'adjust_eye_position',
    'adjust_nose_size',
    'adjust_jaw',
    'adjust_face_size',
    'adjust_mouth_size',
    'adjust_upper_lip_size',
    'adjust_lower_lip_size',
    'adjust_upper_lip_shape',
    'adjust_lower_lip_shape',
    'adjust_upper_lip_width',
    'adjust_lower_lip_width',
    'adjust_lip_vertical_move',
    'adjust_region_size',
    'adjust_region_position',
]
'''

# 파일 저장
os.makedirs('utils/face_morphing/adjustments', exist_ok=True)

with open('utils/face_morphing/adjustments/eye_adjustments.py', 'w', encoding='utf-8') as f:
    f.write(eye_code)

with open('utils/face_morphing/adjustments/nose_adjustments.py', 'w', encoding='utf-8') as f:
    f.write(nose_code)

with open('utils/face_morphing/adjustments/mouth_adjustments.py', 'w', encoding='utf-8') as f:
    f.write(mouth_code)

with open('utils/face_morphing/adjustments/face_adjustments.py', 'w', encoding='utf-8') as f:
    f.write(face_code)

with open('utils/face_morphing/adjustments/region_adjustments.py', 'w', encoding='utf-8') as f:
    f.write(region_code)

with open('utils/face_morphing/adjustments/__init__.py', 'w', encoding='utf-8') as f:
    f.write(init_code)

print("파일 분리 완료!")
print(f"눈 관련: {len(eye_functions)}개 함수")
print(f"코 관련: {len(nose_functions)}개 함수")
print(f"입 관련: {len(mouth_functions)}개 함수")
print(f"얼굴 관련: {len(face_functions)}개 함수")
print(f"부위별: {len(region_functions)}개 함수")

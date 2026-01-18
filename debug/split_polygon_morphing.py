"""
polygon_morphing.py의 함수를 분리하여 파일로 저장하는 스크립트
"""
import os

# 함수 정의 위치 (라인 번호, 1-based)
functions = {
    '_get_neighbor_points': 45,
    '_check_triangles_flipped': 69,
    'morph_face_by_polygons': 129,
    'transform_points_for_eye_size': 754,
    'transform_points_for_nose_size': 1146,
    'transform_points_for_jaw': 1214,
    'transform_points_for_face_size': 1276,
    'transform_points_for_mouth_size': 1329,
    'transform_points_for_eye_position': 1376,
    'transform_points_for_lip_shape': 1430,
    'transform_points_for_lip_width': 1529,
    'transform_points_for_lip_vertical_move': 1613,
    'move_point_group': 1687,
    'move_points': 1769,
}

# 파일 읽기
with open('utils/face_morphing/polygon_morphing.py', 'r', encoding='utf-8') as f:
    content_lines = f.readlines()

# 공통 import 및 docstring
common_imports = '''"""
폴리곤 포인트 변형 및 폴리곤 모핑 모듈

이 모듈은 폴리곤 포인트(랜드마크 + 경계 포인트)를 변형하고,
변형된 포인트를 기반으로 폴리곤(삼각형 메시)을 생성하여 
이미지 모핑을 수행합니다.

개념 정의:
- 랜드마크(Landmark): MediaPipe에서 감지된 얼굴 특징점 좌표 리스트 [(x, y), ...] (참조용)
- 폴리곤 포인트(Polygon Points): 실제 모핑에 사용되는 포인트 (랜드마크 + 경계 포인트)
- 폴리곤(Polygon): 폴리곤 포인트를 꼭짓점으로 하는 삼각형 메시 (Delaunay Triangulation)
- 모핑(Morphing): 원본 폴리곤 포인트를 변형된 폴리곤 포인트로 변환하여 이미지를 변형하는 과정

사용 흐름:
1. 랜드마크 감지 (참조용)
2. 폴리곤 포인트 생성 (랜드마크 + 경계 포인트)
3. 폴리곤 포인트 변형: transform_points_* 함수로 포인트 변형
4. 폴리곤 모핑: morph_face_by_polygons 함수로 변형된 포인트를 사용하여 이미지 변형
"""
import numpy as np
from PIL import Image

from ..constants import _cv2_available, _cv2_cuda_available, _scipy_available, _landmarks_available, _delaunay_cache, _delaunay_cache_max_size

# 외부 모듈 import
try:
    import cv2
except ImportError:
    cv2 = None

try:
    from scipy.spatial import Delaunay
except ImportError:
    Delaunay = None

try:
    from utils.face_landmarks import detect_face_landmarks, get_key_landmarks, LEFT_EYE_INDICES, RIGHT_EYE_INDICES
except ImportError:
    detect_face_landmarks = None
    get_key_landmarks = None
    LEFT_EYE_INDICES = []
    RIGHT_EYE_INDICES = []

'''

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
    func_code = ''.join(func_lines)
    
    return func_code

# utils.py 생성
utils_functions = ['_get_neighbor_points', '_check_triangles_flipped']
utils_code = common_imports + '\n'
for func_name in utils_functions:
    func_code = extract_function(func_name, functions[func_name])
    utils_code += func_code + '\n\n'

# core.py 생성
core_functions = ['morph_face_by_polygons']
core_code = common_imports + '\n'
# utils에서 함수 import
core_code += 'from .utils import _get_neighbor_points, _check_triangles_flipped\n\n'
for func_name in core_functions:
    func_code = extract_function(func_name, functions[func_name])
    core_code += func_code + '\n\n'

# transformations.py 생성
transformation_functions = [
    'transform_points_for_eye_size',
    'transform_points_for_nose_size',
    'transform_points_for_jaw',
    'transform_points_for_face_size',
    'transform_points_for_mouth_size',
    'transform_points_for_eye_position',
    'transform_points_for_lip_shape',
    'transform_points_for_lip_width',
    'transform_points_for_lip_vertical_move'
]
transformations_code = common_imports + '\n'
for func_name in transformation_functions:
    func_code = extract_function(func_name, functions[func_name])
    transformations_code += func_code + '\n\n'

# movement.py 생성
movement_functions = ['move_point_group', 'move_points']
movement_code = common_imports + '\n'
for func_name in movement_functions:
    func_code = extract_function(func_name, functions[func_name])
    movement_code += func_code + '\n\n'

# __init__.py 생성
init_code = '''"""
폴리곤 포인트 변형 및 폴리곤 모핑 모듈
모든 함수를 export
"""
from .utils import (
    _get_neighbor_points,
    _check_triangles_flipped
)
from .core import (
    morph_face_by_polygons
)
from .transformations import (
    transform_points_for_eye_size,
    transform_points_for_nose_size,
    transform_points_for_jaw,
    transform_points_for_face_size,
    transform_points_for_mouth_size,
    transform_points_for_eye_position,
    transform_points_for_lip_shape,
    transform_points_for_lip_width,
    transform_points_for_lip_vertical_move
)
from .movement import (
    move_point_group,
    move_points
)

__all__ = [
    '_get_neighbor_points',
    '_check_triangles_flipped',
    'morph_face_by_polygons',
    'transform_points_for_eye_size',
    'transform_points_for_nose_size',
    'transform_points_for_jaw',
    'transform_points_for_face_size',
    'transform_points_for_mouth_size',
    'transform_points_for_eye_position',
    'transform_points_for_lip_shape',
    'transform_points_for_lip_width',
    'transform_points_for_lip_vertical_move',
    'move_point_group',
    'move_points',
]
'''

# 파일 저장
os.makedirs('utils/face_morphing/polygon_morphing', exist_ok=True)

with open('utils/face_morphing/polygon_morphing/utils.py', 'w', encoding='utf-8') as f:
    f.write(utils_code)

with open('utils/face_morphing/polygon_morphing/core.py', 'w', encoding='utf-8') as f:
    f.write(core_code)

with open('utils/face_morphing/polygon_morphing/transformations.py', 'w', encoding='utf-8') as f:
    f.write(transformations_code)

with open('utils/face_morphing/polygon_morphing/movement.py', 'w', encoding='utf-8') as f:
    f.write(movement_code)

with open('utils/face_morphing/polygon_morphing/__init__.py', 'w', encoding='utf-8') as f:
    f.write(init_code)

print("파일 분리 완료!")
print(f"유틸리티 관련: {len(utils_functions)}개 함수")
print(f"코어 관련: {len(core_functions)}개 함수")
print(f"변환 관련: {len(transformation_functions)}개 함수")
print(f"이동 관련: {len(movement_functions)}개 함수")

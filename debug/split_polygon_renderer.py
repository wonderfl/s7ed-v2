"""
polygon_renderer.py의 메서드를 분리하여 파일로 저장하는 스크립트
"""
import re
import os

def extract_method_lines(content_lines, method_name, start_line, end_line):
    """메서드 라인 추출 (1-based line numbers)"""
    method_lines = content_lines[start_line-1:end_line]
    
    # 메서드 정의 찾기
    method_def_pattern = rf'^\s+def {method_name}\('
    method_start_idx = None
    for i, line in enumerate(method_lines):
        if re.match(method_def_pattern, line):
            method_start_idx = i
            break
    
    if method_start_idx is None:
        # 메서드 정의를 찾을 수 없으면 전체 반환
        return method_lines
    
    # 메서드 정의부터 끝까지 반환
    return method_lines[method_start_idx:]

# 파일 읽기
with open('gui/face_edit/polygon_renderer.py', 'r', encoding='utf-8') as f:
    content = f.read()
    content_lines = content.split('\n')

# 메서드 추출 (line numbers are 1-based)
methods = {
    'on_polygon_line_click': (2644, 2681),
    '_update_connected_polygons': (2871, 2911),
    '_draw_flipped_triangles': (2912, 3013),
    '_get_polygon_from_indices': (2266, 2382),
    '_build_polygon_path_from_connections': (2384, 2642),
    '_fill_polygon_area': (2683, 2871),
}

# _draw_landmark_polygons는 너무 크므로 별도 처리
draw_landmark_polygons_lines = extract_method_lines(content_lines, '_draw_landmark_polygons', 21, 2265)

# interaction.py 생성
interaction_methods = ['on_polygon_line_click', '_update_connected_polygons']
interaction_code = '''"""
폴리곤 상호작용 관련 메서드
"""
'''
for method_name in interaction_methods:
    start, end = methods[method_name]
    method_lines = extract_method_lines(content_lines, method_name, start, end)
    method_code = '\n'.join(method_lines)
    interaction_code += '\n' + method_code + '\n'

# utils.py 생성
utils_methods = ['_draw_flipped_triangles']
utils_code = '''"""
폴리곤 유틸리티 함수
"""
from ..polygon_renderer import _scipy_available, Delaunay
import numpy as np
'''
for method_name in utils_methods:
    start, end = methods[method_name]
    method_lines = extract_method_lines(content_lines, method_name, start, end)
    method_code = '\n'.join(method_lines)
    utils_code += '\n' + method_code + '\n'

# polygon_builder.py 생성
builder_methods = ['_get_polygon_from_indices', '_build_polygon_path_from_connections']
builder_code = '''"""
폴리곤 생성 관련 메서드
"""
import math
'''
for method_name in builder_methods:
    start, end = methods[method_name]
    method_lines = extract_method_lines(content_lines, method_name, start, end)
    method_code = '\n'.join(method_lines)
    builder_code += '\n' + method_code + '\n'

# drawing.py 생성 (부분적으로)
drawing_code = '''"""
폴리곤 그리기 관련 메서드
"""
import math
'''
# _draw_landmark_polygons 추가
drawing_code += '\n' + '\n'.join(draw_landmark_polygons_lines) + '\n'
# _fill_polygon_area 추가
fill_method_lines = extract_method_lines(content_lines, '_fill_polygon_area', 2683, 2871)
drawing_code += '\n' + '\n'.join(fill_method_lines) + '\n'

# 파일 저장
os.makedirs('gui/face_edit/polygon_renderer', exist_ok=True)

with open('gui/face_edit/polygon_renderer/interaction.py', 'w', encoding='utf-8') as f:
    f.write(interaction_code)

with open('gui/face_edit/polygon_renderer/utils.py', 'w', encoding='utf-8') as f:
    f.write(utils_code)

with open('gui/face_edit/polygon_renderer/polygon_builder.py', 'w', encoding='utf-8') as f:
    f.write(builder_code)

with open('gui/face_edit/polygon_renderer/drawing.py', 'w', encoding='utf-8') as f:
    f.write(drawing_code)

print("파일 분리 완료!")

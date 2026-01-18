"""
polygon_renderer.py의 메서드를 분리하는 스크립트
"""
import re

def extract_method(content, method_name, start_line, end_line):
    """메서드 추출"""
    lines = content.split('\n')
    method_lines = lines[start_line-1:end_line]
    method_code = '\n'.join(method_lines)
    
    # 메서드 정의 찾기
    method_def_match = re.search(rf'^\s+def {method_name}\(', method_code, re.MULTILINE)
    if method_def_match:
        # 메서드 정의부터 시작
        method_start = method_code.find(method_def_match.group(0))
        method_code = method_code[method_start:]
    
    return method_code

# 파일 읽기
with open('gui/face_edit/polygon_renderer.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 메서드 추출
methods = {
    'on_polygon_line_click': (2644, 2681),
    '_update_connected_polygons': (2871, 2911),
    '_draw_flipped_triangles': (2912, 3013),
    '_get_polygon_from_indices': (2266, 2382),
    '_build_polygon_path_from_connections': (2384, 2642),
    '_fill_polygon_area': (2683, 2871),
}

# 각 메서드 추출
for method_name, (start, end) in methods.items():
    method_code = extract_method(content, method_name, start, end)
    print(f"\n=== {method_name} ===")
    print(f"Lines: {start}-{end}")
    print(f"Code length: {len(method_code)}")
    print(f"First 200 chars: {method_code[:200]}")

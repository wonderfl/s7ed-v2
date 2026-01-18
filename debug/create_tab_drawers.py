"""
tab_drawers.py 생성 스크립트
각 탭별 메서드를 추출하여 tab_drawers.py에 작성
"""
import os

def create_tab_drawers():
    """tab_drawers.py 파일 생성"""
    input_file = 'gui/face_edit/polygon_renderer/drawing.py'
    
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 각 탭의 범위 정의 (1-based line number)
    tab_ranges = {
        'all': (329, 1369),      # 전체 탭
        'eye': (1370, 1618),     # 눈 탭
        'nose': (1619, 1726),    # 코 탭
        'mouth': (1727, 1839),   # 입 탭
        'eyebrow': (1840, 2005), # 눈썹 탭
        'jaw': (2006, 2165),      # 턱선 탭
        'contour': (2166, 2262)   # 윤곽 탭
    }
    
    # tab_drawers.py 내용 생성
    output_lines = []
    output_lines.append('"""\n')
    output_lines.append('탭별 폴리곤 그리기 메서드\n')
    output_lines.append('각 탭에 맞는 폴리곤 그리기 로직을 담당\n')
    output_lines.append('"""\n')
    output_lines.append('import math\n')
    output_lines.append('\n\n')
    output_lines.append('class TabDrawersMixin:\n')
    output_lines.append('    """탭별 폴리곤 그리기 기능 Mixin"""\n')
    output_lines.append('    \n')
    
    # 각 탭별 메서드 생성
    tab_methods = {
        'all': '_draw_all_tab_polygons',
        'eye': '_draw_eye_tab_polygons',
        'nose': '_draw_nose_tab_polygons',
        'mouth': '_draw_mouth_tab_polygons',
        'eyebrow': '_draw_eyebrow_tab_polygons',
        'jaw': '_draw_jaw_tab_polygons',
        'contour': '_draw_contour_tab_polygons'
    }
    
    for tab_name, (start, end) in tab_ranges.items():
        method_name = tab_methods[tab_name]
        tab_lines = lines[start-1:end]  # 0-based index
        
        # 메서드 시그니처 작성
        output_lines.append(f'    def {method_name}(self, canvas, image, landmarks, pos_x, pos_y, items_list, color, scale_x, scale_y, img_width, img_height, expansion_level, show_indices, bind_polygon_click_events):\n')
        output_lines.append(f'        """{tab_name} 탭 폴리곤 그리기"""\n')
        
        # if/elif 문 제거하고 들여쓰기 조정
        for line in tab_lines:
            stripped = line.rstrip('\n')
            if not stripped.strip():
                output_lines.append('\n')
                continue
            
            # if/elif 문 제거
            if stripped.strip().startswith('if current_tab ==') or stripped.strip().startswith('elif current_tab =='):
                # 주석만 남기거나 제거
                if '#' in stripped:
                    comment = stripped[stripped.index('#'):]
                    # 들여쓰기 조정 (12칸 -> 8칸)
                    output_lines.append('        ' + comment + '\n')
                continue
            
            # 들여쓰기 조정 (12칸 -> 8칸, 16칸 -> 12칸 등)
            # 원본 들여쓰기 레벨 확인
            indent = len(stripped) - len(stripped.lstrip())
            if indent >= 12:
                # 메서드 내부이므로 8칸 기본 + (indent - 12) 추가
                new_indent = 8 + (indent - 12)
                content = stripped.lstrip()
                output_lines.append(' ' * new_indent + content + '\n')
            else:
                # 예외 처리 (try/except 등)
                content = stripped.lstrip()
                output_lines.append('        ' + content + '\n')
        
        output_lines.append('\n\n')
    
    # 파일로 저장
    output_file = 'gui/face_edit/polygon_renderer/tab_drawers.py'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(''.join(output_lines))
    
    print(f"tab_drawers.py 생성 완료: {output_file}")

if __name__ == '__main__':
    create_tab_drawers()

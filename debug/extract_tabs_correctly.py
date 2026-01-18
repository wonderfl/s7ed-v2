"""
tab_drawers.py 정확한 추출 스크립트
원본 백업 파일에서 직접 읽어서 정확한 들여쓰기로 추출
"""
import os
import re

def extract_tabs_correctly():
    """tab_drawers.py 파일 정확하게 추출"""
    input_file = 'gui/face_edit/polygon_renderer.py.bak'
    
    if not os.path.exists(input_file):
        print(f"백업 파일이 없습니다: {input_file}")
        return
    
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 각 탭의 범위 정의 (1-based line number)
    tab_ranges = {
        'all': (329, 1369),
        'eye': (1370, 1618),
        'nose': (1619, 1726),
        'mouth': (1727, 1839),
        'eyebrow': (1840, 2005),
        'jaw': (2006, 2165),
        'contour': (2166, 2262)
    }
    
    tab_methods = {
        'all': '_draw_all_tab_polygons',
        'eye': '_draw_eye_tab_polygons',
        'nose': '_draw_nose_tab_polygons',
        'mouth': '_draw_mouth_tab_polygons',
        'eyebrow': '_draw_eyebrow_tab_polygons',
        'jaw': '_draw_jaw_tab_polygons',
        'contour': '_draw_contour_tab_polygons'
    }
    
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
    
    for tab_name, (start, end) in tab_ranges.items():
        method_name = tab_methods[tab_name]
        tab_lines = lines[start-1:end]  # 0-based index
        
        # 메서드 시그니처
        output_lines.append(f'    def {method_name}(self, canvas, image, landmarks, pos_x, pos_y, items_list, color, scale_x, scale_y, img_width, img_height, expansion_level, show_indices, bind_polygon_click_events):\n')
        output_lines.append(f'        """{tab_name} 탭 폴리곤 그리기"""\n')
        
        # 각 줄 처리
        for line in tab_lines:
            stripped = line.rstrip('\n')
            
            # if/elif current_tab == 제거
            if re.match(r'^\s*if current_tab ==', stripped) or re.match(r'^\s*elif current_tab ==', stripped):
                # 주석만 남기기
                if '#' in stripped:
                    comment = stripped[stripped.index('#'):]
                    output_lines.append('        ' + comment + '\n')
                continue
            
            # 빈 줄
            if not stripped.strip():
                output_lines.append('\n')
                continue
            
            # 들여쓰기 조정
            # 원본은 12칸 들여쓰기 (if 문 내부, 3레벨)
            # 메서드 내부는 8칸 기본 (2레벨)
            # 따라서 12칸 -> 8칸, 16칸 -> 12칸, 20칸 -> 16칸, 24칸 -> 20칸
            indent = len(stripped) - len(stripped.lstrip())
            content = stripped.lstrip()
            
            if indent >= 12:
                # 12칸(3레벨) -> 8칸(2레벨), 16칸(4레벨) -> 12칸(3레벨) 등
                # 4칸씩 줄임
                new_indent = indent - 4
                if new_indent < 8:
                    new_indent = 8
                output_lines.append(' ' * new_indent + content + '\n')
            elif indent == 0:
                # 최상위 레벨
                output_lines.append('        ' + content + '\n')
            else:
                # 그 외 (8칸 이하) - 8칸으로 통일
                output_lines.append('        ' + content + '\n')
        
        output_lines.append('\n\n')
    
    # 파일로 저장
    output_file = 'gui/face_edit/polygon_renderer/tab_drawers.py'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(''.join(output_lines))
    
    print(f"tab_drawers.py 정확한 추출 완료: {output_file}")

if __name__ == '__main__':
    extract_tabs_correctly()

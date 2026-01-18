"""
drawing.py의 탭별 if/elif 블록을 메서드 호출로 변경
"""
import re

def replace_tab_calls():
    """탭별 if/elif 블록을 메서드 호출로 변경"""
    input_file = 'gui/face_edit/polygon_renderer/drawing.py'
    
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 각 탭의 범위와 메서드명 정의 (1-based line number)
    tab_replacements = [
        (331, 1371, '_draw_all_tab_polygons', '전체'),
        (1372, 1620, '_draw_eye_tab_polygons', '눈'),
        (1621, 1728, '_draw_nose_tab_polygons', '코'),
        (1729, 1841, '_draw_mouth_tab_polygons', '입'),
        (1842, 2007, '_draw_eyebrow_tab_polygons', '눈썹'),
        (2008, 2167, '_draw_jaw_tab_polygons', '턱선'),
        (2168, 2261, '_draw_contour_tab_polygons', '윤곽')
    ]
    
    # 역순으로 처리 (인덱스 변경 방지)
    tab_replacements.reverse()
    
    new_lines = lines[:]
    
    for start, end, method_name, tab_name in tab_replacements:
        # 해당 범위의 코드를 메서드 호출로 교체
        # 메서드 호출 코드 생성
        method_call = f"""            if current_tab == '{tab_name}':
                self.{method_name}(
                    canvas, image, landmarks, pos_x, pos_y, items_list, color,
                    scale_x, scale_y, img_width, img_height, expansion_level, show_indices,
                    bind_polygon_click_events
                )
"""
        
        # 해당 범위의 줄 교체
        new_lines[start-1:end] = method_call.splitlines(True)
        # 마지막 줄에 개행 추가
        if not new_lines[start-1+len(method_call.splitlines())-1].endswith('\n'):
            new_lines[start-1+len(method_call.splitlines())-1] += '\n'
    
    # 파일로 저장
    with open(input_file, 'w', encoding='utf-8') as f:
        f.write(''.join(new_lines))
    
    print(f"탭별 메서드 호출로 변경 완료: {input_file}")

if __name__ == '__main__':
    replace_tab_calls()

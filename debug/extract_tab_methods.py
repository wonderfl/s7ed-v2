"""
탭별 메서드 추출 스크립트
"""
import os

def extract_tab_methods():
    """drawing.py에서 탭별 메서드 추출"""
    input_file = 'gui/face_edit/polygon_renderer/drawing.py'
    
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 각 탭의 범위 정의 (0-based index)
    tab_ranges = {
        'all': (328, 1368),      # 전체 탭 (329-1369줄, 0-based: 328-1368)
        'eye': (1369, 1617),      # 눈 탭 (1370-1618줄, 0-based: 1369-1617)
        'nose': (1618, 1725),     # 코 탭 (1619-1726줄, 0-based: 1618-1725)
        'mouth': (1726, 1838),    # 입 탭 (1727-1839줄, 0-based: 1726-1838)
        'eyebrow': (1839, 2004),  # 눈썹 탭 (1840-2005줄, 0-based: 1839-2004)
        'jaw': (2005, 2164),      # 턱선 탭 (2006-2165줄, 0-based: 2005-2164)
        'contour': (2165, 2261)   # 윤곽 탭 (2166-2262줄, 0-based: 2165-2261)
    }
    
    # 각 탭별 코드 추출
    for tab_name, (start, end) in tab_ranges.items():
        tab_lines = lines[start:end+1]
        
        # 들여쓰기 조정 (if/elif 문 제거하고 메서드로 변환)
        # 첫 줄의 들여쓰기 확인
        if tab_lines:
            first_line = tab_lines[0]
            # 들여쓰기 레벨 확인 (12칸 = 3레벨)
            indent_level = len(first_line) - len(first_line.lstrip())
            # 메서드로 만들기 위해 4칸 들여쓰기로 조정
            adjusted_lines = []
            for line in tab_lines:
                if line.strip():  # 빈 줄이 아니면
                    # 기존 들여쓰기 제거 후 4칸 추가
                    stripped = line.lstrip()
                    adjusted_lines.append('    ' + stripped)
                else:
                    adjusted_lines.append('')
            
            # 파일로 저장
            output_file = f'debug/tab_{tab_name}_extracted.py'
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(''.join(adjusted_lines))
            
            print(f"{tab_name} 탭: {len(tab_lines)}줄 추출 -> {output_file}")

if __name__ == '__main__':
    extract_tab_methods()

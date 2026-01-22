"""
Agent log 제거 스크립트
"""
import re
import os

files_to_clean = [
    r'd:\03.python\s7ed-v2\utils\face_morphing\integration.py',
    r'd:\03.python\s7ed-v2\utils\face_morphing\polygon_morphing\core.py',
    r'd:\03.python\s7ed-v2\gui\face_edit\__init__.py',
    r'd:\03.python\s7ed-v2\gui\face_edit\polygon_drag_handler.py',
    r'd:\03.python\s7ed-v2\gui\face_edit\polygon_renderer\all_tab_drawer.py',
    r'd:\03.python\s7ed-v2\gui\face_edit\polygon_renderer\tab_drawers.py'
]

for filepath in files_to_clean:
    if not os.path.exists(filepath):
        print(f'File not found: {filepath}')
        continue
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Remove agent log regions
        cleaned_lines = []
        in_log_region = False
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Check if this is the start of a log region
            if '# #region agent log' in line:
                in_log_region = True
                i += 1
                continue
            
            # Check if this is the end of a log region
            if '# #endregion' in line and in_log_region:
                in_log_region = False
                i += 1
                continue
            
            # Skip lines inside log region
            if in_log_region:
                i += 1
                continue
            
            # Keep non-log lines
            cleaned_lines.append(line)
            i += 1
        
        # Write cleaned content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(cleaned_lines)
        
        print(f'[OK] Cleaned: {os.path.basename(filepath)}')
        
    except Exception as e:
        print(f'[ERROR] Error cleaning {filepath}: {e}')

print('\nLog cleanup complete!')

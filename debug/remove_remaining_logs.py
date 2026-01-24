"""
Remove remaining debug print statements
"""
import re

files_to_clean = [
    r'd:\03.python\s7ed-v2\utils\face_morphing\integration.py',
    r'd:\03.python\s7ed-v2\utils\face_morphing\adjustments\eye_adjustments.py',
    r'd:\03.python\s7ed-v2\utils\face_morphing\adjustments\nose_adjustments.py',
    r'd:\03.python\s7ed-v2\utils\face_morphing\adjustments\face_adjustments.py'
]

for filepath in files_to_clean:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        cleaned_lines = []
        for line in lines:
            # Skip lines with debug print statements
            if 'print(f"[얼굴모핑]' in line:
                continue
            cleaned_lines.append(line)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(cleaned_lines)
        
        removed_count = len(lines) - len(cleaned_lines)
        filename = filepath.split('\\')[-1]
        print(f'[OK] Cleaned: {filename} - Removed {removed_count} lines')
    except Exception as e:
        print(f'[ERROR] Error cleaning {filepath}: {e}')

print('\nRemaining debug log removal complete!')

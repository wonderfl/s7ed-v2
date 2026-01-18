"""하드코딩된 눈동자 인덱스 위치 확인"""
import os
import re

# 실제 MediaPipe 정의 (확인된 값)
ACTUAL_LEFT_IRIS = [474, 475, 476, 477]
ACTUAL_RIGHT_IRIS = [469, 470, 471, 472]
ACTUAL_ALL_IRIS = sorted(ACTUAL_LEFT_IRIS + ACTUAL_RIGHT_IRIS)

# 하드코딩된 잘못된 값
WRONG_LEFT_IRIS = [468, 469, 470, 471, 472]
WRONG_RIGHT_IRIS = [473, 474, 475, 476, 477]
WRONG_ALL_IRIS = sorted(WRONG_LEFT_IRIS + WRONG_RIGHT_IRIS)

# 검색할 파일들
files_to_check = [
    "utils/face_morphing/region_extraction.py",
    "utils/face_morphing/polygon_morphing.py",
    "utils/face_morphing/adjustments.py",
    "gui/face_edit/polygon_drag_handler.py",
    "gui/face_edit/polygon_renderer.py",
    "gui/face_edit/morphing.py",
    "gui/face_edit/tab_renderer.py",
    "gui/face_edit/landmark_display.py",
]

print("=" * 80)
print("하드코딩된 잘못된 눈동자 인덱스 위치")
print("=" * 80)
print(f"\n실제 MediaPipe 정의:")
print(f"  LEFT_IRIS: {ACTUAL_LEFT_IRIS} ({len(ACTUAL_LEFT_IRIS)}개)")
print(f"  RIGHT_IRIS: {ACTUAL_RIGHT_IRIS} ({len(ACTUAL_RIGHT_IRIS)}개)")
print(f"  전체: {ACTUAL_ALL_IRIS} ({len(ACTUAL_ALL_IRIS)}개)")
print(f"\n하드코딩된 잘못된 값:")
print(f"  LEFT_IRIS: {WRONG_LEFT_IRIS} ({len(WRONG_LEFT_IRIS)}개)")
print(f"  RIGHT_IRIS: {WRONG_RIGHT_IRIS} ({len(WRONG_RIGHT_IRIS)}개)")
print(f"  전체: {WRONG_ALL_IRIS} ({len(WRONG_ALL_IRIS)}개)")
print("\n" + "=" * 80)

for file_path in files_to_check:
    if not os.path.exists(file_path):
        continue
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    found = False
    for i, line in enumerate(lines, 1):
        # 왼쪽 눈동자 하드코딩 검색
        if '[468, 469, 470, 471, 472]' in line or '468, 469, 470, 471, 472' in line:
            if not found:
                print(f"\n[{file_path}]")
                found = True
            print(f"  라인 {i}: {line.rstrip()}")
        # 오른쪽 눈동자 하드코딩 검색
        elif '[473, 474, 475, 476, 477]' in line or '473, 474, 475, 476, 477' in line:
            if not found:
                print(f"\n[{file_path}]")
                found = True
            print(f"  라인 {i}: {line.rstrip()}")
        # 전체 하드코딩 검색
        elif '[468, 469, 470, 471, 472, 473, 474, 475, 476, 477]' in line:
            if not found:
                print(f"\n[{file_path}]")
                found = True
            print(f"  라인 {i}: {line.rstrip()}")

print("\n" + "=" * 80)
print("수정 필요: 모든 폴백 값을 실제 MediaPipe 정의로 변경")
print("=" * 80)

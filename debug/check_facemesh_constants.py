"""MediaPipe Face Mesh의 모든 FACEMESH 상수 확인"""
import sys
import os

# 프로젝트 루트를 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    import mediapipe as mp
    mp_face_mesh = mp.solutions.face_mesh
    
    # FACEMESH_로 시작하는 모든 속성 찾기
    facemesh_constants = [attr for attr in dir(mp_face_mesh) if attr.startswith('FACEMESH_')]
    facemesh_constants.sort()
    
    print("="*60)
    print("MediaPipe Face Mesh FACEMESH 상수 목록")
    print("="*60)
    print(f"\n총 {len(facemesh_constants)}개 상수:\n")
    
    for i, attr in enumerate(facemesh_constants, 1):
        try:
            value = getattr(mp_face_mesh, attr)
            if hasattr(value, '__len__'):
                print(f"{i:2d}. {attr:30s} (연결 개수: {len(value)})")
            else:
                print(f"{i:2d}. {attr:30s} (값: {value})")
        except Exception as e:
            print(f"{i:2d}. {attr:30s} (오류: {e})")
    
    print("\n" + "="*60)
    print("현재 코드에서 사용 중인 부위:")
    print("="*60)
    current_regions = [
        'FACEMESH_FACE_OVAL',
        'FACEMESH_LEFT_EYE',
        'FACEMESH_RIGHT_EYE',
        'FACEMESH_LEFT_EYEBROW',
        'FACEMESH_RIGHT_EYEBROW',
        'FACEMESH_NOSE',
        'FACEMESH_LIPS',
        'FACEMESH_LEFT_IRIS',
        'FACEMESH_RIGHT_IRIS',
    ]
    
    print(f"\n현재 사용 중: {len(current_regions)}개")
    for region in current_regions:
        if region in facemesh_constants:
            print(f"  [사용중] {region}")
        else:
            print(f"  [없음]   {region}")
    
    print(f"\n사용 가능하지만 미사용: {len(facemesh_constants) - len([r for r in current_regions if r in facemesh_constants])}개")
    unused = [attr for attr in facemesh_constants if attr not in current_regions]
    for attr in unused:
        print(f"  [미사용] {attr}")
        
except ImportError:
    print("[오류] MediaPipe가 설치되어 있지 않습니다.")
    sys.exit(1)
except Exception as e:
    print(f"[오류] {e}")
    import traceback
    traceback.print_exc()

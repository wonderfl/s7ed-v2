"""MediaPipe Face Mesh 연결 정보 확인 테스트

각 부위별로 FACEMESH_* 상수의 연결 정보를 확인하고,
포함된 포인트 인덱스를 수집하여 출력합니다.
"""

import sys
import os

# 프로젝트 루트를 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    import mediapipe as mp
    mp_face_mesh = mp.solutions.face_mesh
except ImportError:
    print("[오류] MediaPipe가 설치되어 있지 않습니다.")
    sys.exit(1)

def analyze_connections(connections, name):
    """연결 정보를 분석하여 포인트 인덱스 수집"""
    print(f"\n{'='*60}")
    print(f"{name} 분석")
    print(f"{'='*60}")
    
    if not connections:
        print(f"  연결 정보 없음")
        return set()
    
    # 연결 정보 타입 확인
    print(f"  타입: {type(connections)}")
    print(f"  연결 개수: {len(connections)}")
    
    # 모든 포인트 인덱스 수집
    all_indices = set()
    for connection in connections:
        if isinstance(connection, (tuple, list)) and len(connection) == 2:
            idx1, idx2 = connection
            all_indices.add(idx1)
            all_indices.add(idx2)
        else:
            print(f"  경고: 예상치 못한 연결 형식: {connection}")
    
    # 정렬된 인덱스 리스트
    sorted_indices = sorted(all_indices)
    
    print(f"  포함된 포인트 개수: {len(all_indices)}")
    print(f"  포인트 인덱스 범위: {min(sorted_indices) if sorted_indices else 'N/A'} ~ {max(sorted_indices) if sorted_indices else 'N/A'}")
    print(f"  포인트 인덱스 목록: {sorted_indices}")
    
    # 연결 정보 샘플 출력 (처음 10개)
    print(f"  연결 정보 샘플 (처음 10개):")
    for i, conn in enumerate(list(connections)[:10]):
        print(f"    {i+1}. {conn}")
    
    if len(connections) > 10:
        print(f"    ... (총 {len(connections)}개 연결)")
    
    return all_indices

def main():
    """메인 함수"""
    print("MediaPipe Face Mesh 연결 정보 확인")
    print("="*60)
    
    # FACEMESH_TESSELATION 확인
    print(f"\n{'='*60}")
    print("FACEMESH_TESSELATION 분석")
    print(f"{'='*60}")
    tesselation_indices = analyze_connections(mp_face_mesh.FACEMESH_TESSELATION, 'FACEMESH_TESSELATION')
    
    # 각 부위별 연결 정보 확인
    parts = {
        'FACEMESH_LEFT_EYE': mp_face_mesh.FACEMESH_LEFT_EYE,
        'FACEMESH_RIGHT_EYE': mp_face_mesh.FACEMESH_RIGHT_EYE,
        'FACEMESH_LEFT_EYEBROW': mp_face_mesh.FACEMESH_LEFT_EYEBROW,
        'FACEMESH_RIGHT_EYEBROW': mp_face_mesh.FACEMESH_RIGHT_EYEBROW,
        'FACEMESH_NOSE': mp_face_mesh.FACEMESH_NOSE,
        'FACEMESH_LIPS': mp_face_mesh.FACEMESH_LIPS,
    }
    
    all_part_indices = {}
    
    for name, connections in parts.items():
        indices = analyze_connections(connections, name)
        all_part_indices[name] = indices
    
    # 전체 요약
    print(f"\n{'='*60}")
    print("전체 요약")
    print(f"{'='*60}")
    
    total_unique_indices = set()
    for name, indices in all_part_indices.items():
        total_unique_indices.update(indices)
        print(f"{name}: {len(indices)}개 포인트")
    
    print(f"\n전체 고유 포인트 개수: {len(total_unique_indices)}")
    print(f"전체 고유 포인트 인덱스 범위: {min(total_unique_indices) if total_unique_indices else 'N/A'} ~ {max(total_unique_indices) if total_unique_indices else 'N/A'}")
    
    # TESSELATION과 각 부위의 관계 확인
    print(f"\n{'='*60}")
    print("FACEMESH_TESSELATION과 각 부위의 관계")
    print(f"{'='*60}")
    for name, indices in all_part_indices.items():
        in_tesselation = indices & tesselation_indices
        not_in_tesselation = indices - tesselation_indices
        print(f"  {name}:")
        print(f"    TESSELATION에 포함: {len(in_tesselation)}/{len(indices)}개")
        if not_in_tesselation:
            print(f"    TESSELATION에 없음: {len(not_in_tesselation)}개 {sorted(list(not_in_tesselation))[:10]}{'...' if len(not_in_tesselation) > 10 else ''}")
    
    # 중복 확인
    print(f"\n{'='*60}")
    print("부위별 포인트 중복 확인")
    print(f"{'='*60}")
    
    for name1, indices1 in all_part_indices.items():
        for name2, indices2 in all_part_indices.items():
            if name1 != name2:
                overlap = indices1 & indices2
                if overlap:
                    print(f"  {name1} <-> {name2}: {len(overlap)}개 포인트 중복 {sorted(list(overlap))[:10]}{'...' if len(overlap) > 10 else ''}")
    
    # 실제 랜드마크 데이터와 매칭 확인
    print(f"\n{'='*60}")
    print("실제 랜드마크 데이터 매칭 확인")
    print(f"{'='*60}")
    
    try:
        from utils.face_landmarks import detect_face_landmarks
        
        # 테스트 이미지 찾기
        test_images = [
            'test/test_face.png',
            'test/face_000_from_kaodata.png',
            'test/face_001_from_kaodata.png',
        ]
        
        test_image_path = None
        for img_path in test_images:
            full_path = os.path.join(project_root, img_path)
            if os.path.exists(full_path):
                test_image_path = full_path
                break
        
        if test_image_path:
            from PIL import Image
            print(f"\n테스트 이미지: {test_image_path}")
            test_image = Image.open(test_image_path)
            if test_image.mode != 'RGB':
                test_image = test_image.convert('RGB')
            
            landmarks, detected = detect_face_landmarks(test_image)
            
            if detected and landmarks:
                print(f"랜드마크 감지 성공: {len(landmarks)}개 포인트")
                print(f"랜드마크 인덱스 범위: 0 ~ {len(landmarks)-1}")
                
                # 각 부위별 인덱스 유효성 확인
                print(f"\n부위별 인덱스 유효성 확인:")
                for name, indices in all_part_indices.items():
                    valid_indices = [idx for idx in indices if idx < len(landmarks)]
                    invalid_indices = [idx for idx in indices if idx >= len(landmarks)]
                    
                    print(f"  {name}:")
                    print(f"    유효한 인덱스: {len(valid_indices)}/{len(indices)}개")
                    if invalid_indices:
                        print(f"    경고: 유효하지 않은 인덱스 {len(invalid_indices)}개: {sorted(invalid_indices)[:10]}{'...' if len(invalid_indices) > 10 else ''}")
                    else:
                        print(f"    모든 인덱스 유효")
            else:
                print("랜드마크 감지 실패 (이미지에서 얼굴을 찾지 못함)")
        else:
            print("테스트 이미지를 찾을 수 없습니다.")
            print("다음 경로를 확인했습니다:")
            for img_path in test_images:
                print(f"  - {img_path}")
    except Exception as e:
        print(f"랜드마크 매칭 확인 중 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

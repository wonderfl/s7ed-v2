"""MediaPipe 눈동자 인덱스 + 중심점 확인"""
try:
    import mediapipe as mp
    mp_face_mesh = mp.solutions.face_mesh
    
    # 전체 랜드마크 개수 확인
    print("=" * 80)
    print("MediaPipe Face Mesh 랜드마크 정보:")
    print("=" * 80)
    print(f"기본 랜드마크: 468개")
    print(f"refine_landmarks=True일 때: 468 + 10 = 478개")
    print(f"  - 왼쪽 눈동자: 468(중심) + 474,475,476,477(contour) = 5개")
    print(f"  - 오른쪽 눈동자: 473(중심) + 469,470,471,472(contour) = 5개")
    
    # FACEMESH 연결 확인
    LEFT_IRIS = list(mp_face_mesh.FACEMESH_LEFT_IRIS)
    RIGHT_IRIS = list(mp_face_mesh.FACEMESH_RIGHT_IRIS)
    
    left_set = set()
    for a, b in LEFT_IRIS:
        left_set.add(a)
        left_set.add(b)
    
    right_set = set()
    for a, b in RIGHT_IRIS:
        right_set.add(a)
        right_set.add(b)
    
    print("\n" + "=" * 80)
    print("FACEMESH_LEFT_IRIS 연결 (contour만):")
    print("=" * 80)
    print(f"  인덱스: {sorted(left_set)} ({len(left_set)}개)")
    print(f"  중심점 468은 연결에 포함되지 않음")
    
    print("\n" + "=" * 80)
    print("FACEMESH_RIGHT_IRIS 연결 (contour만):")
    print("=" * 80)
    print(f"  인덱스: {sorted(right_set)} ({len(right_set)}개)")
    print(f"  중심점 473은 연결에 포함되지 않음")
    
    print("\n" + "=" * 80)
    print("결론:")
    print("=" * 80)
    print("  - contour 인덱스: {sorted(left_set | right_set)} (8개)")
    print("  - 중심점 인덱스: 468(왼쪽), 473(오른쪽) (2개)")
    print("  - 전체 iris 인덱스: 468, 469, 470, 471, 472, 473, 474, 475, 476, 477 (10개)")
    print("\n  현재 코드는 contour 8개만 제거하고 중심점을 계산해서 추가하고 있음")
    print("  하지만 중심점 인덱스(468, 473)가 이미 있으므로 계산할 필요 없음!")
    print("  -> contour 8개 제거하고, 중심점 2개(468, 473)는 그대로 사용하면 됨")
    
except Exception as e:
    print(f"에러: {e}")
    import traceback
    traceback.print_exc()
